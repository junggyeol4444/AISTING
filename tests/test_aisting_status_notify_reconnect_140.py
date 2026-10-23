# -*- coding: utf-8 -*-
"""140회차: 상태 알림 GUI 예외와 채팅 수신·재연결의 격리 계약 검사.

외부 플랫폼·계정·OBS·방송·실제 모델은 실행하지 않는다.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster import multi_platform_session as module
from ai_broadcaster.multiplatform_readonly import PlatformChat


class 가상수신기:
    생성횟수 = 0

    def __init__(self, channel, callback, *args, **kwargs):
        type(self).생성횟수 += 1
        self.번호 = type(self).생성횟수
        self.callback = callback
        self._terminal_chat_end = False

    def run(self, *, max_seconds=None):
        if self.번호 == 1:
            raise ConnectionError("내부_연결_실패_본문_비공개")
        self.callback("ready", "채널")
        self.callback("chat", PlatformChat("채널", "시청자", "질문", "twitch", "사건1"))
        self.callback("error", "비공개_오류")
        self._terminal_chat_end = True

    def stop(self):
        pass


class 상태알림과재연결격리검사(unittest.TestCase):
    def test_상태알림이_실패해도_재연결후_채팅을_전달(self):
        가상수신기.생성횟수 = 0
        delivered = []

        def emit(kind, value):
            if kind == "chat":
                delivered.append(value.text)
                return True
            raise RuntimeError("GUI_알림_실패_본문_비공개")

        with patch.object(module, "TwitchReadOnlySession", 가상수신기):
            session = module.MultiPlatformReadOnlySession({"twitch": "채널"}, emit)
            session.run()
        state = session.reconnect_snapshot()["twitch"]
        self.assertEqual(delivered, ["질문"])
        self.assertEqual(state["실제읽기시도"], 2)
        self.assertEqual(state["실제읽기실패"], 1)
        self.assertEqual(state["콜백전달완료"], 1)
        self.assertGreaterEqual(state["상태알림전달실패"], 4)
        self.assertNotIn("비공개", str(state))

    def test_준비완료_알림_실패는_입장상태를_되돌리지않음(self):
        with patch.object(module, "TwitchReadOnlySession", 가상수신기):
            session = module.MultiPlatformReadOnlySession(
                {"twitch": "채널"}, lambda *_: (_ for _ in ()).throw(ValueError("GUI")))
        session._callbacks["twitch"]("ready", "채널")
        state = session.reconnect_snapshot()["twitch"]
        self.assertTrue(state["채팅방입장"])
        self.assertEqual(state["상태알림전달실패"], 1)

    def test_채팅_전달_실패는_안전알림으로_숨기지않음(self):
        with patch.object(module, "TwitchReadOnlySession", 가상수신기):
            session = module.MultiPlatformReadOnlySession(
                {"twitch": "채널"}, lambda *_: (_ for _ in ()).throw(ValueError("전달거절")))
        with self.assertRaises(ValueError):
            session._callbacks["twitch"](
                "chat", PlatformChat("채널", "시청자", "질문", "twitch", "사건2"))
        state = session.reconnect_snapshot()["twitch"]
        self.assertEqual(state["콜백전달오류"], 1)
        self.assertEqual(state["콜백전달완료"], 0)
        self.assertEqual(state["상태알림전달실패"], 0)

    def test_플랫폼별_상태알림_실패는_다른플랫폼을_막지않음(self):
        delivered = []
        def emit(kind, value):
            if kind == "chat":
                delivered.append(value.platform)
                return True
            raise RuntimeError("상태창_닫힘")
        with patch.object(module, "TwitchReadOnlySession", 가상수신기), \
             patch.object(module, "SoopReadOnlySession", 가상수신기):
            session = module.MultiPlatformReadOnlySession(
                {"twitch": "채널", "soop": "채널2"}, emit)
        session._callbacks["twitch"]("error", "연결오류")
        self.assertTrue(session._callbacks["soop"](
            "chat", PlatformChat("채널2", "시청자", "질문", "soop", "사건3")))
        state = session.reconnect_snapshot()
        self.assertEqual(delivered, ["soop"])
        self.assertEqual(state["twitch"]["상태알림전달실패"], 1)
        self.assertEqual(state["soop"]["상태알림전달실패"], 0)


if __name__ == "__main__":
    unittest.main()
