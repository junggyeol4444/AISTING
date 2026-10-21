"""Native Windows Google owner OAuth PKCE and consent workflow: offline fakes.

These tests never sign in, open a browser, access Google, save tokens,
post a YouTube message or mutate the user's actual account.
"""
from __future__ import annotations

import hashlib
import base64
import io
import json
import queue
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit, urlencode
from urllib.request import urlopen as raw_open
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster import youtube_desktop_oauth as oauth
from ai_broadcaster.desktop_chat_tab import LocalChatTab

CLIENT = "123456789012-" + "a" * 32 + ".apps.googleusercontent.com"
TOKEN = "ya29." + "R" * 110


class MemoryValue:
    def __init__(self, v=""):
        self.value = v
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class Button:
    def __init__(self):
        self.state = "normal"
    def configure(self, *, state):
        self.state = state


class OwnerPKCETests(unittest.TestCase):
    def test_generated_pkce_has_correct_s256_and_is_nondeterministic(self):
        state, verifier, challenge = oauth.new_pkce()
        self.assertTrue(43 <= len(verifier) <= 128)
        self.assertGreaterEqual(len(state), 30)
        computed = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).decode("ascii").rstrip("=")
        self.assertEqual(challenge, computed)
        self.assertNotEqual(verifier, oauth.new_pkce()[1])

    def test_auth_url_is_google_readonly_pkce_and_memory_only(self):
        state, verifier, challenge = oauth.new_pkce()
        url = oauth.authorization_url(
            CLIENT, "http://127.0.0.1:54321/oauth2callback",
            state, challenge)
        self.assertEqual(urlsplit(url).netloc, "accounts.google.com")
        params = parse_qs(urlsplit(url).query)
        self.assertEqual(params["scope"], [oauth.YOUTUBE_READ_SCOPE])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertEqual(params["access_type"], ["online"])
        self.assertEqual(params["response_type"], ["code"])
        self.assertNotIn(verifier, url)
        with self.assertRaises(ValueError):
            oauth.authorization_url(CLIENT, "http://0.0.0.0:54321/oauth2callback",
                                    state, challenge)

    def test_csrf_rejection_and_duplicate_code_fail_closed(self):
        self.assertEqual(oauth.verify_callback(
            "/oauth2callback?state=STATE123&code=CODE-12345678", "STATE123"),
            "CODE-12345678")
        for suffix in ("state=OTHER&code=CODE-12345678",
                       "state=STATE123&code=CODE-12345678&code=CODE-12345679",
                       "state=STATE123&error=access_denied",
                       "code=CODE-12345678"):
            with self.assertRaises((ValueError, PermissionError)):
                oauth.verify_callback("/oauth2callback?" + suffix, "STATE123")

    def test_invalid_desktop_client_rejected_without_browser_or_http(self):
        for client in ("", "x.apps.googleusercontent.com", "abc\n",
                       "client-id.example.com"):
            with self.assertRaises(ValueError):
                oauth.authorize_owner_readonly(
                    client, operator_approved=True,
                    browser_opener=lambda *_: self.fail("browser opened"))

    def test_without_user_approval_no_browser(self):
        with self.assertRaises(PermissionError):
            oauth.authorize_owner_readonly(
                CLIENT, browser_opener=lambda *_: self.fail("no consent"))

    def test_token_exchange_posts_code_and_pkce_only_to_google(self):
        response = {"access_token": TOKEN, "token_type": "Bearer",
                    "expires_in": 3599, "scope": oauth.YOUTUBE_READ_SCOPE}
        requests = []
        def fake_http(request, timeout):
            requests.append(request)
            return io.BytesIO(json.dumps(response).encode("utf-8"))
        with patch("ai_broadcaster.youtube_desktop_oauth.urlopen",
                   side_effect=fake_http):
            access = oauth.exchange_code(
                CLIENT, "", "http://127.0.0.1:43210/oauth2callback",
                "A"*64, "CODE-12345678")
        self.assertEqual(access, TOKEN)
        self.assertEqual(requests[0].full_url, oauth.TOKEN_ENDPOINT)
        data = parse_qs(requests[0].data.decode("utf-8"))
        self.assertEqual(data["code_verifier"], ["A"*64])
        self.assertEqual(data["grant_type"], ["authorization_code"])
        self.assertNotIn("client_secret", data)

    def test_short_scope_and_http_error_never_leak_response(self):
        def payload(value):
            return io.BytesIO(json.dumps(value).encode("utf-8"))
        with patch("ai_broadcaster.youtube_desktop_oauth.urlopen",
                   return_value=payload({"access_token": TOKEN, "token_type":"Bearer",
                                         "scope":"https://www.googleapis.com/auth/userinfo.profile"})):
            with self.assertRaises(RuntimeError):
                oauth.exchange_code(
                    CLIENT, "", "http://127.0.0.1:43210/oauth2callback",
                    "A"*64, "CODE-12345678")
        with patch("ai_broadcaster.youtube_desktop_oauth.urlopen",
                   side_effect=RuntimeError("do-not-log-token-body")):
            with self.assertRaises(RuntimeError) as ctx:
                oauth.exchange_code(
                    CLIENT, "", "http://127.0.0.1:43210/oauth2callback",
                    "A"*64, "CODE-12345678")
        self.assertNotIn("do-not-log-token-body", str(ctx.exception))

    def test_real_local_loopback_callback_with_no_google_requests(self):
        threads = []
        def local_browser(url):
            p = parse_qs(urlsplit(url).query)
            redirect = p["redirect_uri"][0]
            callback = redirect + "?" + urlencode({
                "code":"CODE-12345678", "state":p["state"][0]})
            def send():
                with raw_open(callback, timeout=3) as response:
                    self.assertIn(b"AISTING", response.read())
            t = threading.Thread(target=send, daemon=True)
            threads.append(t)
            t.start()
            return True
        with patch("ai_broadcaster.youtube_desktop_oauth.exchange_code",
                   return_value=TOKEN) as exchange:
            access = oauth.authorize_owner_readonly(
                CLIENT, operator_approved=True, timeout=15,
                browser_opener=local_browser)
        for t in threads:
            t.join(timeout=2)
        self.assertEqual(access, TOKEN)
        self.assertEqual(exchange.call_count, 1)
        self.assertEqual(exchange.call_args.args[0], CLIENT)

    def test_native_gui_explicit_denial_does_not_open_browser(self):
        fake = SimpleNamespace(
            _closed=False, _oauth_busy=False, _busy=False,
            _pipeline_busy=False, _tts_probe_busy=False,
            _twitch_session=None, _twitch_active_workers=set(),
            _twitch_status=MemoryValue())
        with patch("ai_broadcaster.desktop_chat_tab.messagebox.askyesno",
                   return_value=False), patch(
                   "ai_broadcaster.desktop_chat_tab.simpledialog.askstring"
                   ) as prompt:
            LocalChatTab._begin_owner_youtube_oauth(fake)
        prompt.assert_not_called()

    def test_gui_worker_never_exposes_google_errors(self):
        fake = SimpleNamespace(_results=queue.SimpleQueue())
        with patch("ai_broadcaster.youtube_desktop_oauth.authorize_owner_readonly",
                   side_effect=RuntimeError("PRIVATE GOOGLE SECRET")):
            LocalChatTab._work_owner_youtube_oauth(fake, CLIENT, "")
        self.assertEqual(fake._results.get_nowait(), ("youtube_oauth_error", "RuntimeError"))

    def test_gui_receives_token_in_memory_only_and_has_not_received_chat(self):
        results = queue.SimpleQueue()
        results.put(("youtube_oauth_ok", TOKEN))
        fake = SimpleNamespace(
            _closed=False, _results=results, _oauth_busy=True,
            _youtube_oauth_button=Button(),
            _youtube_oauth_token=MemoryValue(),
            _twitch_status=MemoryValue(), _poll=lambda: None,
            after=lambda *_: None)
        LocalChatTab._poll(fake)
        self.assertEqual(fake._youtube_oauth_token.get(), TOKEN)
        self.assertEqual(fake._youtube_oauth_button.state, "normal")
        self.assertIn("실제 수신은 아직 미실행", fake._twitch_status.get())


if __name__ == "__main__":
    unittest.main()
