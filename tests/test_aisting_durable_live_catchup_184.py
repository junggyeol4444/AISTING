"""184회차 개발 계약검사: 복구 중 신규 채팅 영속 기록/커서 이어읽기.

전체 개발 완료 후 통합 회귀 단계에서 실행할 코드이며
실제 네트워크 수신·실제 시청자 무누락 통과 증거가 아니다.
"""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_broadcaster.durable_public_chat_queue import DurablePublicChatQueue


def public_chat(platform, channel, text, event_id=None):
    return SimpleNamespace(platform=platform, channel=channel,
                           sender="실험용 메시지", text=text, event_id=event_id)


class TestLiveCatchup184(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.spool = DurablePublicChatQueue(Path(self.temp.name) / "pending.sqlite3")
        self.channels = {
            "twitch": "채널A", "chzzk": "채널B",
            "soop": "채널C", "youtube": "채널D",
        }

    def test_과거복구중_4플랫폼신규수신은_커서뒤에순서대로남음(self):
        before = [
            self.spool.append(public_chat("twitch", "채널A", "이전1")),
            self.spool.append(public_chat("chzzk", "채널B", "이전2")),
        ]
        _, old_end = self.spool.recovery_snapshot(self.channels)
        later = [
            self.spool.append(public_chat("soop", "채널C", "신규3")),
            self.spool.append(public_chat("youtube", "채널D", "신규4")),
        ]
        first = list(self.spool.iter_recovery(
            self.channels, through_sequence=old_end, batch_size=1))
        self.assertEqual([p.sequence for p in first], before)
        _, new_end = self.spool.recovery_snapshot(self.channels)
        second = list(self.spool.iter_recovery(
            self.channels, through_sequence=new_end,
            after_sequence=old_end, batch_size=1))
        self.assertEqual([p.sequence for p in second], later)
        self.assertEqual(self.spool.pending_count(), 4)

    def test_복구중_기존메시지확인삭제되어도_후속커서중복없음(self):
        a = self.spool.append(public_chat("twitch", "채널A", "과거"))
        b = self.spool.append(public_chat("soop", "채널C", "새로운"))
        self.assertTrue(self.spool.confirm(a))
        _, ceiling = self.spool.recovery_snapshot(self.channels)
        self.assertEqual([p.sequence for p in self.spool.iter_recovery(
            self.channels, through_sequence=ceiling,
            after_sequence=a)], [b])

    def test_실제서버id재전송만중복방지_동일본문은모두보존(self):
        a = self.spool.append(public_chat("twitch", "채널A", "안녕", "evt1"))
        self.assertIsNone(self.spool.append(
            public_chat("twitch", "채널A", "안녕", "evt1")))
        b = self.spool.append(public_chat("twitch", "채널A", "안녕"))
        c = self.spool.append(public_chat("twitch", "채널A", "안녕"))
        self.assertEqual([p.sequence for p in self.spool.iter_recovery(
            self.channels, through_sequence=c)], [a, b, c])

    def test_잘못된커서는_조용히재조회하지않고거부(self):
        a = self.spool.append(public_chat("youtube", "채널D", "메시지"))
        for after in (-1, True, a + 1, "0"):
            with self.subTest(after=after), self.assertRaises(ValueError):
                list(self.spool.iter_recovery(
                    self.channels, through_sequence=a,
                    after_sequence=after))


if __name__ == "__main__":
    unittest.main()
