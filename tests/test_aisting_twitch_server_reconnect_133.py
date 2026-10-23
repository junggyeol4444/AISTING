"""AISTING 131~133회차 Twitch 서버 RECONNECT 개발 회귀.

모든 수신기와 소켓은 테스트 대역이며 외부 네트워크/계정/채팅 발신은 없다.
이 테스트 통과는 실제 Twitch 무누락·24시간 운용 실증이 아니다.
"""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_broadcaster.twitch_readonly import (
    TwitchChatLine, TwitchReadOnlySession, TwitchReadError, TwitchServerReconnect,
)
from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession


class _가짜소켓:
    def __init__(self, frames):
        self.frames = iter(frames)
        self.closed = False
        self.sent = []

    def send(self, data):
        self.sent.append(data)

    def settimeout(self, seconds):
        pass

    def recv(self):
        return next(self.frames)

    def close(self):
        self.closed = True


class Twitch서버재연결검사(unittest.TestCase):
    def _프레임실행(self, frames):
        sock = _가짜소켓(frames)
        events = []
        fake_ws = types.SimpleNamespace(
            create_connection=lambda *_a, **_kw: sock,
            WebSocketTimeoutException=TimeoutError,
        )
        session = TwitchReadOnlySession(
            "sample", lambda kind, item: events.append((kind, item)) or True
        )
        with patch.dict(sys.modules, {"websocket": fake_ws}):
            with self.assertRaises(TwitchServerReconnect):
                session.run(max_seconds=5)
        return events, sock

    def test_명령앞뒤동일프레임채팅보존(self):
        events, sock = self._프레임실행([
            ":tmi.twitch.tv 366 guest #sample :End of NAMES\r\n"
            "@id=one :first!u@host PRIVMSG #sample :첫 채팅\r\n"
            ":tmi.twitch.tv RECONNECT\r\n"
            "@id=two :second!u@host PRIVMSG #sample :두 번째 채팅\r\n"
        ])
        chats = [value for kind, value in events if kind == "chat"]
        self.assertEqual([x.text for x in chats], ["첫 채팅", "두 번째 채팅"])
        self.assertEqual([x.event_id for x in chats], ["one", "two"])
        self.assertTrue(sock.closed)
        self.assertEqual(events[-1][0], "stopped")

    def test_분할된서버명령(self):
        events, sock = self._프레임실행([
            ":tmi.twitch.tv 366 guest #sample :End of NAMES\r\n"
            "@id=first :first!u@host PRIVMSG #sample :메시지\r\n"
            ":tmi.twitch.tv RECO",
            "NNECT\r\n",
        ])
        self.assertEqual([v.text for k, v in events if k == "chat"], ["메시지"])
        self.assertTrue(sock.closed)

    def test_시청자본문은명령아님(self):
        events, _ = self._프레임실행([
            ":tmi.twitch.tv 366 guest #sample :End of NAMES\r\n"
            "@id=normal :first!u@host PRIVMSG #sample :RECONNECT\r\n"
            ":tmi.twitch.tv RECONNECT\r\n",
        ])
        self.assertEqual([v.text for k, v in events if k == "chat"], ["RECONNECT"])

    def test_서버명령은일반수신오류의하위유형(self):
        self.assertTrue(issubclass(TwitchServerReconnect, TwitchReadError))


class 다중수신기재연결검사(unittest.TestCase):
    def test_서버명령후즉시새수신기와이벤트ID보존(self):
        created = []
        events = []
        owner = {}

        class 가짜수신기:
            def __init__(self, channel, callback):
                self.channel = channel
                self.callback = callback
                self.index = len(created)
                self.stopped = False
                created.append(self)

            def run(self, *, max_seconds=None):
                self.callback("ready", self.channel)
                chat = TwitchChatLine(
                    self.channel, "시청자", "같은 본문", "서버-" + str(self.index + 1)
                )
                if self.callback("chat", chat) is False:
                    raise AssertionError("AI 수신 큐가 채팅을 거절했습니다.")
                if self.index == 0:
                    raise TwitchServerReconnect("서버가 재연결을 요청했습니다.")
                owner["session"].stop()

            def stop(self):
                self.stopped = True

        def receive(kind, item):
            events.append((kind, item))
            return True

        with patch(
            "ai_broadcaster.multi_platform_session.TwitchReadOnlySession", 가짜수신기
        ):
            session = MultiPlatformReadOnlySession({"twitch": "sample"}, receive)
            owner["session"] = session
            # 명시적 서버 RECONNECT는 기존 일반 장애의 1초 대기를 사용하면 안 된다.
            with patch.object(
                session._stop, "wait",
                side_effect=AssertionError("서버 RECONNECT에 지수 대기 발생"),
            ):
                session.run()

        chats = [item for kind, item in events if kind == "chat"]
        self.assertEqual([chat.text for chat in chats], ["같은 본문", "같은 본문"])
        self.assertEqual([chat.event_id for chat in chats], ["서버-1", "서버-2"])
        self.assertEqual(len(created), 2)
        self.assertTrue(all(reader.stopped for reader in created))
        snapshot = session.reconnect_snapshot()["twitch"]
        self.assertEqual(snapshot["재연결완료"], 1)
        self.assertEqual(snapshot["완료공백최근표본"], 1)
        self.assertEqual(snapshot["콜백전달완료"], 2)
        self.assertEqual(snapshot["실제읽기실패"], 1)


if __name__ == "__main__":
    unittest.main()
