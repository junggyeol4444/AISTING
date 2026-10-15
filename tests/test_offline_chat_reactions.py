"""Original 065: manual all-chat response bridge, no real network or LLM."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.platform_chat_connector import OfflinePlatformChatConnector
from ai_broadcaster.offline_chat_receiver import OfflineChatReceiveBuffer, MockReceivedChat
from ai_broadcaster.offline_chat_order import OfflineChatOrder
from ai_broadcaster.offline_chat_reactions import OfflineChatReactions


class ControlledPort:
    def __init__(self):
        self.calls = []
        self.fail = False
        self.value = '모의 응답'

    def generate(self, item, history):
        self.calls.append((item, tuple(history)))
        if self.fail:
            raise RuntimeError('SECRET /token/secret')
        return self.value


def fixture(*platforms):
    session = OfflinePlatformChatConnector(list(platforms))
    session.connect()
    receiver = OfflineChatReceiveBuffer()
    receiver.attach(session)
    order = OfflineChatOrder(receiver)
    port = ControlledPort()
    reactions = OfflineChatReactions(receiver, order, reply_port=port)
    return session, receiver, order, port, reactions


class ReactionTests(unittest.TestCase):
    def test_requires_correct_sources(self):
        receiver = OfflineChatReceiveBuffer()
        order = OfflineChatOrder(receiver)
        for bad in (None, object(), 1):
            with self.assertRaises(ValueError):
                OfflineChatReactions(bad, order)
            with self.assertRaises(ValueError):
                OfflineChatReactions(receiver, bad)
        with self.assertRaises(ValueError):
            OfflineChatReactions(receiver, OfflineChatOrder(OfflineChatReceiveBuffer()))

    def test_empty_state_no_false_success(self):
        _, _, _, _, reactions = fixture('chzzk')
        state = reactions.snapshot()
        self.assertFalse(state.all_responded)
        self.assertTrue(state.mock_only)
        self.assertEqual((state.received, state.unsynced, state.attempts), (0, 0, 0))

    def test_no_implicit_sync_or_response(self):
        _, receiver, order, port, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'hello')
        self.assertEqual(reactions.snapshot().unsynced, 1)
        self.assertEqual(reactions.snapshot().staged, ())
        order.sync()
        self.assertEqual(reactions.snapshot().staged, ())
        self.assertEqual(port.calls, [])

    def test_sync_requires_order_first(self):
        _, receiver, _, _, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'hello')
        reactions.sync()
        self.assertEqual(reactions.snapshot().unsynced, 1)
        with self.assertRaisesRegex(ValueError, '동기화'):
            reactions.reply_next()

    def test_fifo_across_platforms(self):
        _, receiver, order, _, reactions = fixture('chzzk', 'youtube', 'twitch')
        for platform in ('youtube', 'chzzk', 'twitch'):
            receiver.inject(platform, 'a', platform)
        order.sync()
        reactions.sync()
        self.assertEqual([reactions.reply_next().event.platform for _ in range(3)],
                         ['youtube', 'chzzk', 'twitch'])
        self.assertTrue(reactions.snapshot().all_responded)

    def test_duplicate_content_separate_replies(self):
        _, receiver, order, port, reactions = fixture('chzzk')
        for _ in range(3):
            receiver.inject('chzzk', 'same', 'same')
        order.sync()
        reactions.sync()
        reactions.reply_batch()
        self.assertEqual([item.event.ordinal for item in reactions.snapshot().responded], [1, 2, 3])
        self.assertEqual(len(port.calls), 3)

    def test_sender_not_filtered(self):
        _, receiver, order, _, reactions = fixture('chzzk')
        for sender in ('viewer', 'moderator', 'bot', 'admin'):
            receiver.inject('chzzk', sender, 'ㅋㅋㅋ')
        order.sync()
        reactions.sync()
        reactions.reply_batch()
        self.assertEqual(len(reactions.snapshot().responded), 4)

    def test_no_response_before_manual_button(self):
        _, receiver, order, port, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'hello')
        order.sync()
        reactions.sync()
        self.assertEqual(port.calls, [])
        self.assertEqual(len(reactions.snapshot().pending), 1)

    def test_existing_order_ack_not_a_reply(self):
        _, receiver, order, _, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'hello')
        order.sync()
        order.acknowledge_next()
        reactions.sync()
        self.assertEqual(len(reactions.snapshot().responded), 0)
        reactions.reply_next()
        self.assertTrue(reactions.snapshot().all_responded)

    def test_incremental_sync_does_not_repeat(self):
        _, receiver, order, _, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'first')
        order.sync()
        reactions.sync()
        reactions.reply_next()
        receiver.inject('chzzk', 'a', 'second')
        order.sync()
        reactions.sync()
        reactions.sync()
        self.assertEqual([e.ordinal for e in reactions.snapshot().pending], [2])
        reactions.reply_next()
        self.assertEqual([x.event.ordinal for x in reactions.snapshot().responded], [1, 2])

    def test_failure_keeps_head_and_redacts_exception(self):
        _, receiver, order, port, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'secret')
        order.sync()
        reactions.sync()
        port.fail = True
        with self.assertRaisesRegex(ValueError, '생성 실패') as ctx:
            reactions.reply_next()
        self.assertNotIn('SECRET', str(ctx.exception))
        self.assertTrue(reactions.snapshot().blocked)
        self.assertEqual([e.ordinal for e in reactions.snapshot().pending], [1])

    def test_no_automatic_retry(self):
        _, receiver, order, port, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        reactions.sync()
        port.fail = True
        with self.assertRaises(ValueError):
            reactions.reply_next()
        port.fail = False
        with self.assertRaisesRegex(ValueError, '수동 재개'):
            reactions.reply_next()
        self.assertEqual(len(port.calls), 1)
        reactions.resume()
        reactions.reply_next()
        self.assertEqual(len(port.calls), 2)

    def test_simulated_failure_preserves_pending(self):
        _, receiver, order, port, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        reactions.sync()
        with self.assertRaises(ValueError):
            reactions.reply_next(simulate_failure=True)
        self.assertEqual(port.calls, [])
        self.assertEqual(len(reactions.snapshot().pending), 1)
        reactions.resume()
        reactions.reply_next()
        self.assertTrue(reactions.snapshot().all_responded)

    def test_invalid_response_does_not_advance(self):
        _, receiver, order, port, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        reactions.sync()
        for value in (None, '', ' ', 1, 'x' * 6001):
            port.value = value
            with self.assertRaises(ValueError):
                reactions.reply_next()
            self.assertEqual(len(reactions.snapshot().pending), 1)
            reactions.resume()

    def test_order_paused_prevents_reply(self):
        _, receiver, order, _, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        reactions.sync()
        with self.assertRaises(ValueError):
            order.acknowledge_next(simulate_failure=True)
        with self.assertRaisesRegex(ValueError, '63단계'):
            reactions.reply_next()
        order.resume()
        reactions.reply_next()
        self.assertTrue(reactions.snapshot().all_responded)

    def test_order_mutation_rejected(self):
        _, receiver, order, port, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        reactions.sync()
        order._events[0] = MockReceivedChat(1, 'chzzk', 'a', 'tamper')
        with self.assertRaises(ValueError):
            reactions.reply_next()
        self.assertEqual(port.calls, [])

    def test_receiver_mutation_rejected(self):
        _, receiver, order, port, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        reactions.sync()
        receiver._buffer[0] = MockReceivedChat(1, 'chzzk', 'a', 'tamper')
        with self.assertRaises(ValueError):
            reactions.reply_next()
        self.assertEqual(port.calls, [])

    def test_gap_rejected_without_partial_sync(self):
        _, receiver, order, _, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        reactions.sync()
        order._events.append(MockReceivedChat(3, 'chzzk', 'a', 'z'))
        with self.assertRaises(ValueError):
            reactions.sync()
        self.assertEqual(len(reactions.snapshot().staged), 1)

    def test_batch_bounded_and_invalid_type(self):
        _, receiver, order, _, reactions = fixture('chzzk')
        for i in range(60):
            receiver.inject('chzzk', 'a', str(i))
        order.sync()
        reactions.sync()
        for value in (0, 51, True, '50', None):
            with self.assertRaises(ValueError):
                reactions.reply_batch(value)
        reactions.reply_batch()
        self.assertEqual((len(reactions.snapshot().responded), len(reactions.snapshot().pending)), (50, 10))
        reactions.reply_batch()
        self.assertTrue(reactions.snapshot().all_responded)

    def test_batch_failure_preserves_tail(self):
        _, receiver, order, port, reactions = fixture('chzzk')
        for i in range(3):
            receiver.inject('chzzk', 'a', str(i))
        order.sync()
        reactions.sync()
        port.fail = True
        with self.assertRaises(ValueError):
            reactions.reply_batch()
        self.assertEqual(len(reactions.snapshot().pending), 3)
        self.assertEqual(len(port.calls), 1)

    def test_disconnect_keeps_existing_events(self):
        session, receiver, order, _, reactions = fixture('youtube')
        receiver.inject('youtube', 'a', 'x')
        order.sync()
        reactions.sync()
        session.disconnect()
        reactions.reply_next()
        self.assertTrue(reactions.snapshot().all_responded)

    def test_sources_not_mutated(self):
        _, receiver, order, _, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        old_received = receiver.snapshot()
        old_order = order.snapshot()
        reactions.sync()
        reactions.reply_next()
        self.assertEqual(receiver.snapshot(), old_received)
        self.assertEqual(order.snapshot(), old_order)

    def test_no_io(self):
        _, receiver, order, _, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            order.sync()
            reactions.sync()
            reactions.reply_next()
        self.assertIn('실제 플랫폼 채팅 0건', reactions.snapshot().describe())

    def test_invalid_failure_flag_does_not_advance(self):
        _, receiver, order, _, reactions = fixture('chzzk')
        receiver.inject('chzzk', 'a', 'x')
        order.sync()
        reactions.sync()
        with self.assertRaises(ValueError):
            reactions.reply_next(simulate_failure=1)
        self.assertEqual(reactions.snapshot().attempts, 0)

    def test_no_resume_without_failure(self):
        _, _, _, _, reactions = fixture('chzzk')
        with self.assertRaises(ValueError):
            reactions.resume()


if __name__ == '__main__':
    unittest.main()
