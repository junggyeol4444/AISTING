# -*- coding: utf-8 -*-
"""164회차: 실제 수신기 콜백의 로컬 정산 계약. 외부 접속/송출 없음."""
import sys
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession
from ai_broadcaster.multiplatform_readonly import PlatformChat


class _가상수신기:
    def __init__(self, channel, emit, *args, **kwargs):
        self.emit = emit

    def stop(self):
        pass

    def run(self, *, max_seconds=None):
        pass


class 수신콜백정산검사(unittest.TestCase):
    def _세션(self, channels, emit):
        stack = ExitStack()
        for name in ("TwitchReadOnlySession", "ChzzkReadOnlySession",
                     "SoopReadOnlySession", "YouTubeReadOnlySession"):
            stack.enter_context(patch(
                "ai_broadcaster.multi_platform_session." + name, _가상수신기))
        self.addCleanup(stack.close)
        return MultiPlatformReadOnlySession(
            channels, emit, youtube_api_key="k" * 39)

    def test_4플랫폼_500건_로컬콜백_정산_일치(self):
        seen = []
        channels = {code: code for code in
                    ("twitch", "chzzk", "soop", "youtube")}
        session = self._세션(channels, lambda kind, item: seen.append(item) or True)
        for code in channels:
            for index in range(125):
                self.assertTrue(session._callbacks[code](
                    "chat", PlatformChat(code, "시청자", "동일 문장", code,
                                         f"{code}-{index}")))
        self.assertEqual(len(seen), 500)
        for code, stats in session.reconnect_snapshot().items():
            self.assertEqual(stats["콜백수신"], 125, code)
            self.assertEqual(stats["콜백전달완료"], 125, code)
            self.assertEqual(stats["콜백정산차이"], 0, code)
            self.assertEqual(stats["콜백내부중복ID"], 0, code)

    def test_같은서버ID_재수신과_유튜브내부재생은_별개(self):
        seen = []
        session = self._세션({"youtube": "livechat"},
                            lambda kind, item: seen.append(item) or True)
        cb = session._callbacks["youtube"]
        chat = PlatformChat("livechat", "시청자", "반복 문장", "youtube", "evt-1")
        self.assertTrue(cb("chat", chat))
        self.assertTrue(cb("chat", chat))
        cb("server_replay", None)
        stats = session.reconnect_snapshot()["youtube"]
        self.assertEqual(len(seen), 1)
        self.assertEqual(stats["콜백수신"], 2)
        self.assertEqual(stats["콜백내부중복ID"], 1)
        self.assertEqual(stats["서버이벤트ID재수신차단"], 2)
        self.assertEqual(stats["콜백정산차이"], 0)

    def test_진행중콜백은_정산확정하지_않음(self):
        entered, release = threading.Event(), threading.Event()
        def emit(kind, item):
            entered.set()
            if not release.wait(2):
                raise TimeoutError("가상 콜백 대기 시간 초과")
            return True
        session = self._세션({"chzzk": "channel"}, emit)
        worker = threading.Thread(target=lambda: session._callbacks["chzzk"](
            "chat", PlatformChat("channel", "시청자", "안녕", "chzzk")))
        worker.start()
        try:
            self.assertTrue(entered.wait(1))
            pending = session.reconnect_snapshot()["chzzk"]
            self.assertTrue(pending["콜백전달진행중"])
            self.assertIsNone(pending["콜백정산차이"])
        finally:
            release.set()
            worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(session.reconnect_snapshot()["chzzk"]["콜백정산차이"], 0)

    def test_거절과_예외도_정산하며_성공으로_속이지_않음(self):
        session = self._세션({"soop": "channel"}, lambda *_: False)
        chat = PlatformChat("channel", "시청자", "질문", "soop")
        self.assertFalse(session._callbacks["soop"]("chat", chat))
        stats = session.reconnect_snapshot()["soop"]
        self.assertEqual(stats["콜백전달완료"], 0)
        self.assertEqual(stats["콜백전달중단"], 1)
        self.assertEqual(stats["콜백정산차이"], 0)
        def broken(*_):
            raise RuntimeError("가상 GUI 전달 실패")
        session._emit = broken
        with self.assertRaises(RuntimeError):
            session._callbacks["soop"]("chat", chat)
        stats = session.reconnect_snapshot()["soop"]
        self.assertEqual(stats["콜백전달오류"], 1)
        self.assertEqual(stats["콜백정산차이"], 0)

    def test_운영자중지후_늦은채팅은_거절로_별도기록(self):
        session = self._세션({"twitch": "channel"}, lambda *_: True)
        session.stop()
        self.assertFalse(session._callbacks["twitch"](
            "chat", PlatformChat("channel", "시청자", "늦은 질문", "twitch")))
        stats = session.reconnect_snapshot()["twitch"]
        self.assertEqual(stats["중지후채팅거절"], 1)
        self.assertEqual(stats["콜백전달완료"], 0)
        self.assertEqual(stats["콜백수신"], 0)
        self.assertEqual(stats["콜백정산차이"], 0)


if __name__ == "__main__":
    unittest.main()
