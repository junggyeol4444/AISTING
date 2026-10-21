"""YouTube owner-authorized read-only live chat; no login, network or token persistence."""
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_broadcaster import multiplatform_readonly as youtube
from ai_broadcaster import multi_platform_session as multi


TOKEN = "ya29." + "Q" * 90
KEY = "k" * 39


def final_page(text="같은 메시지"):
    return {"items":[
        {"id":"a","snippet":{"type":"textMessageEvent","displayMessage":text},
         "authorDetails":{"displayName":"사람"}},
        {"id":"b","snippet":{"type":"textMessageEvent","displayMessage":text},
         "authorDetails":{"displayName":"사람"}}],
        "offlineAt":"2026-10-21T00:00:00Z",
        "pollingIntervalMillis":1000}


def broadcasts(chats=("owner-chat",), status="live"):
    return {"items":[{"snippet":{"liveChatId":name},
                      "status":{"lifeCycleStatus":status}}
                     for name in chats]}


class OwnerOAuthReadOnlyTests(unittest.TestCase):
    def test_no_requests_or_login_just_from_construction(self):
        with patch("ai_broadcaster.multiplatform_readonly._json_get") as get:
            r = youtube.YouTubeReadOnlySession(
                "내 활성 방송", lambda *_: None, oauth_access_token=TOKEN)
            self.assertFalse(r._stop.is_set())
            get.assert_not_called()

    def test_owner_active_discovery_bearer_only_and_duplicate_text_preserved(self):
        requests, events = [], []
        def transport(url, *, timeout=10, headers=None):
            requests.append((url, headers))
            self.assertEqual(headers, {"Authorization":"Bearer " + TOKEN})
            self.assertNotIn(TOKEN, url)
            self.assertNotIn("key=", url)
            parsed = urlsplit(url)
            params = parse_qs(parsed.query)
            if parsed.path.endswith("/liveBroadcasts"):
                self.assertEqual(params["mine"], ["true"])
                self.assertEqual(params["broadcastType"], ["all"])
                return broadcasts()
            self.assertEqual(params["liveChatId"], ["owner-chat"])
            return final_page()
        with patch.object(youtube, "_json_get", side_effect=transport):
            reader = youtube.YouTubeReadOnlySession(
                "내 활성 방송", lambda *e: events.append(e), oauth_access_token=TOKEN)
            reader.run(max_seconds=5)
        self.assertEqual(len(requests), 2)
        self.assertEqual([event[1].text for event in events if event[0] == "chat"],
                         ["같은 메시지", "같은 메시지"])
        self.assertTrue(any(e[0] == "ready" for e in events))

    def test_expired_token_never_retries_or_leaks(self):
        sent = []
        def unauthorized(url, *, timeout=10, headers=None):
            sent.append(url)
            raise HTTPError(url, 401, "secret-oauth-access-token", {}, None)
        reader = youtube.YouTubeReadOnlySession(
            "내 활성 방송", lambda *_: None, oauth_access_token=TOKEN)
        with patch.object(youtube, "_json_get", side_effect=unauthorized):
            with self.assertRaises(RuntimeError) as caught:
                reader.run(max_seconds=2)
        self.assertEqual(len(sent), 1)
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertNotIn("secret-oauth-access-token", str(caught.exception))

    def test_ambiguous_or_missing_owned_live_broadcast_denied_without_chat_api(self):
        for result in (
            broadcasts(()), broadcasts(("one", "two")),
            broadcasts(("inactive",), status="ready"),
            {"items":[],"nextPageToken":"more"},
            {"items":"invalid"},
        ):
            with self.subTest(result=result):
                req = []
                def transport(url, *, timeout=10, headers=None):
                    req.append(url)
                    return result
                reader = youtube.YouTubeReadOnlySession(
                    "내 활성 방송", lambda *_: None, oauth_access_token=TOKEN)
                with patch.object(youtube, "_json_get", side_effect=transport):
                    with self.assertRaises(RuntimeError):
                        reader.run(max_seconds=2)
                self.assertEqual(len(req), 1)
                self.assertIn("liveBroadcasts", req[0])

    def test_owner_mode_refused_with_api_key_alone(self):
        for invalid in ("", "\n", "a" * 29, "a" * 4097,
                        "a" * 44 + " ", "a" * 44 + "\n"):
            with self.subTest(invalid_length=len(invalid)):
                with patch.object(youtube, "_json_get") as getter:
                    with self.assertRaises(ValueError):
                        youtube.YouTubeReadOnlySession(
                            "내 활성 방송", lambda *_: None, KEY,
                            oauth_access_token=invalid)
                    getter.assert_not_called()

    def test_existing_key_mode_remains_compatible_without_oauth(self):
        events, urls = [], []
        def api(url, *, timeout=10):
            urls.append(url)
            return final_page("기존 API 키")
        with patch.object(youtube, "_json_get", side_effect=api):
            reader = youtube.YouTubeReadOnlySession(
                "livechatId-1", lambda *e:events.append(e), KEY)
            reader.run(max_seconds=5)
        self.assertEqual(len(urls), 1)
        self.assertIn("key=" + KEY, urls[0])
        self.assertEqual([e[1].text for e in events if e[0] == "chat"],
                         ["기존 API 키", "기존 API 키"])

    def test_coordinator_forwards_credential_to_youtube_only_with_owner_choice(self):
        created = []
        class Fake:
            def __init__(self, channel, emit, api_key="", *,
                         oauth_access_token=""):
                created.append((channel, api_key, oauth_access_token))
            def stop(self):
                pass
        class Other:
            def __init__(self, *args):
                pass
            def stop(self):
                pass
        with patch.object(multi, "YouTubeReadOnlySession", Fake), patch.object(
              multi, "TwitchReadOnlySession", Other), patch.object(
              multi, "ChzzkReadOnlySession", Other):
            session = multi.MultiPlatformReadOnlySession(
                {"twitch": "tester", "chzzk": "a" * 32, "youtube": "내 활성 방송"},
                lambda *_: None, youtube_oauth_token=TOKEN)
        self.assertEqual(len(session._readers), 3)
        self.assertEqual(created, [("내 활성 방송", "", TOKEN)])


if __name__ == "__main__":
    unittest.main()
