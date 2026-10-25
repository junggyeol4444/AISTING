"""182회차: 대량 미처리 채팅의 순차 복구 계약검사 (실행 전)."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_broadcaster.durable_public_chat_queue import DurablePublicChatQueue


def chat(platform, channel, text, event_id=None):
    return SimpleNamespace(platform=platform, channel=channel, sender="시청자",
                           text=text, event_id=event_id)


class TestDurablePagedRecovery182(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.queue = DurablePublicChatQueue(Path(self.temp.name) / "pending.sqlite3")

    def test_4096건_초과도_순서대로_복구(self):
        for i in range(4100):
            self.queue.append(chat("twitch", "채널", str(i)))
        count, last = self.queue.recovery_snapshot({"twitch": "채널"})
        self.assertEqual(count, 4100)
        recovered = list(self.queue.iter_recovery(
            {"twitch": "채널"}, through_sequence=last, batch_size=73))
        self.assertEqual(len(recovered), 4100)
        self.assertEqual([p.message.text for p in recovered],
                         [str(i) for i in range(4100)])
        self.assertEqual(self.queue.pending_count(), 4100)

    def test_플랫폼_채널_격리와_전역_순서(self):
        first = self.queue.append(chat("youtube", "영상", "가"))
        self.queue.append(chat("twitch", "다른", "제외"))
        last = self.queue.append(chat("twitch", "채널", "나"))
        count, ceiling = self.queue.recovery_snapshot(
            {"twitch": "채널", "youtube": "영상"})
        self.assertEqual((count, ceiling), (2, last))
        items = list(self.queue.iter_recovery(
            {"twitch": "채널", "youtube": "영상"},
            through_sequence=ceiling, batch_size=1))
        self.assertEqual([p.sequence for p in items], [first, last])

    def test_복구_시작_뒤_새_메시지는_다음_회차(self):
        self.queue.append(chat("soop", "방", "이전"))
        _, ceiling = self.queue.recovery_snapshot({"soop": "방"})
        self.queue.append(chat("soop", "방", "이후"))
        items = list(self.queue.iter_recovery(
            {"soop": "방"}, through_sequence=ceiling))
        self.assertEqual([p.message.text for p in items], ["이전"])

    def test_확인된_행만_삭제_미확인_행_유지(self):
        a = self.queue.append(chat("chzzk", "채널", "첫째"))
        b = self.queue.append(chat("chzzk", "채널", "둘째"))
        self.assertTrue(self.queue.confirm(a))
        count, ceiling = self.queue.recovery_snapshot({"chzzk": "채널"})
        self.assertEqual(count, 1)
        self.assertEqual([p.sequence for p in self.queue.iter_recovery(
            {"chzzk": "채널"}, through_sequence=ceiling)], [b])

    def test_서버_id_중복만_거부_동일_본문_유지(self):
        self.assertIsNotNone(self.queue.append(chat("twitch", "채널", "안녕", "id1")))
        self.assertIsNone(self.queue.append(chat("twitch", "채널", "안녕", "id1")))
        self.assertIsNotNone(self.queue.append(chat("twitch", "채널", "안녕")))
        self.assertIsNotNone(self.queue.append(chat("twitch", "채널", "안녕")))
        self.assertEqual(self.queue.recovery_snapshot({"twitch": "채널"})[0], 3)

    def test_잘못된_복구_입력은_거부(self):
        for args in (
            {"channels": {}, "through_sequence": 1},
            {"channels": {"twitch": "채널"}, "through_sequence": True},
            {"channels": {"twitch": "채널"}, "through_sequence": -1},
            {"channels": {"twitch": "채널"}, "through_sequence": 1, "batch_size": 0},
        ):
            with self.subTest(args=args), self.assertRaises(ValueError):
                list(self.queue.iter_recovery(**args))


if __name__ == "__main__":
    unittest.main()
