"""Original 069: recovery without any actual external connection."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.platform_chat_connector import OfflinePlatformChatConnector
from ai_broadcaster.offline_chat_receiver import OfflineChatReceiveBuffer
from ai_broadcaster.offline_chat_order import OfflineChatOrder
from ai_broadcaster.offline_chat_reactions import OfflineChatReactions
from ai_broadcaster.offline_chat_recovery import OfflineChatConnectionRecovery


class OfflineRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.connector = OfflinePlatformChatConnector(['chzzk', 'youtube'])
        self.receiver = OfflineChatReceiveBuffer()
        self.order = OfflineChatOrder(self.receiver)
        self.reactions = OfflineChatReactions(self.receiver, self.order)
        self.recovery = OfflineChatConnectionRecovery(self.connector, self.receiver, self.order, self.reactions)

    def ready(self):
        self.connector.connect()
        self.receiver.attach(self.connector)

    def seed(self):
        self.ready()
        for platform, sender, text in [('chzzk','a','안녕'),('youtube','b','안녕'),
                                       ('chzzk','a','안녕'),('youtube','b','다음')]:
            self.receiver.inject(platform, sender, text)
        self.order.sync()
        self.reactions.sync()
        self.reactions.reply_next()
        return self.receiver.snapshot().buffered

    def test_precondition_no_connect(self):
        with self.assertRaises(ValueError): self.recovery.inject_outage(self.connector)
        self.assertEqual(self.connector.snapshot().attempts, 0)

    def test_precondition_no_attach(self):
        self.connector.connect()
        with self.assertRaises(ValueError): self.recovery.inject_outage(self.connector)

    def test_empty_inbox_can_recover(self):
        self.ready()
        self.recovery.inject_outage(self.connector)
        self.recovery.reconnect(self.connector)
        self.assertTrue(self.recovery.reattach(self.connector).recovery_complete)

    def test_outage_blocks_new_ingress_and_preserves(self):
        old = self.seed()
        report = self.recovery.inject_outage(self.connector)
        self.assertFalse(report.connected)
        self.assertFalse(report.attached)
        self.assertEqual(self.receiver.snapshot().buffered, old)
        self.assertEqual(report.replied, 1)
        with self.assertRaises(ValueError): self.receiver.inject('chzzk', 'a', 'blocked')
        self.assertEqual(self.receiver.snapshot().buffered, old)

    def test_failed_reconnect_no_automatic_retry_or_attach(self):
        self.seed()
        self.recovery.inject_outage(self.connector)
        report = self.recovery.reconnect(self.connector, fail_handshake=True)
        self.assertEqual((report.reconnect_attempts, report.failed_attempts), (1, 1))
        self.assertFalse(report.connected)
        self.assertFalse(report.attached)
        self.assertEqual(self.connector.snapshot().attempts, 2)
        self.assertEqual(self.connector.snapshot().connected, ())
        with self.assertRaises(ValueError): self.recovery.reattach(self.connector)
        self.assertEqual(self.connector.snapshot().attempts, 2)

    def test_manual_retry_then_manual_attach_retains_all(self):
        old = self.seed()
        self.recovery.inject_outage(self.connector)
        self.recovery.reconnect(self.connector, fail_handshake=True)
        report = self.recovery.reconnect(self.connector)
        self.assertTrue(report.connected)
        self.assertFalse(report.attached)
        self.assertFalse(report.recovery_complete)
        with self.assertRaises(ValueError): self.receiver.inject('chzzk','a','not yet')
        report = self.recovery.reattach(self.connector)
        self.assertTrue(report.recovery_complete)
        self.assertEqual((report.accepted, report.staged, report.replied, report.pending), (4,4,1,3))
        self.assertEqual(self.receiver.snapshot().buffered, old)
        self.reactions.reply_batch()
        self.assertEqual([r.event.ordinal for r in self.reactions.snapshot().responded], [1,2,3,4])
        self.assertTrue(self.recovery.snapshot(self.connector).recovery_complete)
        self.receiver.inject('chzzk','c','새 채팅')
        self.assertTrue(self.recovery.snapshot(self.connector).recovery_complete)  # append-only new chat is allowed
        self.order.sync()
        self.reactions.sync()
        self.assertEqual(len(self.reactions.snapshot().pending), 1)

    def test_no_second_outage_same_session(self):
        self.ready()
        self.recovery.inject_outage(self.connector)
        with self.assertRaises(ValueError): self.recovery.inject_outage(self.connector)

    def test_reconnect_before_fault_denied(self):
        with self.assertRaises(ValueError): self.recovery.reconnect(self.connector)

    def test_reattach_before_fault_denied(self):
        with self.assertRaises(ValueError): self.recovery.reattach(self.connector)

    def test_reattach_before_reconnect_denied(self):
        self.ready(); self.recovery.inject_outage(self.connector)
        with self.assertRaises(ValueError): self.recovery.reattach(self.connector)

    def test_double_reconnect_denied(self):
        self.ready(); self.recovery.inject_outage(self.connector)
        self.recovery.reconnect(self.connector)
        with self.assertRaises(ValueError): self.recovery.reconnect(self.connector)
        self.assertEqual(self.connector.snapshot().attempts, 2)

    def test_double_reattach_denied(self):
        self.ready(); self.recovery.inject_outage(self.connector)
        self.recovery.reconnect(self.connector); self.recovery.reattach(self.connector)
        with self.assertRaises(ValueError): self.recovery.reattach(self.connector)

    def test_reject_new_connector_even_same_selection(self):
        self.seed(); self.recovery.inject_outage(self.connector)
        new = OfflinePlatformChatConnector(['chzzk','youtube'])
        self.assertFalse(self.recovery.snapshot(new).same_session)
        self.assertIn('무효', self.recovery.snapshot(new).phase)
        with self.assertRaises(ValueError): self.recovery.reconnect(new)
        with self.assertRaises(ValueError): self.recovery.reattach(new)
        self.assertEqual(new.snapshot().attempts, 0)

    def test_external_disconnect_invalidates_success(self):
        self.ready(); self.recovery.inject_outage(self.connector)
        self.recovery.reconnect(self.connector); self.recovery.reattach(self.connector)
        self.connector.disconnect(); self.receiver.detach()
        self.assertFalse(self.recovery.snapshot(self.connector).recovery_complete)

    def test_tampered_receiver_blocks_reconnect(self):
        self.seed(); self.recovery.inject_outage(self.connector)
        self.receiver._buffer.pop()
        with self.assertRaises(ValueError): self.recovery.reconnect(self.connector)
        self.assertEqual(self.connector.snapshot().attempts, 1)

    def test_tampered_order_blocks_reconnect(self):
        self.seed(); self.recovery.inject_outage(self.connector)
        self.order._events[0] = self.order._events[1]
        with self.assertRaises(ValueError): self.recovery.reconnect(self.connector)

    def test_tampered_replies_blocks_reconnect(self):
        self.seed(); self.recovery.inject_outage(self.connector)
        self.reactions._replied.clear()
        self.assertFalse(self.recovery.snapshot(self.connector).source_consistent)
        with self.assertRaises(ValueError): self.recovery.reconnect(self.connector)

    def test_invalid_failure_flag(self):
        self.ready(); self.recovery.inject_outage(self.connector)
        with self.assertRaises(ValueError): self.recovery.reconnect(self.connector, fail_handshake='yes')
        self.assertEqual(self.connector.snapshot().attempts, 1)

    def test_connector_fault_configuration_is_manual_only(self):
        self.connector.set_mock_failure('chzzk')
        self.assertEqual(self.connector.snapshot().attempts, 0)
        self.assertFalse(self.connector.connect().connected)
        self.connector.set_mock_failure(None)
        self.assertEqual(self.connector.connect().connected, ('chzzk','youtube'))
        with self.assertRaises(ValueError): self.connector.set_mock_failure('youtube')
        with self.assertRaises(ValueError): self.connector.set_mock_failure('unknown')

    def test_no_io_sleep_threads(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('db')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('time.sleep', side_effect=AssertionError('delay')), \
             patch('builtins.open', side_effect=AssertionError('disk')):
            self.seed(); self.recovery.inject_outage(self.connector)
            self.recovery.reconnect(self.connector, fail_handshake=True)
            self.recovery.reconnect(self.connector)
            self.recovery.reattach(self.connector)

    def test_snapshot_is_immutable(self):
        self.ready(); before = self.recovery.snapshot(self.connector)
        self.recovery.inject_outage(self.connector)
        self.assertEqual(before.phase, '수동 장애 시험 대기')
        self.assertFalse(before.recovery_complete)

    def test_no_real_connection_claim(self):
        self.ready(); self.recovery.inject_outage(self.connector)
        self.recovery.reconnect(self.connector); self.recovery.reattach(self.connector)
        report = self.recovery.snapshot(self.connector)
        self.assertTrue(report.mock_only)
        self.assertIn('실제 채팅 플랫폼 장애', report.describe())
        self.assertIn('자동 재시도', report.describe())

    def test_bad_dependency_rejected(self):
        with self.assertRaises(ValueError):
            OfflineChatConnectionRecovery(self.connector, self.receiver, OfflineChatOrder(OfflineChatReceiveBuffer()), self.reactions)
        with self.assertRaises(ValueError):
            OfflineChatConnectionRecovery(self.connector, self.receiver, self.order,
                                          OfflineChatReactions(OfflineChatReceiveBuffer(), OfflineChatOrder(OfflineChatReceiveBuffer())))


if __name__ == '__main__': unittest.main()
