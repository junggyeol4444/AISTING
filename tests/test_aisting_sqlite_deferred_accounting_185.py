"""185절: 실제 4플랫폼 수신 → 영속 SQLite → AI FIFO 구분 계측 계약검사.

로컬 가상 콜백 계약만 검사하고 실제 플랫폼 시청자·모델 처리·방송
성공을 증명하지 않는다. 전체 기능 개발 완료 뒤 실행 대상이다.
"""
import unittest

from ai_broadcaster.multi_platform_session import (
    MultiPlatformReadOnlySession, SQLITE_DEFERRED_CHAT)
from ai_broadcaster.multiplatform_readonly import PlatformChat


class TestDeferredSqliteAccounting185(unittest.TestCase):
    def setUp(self):
        self.session = MultiPlatformReadOnlySession(
            {"twitch": "채널"}, lambda kind, item: SQLITE_DEFERRED_CHAT)

    def test_영속저장직후_아직AI에들어가지않았음을_기록(self):
        chat = PlatformChat(
            "채널", "시청자", "첫 질문", "twitch", "id1", None)
        self.assertTrue(self.session._callbacks["twitch"]("chat", chat))
        stats = self.session.reconnect_snapshot()["twitch"]
        self.assertEqual(stats["SQLite우선보존"], 1)
        self.assertEqual(stats["SQLite보존AI대기"], 1)
        self.assertEqual(stats["SQLite보존후AI재등록"], 0)
        self.session.note_deferred_sqlite_chat_enqueued("twitch")
        after = self.session.reconnect_snapshot()["twitch"]
        self.assertEqual(after["SQLite보존후AI재등록"], 1)
        self.assertEqual(after["SQLite보존AI대기"], 0)

    def test_서버이벤트_ID_반복은_누적_영속대기_증가하지않음(self):
        message = PlatformChat(
            "채널", "시청자", "같음", "twitch", "서버-id", None)
        callback = self.session._callbacks["twitch"]
        self.assertTrue(callback("chat", message))
        self.assertTrue(callback("chat", message))
        stats = self.session.reconnect_snapshot()["twitch"]
        self.assertEqual(stats["SQLite우선보존"], 1)

    def test_서버ID없는_별개메시지는_둘다보존(self):
        callback = self.session._callbacks["twitch"]
        for _ in range(2):
            self.assertTrue(callback("chat", PlatformChat(
                "채널", "시청자", "같음", "twitch", None, None)))
        stats = self.session.reconnect_snapshot()["twitch"]
        self.assertEqual(stats["SQLite우선보존"], 2)
        self.assertEqual(stats["SQLite보존AI대기"], 2)

    def test_재등록_통계가_콜백_정산보다_먼저와도_소실하지않음(self):
        self.session.note_deferred_sqlite_chat_enqueued("twitch")
        self.assertEqual(
            self.session.reconnect_snapshot()["twitch"]["SQLite보존후AI재등록"],
            1)
        callback = self.session._callbacks["twitch"]
        self.assertTrue(callback("chat", PlatformChat(
            "채널", "시청자", "뒤에완료", "twitch", "id", None)))
        self.assertEqual(
            self.session.reconnect_snapshot()["twitch"]["SQLite보존AI대기"],
            0)


if __name__ == "__main__":
    unittest.main()
