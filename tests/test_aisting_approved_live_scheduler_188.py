"""188절: 승인형 Windows 주간 실제 OBS 자동 방송/채팅/공지의 계약검사.

이 파일은 전체 기능 개발 이후 검사 단계에서 실행하도록 작성한다.
가상 OBS와 단조 시계로 제어 계약만 정의하며 실제 송출/수백명/24시간
실증, 화면·오디오·시청자 응답 성공을 뜻하지 않는다.
"""
from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from ai_broadcaster.approved_live_scheduler import ApprovedLiveScheduler
from ai_broadcaster.offline_broadcast_schedule import (
    BroadcastScheduleDraft, WeeklyStartSlot, KST)
from ai_broadcaster.offline_broadcast_duration import BroadcastDurationRules


class FakeOwnerObs:
    starts = 0
    stops = 0
    already_streaming = False
    wrong_scene = False

    def __init__(self, password, *, port):
        assert password == "운영자 테스트 전용"
        assert port == 4455
        self._client = SimpleNamespace(
            get_record_status=lambda: SimpleNamespace(output_active=False),
            disconnect=lambda: None)
        self.streaming = self.already_streaming
        self.scene = "방송 장면"

    def connect(self):
        return self.status()

    def status(self):
        return SimpleNamespace(
            scene=("외부 장면" if self.wrong_scene else self.scene),
            streaming=self.streaming)

    def read_scene_media_path(self):
        return SimpleNamespace(
            problems=(), audio_sources=("한국어 음성 입력",),
            capture_sources=(
                "실제 버추얼창 (window_capture, 활성) / 선택된 창 "
                "AISTING | 공식 Live2D 및 AI 대화:WebView2",))

    def start_stream(self, *, operator_confirmed=False):
        assert operator_confirmed is True
        self.streaming = True
        type(self).starts += 1
        return self.status()

    def stop_stream(self, *, operator_confirmed=False):
        assert operator_confirmed is True
        self.streaming = False
        type(self).stops += 1
        return self.status()


class ApprovedLiveSchedulerContracts188(unittest.TestCase):
    def setUp(self):
        FakeOwnerObs.starts = 0
        FakeOwnerObs.stops = 0
        FakeOwnerObs.already_streaming = False
        FakeOwnerObs.wrong_scene = False
        self.env = patch.dict(os.environ, {"AISTING_APPROVED_OBS_OUTGOING": "YES"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.calls = []
        self.start = datetime(2026, 10, 26, 10, 30, tzinfo=KST)  # Monday
        self.second = datetime(2026, 10, 26, 10, 35, tzinfo=KST)

    def controller(self, **kwargs):
        draft = BroadcastScheduleDraft((
            WeeklyStartSlot(0, "10:30"),
            WeeklyStartSlot(0, "10:35")))
        opts = dict(
            obs_password="운영자 테스트 전용", obs_port=4455,
            scene="방송 장면", closing_text="운영자 지정 인사",
            operator_approved=True, rights_confirmed=True,
            media_preflight=lambda: True,
            deliver_closing=lambda msg: self.calls.append(("close", msg)) or True,
            client_factory=FakeOwnerObs)
        opts.update(kwargs)
        return ApprovedLiveScheduler(
            draft, BroadcastDurationRules(1, 1), **opts)

    def test_권한이나_기존OBS_환경게이트_없으면_실제시작금지(self):
        with self.assertRaises(PermissionError):
            self.controller(operator_approved=False)
        with patch.dict(os.environ, {"AISTING_APPROVED_OBS_OUTGOING": "NO"}):
            with self.assertRaises(PermissionError):
                self.controller()
        self.assertEqual(FakeOwnerObs.starts, 0)

    def test_첫방송_종료후_다음주간슬롯도_별도시작(self):
        runner = self.controller()
        self.assertFalse(runner.tick(
            self.start - timedelta(minutes=1), 90).owns_stream)
        first = runner.tick(self.start, 100)
        self.assertTrue(first.owns_stream)
        self.assertTrue(first.start_confirmed)
        self.assertEqual(FakeOwnerObs.starts, 1)
        self.assertEqual(runner.tick(self.start, 100.5).state, "실제 방송 중")
        self.assertEqual(FakeOwnerObs.starts, 1)
        ended = runner.tick(self.start + timedelta(seconds=61), 161)
        self.assertTrue(ended.stop_confirmed)
        self.assertFalse(ended.owns_stream)
        self.assertEqual(ended.state, "예약 승인됨")
        self.assertEqual(FakeOwnerObs.stops, 1)
        second = runner.tick(self.second, 400)
        self.assertTrue(second.owns_stream)
        self.assertEqual(FakeOwnerObs.starts, 2)
        runner.request_stop()
        runner.tick(self.second + timedelta(seconds=1), 401)
        self.assertEqual(FakeOwnerObs.stops, 2)

    def test_승인된_AI채팅은_각방송의_시작과_종료에만_호출(self):
        def start():
            self.calls.append(("chat_start", 1))
            return True
        def stop():
            self.calls.append(("chat_stop", 1))
            return True
        runner = self.controller(
            begin_live_chat=start, end_live_chat=stop, chat_approved=True)
        runner.tick(self.start, 100)
        runner.tick(self.start + timedelta(seconds=65), 165)
        runner.tick(self.second, 400)
        runner.request_stop()
        runner.tick(self.second, 401)
        self.assertEqual([name for name, _ in self.calls].count("chat_start"), 2)
        self.assertEqual([name for name, _ in self.calls].count("chat_stop"), 2)
        self.assertEqual(FakeOwnerObs.stops, 2)

    def test_승인안된_채팅이나_공지자동시작은_불가(self):
        with self.assertRaises(PermissionError):
            self.controller(
                begin_live_chat=lambda: True,
                end_live_chat=lambda: True, chat_approved=False)
        with self.assertRaises(PermissionError):
            self.controller(on_started_notice=lambda _occur: True)
        self.assertEqual(FakeOwnerObs.starts, 0)

    def test_다른_사람이_이미_송출중인_OBS는_건드리지않음(self):
        FakeOwnerObs.already_streaming = True
        runner = self.controller()
        result = runner.tick(self.start, 100)
        self.assertEqual(result.state, "시작 확인 실패")
        self.assertFalse(result.owns_stream)
        self.assertEqual(FakeOwnerObs.starts, 0)
        self.assertEqual(FakeOwnerObs.stops, 0)

    def test_실제_시작종료가_확인된경우에만_별도공지(self):
        runner = self.controller(
            on_started_notice=lambda _: self.calls.append(("notice_start", 1)) or True,
            on_finished_notice=lambda _: self.calls.append(("notice_end", 1)) or True,
            notice_approved=True)
        start = runner.tick(self.start, 100)
        self.assertEqual(start.start_notice, "서버 204 확인")
        self.assertEqual(start.end_notice, "대기")
        ended = runner.tick(self.start + timedelta(seconds=61), 161)
        self.assertEqual(ended.end_notice, "서버 204 확인")
        self.assertEqual([name for name, _ in self.calls].count("notice_start"), 1)
        self.assertEqual([name for name, _ in self.calls].count("notice_end"), 1)


if __name__ == "__main__":
    unittest.main()
