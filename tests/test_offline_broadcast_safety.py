"""Stage 095 safety gates: isolated synthetic streams, no OS/network or OBS."""
import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_safety import (
    OfflineBroadcastSafetyGate, SafetyDenied, run_offline_broadcast_safety_audit,
)
from ai_broadcaster.platform_chat_connector import OfflinePlatformChatConnector
from ai_broadcaster.offline_chat_receiver import OfflineChatReceiveBuffer
from ai_broadcaster.offline_chat_order import OfflineChatOrder
from ai_broadcaster.offline_chat_reactions import OfflineChatReactions


def make(n=2, **kwargs):
    connector = OfflinePlatformChatConnector(['chzzk'])
    connector.connect()
    receiver = OfflineChatReceiveBuffer()
    receiver.attach(connector)
    order = OfflineChatOrder(receiver)
    for i in range(n):
        receiver.inject('chzzk', 'viewer', 'same message')
    order.sync()
    reactions = OfflineChatReactions(receiver, order)
    reactions.sync()
    return connector, receiver, order, reactions, OfflineBroadcastSafetyGate(receiver, order, reactions, **kwargs)


class BroadcastSafetyTests(unittest.TestCase):
    def test_normal(self):
        *_, gate = make()
        d = gate.inspect(0)
        self.assertTrue(d.safe_for_mock_review)
        self.assertEqual((d.received, d.replied, d.pending), (2, 0, 2))
        self.assertFalse(d.actual_stream_stopped)
        self.assertFalse(d.actual_output_stopped)

    def test_no_messages_never_stall(self):
        *_, gate = make(0)
        gate.inspect(0)
        self.assertFalse(gate.inspect(300).held)

    def test_stall_on_threshold(self):
        *_, gate = make(timeout_seconds=10)
        gate.inspect(0)
        self.assertFalse(gate.inspect(9).held)
        d = gate.inspect(10)
        self.assertIn('가상 응답 진행 정체', d.issues)
        self.assertTrue(d.held)

    def test_progress_resets_clock(self):
        *_, reactions, gate = make(timeout_seconds=10)
        gate.inspect(0)
        reactions.reply_next()
        self.assertFalse(gate.inspect(9).held)
        self.assertFalse(gate.inspect(18).held)
        self.assertTrue(gate.inspect(19).held)

    def test_latch_does_not_auto_clear(self):
        *_, reactions, gate = make(timeout_seconds=5)
        gate.inspect(0)
        gate.inspect(5)
        reactions.reply_next()
        reactions.reply_next()
        d = gate.inspect(6)
        self.assertFalse(d.issues)
        self.assertTrue(d.held)
        self.assertFalse(d.safe_for_mock_review)

    def test_manual_acknowledge_after_clear(self):
        *_, reactions, gate = make(timeout_seconds=5)
        gate.inspect(0)
        gate.inspect(5)
        reactions.reply_next()
        reactions.reply_next()
        self.assertTrue(gate.manual_acknowledge(6).safe_for_mock_review)
        self.assertFalse(gate.held)

    def test_deny_early_ack(self):
        *_, gate = make()
        with self.assertRaises(SafetyDenied):
            gate.manual_acknowledge(0)

    def test_deny_ack_if_stall_still_present(self):
        *_, gate = make(timeout_seconds=5)
        gate.inspect(0)
        gate.inspect(5)
        with self.assertRaises(SafetyDenied):
            gate.manual_acknowledge(6)
        self.assertTrue(gate.held)

    def test_disconnect_latched(self):
        connector, *_, gate = make()
        connector.disconnect()
        self.assertIn('가상 연결 끊김', gate.inspect(0).issues)
        with self.assertRaises(SafetyDenied):
            gate.manual_acknowledge(1)

    def test_disconnect_reconnect_requires_new_session(self):
        connector, *_, gate = make()
        connector.disconnect()
        gate.inspect(0)
        connector.connect()
        self.assertIn('가상 연결 세션 변경', gate.inspect(1).issues)
        with self.assertRaises(SafetyDenied):
            gate.manual_acknowledge(2)

    def test_receiver_detach(self):
        _, receiver, _, _, gate = make()
        receiver.detach()
        self.assertTrue(gate.inspect(0).held)

    def test_reply_block(self):
        *_, reactions, gate = make()
        with self.assertRaises(ValueError):
            reactions.reply_next(simulate_failure=True)
        self.assertIn('모의 처리 중단', gate.inspect(0).issues)
        with self.assertRaises(SafetyDenied):
            gate.manual_acknowledge(1)

    def test_order_pause(self):
        _, _, order, _, gate = make()
        with self.assertRaises(ValueError):
            order.acknowledge_next(simulate_failure=True)
        self.assertIn('모의 처리 중단', gate.inspect(0).issues)

    def test_incoming_mutation(self):
        _, receiver, _, _, gate = make()
        receiver._buffer.pop()
        self.assertIn('모의 채팅 기록 불일치', gate.inspect(0).issues)

    def test_order_mutation(self):
        _, _, order, _, gate = make()
        order._events.pop()
        self.assertIn('모의 채팅 기록 불일치', gate.inspect(0).issues)

    def test_order_cursor_corruption(self):
        _, _, order, _, gate = make()
        order._cursor = 100
        self.assertIn('모의 채팅 기록 불일치', gate.inspect(0).issues)

    def test_connection_replace(self):
        _, receiver, _, _, gate = make()
        connector = OfflinePlatformChatConnector(['chzzk'])
        connector.connect()
        receiver._connector = connector
        self.assertIn('가상 연결 세션 변경', gate.inspect(0).issues)

    def test_reply_mutation(self):
        _, _, _, reactions, gate = make()
        reactions.reply_next()
        gate.inspect(1)
        reactions._replied.clear()
        self.assertIn('처리 기록 역행', gate.inspect(2).issues)

    def test_ordinal_mutation(self):
        _, receiver, _, _, gate = make()
        receiver._buffer[0] = receiver._buffer[0].__class__(7, 'chzzk', 'viewer', 'same message')
        self.assertIn('모의 채팅 기록 불일치', gate.inspect(0).issues)

    def test_backlog_alarm_preserves_duplicate(self):
        _, receiver, _, reactions, gate = make(3, backlog_limit=2)
        self.assertIn('모의 대기열 경고', gate.inspect(0).issues)
        self.assertEqual(len(receiver.snapshot().buffered), 3)
        self.assertEqual(len(reactions.snapshot().pending), 3)

    def test_manual_report_no_content_scan(self):
        *_, gate = make()
        self.assertIn('운영자 수동 이상 제보', gate.inspect(0, operator_incident=True).issues)

    def test_report_boolean_strict(self):
        *_, gate = make()
        for item in ('true', 1, None):
            with self.subTest(item=item), self.assertRaises(ValueError):
                gate.inspect(0, operator_incident=item)
        self.assertFalse(gate.held)

    def test_invalid_times_and_rollback(self):
        *_, gate = make()
        for invalid in (-1, True, 3.4, '3'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                gate.inspect(invalid)
        gate.inspect(100)
        self.assertIn('가상 시계 역행', gate.inspect(99).issues)

    def test_strict_threshold_config(self):
        connector, receiver, order, reactions, _ = make()
        for opts in ({'backlog_limit': True}, {'timeout_seconds': 0},
                     {'timeout_seconds': 86401}, {'backlog_limit': 501}):
            with self.subTest(opts=opts), self.assertRaises(ValueError):
                OfflineBroadcastSafetyGate(receiver, order, reactions, **opts)

    def test_cross_session_denied(self):
        _, receiver, order, reactions, _ = make()
        other = OfflineChatReceiveBuffer()
        with self.assertRaises(ValueError):
            OfflineBroadcastSafetyGate(other, order, reactions)

    def test_immutable_decision_and_redacted_output(self):
        *_, gate = make()
        d = gate.inspect(0)
        with self.assertRaises(FrozenInstanceError):
            d.pending = 100
        self.assertNotIn('same message', d.describe())
        self.assertIn('실제 송출', d.describe())

    def test_exception_fail_closed_without_leaking(self):
        *_, gate = make()
        with patch.object(gate.reactions, 'snapshot', side_effect=RuntimeError('SECRET')):
            d = gate.inspect(0)
        self.assertTrue(d.held)
        self.assertIn('모의 상태 조회 오류', d.issues)
        self.assertNotIn('SECRET', d.describe())

    def test_dry_run_six_scenarios(self):
        scenarios = run_offline_broadcast_safety_audit()
        self.assertEqual(len(scenarios), 6)
        self.assertEqual([x[0] for x in scenarios], ['정상', '정체 감지', '보류 유지', '수동 해제', '연결 끊김', '기록 손상'])
        self.assertTrue(scenarios[2][1].held)
        self.assertFalse(scenarios[3][1].held)

    def test_no_external_actions(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('builtins.open', side_effect=AssertionError('file')):
            self.assertEqual(len(run_offline_broadcast_safety_audit()), 6)


if __name__ == '__main__':
    unittest.main()
