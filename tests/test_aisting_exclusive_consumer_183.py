"""183회차: 실제 공개 채팅 DB 중복 실행 방지의 개발 계약검사.

개발 코드 작성 단계의 검사이며 실행/통과를 주장하지 않는다.
운영자 계정·방송·OBS·모델 호출 없이 임시 SQLite만 사용한다.
"""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_broadcaster.durable_public_chat_queue import DurablePublicChatQueue


def _chat(message):
    return SimpleNamespace(
        platform="chzzk", channel="방송", sender="시청자",
        text=message, event_id=None)


class TestExclusiveConsumer183(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "pending.sqlite3"

    def test_동일_DB_두_창_중복_AI_처리_거부(self):
        first = DurablePublicChatQueue(self.path)
        second = DurablePublicChatQueue(self.path)
        try:
            first.acquire_exclusive_consumer()
            first.acquire_exclusive_consumer()
            with self.assertRaises(RuntimeError):
                second.acquire_exclusive_consumer()
            first.append(_chat("첫 채팅"))
            self.assertEqual(
                [item.message.text for item in first.iter_recovery(
                    {"chzzk": "방송"}, through_sequence=10)], ["첫 채팅"])
        finally:
            first.release_exclusive_consumer()
            second.release_exclusive_consumer()
        second.acquire_exclusive_consumer()
        second.release_exclusive_consumer()

    def test_강제_재시작_대비_해제_후_복구_데이터_불변(self):
        first = DurablePublicChatQueue(self.path)
        first.acquire_exclusive_consumer()
        sequence = first.append(_chat("보류"))
        first.release_exclusive_consumer()
        second = DurablePublicChatQueue(self.path)
        try:
            second.acquire_exclusive_consumer()
            self.assertEqual(second.recovery_snapshot({"chzzk": "방송"}), (1, sequence))
            self.assertEqual(second.pending_count(), 1)
        finally:
            second.release_exclusive_consumer()

    def test_서로_다른_DB는_독립적으로_사용(self):
        first = DurablePublicChatQueue(self.path)
        second = DurablePublicChatQueue(Path(self.temp.name) / "other.sqlite3")
        try:
            first.acquire_exclusive_consumer()
            second.acquire_exclusive_consumer()
            self.assertEqual(first.pending_count(), 0)
            self.assertEqual(second.pending_count(), 0)
        finally:
            first.release_exclusive_consumer()
            second.release_exclusive_consumer()

    def test_다른_파일_소유권과_잠금_소실시_실패(self):
        first = DurablePublicChatQueue(self.path)
        lock_path = self.path.with_name(self.path.name + ".consumer.lock")
        lock_path.mkdir()
        try:
            with self.assertRaises((OSError, RuntimeError)):
                first.acquire_exclusive_consumer()
            self.assertEqual(first.recovery_snapshot({"chzzk": "방송"}), (0, 0))
        finally:
            lock_path.rmdir()


if __name__ == "__main__":
    unittest.main()
