"""기존 Twitch 수신기 회귀검사: 공개 읽기 전용·중복 포함 FIFO·Stop.

실제 인터넷 접속, 채팅 전송, 계정 인증, 방송/녹화 없이 메모리 소켓 사용.
"""
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.twitch_readonly import TwitchReadOnlySession, TwitchReadError


class TwitchCumulativeHardeningTests(unittest.TestCase):
    def run_frames(self, frames, *, closing_raises=False):
        events = []
        socket_holder = []

        class Socket:
            def __init__(self):
                self.frames = list(frames)
                self.writes = []
            def settimeout(self, _):
                pass
            def send(self, text):
                self.writes.append(text)
            def recv(self):
                if self.frames:
                    return self.frames.pop(0)
                session.stop()
                return ""
            def close(self):
                if closing_raises:
                    raise RuntimeError("socket already closed")

        sock = Socket()
        socket_holder.append(sock)
        session = TwitchReadOnlySession("streamer", lambda k, v: events.append((k, v)))
        fake = SimpleNamespace(create_connection=lambda *_a, **_k: sock,
                               WebSocketTimeoutException=TimeoutError)
        with patch.dict(sys.modules, {"websocket": fake}):
            session.run(max_seconds=30)
        return events, sock

    def test_10000_messages_duplicate_and_fifo_preserved(self):
        ack = ":server 366 guest #streamer :End of NAMES\r\n"
        lines = [f":viewer!u@host PRIVMSG #streamer :line-{i // 2}\r\n"
                 for i in range(10000)]
        events, _ = self.run_frames([ack + "".join(lines)])
        chats = [item.text for kind, item in events if kind == "chat"]
        self.assertEqual(len(chats), 10000)
        self.assertEqual(chats[0:4], ["line-0", "line-0", "line-1", "line-1"])
        self.assertEqual(chats[-1], "line-4999")

    def test_other_channel_ack_cannot_authorize_own_channel(self):
        events, _ = self.run_frames([
            ":server 366 guest #streamer2 :End\r\n"
            ":viewer!u@host PRIVMSG #streamer :hi\r\n"
            ":server 366 guest #streamer :End\r\n"
        ])
        self.assertEqual([value for kind, value in events if kind == "ready"],
                         ["streamer"])
        self.assertEqual([value.text for kind, value in events if kind == "chat"],
                         ["hi"])

    def test_error_words_in_viewer_message_not_auth_error(self):
        events, _ = self.run_frames([
            ":server 366 guest #streamer :End\r\n"
            ":viewer!u@host PRIVMSG #streamer :Login authentication failed  NOTICE  366\r\n"
        ])
        self.assertEqual([v.text for k, v in events if k == "chat"],
                         ["Login authentication failed  NOTICE  366"])

    def test_double_run_refused_without_opening_network(self):
        session = TwitchReadOnlySession("streamer", lambda *_a: None)
        session._running = True
        with self.assertRaises(TwitchReadError):
            session.run(max_seconds=1)
        self.assertTrue(session._running)

    def test_nonfinite_probe_times_rejected(self):
        for value in [float("nan"), math.inf, -math.inf, True, 0, 121, "5"]:
            with self.subTest(value=value):
                session = TwitchReadOnlySession("streamer", lambda *_a: None)
                with self.assertRaises(ValueError):
                    session.run(max_seconds=value)

    def test_closed_socket_does_not_hide_received_message(self):
        events, _ = self.run_frames([
            ":server 366 guest #streamer :End\r\n"
            ":viewer!u@host PRIVMSG #streamer :persist\r\n"
        ], closing_raises=True)
        self.assertEqual([v.text for k, v in events if k == "chat"], ["persist"])
        self.assertIn(("stopped", 1), events)


if __name__ == "__main__":
    unittest.main()
