"""184절: 기존 4플랫폼 채팅 영속 큐의 복구·신규 수신 커서 개발 계약검사.

원본 네트워크·OAuth·방송/녹화·로컬 모델을 실행하지 않는다.
전체 기능 개발 완료 뒤 회귀 단계에서 함께 실행한다.
"""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_broadcaster.durable_public_chat_queue import DurablePublicChatQueue


def chat(platform, channel, text, event_id=None):
    return SimpleNamespace(
        platform=platform, channel=channel, sender="시청자",
        text=text, event_id=event_id)


class TestLiveRecoveryCursor184(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.queue = DurablePublicChatQueue(
            Path(tmp.name) / "pending_public_chat.sqlite3")

    def test_과거_복구_뒤_신규_수신을_정확히_이어읽음(self):
        selected = {"twitch": "채널", "youtube": "영상"}
        old = [self.queue.append(chat("twitch", "채널", str(i)))
               for i in range(5)]
        _, upper = self.queue.recovery_snapshot(selected)
        newer = [self.queue.append(chat("youtube", "영상", str(i)))
                 for i in range(5, 10)]
        before = list(self.queue.iter_recovery(
            selected, through_sequence=upper, batch_size=2))
        self.assertEqual([item.sequence for item in before], old)
        _, new_upper = self.queue.recovery_snapshot(selected)
        after = list(self.queue.iter_recovery(
            selected, after_sequence=upper,
            through_sequence=new_upper, batch_size=2))
        self.assertEqual([item.sequence for item in after], newer)
        self.assertEqual(self.queue.pending_count(), 10)

    def test_확인_삭제된_기존_건을_다시_큐에_넣지_않음(self):
        selected = {"chzzk": "채널"}
        earlier = self.queue.append(chat("chzzk", "채널", "첫"))
        next_seq = self.queue.append(chat("chzzk", "채널", "둘"))
        self.assertTrue(self.queue.confirm(earlier))
        self.assertEqual([item.sequence for item in self.queue.iter_recovery(
            selected, after_sequence=earlier,
            through_sequence=next_seq)], [next_seq])

    def test_선택하지_않은_채널은_복구_범위에서_제외(self):
        self.queue.append(chat("soop", "다른 채널", "제외"))
        selected = {"soop": "원래 채널"}
        self.assertEqual(self.queue.recovery_snapshot(selected), (0, 0))
        self.assertEqual(list(self.queue.iter_recovery(
            selected, through_sequence=0)), [])

    def test_잘못된_이어읽기_커서는_거부(self):
        for after in (True, -1, 4, 1.5):
            with self.subTest(after=after), self.assertRaises(ValueError):
                list(self.queue.iter_recovery(
                    {"twitch": "채널"},
                    through_sequence=3, after_sequence=after))


if __name__ == "__main__":
    unittest.main()
