"""YouTube 공식 chat event 보존 (승인 없는 실계정/API 요청 없음)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.multiplatform_readonly import parse_youtube_page


class YouTubeMemberMessageTests(unittest.TestCase):
    def test_member_milestone_and_regular_message_keep_arrival_order(self):
        page = {"items": [
            {"snippet": {"type": "memberMilestoneChatEvent",
                         "displayMessage": "멤버십 12개월 기념!" },
             "authorDetails": {"displayName": "멤버"}},
            {"snippet": {"type": "textMessageEvent",
                         "displayMessage": "안녕하세요"},
             "authorDetails": {"displayName": "시청자"}},
            {"snippet": {"type": "memberMilestoneChatEvent",
                         "displayMessage": "멤버십 12개월 기념!" },
             "authorDetails": {"displayName": "멤버"}},
        ]}
        chats = parse_youtube_page(page, "live-chat")
        self.assertEqual([v.text for v in chats],
                         ["멤버십 12개월 기념!", "안녕하세요", "멤버십 12개월 기념!"])
        self.assertEqual([v.sender for v in chats], ["멤버", "시청자", "멤버"])
        self.assertTrue(all(v.platform == "youtube" for v in chats))

    def test_non_viewer_control_event_is_not_invented_as_chat(self):
        page = {"items": [
            {"snippet": {"type": "chatEndedEvent", "displayMessage": "종료"},
             "authorDetails": {"displayName": "시스템"}},
            {"snippet": {"type": "memberMilestoneChatEvent", "displayMessage": "반가워요"},
             "authorDetails": {"displayName": "회원"}},
        ]}
        self.assertEqual([v.text for v in parse_youtube_page(page, "chat")],
                         ["반가워요"])


if __name__ == "__main__":
    unittest.main()
