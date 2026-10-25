"""185절: 4플랫폼 실제 서버 이벤트 ID 처리 완료/복구 계약검사.

기능 개발 단계에 작성한 검사다. 실행/통과는 전체 기능 개발 이후.
"""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_broadcaster.durable_public_chat_queue import DurablePublicChatQueue


def chat(text, event_id, platform="twitch", channel="방송"):
    return SimpleNamespace(
        platform=platform, channel=channel, sender="시청자",
        text=text, event_id=event_id)


class TestConfirmedServerEvents185(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "pending.sqlite3"

    def test_완료한_실제_서버_ID는_재시작후_중복등록하지않음(self):
        q = DurablePublicChatQueue(self.path)
        seq = q.append(chat("원래 채팅", "서버-1"))
        self.assertIsNotNone(seq)
        self.assertTrue(q.confirm(seq))
        restarted = DurablePublicChatQueue(self.path)
        self.assertIsNone(restarted.append(chat("원래 채팅", "서버-1")))
        self.assertEqual(restarted.pending_count(), 0)

    def test_서로_다른_실제_ID와_동일본문_별개채팅은_보존(self):
        q = DurablePublicChatQueue(self.path)
        ids = [
            q.append(chat("안녕", "A")),
            q.append(chat("안녕", "B")),
            q.append(chat("안녕", None)),
            q.append(chat("안녕", None)),
        ]
        self.assertEqual(len(set(ids)), 4)
        self.assertEqual(q.pending_count(), 4)

    def test_같은_서버_ID라도_플랫폼_채널이_다르면_별개(self):
        q = DurablePublicChatQueue(self.path)
        a = q.append(chat("1", "같은-id", "youtube", "방1"))
        b = q.append(chat("2", "같은-id", "youtube", "방2"))
        c = q.append(chat("3", "같은-id", "chzzk", "방1"))
        for seq in (a, b, c):
            self.assertTrue(q.confirm(seq))
        self.assertIsNone(q.append(chat("1", "같은-id", "youtube", "방1")))
        self.assertIsNotNone(q.append(chat("새", "새-id", "youtube", "방1")))

    def test_오류로_미확인된_채팅은_완료장부에_기록되지않음(self):
        q = DurablePublicChatQueue(self.path)
        seq = q.append(chat("미응답", "id-2"))
        self.assertFalse(q.confirm(seq + 1))
        restarted = DurablePublicChatQueue(self.path)
        self.assertIsNone(restarted.append(chat("미응답", "id-2")))
        self.assertEqual(
            [entry.sequence for entry in restarted.iter_recovery(
                {"twitch": "방송"}, through_sequence=seq)], [seq])
        self.assertTrue(restarted.confirm(seq))
        self.assertIsNone(restarted.append(chat("미응답", "id-2")))

    def test_기존_단일테이블_데이터를_재시작후_보존(self):
        # Additive migration only: original pending data and sequence do not reset.
        import sqlite3
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA application_id=1095980103")  # ASTG
            db.execute(
                "CREATE TABLE pending_public_chat("
                "sequence INTEGER PRIMARY KEY AUTOINCREMENT,"
                "platform TEXT NOT NULL,channel TEXT NOT NULL,"
                "sender TEXT NOT NULL,message TEXT NOT NULL,"
                "event_id TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute(
                "INSERT INTO pending_public_chat"
                "(platform,channel,sender,message,event_id)"
                " VALUES('soop','기존','시청자','기존 원문','기존-1')")
        q = DurablePublicChatQueue(self.path)
        self.assertEqual(q.recovery_snapshot({"soop": "기존"})[0], 1)
        seq = next(q.iter_recovery(
            {"soop": "기존"}, through_sequence=1))
        self.assertEqual(seq.message.text, "기존 원문")


if __name__ == "__main__":
    unittest.main()
