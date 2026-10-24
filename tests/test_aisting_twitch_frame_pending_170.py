"""170회차 트위치 IRC 프레임 미수용 채팅 보존 계약검사.

모든 소켓·프레임·콜백은 가상 객체이다. 실제 계정/시청자/방송 검증 아님.
"""
import sys
import unittest
from collections import deque
from types import SimpleNamespace
from unittest.mock import patch

from ai_broadcaster.twitch_readonly import (
    TwitchChatLine, TwitchReadError, TwitchReadOnlySession,
    TwitchServerReconnect,
)
from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession


def 채팅줄(번호, *, id포함=True):
    태그 = f"@id=evt{번호} " if id포함 else ""
    return f"{태그}:user!user@host PRIVMSG #mychannel :채팅 {번호}\r\n"


class 가상소켓:
    def __init__(self, frames):
        self.frames = deque(frames)
        self.sent = []
        self.closed = False

    def settimeout(self, seconds):
        pass

    def recv(self):
        if not self.frames:
            raise RuntimeError("가상 수신 프레임 종료")
        return self.frames.popleft()

    def send(self, text):
        self.sent.append(text)

    def close(self):
        self.closed = True


def 가상실행(reader, frames, *, expected=RuntimeError):
    sock = 가상소켓(frames)
    ws = SimpleNamespace(
        create_connection=lambda *a, **kw: sock,
        WebSocketTimeoutException=TimeoutError,
    )
    with patch.dict(sys.modules, {"websocket": ws}):
        with unittest.TestCase().assertRaises(expected):
            reader.run(max_seconds=3)
    return sock


승인 = ":tmi.twitch.tv 366 nick #mychannel :End of NAMES\r\n"


class 트위치프레임보존검사(unittest.TestCase):
    def setUp(self):
        self.received = []
        self.reader = TwitchReadOnlySession(
            "mychannel",
            lambda kind, value: self.received.append(value)
            if kind == "chat" else None,
        )

    def test_join_승인_전_수신_보류(self):
        가상실행(self.reader, [채팅줄(1)])
        self.assertEqual(self.received, [])
        self.assertEqual(len(self.reader._pending_chats), 1)

    def test_동일프레임_join_전_채팅도_승인_후_전달(self):
        가상실행(self.reader, [채팅줄(1) + 승인 + 채팅줄(2)])
        self.assertEqual([c.text for c in self.received], ["채팅 1", "채팅 2"])
        self.assertFalse(self.reader._pending_chats)

    def test_중간_false_뒤쪽_프레임_전체_보존(self):
        delivered = []
        def emit(kind, item):
            if kind != "chat":
                return None
            if item.event_id == "evt2":
                return False
            delivered.append(item.event_id)
            return True
        self.reader.emit = emit
        가상실행(self.reader, [승인 + 채팅줄(1) + 채팅줄(2) + 채팅줄(3)],
               expected=TwitchReadError)
        self.assertEqual(delivered, ["evt1"])
        self.assertEqual([c.event_id for c in self.reader._pending_chats],
                         ["evt2", "evt3"])

    def test_중간_예외_뒤쪽_프레임_전체_보존(self):
        def emit(kind, item):
            if kind == "chat" and item.event_id == "evt2":
                raise LookupError("가상 콜백 예외")
        self.reader.emit = emit
        가상실행(self.reader, [승인 + 채팅줄(1) + 채팅줄(2) + 채팅줄(3)],
               expected=LookupError)
        self.assertEqual([c.event_id for c in self.reader._pending_chats],
                         ["evt2", "evt3"])

    def test_새_수신기에_기존_미수용_큐_공유(self):
        self.reader._pending_chats.extend([
            TwitchChatLine("mychannel", "u", "이전 1", "old1"),
            TwitchChatLine("mychannel", "u", "이전 2", "old2"),
        ])
        next_reader = TwitchReadOnlySession(
            "mychannel",
            lambda kind, item: self.received.append(item)
            if kind == "chat" else None,
        )
        next_reader._pending_chats = self.reader._pending_chats
        가상실행(next_reader, [승인 + 채팅줄(3)])
        self.assertEqual([c.text for c in self.received],
                         ["이전 1", "이전 2", "채팅 3"])
        self.assertFalse(self.reader._pending_chats)

    def test_서버_reconnect_프레임_채팅_먼저_수용(self):
        가상실행(self.reader, [
            승인 + 채팅줄(1) + ":tmi.twitch.tv RECONNECT\r\n" + 채팅줄(2)
        ], expected=TwitchServerReconnect)
        self.assertEqual([c.event_id for c in self.received], ["evt1", "evt2"])

    def test_운영자_stop_이후_보류_미전달(self):
        self.reader._pending_chats.append(
            TwitchChatLine("mychannel", "u", "보류", "old"))
        self.reader.stop()
        self.assertEqual(self.reader._flush_pending_chats(), 0)
        self.assertEqual(len(self.reader._pending_chats), 1)
        self.assertFalse(self.received)

    def test_같은_본문_id_없으면_서로_다른_사건(self):
        가상실행(self.reader, [승인 + 채팅줄(1, id포함=False) * 2])
        self.assertEqual(len(self.received), 2)
        self.assertEqual([c.event_id for c in self.received], [None, None])

    def test_합성_500건_한_프레임_전량_보류후_수용(self):
        # 실수백 명이 아니라 가상 IRC 프레임 500개이다.
        가상실행(self.reader, [승인 + "".join(채팅줄(i) for i in range(500))])
        self.assertEqual(len(self.received), 500)
        self.assertEqual(self.received[-1].event_id, "evt499")
        self.assertFalse(self.reader._pending_chats)

    def test_조정기_트위치_재연결_공유_및_진단(self):
        coordinator = MultiPlatformReadOnlySession(
            {"twitch": "mychannel"}, lambda *args: True)
        self.assertIs(coordinator._readers["twitch"]._pending_chats,
                      coordinator._pending_websocket_chats["twitch"])
        coordinator._pending_websocket_chats["twitch"].append(
            TwitchChatLine("mychannel", "u", "보류", "old"))
        snapshot = coordinator.reconnect_snapshot()
        self.assertEqual(snapshot["twitch"]["수신프레임미수용보류"], 1)


if __name__ == "__main__":
    unittest.main()
