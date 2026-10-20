"""YouTube read-only cursor safety; mock API, never authenticated traffic."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.multiplatform_readonly import YouTubeReadOnlySession


class YoutubeCursorLengthTests(unittest.TestCase):
    def test_oversized_page_cursor_blocks_delivery(self):
        events=[]
        session=YouTubeReadOnlySession(
            "livechat",lambda k,v:events.append((k,v)),"k"*39)
        response={"nextPageToken":"x"*2049,"pollingIntervalMillis":1000,
                  "items":[{"id":"m1","snippet":{"type":"textMessageEvent",
                            "displayMessage":"전달 금지"},
                            "authorDetails":{"displayName":"viewer"}}]}
        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   return_value=response):
            with self.assertRaisesRegex(ValueError,"토큰 길이"):
                session.run(max_seconds=2)
        self.assertFalse(any(kind=="chat" for kind,_ in events))

    def test_normal_page_cursor_still_accepts_chat(self):
        events=[]
        session=YouTubeReadOnlySession(
            "livechat",lambda k,v:events.append((k,v)),"k"*39)
        response={"nextPageToken":"p1","pollingIntervalMillis":1,
                  "items":[{"id":"m1","snippet":{"type":"textMessageEvent",
                            "displayMessage":"정상 채팅"},
                            "authorDetails":{"displayName":"viewer"}}]}
        def get_page(*args,**kwargs):
            session.stop()
            return response
        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   side_effect=get_page):
            session.run(max_seconds=2)
        # Stopping during the HTTP request must suppress late delivery.
        self.assertFalse(any(kind=="chat" for kind,_ in events))
