"""Twitch IRC chat:read user authorization, never chat:edit or PRIVMSG."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_broadcaster.twitch_readonly import TwitchReadOnlySession
from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession
from ai_broadcaster import multi_platform_session as multi

TOKEN = "0123456789abcdef0123456789abcdef"


class AuthenticatedTwitchReadonly(unittest.TestCase):
    def test_no_authentication_or_socket_on_construct(self):
        with patch.dict(sys.modules, {"websocket": types.SimpleNamespace(
                create_connection=lambda *args, **kwargs:
                self.fail("constructor opened a network connection"))}):
            r = TwitchReadOnlySession(
                "streamer", lambda *_: None,
                oauth_token=TOKEN, oauth_login="testviewer")
        self.assertEqual(r.channel, "streamer")
        self.assertFalse(r._stop.is_set())

    def test_explicit_chat_read_credential_send_and_every_duplicate_arrives(self):
        observed, sent = [], []
        class Socket:
            frames = [
                ":tmi.twitch.tv 001 testviewer :Welcome\r\n"
                ":tmi.twitch.tv 366 testviewer #streamer :End of /NAMES list\r\n",
                ":alice!alice@host PRIVMSG #streamer :중복 채팅\r\n"
                ":bob!bob@host PRIVMSG #streamer :중복 채팅\r\n",
            ]
            def send(self, msg):
                sent.append(msg)
            def recv(self):
                if self.frames:
                    return self.frames.pop(0)
                reader.stop()
                return ""
            def settimeout(self, *_):
                pass
            def close(self):
                pass
        def got(kind, item):
            observed.append((kind, item))
            if sum(k == "chat" for k, _ in observed) == 2:
                reader.stop()
        reader = TwitchReadOnlySession(
            "streamer", got, oauth_token=TOKEN, oauth_login="testviewer")
        with patch.dict(sys.modules, {"websocket": types.SimpleNamespace(
                create_connection=lambda *args, **kwargs: Socket(),
                WebSocketTimeoutException=TimeoutError)}):
            reader.run(max_seconds=5)
        self.assertEqual(sent[0], "PASS oauth:" + TOKEN + "\r\n")
        self.assertEqual(sent[1], "NICK testviewer\r\n")
        self.assertTrue(any("JOIN #streamer" in row for row in sent))
        self.assertFalse(any("PRIVMSG" in row for row in sent))
        self.assertFalse(any("chat:edit" in row for row in sent))
        self.assertEqual(
            [item.text for k, item in observed if k == "chat"],
            ["중복 채팅", "중복 채팅"])
        self.assertTrue(any(k == "ready" for k, _ in observed))

    def test_bad_credentials_denied_without_any_network(self):
        for token, name in ((TOKEN, ""), ("", "testviewer"), ("a"*8, "tester"),
                            ("bad\nsecret", "tester"), (TOKEN, "invalid login")):
            with self.subTest(name=name, token_length=len(token)):
                with patch.dict(sys.modules, {"websocket": types.SimpleNamespace(
                        create_connection=lambda *a, **k:
                        self.fail("network without credentials"))}):
                    with self.assertRaises(ValueError) as error:
                        TwitchReadOnlySession(
                            "streamer", lambda *_: None,
                            oauth_token=token, oauth_login=name)
                self.assertNotIn(token, str(error.exception))

    def test_four_platform_session_passes_token_only_to_twitch(self):
        seen = []
        class Twitch:
            def __init__(self, channel, emit, *, oauth_token, oauth_login):
                seen.append((channel, oauth_token, oauth_login))
            def stop(self):
                pass
        class Other:
            def __init__(self, *args, **kwargs):
                pass
            def stop(self):
                pass
        with patch.object(multi, "TwitchReadOnlySession", Twitch), patch.object(
                multi, "ChzzkReadOnlySession", Other), patch.object(
                multi, "SoopReadOnlySession", Other):
            session = MultiPlatformReadOnlySession(
                {"twitch":"streamer", "chzzk":"a"*32, "soop":"user/1"},
                lambda *_: None, twitch_oauth_token=TOKEN,
                twitch_oauth_login="testviewer")
        self.assertEqual(len(session._readers), 3)
        self.assertEqual(seen, [("streamer", TOKEN, "testviewer")])

    def test_anonymous_mode_remains_compatible(self):
        reader = TwitchReadOnlySession("streamer", lambda *_: None)
        self.assertEqual(reader._oauth_token, "")
        self.assertEqual(reader._oauth_login, "")


if __name__ == "__main__":
    unittest.main()
