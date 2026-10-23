# -*- coding: utf-8 -*-
"""143회차: 공식 OBS 미터 이벤트 구독 완료 뒤에만 단일 질문 전송.

가상 OBS와 가상 공식 응답의 계약검사다. 실제 OBS/음성/시청자 검증이 아니다.
"""
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster import original_plan_full_pipeline as pipeline
from ai_broadcaster.original_plan_obs import OfficialObsWebsocket


class 구독완료가상OBS:
    준비됨 = threading.Event()

    def __init__(self, password, *, port=4455):
        self._client = self

    def connect(self):
        return SimpleNamespace(streaming=False, scene="기존장면")

    def status(self):
        return SimpleNamespace(streaming=False, scene="기존장면")

    def get_record_status(self):
        return SimpleNamespace(output_active=False)

    def read_program_audio_route(self, *, input_name, scene):
        return SimpleNamespace(confirmed=True)

    def inspect_program_media_with_meter_ready(
        self, *, ready_action, operator_approved, input_name,
        duration, observe_program_motion,
    ):
        # 실제 구현의 미터 이벤트 등록 완료 콜백을 모의한다.
        time.sleep(0.02)
        type(self).준비됨.set()
        ready_action()
        time.sleep(0.05)
        return SimpleNamespace(
            coherent_media_candidate=False,
            program_video_change_candidate=False,
            audio=SimpleNamespace(
                first_selected_signal_monotonic=None,
                last_selected_signal_monotonic=None),
        )


class 구독실패가상OBS(구독완료가상OBS):
    def inspect_program_media_with_meter_ready(self, **kwargs):
        raise RuntimeError("가상 미터 이벤트 구독 실패")


class 공식미터구독준비검사(unittest.TestCase):
    def setUp(self):
        구독완료가상OBS.준비됨.clear()

    def test_미터구독준비_이전에는_질문을_전송하지_않는다(self):
        sent = []
        def send(text, *, operator_approved, duration):
            self.assertTrue(구독완료가상OBS.준비됨.is_set())
            sent.append(text)
            return SimpleNamespace(
                verified_signal=False,
                first_audio_mouth_monotonic=0.0,
                last_audio_mouth_monotonic=0.0)
        with patch.object(pipeline, "OfficialObsWebsocket", 구독완료가상OBS), \
             patch.object(pipeline, "send_to_native_live2d_session_with_observation", send):
            evidence = pipeline.verify_official_chat_live2d_obs(
                "승인된 가상 질문", obs_password="가상암호",
                obs_input_name="기존입력", duration=1,
                operator_approved=True, voice_rights_confirmed=True)
        self.assertEqual(sent, ["승인된 가상 질문"])
        self.assertFalse(evidence.verified_observation)

    def test_미터구독실패면_질문은_전송하지_않는다(self):
        sent = []
        def send(*args, **kwargs):
            sent.append(args)
            raise AssertionError("미터 준비 실패 후 전송 금지")
        with patch.object(pipeline, "OfficialObsWebsocket", 구독실패가상OBS), \
             patch.object(pipeline, "send_to_native_live2d_session_with_observation", send):
            with self.assertRaisesRegex(RuntimeError, "질문 미전송"):
                pipeline.verify_official_chat_live2d_obs(
                    "승인된 가상 질문", obs_password="가상암호",
                    obs_input_name="기존입력", duration=1,
                    operator_approved=True, voice_rights_confirmed=True)
        self.assertEqual(sent, [])

    def test_실제OBS_준비메서드는_미터구독콜백을_전달한다(self):
        ready = []
        def fake_inspect(self, **kwargs):
            ready.append("메서드")
            kwargs["meter_ready_action"]()
            return "가상관찰"
        with patch.object(OfficialObsWebsocket, "inspect_program_media", fake_inspect):
            instance = object.__new__(OfficialObsWebsocket)
            result = instance.inspect_program_media_with_meter_ready(
                ready_action=lambda: ready.append("구독"),
                operator_approved=True, input_name="기존입력",
                duration=1, observe_program_motion=True)
        self.assertEqual(result, "가상관찰")
        self.assertEqual(ready, ["메서드", "구독"])


if __name__ == "__main__":
    unittest.main()
