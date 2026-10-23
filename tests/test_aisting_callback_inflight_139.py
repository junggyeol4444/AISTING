# -*- coding: utf-8 -*-
"""139회차: 실제 콜백 진행 중 병목과 Stop 시각 동결의 로컬 계약 검사.

가상 수신기만 사용하며 실제 플랫폼 로그인·발신·OBS·모델·방송은 실행하지 않는다.
"""
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster import multi_platform_session as module
from ai_broadcaster.multiplatform_readonly import PlatformChat


class 가상수신기:
    def __init__(self, channel, callback, *args, **kwargs):
        self.callback = callback
    def run(self, *, max_seconds=None):
        pass
    def stop(self):
        pass


class 콜백진행병목검사(unittest.TestCase):
    def setUp(self):
        self.patchers = [
            patch.object(module, name, 가상수신기)
            for name in ("TwitchReadOnlySession", "ChzzkReadOnlySession",
                         "SoopReadOnlySession", "YouTubeReadOnlySession")
        ]
        for item in self.patchers:
            item.start()
            self.addCleanup(item.stop)

    def test_진행중_콜백은_완료_p95와_별개로_표시(self):
        entered, release = threading.Event(), threading.Event()
        def emit(kind, value):
            if kind == "chat":
                entered.set()
                self.assertTrue(release.wait(3))
            return True
        session = module.MultiPlatformReadOnlySession({"twitch": "채널"}, emit)
        message = PlatformChat("채널", "시청자", "질문", "twitch")
        worker = threading.Thread(target=session._callbacks["twitch"],
                                  args=("chat", message), daemon=True)
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            time.sleep(0.02)
            state = session.reconnect_snapshot()["twitch"]
            self.assertTrue(state["콜백전달진행중"])
            self.assertGreater(state["콜백전달진행초"], 0)
            self.assertEqual(state["콜백소요최근표본"], 0)
            self.assertEqual(state["콜백전달완료"], 0)
        finally:
            release.set()
            worker.join(3)
        self.assertFalse(worker.is_alive())
        state = session.reconnect_snapshot()["twitch"]
        self.assertFalse(state["콜백전달진행중"])
        self.assertIsNone(state["콜백전달진행초"])
        self.assertEqual(state["콜백소요최근표본"], 1)
        self.assertEqual(state["콜백전달완료"], 1)

    def test_콜백_예외에서도_진행상태_정리(self):
        def emit(kind, value):
            raise RuntimeError("PRIVATE_DO_NOT_LOG")
        session = module.MultiPlatformReadOnlySession({"chzzk": "채널"}, emit)
        with self.assertRaises(RuntimeError):
            session._callbacks["chzzk"](
                "chat", PlatformChat("채널", "시청자", "질문", "chzzk"))
        state = session.reconnect_snapshot()["chzzk"]
        self.assertFalse(state["콜백전달진행중"])
        self.assertEqual(state["콜백전달오류"], 1)
        self.assertEqual(state["콜백소요최근표본"], 1)
        self.assertNotIn("PRIVATE_DO_NOT_LOG", str(state))

    def test_한플랫폼_콜백대기중_다른플랫폼은_계속전달(self):
        entered, release = threading.Event(), threading.Event()
        events = []
        def emit(kind, value):
            if kind == "chat":
                if value.platform == "twitch":
                    entered.set()
                    self.assertTrue(release.wait(3))
                events.append(value.platform)
            return True
        session = module.MultiPlatformReadOnlySession(
            {"twitch": "방1", "soop": "방2"}, emit)
        worker = threading.Thread(
            target=session._callbacks["twitch"],
            args=("chat", PlatformChat("방1", "A", "첫째", "twitch")),
            daemon=True)
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            self.assertTrue(session._callbacks["soop"](
                "chat", PlatformChat("방2", "B", "둘째", "soop")))
            state = session.reconnect_snapshot()
            self.assertTrue(state["twitch"]["콜백전달진행중"])
            self.assertFalse(state["soop"]["콜백전달진행중"])
            self.assertEqual(state["soop"]["콜백전달완료"], 1)
        finally:
            release.set()
            worker.join(3)
        self.assertEqual(events, ["soop", "twitch"])

    def test_Stop_뒤_경과시간은_증가하지않음(self):
        session = module.MultiPlatformReadOnlySession({"youtube": "채널"}, lambda *_: True)
        now = time.monotonic()
        session._session_started_at = now - 20
        session._last_chat_at["youtube"] = now - 10
        session._last_transport_activity_at["youtube"] = now - 8
        session._last_reader_failure_at["youtube"] = now - 5
        session.stop()
        before = session.reconnect_snapshot()["youtube"]
        time.sleep(0.02)
        after = session.reconnect_snapshot()["youtube"]
        for key in ("마지막채팅콜백경과초", "마지막통신응답경과초",
                    "마지막읽기실패경과초", "관측입장시간비율"):
            self.assertEqual(before[key], after[key], key)
        self.assertFalse(after["채팅방입장"])


if __name__ == "__main__":
    unittest.main()
