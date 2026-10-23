# -*- coding: utf-8 -*-
"""AISTING 134회차: 실제 수신 콜백→GUI/AI FIFO 구간의 소요시간 계측.

외부 네트워크·모델·방송을 실행하지 않는 단위 검사이며, 실제 시청자
1~3초 종단간 응답 달성 또는 4플랫폼 무누락의 증거로 사용하지 않는다.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession
from ai_broadcaster.twitch_readonly import TwitchChatLine


class 플랫폼별실제콜백소요시간검사(unittest.TestCase):
    def test_실제콜백소요시간_p95_3초초과_별도기록(self):
        clock = [100.0]
        def emit(kind, item):
            clock[0] += 3.25
            return True
        with patch("ai_broadcaster.multi_platform_session.time.monotonic",
                   side_effect=lambda: clock[0]):
            session = MultiPlatformReadOnlySession({"twitch": "sample"}, emit)
            self.assertTrue(session._callbacks["twitch"](
                "chat", TwitchChatLine("sample", "시청자", "본문", "서버1")))
            state = session.reconnect_snapshot()["twitch"]
        self.assertEqual(state["콜백전달완료"], 1)
        self.assertEqual(state["콜백소요최근표본"], 1)
        self.assertEqual(state["콜백소요최근p95초"], 3.25)
        self.assertEqual(state["콜백소요3초초과"], 1)

    def test_거절된콜백_성공으로_위장하지않고_시간은계측(self):
        clock = [200.0]
        def emit(kind, item):
            clock[0] += 4.0
            return False
        with patch("ai_broadcaster.multi_platform_session.time.monotonic",
                   side_effect=lambda: clock[0]):
            session = MultiPlatformReadOnlySession({"twitch": "sample"}, emit)
            self.assertFalse(session._callbacks["twitch"](
                "chat", TwitchChatLine("sample", "시청자", "본문", "서버2")))
            state = session.reconnect_snapshot()["twitch"]
        self.assertEqual(state["콜백전달완료"], 0)
        self.assertEqual(state["콜백전달중단"], 1)
        self.assertEqual(state["콜백소요최근p95초"], 4.0)
        self.assertEqual(state["콜백소요3초초과"], 1)

    def test_중복서버이벤트는_실제콜백호출과_측정에서제외(self):
        clock = [300.0]
        def emit(kind, item):
            clock[0] += 0.1
            return True
        with patch("ai_broadcaster.multi_platform_session.time.monotonic",
                   side_effect=lambda: clock[0]):
            session = MultiPlatformReadOnlySession({"twitch": "sample"}, emit)
            chat = TwitchChatLine("sample", "시청자", "동일 사건", "서버3")
            self.assertTrue(session._callbacks["twitch"]("chat", chat))
            self.assertTrue(session._callbacks["twitch"]("chat", chat))
            state = session.reconnect_snapshot()["twitch"]
        self.assertEqual(state["콜백수신"], 2)
        self.assertEqual(state["서버이벤트ID재수신차단"], 1)
        self.assertEqual(state["콜백전달완료"], 1)
        self.assertEqual(state["콜백소요최근표본"], 1)

    def test_장시간수신_최근512건만_유지하고_전체계수는보존(self):
        clock = [400.0]
        def emit(kind, item):
            clock[0] += 0.005
            return True
        with patch("ai_broadcaster.multi_platform_session.time.monotonic",
                   side_effect=lambda: clock[0]):
            session = MultiPlatformReadOnlySession({"twitch": "sample"}, emit)
            for index in range(530):
                self.assertTrue(session._callbacks["twitch"](
                    "chat", TwitchChatLine("sample", "시청자", "본문", str(index))))
            state = session.reconnect_snapshot()["twitch"]
        self.assertEqual(state["콜백전달완료"], 530)
        self.assertEqual(state["콜백소요최근표본"], 512)
        self.assertEqual(state["콜백소요3초초과"], 0)
        self.assertAlmostEqual(state["콜백소요최근p95초"], 0.005, places=6)


if __name__ == "__main__":
    unittest.main()
