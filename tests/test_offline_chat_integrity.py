"""Original 064: duplicate/omission inspection of mock inbox and FIFO queue."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.platform_chat_connector import OfflinePlatformChatConnector
from ai_broadcaster.offline_chat_receiver import OfflineChatReceiveBuffer, MockReceivedChat
from ai_broadcaster.offline_chat_order import OfflineChatOrder
from ai_broadcaster.offline_chat_integrity import OfflineChatIntegrity


def fixture(*platforms):
    receiver = OfflineChatReceiveBuffer()
    session = OfflinePlatformChatConnector(list(platforms or ('chzzk',)))
    session.connect()
    receiver.attach(session)
    order = OfflineChatOrder(receiver)
    return receiver, session, order, OfflineChatIntegrity(receiver, order)


class IntegrityTests(unittest.TestCase):
    def test_reject_invalid_receiver(self):
        _, _, order, _ = fixture()
        for obj in (None, 'x', object()):
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                OfflineChatIntegrity(obj, order)

    def test_reject_invalid_order(self):
        receiver, _, _, _ = fixture()
        for obj in (None, 'x', object()):
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                OfflineChatIntegrity(receiver, obj)

    def test_reject_other_receiver_order(self):
        receiver, _, _, _ = fixture()
        _, _, other, _ = fixture()
        with self.assertRaises(ValueError):
            OfflineChatIntegrity(receiver, other)

    def test_empty_is_consistent_not_proof_of_delivery(self):
        _, _, _, audit = fixture()
        result = audit.inspect()
        self.assertTrue(result.structurally_consistent)
        self.assertEqual((result.received, result.synced, result.unsynced), (0, 0, 0))
        self.assertTrue(result.mock_only)
        self.assertIn('미도착', result.describe())

    def test_single_received_unsynced_not_missing(self):
        receiver, _, _, audit = fixture()
        receiver.inject('chzzk', 'a', 'hello')
        report = audit.inspect()
        self.assertTrue(report.structurally_consistent)
        self.assertEqual(report.unsynced, 1)
        self.assertIn('누락 판정 아님', report.describe())

    def test_incremental_unsynced_after_sync(self):
        receiver, _, order, audit = fixture()
        receiver.inject('chzzk', 'a', '1')
        order.sync()
        receiver.inject('chzzk', 'a', '2')
        report = audit.inspect()
        self.assertEqual((report.received, report.synced, report.unsynced), (2, 1, 1))
        self.assertEqual(report.issues, ())

    def test_sync_and_process_no_missing(self):
        receiver, _, order, audit = fixture('chzzk', 'youtube', 'twitch')
        for platform in ('youtube', 'chzzk', 'twitch'):
            receiver.inject(platform, 'a', 'hello')
        order.sync()
        order.acknowledge_next()
        report = audit.inspect()
        self.assertEqual((report.received, report.synced, report.checked, report.pending), (3, 3, 1, 2))
        self.assertTrue(report.structurally_consistent)

    def test_same_content_retained_not_error(self):
        receiver, _, order, audit = fixture()
        for _ in range(4):
            receiver.inject('chzzk', 'a', 'same')
        order.sync()
        report = audit.inspect()
        self.assertTrue(report.structurally_consistent)
        self.assertEqual((report.repeated_content_groups, report.repeated_content_extra), (1, 3))
        self.assertEqual(len(order.snapshot().pending), 4)

    def test_distinct_sender_not_content_duplicate(self):
        receiver, _, _, audit = fixture()
        receiver.inject('chzzk', 'a', 'same')
        receiver.inject('chzzk', 'b', 'same')
        self.assertEqual(audit.inspect().repeated_content_extra, 0)

    def test_distinct_platform_not_content_duplicate(self):
        receiver, _, _, audit = fixture('chzzk', 'youtube')
        receiver.inject('chzzk', 'a', 'same')
        receiver.inject('youtube', 'a', 'same')
        self.assertEqual(audit.inspect().repeated_content_extra, 0)

    def test_duplicate_ordinal_detected(self):
        receiver, _, _, audit = fixture()
        receiver.inject('chzzk', 'a', 'first')
        receiver._buffer.append(MockReceivedChat(1, 'chzzk', 'b', 'second'))
        self.assertIn('순번 중복', ' '.join(audit.inspect().issues))

    def test_missing_ordinal_detected(self):
        receiver, _, _, audit = fixture()
        receiver._buffer.append(MockReceivedChat(1, 'chzzk', 'a', 'first'))
        receiver._buffer.append(MockReceivedChat(3, 'chzzk', 'b', 'third'))
        self.assertIn('누락', ' '.join(audit.inspect().issues))

    def test_missing_first_detected(self):
        receiver, _, _, audit = fixture()
        receiver._buffer.append(MockReceivedChat(2, 'chzzk', 'a', 'second'))
        self.assertIn('#1', ' '.join(audit.inspect().issues))

    def test_reorder_detected(self):
        receiver, _, _, audit = fixture()
        receiver._buffer.extend((MockReceivedChat(2, 'chzzk', 'a', '2'),
                                 MockReceivedChat(1, 'chzzk', 'a', '1')))
        self.assertIn('접수 순서', ' '.join(audit.inspect().issues))

    def test_modified_prefix_detected(self):
        receiver, _, order, audit = fixture()
        receiver.inject('chzzk', 'a', 'first')
        order.sync()
        receiver._buffer[0] = MockReceivedChat(1, 'chzzk', 'a', 'tampered')
        report = audit.inspect()
        self.assertIn('접두 기록', ' '.join(report.issues))
        self.assertEqual(report.unsynced, 0)

    def test_truncated_synced_history_detected(self):
        receiver, _, order, audit = fixture()
        receiver.inject('chzzk', 'a', 'first')
        order.sync()
        receiver._buffer.clear()
        self.assertIn('접두 기록', ' '.join(audit.inspect().issues))

    def test_bogus_ordinal_type_detected(self):
        receiver, _, _, audit = fixture()
        receiver._buffer.append(MockReceivedChat(True, 'chzzk', 'a', 'x'))
        self.assertIn('올바르지 않은', ' '.join(audit.inspect().issues))

    def test_bogus_record_type_detected(self):
        receiver, _, _, audit = fixture()
        receiver._buffer.append('not a message')
        self.assertIn('형식', ' '.join(audit.inspect().issues))

    def test_malformed_content_detected_without_crash(self):
        receiver, _, _, audit = fixture()
        receiver._buffer.append(MockReceivedChat(1, 'chzzk', [], 'x'))
        self.assertIn('내용 형식', ' '.join(audit.inspect().issues))

    def test_huge_ordinal_does_not_allocate_huge_range(self):
        receiver, _, _, audit = fixture()
        receiver._buffer.append(MockReceivedChat(10**80, 'chzzk', 'a', 'x'))
        self.assertIn('누락', ' '.join(audit.inspect().issues))

    def test_paused_state_read_only(self):
        receiver, _, order, audit = fixture()
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        with self.assertRaises(ValueError):
            order.acknowledge_next(simulate_failure=True)
        report = audit.inspect()
        self.assertTrue(report.paused)
        self.assertEqual(len(order.snapshot().pending), 1)

    def test_disconnect_retains_observed(self):
        receiver, session, order, audit = fixture()
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        session.disconnect()
        self.assertTrue(audit.inspect().structurally_consistent)
        self.assertEqual(audit.inspect().received, 1)

    def test_inspect_is_idempotent_and_no_state_change(self):
        receiver, _, order, audit = fixture()
        receiver.inject('chzzk', 'a', 'x')
        before = (receiver.snapshot(), order.snapshot())
        self.assertEqual(audit.inspect(), audit.inspect())
        self.assertEqual((receiver.snapshot(), order.snapshot()), before)

    def test_no_network_disk_or_process_calls(self):
        receiver, _, order, audit = fixture()
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('db')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('builtins.open', side_effect=AssertionError('disk')):
            self.assertTrue(audit.inspect().structurally_consistent)


if __name__ == '__main__':
    unittest.main()
