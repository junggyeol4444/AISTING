"""Original 070: offline end-to-end communication audit safety/regression."""
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.offline_chat_communication_audit import (
    CommunicationCheck, CommunicationAuditReport, run_offline_chat_communication_audit)
from ai_broadcaster.offline_chat_receiver import OfflineChatReceiveBuffer
from ai_broadcaster.offline_chat_order import OfflineChatOrder
from ai_broadcaster.offline_chat_reactions import OfflineChatReactions
from ai_broadcaster.platform_chat_connector import OfflinePlatformChatConnector


class CommunicationAuditTests(unittest.TestCase):
    def test_single_platform(self):
        r = run_offline_chat_communication_audit(['chzzk'])
        self.assertTrue(r.passed, r.describe())
        self.assertEqual((r.received, r.responded, r.simulated_reconnect_failures), (6, 6, 1))

    def test_two_platforms(self):
        r = run_offline_chat_communication_audit(['youtube', 'twitch'])
        self.assertTrue(r.passed, r.describe())
        self.assertEqual(r.selected, ('youtube', 'twitch'))

    def test_three_platforms(self):
        r = run_offline_chat_communication_audit(['chzzk', 'youtube', 'twitch'])
        self.assertTrue(r.passed, r.describe())
        self.assertEqual(r.selected, ('chzzk', 'youtube', 'twitch'))

    def test_each_single_platform(self):
        for code in ('chzzk', 'youtube', 'twitch'):
            with self.subTest(code=code):
                self.assertTrue(run_offline_chat_communication_audit([code]).passed)

    def test_no_platform_is_not_auto_selected(self):
        with self.assertRaisesRegex(ValueError, '하나 이상'):
            run_offline_chat_communication_audit([])

    def test_invalid_platform(self):
        with self.assertRaises(ValueError):
            run_offline_chat_communication_audit(['unknown'])

    def test_duplicate_platform_rejected(self):
        with self.assertRaises(ValueError):
            run_offline_chat_communication_audit(['chzzk', 'chzzk'])

    def test_bad_selection_type_rejected(self):
        for selection in ('chzzk', None, ['chzzk', 1], [None]):
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                run_offline_chat_communication_audit(selection)

    def test_selection_not_mutated(self):
        selected = ['chzzk', 'youtube']
        run_offline_chat_communication_audit(selected)
        self.assertEqual(selected, ['chzzk', 'youtube'])

    def test_repeated_is_independent(self):
        first = run_offline_chat_communication_audit(['chzzk'])
        second = run_offline_chat_communication_audit(['chzzk'])
        self.assertTrue(first.passed and second.passed)
        self.assertEqual(first.checks, second.checks)

    def test_checklist_is_full_and_explicit(self):
        report = run_offline_chat_communication_audit(['chzzk'])
        self.assertEqual(len(report.checks), 15)
        self.assertTrue(all(item.passed for item in report.checks))
        self.assertEqual(report.blocked_attempts, 6)
        self.assertTrue(report.mock_only)

    def test_describe_distinguishes_real_time(self):
        text = run_offline_chat_communication_audit(['chzzk']).describe()
        for marker in ('원본 070', '오프라인', '실제 플랫폼', 'Windows', '사용자 최종 승인'):
            self.assertIn(marker, text)

    def test_failed_report_never_passes(self):
        report = CommunicationAuditReport(('chzzk',),
                   (CommunicationCheck('a', True, ''), CommunicationCheck('b', False, '')), 2, 1, 0, 0)
        self.assertFalse(report.passed)
        self.assertIn('실패', report.describe())

    def test_empty_checklist_never_passes(self):
        self.assertFalse(CommunicationAuditReport(('chzzk',), (), 0, 0, 0, 0).passed)

    def test_immutable_report(self):
        report = run_offline_chat_communication_audit(['chzzk'])
        with self.assertRaises(FrozenInstanceError):
            report.received = 9

    def test_mock_reply_port_failure_must_fail(self):
        with patch('ai_broadcaster.offline_chat_communication_audit.MockCoreReplyPort.generate',
                   side_effect=RuntimeError('test failure')):
            report = run_offline_chat_communication_audit(['chzzk'])
        self.assertFalse(report.passed)
        self.assertLess(report.responded, 6)
        self.assertIn('실패', report.describe())

    def test_silent_queue_sync_fault_must_fail(self):
        with patch('ai_broadcaster.offline_chat_communication_audit.OfflineChatOrder.sync',
                   side_effect=lambda self: self.snapshot(), autospec=True):
            report = run_offline_chat_communication_audit(['chzzk'])
        self.assertFalse(report.passed)
        self.assertLess(report.responded, 6)

    def test_connection_fault_must_fail(self):
        with patch('ai_broadcaster.offline_chat_communication_audit.OfflinePlatformChatConnector.connect',
                   side_effect=ValueError('simulated')):
            report = run_offline_chat_communication_audit(['chzzk'])
        self.assertFalse(report.passed)
        self.assertEqual(report.responded, 0)

    def test_no_file_or_network_or_process_calls(self):
        with patch('builtins.open', side_effect=AssertionError('file')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            self.assertTrue(run_offline_chat_communication_audit(['chzzk', 'youtube']).passed)

    def test_existing_objects_unmodified(self):
        connector = OfflinePlatformChatConnector(['chzzk'])
        receiver = OfflineChatReceiveBuffer()
        order = OfflineChatOrder(receiver)
        reactions = OfflineChatReactions(receiver, order)
        connector.connect()
        receiver.attach(connector)
        receiver.inject('chzzk', 'real-local', 'keep')
        old = (connector.snapshot(), receiver.snapshot(), order.snapshot(), reactions.snapshot())
        report = run_offline_chat_communication_audit(['chzzk'])
        self.assertTrue(report.passed)
        self.assertEqual(old, (connector.snapshot(), receiver.snapshot(), order.snapshot(), reactions.snapshot()))

    def test_approval_not_claimed(self):
        text = run_offline_chat_communication_audit(['chzzk']).describe()
        self.assertIn('별도 대기', text)
        self.assertNotIn('실방송 통과', text)


if __name__ == '__main__':
    unittest.main()
