"""174회차: 손상된 트위치 IRC 채팅의 무음 폐기 방지와 정상 채팅 보류 계약검사.

가상 IRC 소켓과 가상 메시지만 사용한다. 실제 트위치 채팅·시청자·
모델·Windows EXE·OBS·24시간 운영 성공의 증거가 아니다.
"""
import sys
import unittest
from collections import deque
from types import SimpleNamespace
from unittest.mock import patch

from ai_broadcaster.twitch_readonly import TwitchReadError, TwitchReadOnlySession


승인 = ":tmi.twitch.tv 366 nick #mychannel :End of NAMES\r\n"


def 채팅(번호, 채널="mychannel"):
    return f"@id=evt{번호} :viewer!u@host PRIVMSG #{채널} :내용{번호}\r\n"


class 가상소켓:
    def __init__(self, frames):
        self.frames = deque(frames)
        self.sent = []
        self.closed = False

    def settimeout(self, seconds):
        pass

    def recv(self):
        if not self.frames:
            raise RuntimeError("가상 입력 종료")
        return self.frames.popleft()

    def send(self, value):
        self.sent.append(value)

    def close(self):
        self.closed = True


def 가상실행(reader, frames, expected=RuntimeError):
    sock = 가상소켓(frames)
    websocket = SimpleNamespace(
        create_connection=lambda *args, **kwargs: sock,
        WebSocketTimeoutException=TimeoutError,
    )
    with patch.dict(sys.modules, {"websocket": websocket}):
        with unittest.TestCase().assertRaises(expected) as caught:
            reader.run(max_seconds=3)
    return caught.exception, sock


class 손상된IRC채팅보존검사(unittest.TestCase):
    def setUp(self):
        self.received = []
        self.reader = TwitchReadOnlySession(
            "mychannel",
            lambda kind, item: self.received.append(item)
            if kind == "chat" else None,
        )

    def test_대상채팅_보낸사람구조손상_명시적실패(self):
        err, _ = 가상실행(
            self.reader,
            [":viewer PRIVMSG #mychannel :손상\r\n"],
            TwitchReadError,
        )
        self.assertIn("PRIVMSG 형식 손상", str(err))
        self.assertEqual(self.received, [])

    def test_대상채팅_본문구분자누락_명시적실패(self):
        err, _ = 가상실행(
            self.reader,
            [":viewer!u@host PRIVMSG #mychannel 손상\r\n"],
            TwitchReadError,
        )
        self.assertIn("형식 손상", str(err))

    def test_태그있는_대상채팅_손상도_명시적실패(self):
        err, _ = 가상실행(
            self.reader,
            ["@id=evt1 :viewer PRIVMSG #mychannel :손상\r\n"],
            TwitchReadError,
        )
        self.assertIn("형식 손상", str(err))

    def test_손상채팅_앞뒤의_정상채팅은_모두_보류(self):
        err, _ = 가상실행(
            self.reader,
            [채팅(1) + ":viewer PRIVMSG #mychannel :손상\r\n" + 채팅(2)],
            TwitchReadError,
        )
        self.assertIn("형식 손상", str(err))
        self.assertEqual([x.event_id for x in self.reader._pending_chats],
                         ["evt1", "evt2"])
        self.assertEqual(self.received, [])

    def test_손상채팅_뒤_JOIN승인_같은프레임에서는_전달금지(self):
        가상실행(
            self.reader,
            [채팅(1) + ":viewer PRIVMSG #mychannel :손상\r\n" + 승인],
            TwitchReadError,
        )
        self.assertEqual([x.event_id for x in self.reader._pending_chats],
                         ["evt1"])
        self.assertFalse(self.received)

    def test_재연결후_같은_보류큐의_정상채팅_순서대로_전달(self):
        가상실행(
            self.reader,
            [채팅(1) + ":viewer PRIVMSG #mychannel :손상\r\n" + 채팅(2)],
            TwitchReadError,
        )
        next_reader = TwitchReadOnlySession(
            "mychannel",
            lambda kind, item: self.received.append(item)
            if kind == "chat" else None,
        )
        next_reader._pending_chats = self.reader._pending_chats
        가상실행(next_reader, [승인 + 채팅(3)])
        self.assertEqual([x.event_id for x in self.received],
                         ["evt1", "evt2", "evt3"])
        self.assertFalse(next_reader._pending_chats)

    def test_다른채널의_손상채팅은_현재채널_오류로_오인금지(self):
        가상실행(
            self.reader,
            [승인 + ":viewer PRIVMSG #otherchannel :손상\r\n" + 채팅(1)],
        )
        self.assertEqual([x.event_id for x in self.received], ["evt1"])

    def test_크기초과줄_뒤쪽_정상채팅도_보류(self):
        large = ":viewer!u@host PRIVMSG #mychannel :" + "x" * 65536 + "\r\n"
        err, _ = 가상실행(
            self.reader,
            [채팅(1) + large + 채팅(2)],
            TwitchReadError,
        )
        self.assertIn("크기 한도 초과", str(err))
        self.assertEqual([x.event_id for x in self.reader._pending_chats],
                         ["evt1", "evt2"])

    def test_정상_JOIN_PING_및_채팅은_기존대로_처리(self):
        _, sock = 가상실행(
            self.reader,
            [승인 + "PING :tmi.twitch.tv\r\n" + 채팅(1)],
        )
        self.assertEqual([x.event_id for x in self.received], ["evt1"])
        self.assertIn("PONG :tmi.twitch.tv\r\n", sock.sent)

    def test_본문에_PRIVMSG_문자열이_들어가도_정상채팅(self):
        가상실행(
            self.reader,
            [승인 + ":viewer!u@host PRIVMSG #mychannel :PRIVMSG #mychannel\r\n"],
        )
        self.assertEqual([x.text for x in self.received], ["PRIVMSG #mychannel"])


if __name__ == "__main__":
    unittest.main()
