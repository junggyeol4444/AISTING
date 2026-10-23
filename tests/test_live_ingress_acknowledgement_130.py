"""AISTING의 공개 채팅 수용 확인/페이지 재수신 경로 비네트워크 검사.

여기서 확인하는 것은 프로그램 내부의 수용 여부와 커서 안전성이다.
실제 채팅, 실사용자, 모델, Windows EXE 검증으로 해석하지 않는다.
"""
import unittest
from unittest.mock import patch

from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession
from ai_broadcaster.multiplatform_readonly import (
    PlatformChat, YouTubeChatResumeState, YouTubeReadOnlySession,
)


def _youtube_payload(items):
    return {
        "items": items,
        "nextPageToken": "다음페이지",
        "pollingIntervalMillis": 20,
    }


def _youtube_chat(message_id, text="같은 메시지"):
    return {
        "id": message_id,
        "snippet": {"type": "textMessageEvent", "displayMessage": text},
        "authorDetails": {"displayName": "가상 시청자"},
    }


class TestPlatformIngressAck(unittest.TestCase):
    def test_local_queue_rejection_is_returned_and_id_is_not_committed(self):
        accept = iter((False, True))
        forwarded = []

        def emit(kind, item):
            forwarded.append((kind, item.text))
            return next(accept)

        multi = MultiPlatformReadOnlySession(
            {"chzzk": "a" * 32}, emit)
        cb = multi._callbacks["chzzk"]
        chat = PlatformChat("a" * 32, "시청자", "안녕하세요", "chzzk", "m001")
        self.assertIs(cb("chat", chat), False)
        self.assertIs(cb("chat", chat), True)
        state = multi.reconnect_snapshot()["chzzk"]
        self.assertEqual(state["콜백수신"], 2)
        self.assertEqual(state["콜백전달중단"], 1)
        self.assertEqual(state["콜백전달완료"], 1)
        self.assertEqual(state["서버이벤트ID재수신차단"], 0)
        self.assertEqual(len(forwarded), 2)

    def test_duplicate_event_id_is_acknowledged_without_second_ai_registration(self):
        forwarded = []
        multi = MultiPlatformReadOnlySession(
            {"soop": "tester/123"}, lambda kind, item: forwarded.append(item))
        cb = multi._callbacks["soop"]
        self.assertIs(cb("chat", PlatformChat(
            "tester/123", "시청자", "같은 내용", "soop", "id-1")), True)
        self.assertIs(cb("chat", PlatformChat(
            "tester/123", "시청자", "같은 내용", "soop", "id-2")), True)
        self.assertIs(cb("chat", PlatformChat(
            "tester/123", "시청자", "같은 내용", "soop", "id-1")), True)
        state = multi.reconnect_snapshot()["soop"]
        self.assertEqual(len(forwarded), 2)
        self.assertEqual(state["콜백수신"], 3)
        self.assertEqual(state["콜백전달완료"], 2)
        self.assertEqual(state["서버이벤트ID재수신차단"], 1)

    def test_youtube_cursor_is_not_advanced_after_queue_rejection(self):
        resume = YouTubeChatResumeState()
        events = []
        def reject(kind, item):
            events.append(kind)
            return False if kind == "chat" else True

        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   return_value=_youtube_payload([_youtube_chat("yt-1")])):
            with self.assertRaises(RuntimeError):
                YouTubeReadOnlySession(
                    "stream-chat-room-1234", reject, "K" * 30,
                    resume_state=resume).run(max_seconds=0.05)
        self.assertEqual(resume.delivered, 0)
        self.assertEqual(resume.next_page_token, "")
        self.assertNotIn("yt-1", resume.seen_message_ids)

    def test_youtube_replayed_server_id_is_observed_and_not_reenqueued(self):
        resume = YouTubeChatResumeState()
        received = []
        pages = [
            _youtube_payload([_youtube_chat("yt-1"),
                              _youtube_chat("yt-1"),
                              _youtube_chat("yt-2")]),
            _youtube_payload([]),
        ]

        def fetch(_url, **_kwargs):
            return pages.pop(0) if len(pages) > 1 else pages[0]

        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   side_effect=fetch):
            YouTubeReadOnlySession(
                "stream-chat-room-1234",
                lambda kind, item: received.append(kind) or True,
                "K" * 30, resume_state=resume).run(max_seconds=0.05)
        self.assertEqual(received.count("chat"), 2)
        self.assertEqual(received.count("server_replay"), 1)
        self.assertEqual(resume.delivered, 2)
        self.assertEqual(resume.next_page_token, "다음페이지")


if __name__ == "__main__":
    unittest.main()
