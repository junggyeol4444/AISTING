"""Original stage 094: actual isolated memory-fault recovery with fail-closed guards."""
import unittest
from unittest.mock import patch

from ai_broadcaster.offline_program_recovery import (
    OfflineProgramRecovery, RecoveryDecision, RecoveryDenied,
    run_offline_program_recovery_audit,
)
from ai_broadcaster.platform_chat_connector import OfflinePlatformChatConnector
from ai_broadcaster.offline_chat_receiver import OfflineChatReceiveBuffer, MockReceivedChat
from ai_broadcaster.offline_chat_order import OfflineChatOrder
from ai_broadcaster.offline_chat_reactions import OfflineChatReactions


class Port:
    def __init__(self):
        self.calls = 0
        self.fail = False
        self.injected = None

    def generate(self, item, history):
        self.calls += 1
        if self.injected:
            self.injected()
        if self.fail:
            raise RuntimeError('token-is-not-for-logs')
        return '가상 응답'


def build(messages=('one', 'two', 'two')):
    connector = OfflinePlatformChatConnector(['chzzk'])
    connector.connect()
    receiver = OfflineChatReceiveBuffer()
    receiver.attach(connector)
    order = OfflineChatOrder(receiver)
    for text in messages:
        receiver.inject('chzzk', 'tester', text)
    order.sync()
    port = Port()
    reactions = OfflineChatReactions(receiver, order, reply_port=port)
    reactions.sync()
    return receiver, order, reactions, port, OfflineProgramRecovery(receiver, order, reactions)


class RecoveryTests(unittest.TestCase):
    def test_initial_no_consumption(self):
        receiver, order, reactions, port, recovery = build()
        self.assertEqual(len(reactions.snapshot().pending), 3)
        self.assertEqual(port.calls, 0)
        self.assertEqual(recovery.failure_count, 0)

    def test_manual_success_one_only(self):
        _, _, reactions, port, recovery = build()
        result = recovery.process_one()
        self.assertTrue(result.reply_created)
        self.assertFalse(result.resumed)
        self.assertEqual((result.pending, result.replied, port.calls), (2, 1, 1))

    def test_simulated_failure_preserves_head(self):
        _, _, reactions, port, recovery = build()
        before = reactions.snapshot().pending
        result = recovery.process_one(simulate_failure=True)
        self.assertEqual(reactions.snapshot().pending, before)
        self.assertTrue(result.resumed)
        self.assertFalse(result.reply_created)
        self.assertEqual(result.failure_count, 1)
        self.assertEqual(port.calls, 0)
        self.assertFalse(reactions.snapshot().blocked)

    def test_original_reply_failure_auto_unblocks_without_retry(self):
        _, _, reactions, port, recovery = build()
        port.fail = True
        result = recovery.process_one()
        self.assertTrue(result.resumed)
        self.assertEqual(port.calls, 1)
        self.assertEqual(result.pending, 3)
        self.assertEqual(result.replied, 0)
        port.fail = False
        recovery.process_one()  # explicit next button press only
        self.assertEqual(port.calls, 2)
        self.assertEqual(reactions.snapshot().responded[0].event.ordinal, 1)

    def test_failed_item_not_skipped(self):
        _, _, reactions, _, recovery = build()
        recovery.process_one()
        recovery.process_one(simulate_failure=True)
        outcome = recovery.process_one()
        self.assertEqual(outcome.replied, 2)
        self.assertEqual([item.event.ordinal for item in reactions.snapshot().responded], [1, 2])

    def test_duplicate_content_kept(self):
        _, _, reactions, _, recovery = build()
        for _ in range(3):
            recovery.process_one()
        self.assertEqual([r.event.text for r in reactions.snapshot().responded], ['one', 'two', 'two'])
        self.assertTrue(reactions.snapshot().all_responded)

    def test_manual_audit_isolated(self):
        results = run_offline_program_recovery_audit()
        self.assertEqual(len(results), 4)
        self.assertEqual([r.pending for r in results], [2, 2, 1, 0])
        self.assertTrue(results[1].resumed)

    def test_empty_denied(self):
        *_, recovery = build(())
        with self.assertRaises(RecoveryDenied):
            recovery.process_one()

    def test_invalid_flag_denied(self):
        *_, recovery = build()
        for invalid in (1, None, 'false'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                recovery.process_one(simulate_failure=invalid)

    def test_wrong_source_objects_denied(self):
        receiver, order, reactions, _, _ = build()
        for a, b, c in ((None, order, reactions), (receiver, None, reactions),
                        (receiver, order, None), (OfflineChatReceiveBuffer(), order, reactions)):
            with self.assertRaises(ValueError):
                OfflineProgramRecovery(a, b, c)

    def test_already_blocked_not_silently_reset(self):
        _, _, reactions, _, recovery = build()
        with self.assertRaises(ValueError):
            reactions.reply_next(simulate_failure=True)
        with self.assertRaises(RecoveryDenied):
            recovery.process_one()
        self.assertTrue(reactions.snapshot().blocked)

    def test_prior_order_pause_not_unblocked(self):
        _, order, _, _, recovery = build()
        with self.assertRaises(ValueError):
            order.acknowledge_next(simulate_failure=True)
        with self.assertRaises(RecoveryDenied):
            recovery.process_one()
        self.assertTrue(order.snapshot().paused)

    def test_mutated_source_during_failure_quarantined(self):
        receiver, _, reactions, port, recovery = build()
        port.injected = lambda: receiver._buffer.pop()
        port.fail = True
        with self.assertRaises(RecoveryDenied):
            recovery.process_one()
        self.assertTrue(reactions.snapshot().blocked)
        with self.assertRaises(RecoveryDenied):
            recovery.process_one()

    def test_append_source_during_failure_quarantined(self):
        receiver, _, reactions, port, recovery = build()
        port.injected = lambda: receiver.inject('chzzk', 'tester', 'unexpected')
        port.fail = True
        with self.assertRaises(RecoveryDenied):
            recovery.process_one()
        self.assertTrue(reactions.snapshot().blocked)

    def test_detach_during_error_denies_recovery(self):
        receiver, _, reactions, port, recovery = build()
        port.injected = receiver.detach
        port.fail = True
        with self.assertRaises(RecoveryDenied):
            recovery.process_one()
        self.assertTrue(reactions.snapshot().blocked)

    def test_connection_changed_during_error_denies_recovery(self):
        receiver, _, reactions, port, recovery = build()
        connector = receiver._connector
        port.injected = connector.disconnect
        port.fail = True
        with self.assertRaises(RecoveryDenied):
            recovery.process_one()
        self.assertTrue(reactions.snapshot().blocked)

    def test_modified_order_during_failure_quarantined(self):
        _, order, reactions, port, recovery = build()
        port.injected = lambda: order._events.pop()
        port.fail = True
        with self.assertRaises(RecoveryDenied):
            recovery.process_one()
        self.assertTrue(reactions.snapshot().blocked)

    def test_modified_prior_reply_during_failure_quarantined(self):
        _, _, reactions, port, recovery = build()
        recovery.process_one()
        port.injected = lambda: reactions._replied.clear()
        port.fail = True
        with self.assertRaises(RecoveryDenied):
            recovery.process_one()
        self.assertTrue(reactions.snapshot().blocked)

    def test_unexpected_exception_quarantined(self):
        _, _, reactions, _, recovery = build()
        with patch.object(reactions, 'reply_next', side_effect=RuntimeError('private secret')):
            with self.assertRaisesRegex(RecoveryDenied, '예상 밖'):
                recovery.process_one()
        with self.assertRaises(RecoveryDenied):
            recovery.process_one()

    def test_unblocked_value_error_quarantined(self):
        _, _, _, _, recovery = build()
        with patch.object(recovery.reactions, 'reply_next', side_effect=ValueError('bad')):
            with self.assertRaises(RecoveryDenied):
                recovery.process_one()
        self.assertEqual(recovery.failure_count, 1)

    def test_resume_failure_quarantined(self):
        _, _, reactions, _, recovery = build()
        with patch.object(reactions, 'resume', side_effect=ValueError('fake')):
            with self.assertRaises(RecoveryDenied):
                recovery.process_one(simulate_failure=True)
        self.assertTrue(reactions.snapshot().blocked)

    def test_success_result_corruption_denied(self):
        _, _, reactions, _, recovery = build()
        original = reactions.reply_next
        def corrupt(*args, **kwargs):
            reply = original(*args, **kwargs)
            reactions._replied.clear()
            return reply
        with patch.object(reactions, 'reply_next', side_effect=corrupt):
            with self.assertRaises(RecoveryDenied):
                recovery.process_one()
        with self.assertRaises(RecoveryDenied):
            recovery.process_one()

    def test_no_network_or_process_or_files(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('builtins.open', side_effect=AssertionError('files')):
            self.assertEqual(len(run_offline_program_recovery_audit()), 4)

    def test_safe_flags_and_redaction(self):
        _, _, _, port, recovery = build()
        port.fail = True
        outcome = recovery.process_one()
        self.assertTrue(outcome.mock_only)
        self.assertFalse(outcome.actual_process_restarted)
        self.assertFalse(outcome.actual_stream_recovered)
        self.assertNotIn('token-is-not-for-logs', outcome.describe())

    def test_dataclass_is_immutable(self):
        from dataclasses import FrozenInstanceError
        outcome = run_offline_program_recovery_audit()[0]
        with self.assertRaises(FrozenInstanceError):
            outcome.state = 'not true'

    def test_no_auto_batch_or_schedule(self):
        _, _, _, port, recovery = build()
        recovery.process_one(simulate_failure=True)
        self.assertEqual(port.calls, 0)
        self.assertEqual(recovery.failure_count, 1)


if __name__ == '__main__':
    unittest.main()
