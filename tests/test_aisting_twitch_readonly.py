"""Read-only Twitch IRC parser and session tests; no platform chat sent."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.twitch_readonly import (
    TwitchChatLine, TwitchReadOnlySession, parse_irc_chat_line,
)


class TwitchParserTests(unittest.TestCase):
    def test_tags_korean_emoji_and_colon_not_lost(self):
        line = "@id=123;mod=0 :tester!tester@tester.tmi.twitch.tv PRIVMSG #mychannel :한글: 😀 메시지"
        self.assertEqual(
            parse_irc_chat_line(line, "mychannel"),
            TwitchChatLine("mychannel", "tester", "한글: 😀 메시지"),
        )

    def test_no_arbitrary_deduplication_or_sender_filter(self):
        line = ":viewer!viewer@a PRIVMSG #mychannel :same"
        self.assertEqual(
            [parse_irc_chat_line(line, "mychannel") for _ in range(2)],
            [TwitchChatLine("mychannel", "viewer", "same")] * 2,
        )

    def test_unrelated_room_and_control_lines_are_not_chats(self):
        for row in ("PING :tmi.twitch.tv", ":tmi 001 guest :Welcome",
                    ":abc!x@y PRIVMSG #otherroom :secret", "NOTICE #mychannel :info"):
            self.assertIsNone(parse_irc_chat_line(row, "mychannel"))

    def test_operator_stop_during_receive_is_not_a_network_error(self):
        from types import SimpleNamespace
        for mode in ("empty", "socket_closed"):
            with self.subTest(mode=mode):
                observed = []

                class Socket:
                    def send(self, item):
                        pass

                    def settimeout(self, seconds):
                        pass

                    def recv(self):
                        session.stop()
                        if mode == "socket_closed":
                            raise OSError("Operator clicked Stop")
                        return ""

                    def close(self):
                        pass

                socket = Socket()
                session = TwitchReadOnlySession(
                    "streamer", lambda kind, item: observed.append((kind, item)))
                transport = SimpleNamespace(
                    create_connection=lambda *args, **kwargs: socket,
                    WebSocketTimeoutException=TimeoutError)
                with patch.dict(sys.modules, {"websocket": transport}):
                    session.run(max_seconds=3)
                self.assertEqual(
                    [kind for kind, _ in observed],
                    ["connecting", "stopped"])
                self.assertEqual(observed[-1], ("stopped", 0))


    def test_large_complete_irc_frame_preserves_all_messages(self):
        from types import SimpleNamespace
        n = 1600
        frame = ":tmi 366 guest #streamer :End of /NAMES list\r\n"
        frame += "".join(":viewer!v@host PRIVMSG #streamer :%04d 안녕😀\r\n" % i for i in range(n))
        self.assertGreater(len(frame), 65536)
        observed = []
        session = TwitchReadOnlySession("streamer", lambda kind, value: observed.append((kind, value)))
        class Sock:
            frames = [frame]
            def send(self, value):
                pass
            def settimeout(self, seconds):
                pass
            def recv(self):
                if self.frames:
                    return self.frames.pop(0)
                session.stop()
                return ""
            def close(self):
                pass
        with patch.dict(sys.modules, {"websocket": SimpleNamespace(
             create_connection=lambda *args, **kwargs: Sock(),
             WebSocketTimeoutException=TimeoutError)}):
            session.run(max_seconds=5)
        self.assertEqual(
            [value.text for kind, value in observed if kind == "chat"],
            ["%04d 안녕😀" % i for i in range(n)])
        self.assertEqual(sum(kind == "ready" for kind, _ in observed), 1)

    def test_stop_during_multiline_frame_discards_unread_messages(self):
        from types import SimpleNamespace
        observed = []
        def emit(kind, value):
            observed.append((kind, value))
            if kind == "chat":
                session.stop()
        session = TwitchReadOnlySession("streamer", emit)
        class Sock:
            def send(self, value):
                pass
            def settimeout(self, seconds):
                pass
            def recv(self):
                return (":tmi 366 guest #streamer :End of /NAMES list\r\n"
                        ":a!a@h PRIVMSG #streamer :첫째\r\n"
                        ":b!b@h PRIVMSG #streamer :둘째\r\n")
            def close(self):
                pass
        with patch.dict(sys.modules, {"websocket": SimpleNamespace(
             create_connection=lambda *args, **kwargs: Sock(),
             WebSocketTimeoutException=TimeoutError)}):
            session.run(max_seconds=3)
        self.assertEqual([v.text for k, v in observed if k == "chat"], ["첫째"])
        self.assertEqual(observed[-1], ("stopped", 1))

    def test_oversized_incomplete_irc_line_is_still_rejected(self):
        from types import SimpleNamespace
        observed = []
        session = TwitchReadOnlySession("streamer", lambda *args: observed.append(args))
        class Sock:
            def send(self, value):
                pass
            def settimeout(self, seconds):
                pass
            def recv(self):
                return "x" * 65537
            def close(self):
                pass
        with patch.dict(sys.modules, {"websocket": SimpleNamespace(
             create_connection=lambda *args, **kwargs: Sock(),
             WebSocketTimeoutException=TimeoutError)}):
            with self.assertRaisesRegex(Exception, "미완성"):
                session.run(max_seconds=3)
        self.assertEqual(observed[-1], ("stopped", 0))

    def test_reject_invalid_operator_channel(self):
        for bad in ("", "a", "www.twitch.tv", "#streamer", "한글채널", "a" * 26, "../secret"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                TwitchReadOnlySession(bad, lambda *a: None)

    def test_protocol_accepts_every_message_but_never_posts_chat(self):
        class Transport:
            def __init__(self):
                self.sent = []
                self.closed = False
                self.frames = [
                    ":tmi.twitch.tv 001 justinfan123 :Welcome\r\n",
                    ":tmi.twitch.tv 366 justinfan123 #streamer :End of /NAMES list\r\n",
                    "PING :tmi.twitch.tv\r\n",
                    "@id=one :one!one@one PRIVMSG #streamer :첫 번째\r\n"
                    ":two!two@two PRIVMSG #streamer :두 번째\r\n"
                    ":one!one@one PRIVMSG #streamer :첫 번째\r\n",
                ]
            def send(self, item):
                self.sent.append(item)
            def recv(self):
                return self.frames.pop(0)
            def settimeout(self, secs):
                pass
            def close(self):
                self.closed = True
        transport = Transport()
        observed = []
        session = TwitchReadOnlySession("streamer", lambda kind, item: (
            observed.append((kind, item)),
            session.stop() if kind == "chat" and len([1 for k, _ in observed if k == "chat"]) == 3 else None
        ))
        fake_ws = types.SimpleNamespace(
            create_connection=lambda *args, **kwargs: transport,
            WebSocketTimeoutException=TimeoutError,
        )
        with patch.dict(sys.modules, {"websocket": fake_ws}):
            session.run(max_seconds=5)
        actual = [event for kind, event in observed if kind == "chat"]
        self.assertEqual([x.text for x in actual], ["첫 번째", "두 번째", "첫 번째"])
        self.assertIn(("ready", "streamer"), observed)
        self.assertTrue(transport.closed)
        self.assertTrue(any(x.startswith("PONG ") for x in transport.sent))
        self.assertTrue(any(x.startswith("JOIN #streamer") for x in transport.sent))
        self.assertFalse(any("PRIVMSG" in x for x in transport.sent))
        self.assertFalse(any(x.startswith("PASS") for x in transport.sent))


if __name__ == "__main__":
    unittest.main()
