"""171회차 YouTube API 페이지 중간 실패·재연결 FIFO 보존 계약검사.

가상 API 응답과 가상 채팅만 사용한다. 실제 계정·시청자·방송·모델
또는 24시간 연결 성공의 증거가 아니며 외부 네트워크를 호출하지 않는다.
"""
import unittest
from unittest.mock import patch

from ai_broadcaster.multiplatform_readonly import (
    PlatformChat, YouTubeChatResumeState, YouTubeReadOnlySession,
)
from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession


def 가상항목(number, *, server_id=True, text=None):
    result = {
        "snippet": {"type": "textMessageEvent",
                    "displayMessage": text or f"가상 채팅 {number}"},
        "authorDetails": {"displayName": f"가상 시청자 {number}"},
    }
    if server_id:
        result["id"] = f"server-event-{number}"
    return result


def 가상페이지(items, *, ended=True, interval=1000, next_token="next-1"):
    page = {
        "items": items,
        "pollingIntervalMillis": interval,
        "nextPageToken": next_token,
    }
    if ended:
        page["offlineAt"] = "2026-10-25T00:00:00Z"
    return page


def 수신기(resume, callback):
    return YouTubeReadOnlySession(
        "가상_채팅방_ID", callback, "가상키" * 8, resume_state=resume)


class 유튜브페이지보류검사(unittest.TestCase):
    def setUp(self):
        self.resume = YouTubeChatResumeState()
        self.events = []

    def run_with_page(self, reader, page):
        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   return_value=page) as getter:
            reader.run()
        return getter

    def test_페이지중간_false_뒤쪽_보존_재연결시_재조회없음(self):
        page = 가상페이지([가상항목(i) for i in range(4)])
        def 첫콜백(kind, item):
            if kind != "chat":
                return True
            if item.event_id == "server-event-2":
                return False
            self.events.append(item.event_id)
            return True
        first = 수신기(self.resume, 첫콜백)
        with self.assertRaises(RuntimeError):
            self.run_with_page(first, page)
        self.assertEqual(self.events, ["server-event-0", "server-event-1"])
        self.assertEqual(
            [item.event_id for item in self.resume.pending_page_chats],
            ["server-event-2", "server-event-3"])
        self.assertEqual(self.resume.completed_pages, 0)
        self.assertEqual(self.resume.next_page_token, "")
        def 다음콜백(kind, item):
            if kind == "chat":
                self.events.append(item.event_id)
            return True
        second = 수신기(self.resume, 다음콜백)
        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   side_effect=AssertionError("같은 페이지를 다시 요청하지 않아야 함")) as getter:
            second.run()
        getter.assert_not_called()
        self.assertEqual(self.events, [f"server-event-{i}" for i in range(4)])
        self.assertFalse(self.resume.pending_page_active)
        self.assertEqual(self.resume.completed_pages, 1)
        self.assertEqual(self.resume.next_page_token, "next-1")
        self.assertTrue(second._terminal_chat_end)

    def test_ID없는_동일본문_별개사건도_재연결_중복없음(self):
        page = 가상페이지([가상항목(i, server_id=False, text="동일 내용")
                           for i in range(3)])
        attempt = 0
        def 첫콜백(kind, item):
            nonlocal attempt
            if kind == "chat":
                attempt += 1
                if attempt == 2:
                    return False
                self.events.append(item.text)
            return True
        with self.assertRaises(RuntimeError):
            self.run_with_page(수신기(self.resume, 첫콜백), page)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(len(self.resume.pending_page_chats), 2)
        second = 수신기(self.resume, lambda kind, item:
                      self.events.append(item.text) if kind == "chat" else None)
        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   side_effect=AssertionError("중복 조회")):
            second.run()
        self.assertEqual(self.events, ["동일 내용"] * 3)
        self.assertEqual(self.resume.delivered, 3)

    def test_콜백예외시_미수용선두_뒤쪽보존(self):
        page = 가상페이지([가상항목(i) for i in range(3)])
        def fail(kind, item):
            if kind == "chat":
                raise LookupError("가상 큐 예외")
        with self.assertRaises(LookupError):
            self.run_with_page(수신기(self.resume, fail), page)
        self.assertEqual(len(self.resume.pending_page_chats), 3)
        self.assertEqual(self.resume.delivered, 0)

    def test_운영자_stop_이후_남은_채팅은_발신안함(self):
        page = 가상페이지([가상항목(i) for i in range(3)])
        reader = None
        def callback(kind, item):
            if kind == "chat":
                self.events.append(item.event_id)
                reader.stop()
            return True
        reader = 수신기(self.resume, callback)
        self.run_with_page(reader, page)
        self.assertEqual(self.events, ["server-event-0"])
        self.assertEqual(len(self.resume.pending_page_chats), 2)
        self.assertEqual(self.resume.completed_pages, 0)
        self.assertTrue(self.resume.pending_page_active)

    def test_가상_500건_한_페이지_실패뒤_전량_이어받기(self):
        page = 가상페이지([가상항목(i) for i in range(500)])
        delivered = []
        def first(kind, item):
            if kind == "chat":
                if item.event_id == "server-event-200":
                    return False
                delivered.append(item.event_id)
            return True
        with self.assertRaises(RuntimeError):
            self.run_with_page(수신기(self.resume, first), page)
        self.assertEqual(len(delivered), 200)
        self.assertEqual(len(self.resume.pending_page_chats), 300)
        def second(kind, item):
            if kind == "chat":
                delivered.append(item.event_id)
            return True
        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   side_effect=AssertionError("페이지 재조회 금지")):
            수신기(self.resume, second).run()
        self.assertEqual(delivered, [f"server-event-{i}" for i in range(500)])
        self.assertEqual(self.resume.delivered, 500)

    def test_이미수용한_서버ID_재수신_중복방지(self):
        self.resume.delivered_event("server-event-1")
        self.resume.bind_chat("가상_채팅방_ID")
        self.resume.stage_page(
            [PlatformChat("가상_채팅방_ID", "u", "중복", "youtube", "server-event-1")],
            "next-1", 1000, True)
        replays = []
        def cb(kind, item):
            if kind == "server_replay":
                replays.append(True)
            if kind == "chat":
                self.fail("이미 수용한 ID는 중복 전달 금지")
            return True
        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   side_effect=AssertionError("보류 페이지는 재조회 금지")):
            수신기(self.resume, cb).run()
        self.assertEqual(replays, [True])
        self.assertEqual(self.resume.delivered, 1)

    def test_유효하지않은_폴링간격은_전달전_거절(self):
        page = 가상페이지([가상항목(1)], interval=0)
        with self.assertRaises(ValueError):
            self.run_with_page(
                수신기(self.resume, lambda kind, item: self.events.append(kind)), page)
        self.assertFalse(self.resume.pending_page_active)
        self.assertNotIn("chat", self.events)

    def test_페이지미수용_상태에서_다음페이지_덮어쓰기_거부(self):
        chat = PlatformChat("가상_채팅방_ID", "u", "보류", "youtube")
        self.resume.stage_page([chat], "next-1", 1000, False)
        with self.assertRaises(RuntimeError):
            self.resume.stage_page([chat], "next-2", 1000, False)
        self.assertEqual(len(self.resume.pending_page_chats), 1)
        self.assertEqual(self.resume.pending_page_next_token, "next-1")
        with self.assertRaises(RuntimeError):
            self.resume.clear_completed_page()

    def test_다른_채팅방_재연결시_기존_보류_전송차단(self):
        self.resume.bind_chat("가상_채팅방_ID")
        self.resume.stage_page(
            [PlatformChat("가상_채팅방_ID", "u", "보류", "youtube")],
            "next-1", 1000, False)
        with self.assertRaises(RuntimeError):
            self.resume.bind_chat("다른_채팅방_ID")
        self.assertEqual(len(self.resume.pending_page_chats), 1)

    def test_조정기_유튜브_보류건수_및_확정대기_표시(self):
        coordinator = MultiPlatformReadOnlySession(
            {"youtube": "가상_채팅방_ID"}, lambda *args: True,
            youtube_api_key="가상키" * 8)
        coordinator._youtube_resume.stage_page([
            PlatformChat("가상_채팅방_ID", "u", "보류", "youtube")
        ], "next-1", 1000, False)
        snapshot = coordinator.reconnect_snapshot()["youtube"]
        self.assertEqual(snapshot["수신페이지미수용보류"], 1)
        self.assertTrue(snapshot["수신페이지확정대기"])
        self.assertEqual(snapshot["수신프레임미수용보류"], 0)


if __name__ == "__main__":
    unittest.main()
