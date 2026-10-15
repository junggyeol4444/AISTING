"""Stage 063 FIFO synthetic ingress ordering tests."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.platform_chat_connector import OfflinePlatformChatConnector
from ai_broadcaster.offline_chat_receiver import OfflineChatReceiveBuffer, MockReceivedChat
from ai_broadcaster.offline_chat_order import OfflineChatOrder


def fixture(*platforms):
    receiver = OfflineChatReceiveBuffer()
    session = OfflinePlatformChatConnector(list(platforms))
    session.connect()
    receiver.attach(session)
    return receiver, session, OfflineChatOrder(receiver)


class OrderTests(unittest.TestCase):
    def test_requires_receiver(self):
        for invalid in (None, 1, [], object()):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                OfflineChatOrder(invalid)

    def test_empty_default(self):
        receiver = OfflineChatReceiveBuffer()
        state = OfflineChatOrder(receiver).snapshot()
        self.assertEqual((state.queued, state.processed, state.pending), ((), (), ()))
        self.assertTrue(state.mock_only)
        self.assertFalse(state.paused)

    def test_no_next_before_sync(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        with self.assertRaisesRegex(ValueError, '동기화'):
            order.acknowledge_next()

    def test_sync_requires_manual_action(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        self.assertEqual(order.snapshot().queued, ())
        self.assertEqual(len(order.sync().pending), 1)

    def test_fifo_multiple_platforms(self):
        receiver, _, order = fixture('chzzk', 'youtube', 'twitch')
        for platform in ('youtube', 'chzzk', 'twitch'):
            receiver.inject(platform, 'a', platform)
        order.sync()
        self.assertEqual([order.acknowledge_next().platform for _ in range(3)],
                         ['youtube', 'chzzk', 'twitch'])
        self.assertEqual(order.snapshot().pending, ())

    def test_identical_text_not_deduplicated(self):
        receiver, _, order = fixture('chzzk')
        for _ in range(3):
            receiver.inject('chzzk', 'a', 'same')
        order.sync()
        self.assertEqual([order.acknowledge_next().ordinal for _ in range(3)], [1, 2, 3])

    def test_sync_idempotent(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        order.sync()
        self.assertEqual(len(order.snapshot().queued), 1)

    def test_incremental_sync_retains_cursor(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'first')
        order.sync()
        order.acknowledge_next()
        receiver.inject('chzzk', 'a', 'second')
        order.sync()
        self.assertEqual([x.ordinal for x in order.snapshot().processed], [1])
        self.assertEqual(order.acknowledge_next().ordinal, 2)

    def test_failure_keeps_head(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        with self.assertRaisesRegex(ValueError, '보존'):
            order.acknowledge_next(simulate_failure=True)
        self.assertEqual([x.ordinal for x in order.snapshot().pending], [1])
        self.assertTrue(order.snapshot().paused)

    def test_failure_requires_resume(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        with self.assertRaises(ValueError):
            order.acknowledge_next(simulate_failure=True)
        with self.assertRaisesRegex(ValueError, '수동 재개'):
            order.acknowledge_next()
        order.resume()
        self.assertEqual(order.acknowledge_next().ordinal, 1)

    def test_double_resume_rejected(self):
        _, _, order = fixture('chzzk')
        with self.assertRaises(ValueError):
            order.resume()

    def test_invalid_failure_argument_no_progress(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        for value in (None, 1, 'true'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                order.acknowledge_next(simulate_failure=value)
        self.assertEqual(len(order.snapshot().pending), 1)

    def test_sync_while_paused_keeps_pause_and_head(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        with self.assertRaises(ValueError):
            order.acknowledge_next(simulate_failure=True)
        receiver.inject('chzzk', 'a', 'y')
        order.sync()
        self.assertTrue(order.snapshot().paused)
        self.assertEqual([x.ordinal for x in order.snapshot().pending], [1, 2])

    def test_disconnect_does_not_drop_pending(self):
        receiver, session, order = fixture('youtube')
        receiver.inject('youtube', 'a', 'x')
        session.disconnect()
        order.sync()
        self.assertEqual(order.acknowledge_next().ordinal, 1)

    def test_no_auto_sync_on_reconnect(self):
        receiver, session, order = fixture('youtube')
        receiver.inject('youtube', 'a', 'x')
        order.sync()
        session.disconnect()
        session.connect()
        receiver.attach(session)
        receiver.inject('youtube', 'a', 'y')
        self.assertEqual(len(order.snapshot().queued), 1)
        self.assertEqual(len(order.sync().queued), 2)

    def test_no_mutation_of_received_events(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        original = receiver.snapshot().buffered
        order.sync()
        order.acknowledge_next()
        self.assertEqual(receiver.snapshot().buffered, original)

    def test_gap_refused_atomically(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        receiver._buffer.append(MockReceivedChat(3, 'chzzk', 'a', 'z'))
        with self.assertRaisesRegex(ValueError, '누락'):
            order.sync()
        self.assertEqual(order.snapshot().queued, ())

    def test_prefix_mutation_refused_atomically(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        receiver._buffer[0] = MockReceivedChat(1, 'chzzk', 'a', 'tamper')
        with self.assertRaisesRegex(ValueError, '변경'):
            order.sync()
        self.assertEqual(order.snapshot().queued[0].text, 'x')

    def test_prefix_truncation_refused(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        receiver._buffer.clear()
        with self.assertRaises(ValueError):
            order.sync()
        self.assertEqual(len(order.snapshot().queued), 1)

    def test_no_io_for_manual_operations(self):
        receiver, _, order = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('db')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            order.sync()
            order.acknowledge_next()
            self.assertIn('실제 플랫폼 메시지 0건', order.snapshot().describe())

    def test_no_hidden_automatic_processing(self):
        receiver, _, order = fixture('chzzk')
        for i in range(10):
            receiver.inject('chzzk', 'a', str(i))
        order.sync()
        self.assertEqual(len(order.snapshot().pending), 10)
        order.acknowledge_next()
        self.assertEqual(len(order.snapshot().pending), 9)


if __name__ == '__main__':
    unittest.main()
