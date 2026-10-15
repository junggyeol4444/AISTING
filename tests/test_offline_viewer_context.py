"""Original stage 067: viewer-specific context connected to existing FIFO port."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.core_execution import MAX_CONTEXT_TURNS
from ai_broadcaster.offline_chat_reactions import OfflineChatReactions
from ai_broadcaster.offline_chat_receiver import OfflineChatReceiveBuffer, MockReceivedChat
from ai_broadcaster.offline_chat_order import OfflineChatOrder
from ai_broadcaster.platform_chat_connector import OfflinePlatformChatConnector
from ai_broadcaster.offline_viewer_context import OfflineViewerContext


class RecordingPort:
    def __init__(self):
        self.calls = []
        self.fail = False

    def generate(self, item, history):
        self.calls.append((item, tuple(history)))
        if self.fail:
            raise RuntimeError('PRIVATE_TOKEN')
        return 'mock:' + item.text


def fixture(*platforms):
    connector = OfflinePlatformChatConnector(list(platforms or ('chzzk',)))
    connector.connect()
    receiver = OfflineChatReceiveBuffer()
    receiver.attach(connector)
    order = OfflineChatOrder(receiver)
    port = RecordingPort()
    reactions = OfflineChatReactions(receiver, order, reply_port=port)
    return connector, receiver, order, port, reactions, OfflineViewerContext(reactions)


class ViewerContextTests(unittest.TestCase):
    def test_requires_existing_session(self):
        for value in (None, 1, object()):
            with self.assertRaises(ValueError):
                OfflineViewerContext(value)

    def test_default_is_existing_global_context_policy(self):
        _, receiver, order, port, reactions, audit = fixture()
        receiver.inject('chzzk', 'a', 'one')
        receiver.inject('chzzk', 'b', 'two')
        order.sync(); reactions.sync()
        reactions.reply_batch()
        self.assertFalse(audit.snapshot().enabled)
        self.assertEqual([r.input.text for r in port.calls[1][1]], ['one'])

    def test_enable_requires_explicit_call(self):
        _, receiver, order, port, reactions, audit = fixture()
        self.assertFalse(audit.snapshot().enabled)
        self.assertEqual(port.calls, [])
        self.assertTrue(audit.enable().enabled)
        self.assertTrue(reactions.viewer_context_enabled)
        self.assertEqual(port.calls, [])

    def test_same_viewer_history_reaches_existing_port(self):
        _, receiver, order, port, reactions, audit = fixture()
        for text in ('first', 'second', 'third'):
            receiver.inject('chzzk', 'alice', text)
        order.sync(); reactions.sync(); audit.enable(); reactions.reply_batch()
        self.assertEqual([[r.input.text for r in history] for _, history in port.calls],
                         [[], ['first'], ['first', 'second']])
        self.assertEqual([r.text for r in port.calls[-1][1]], ['mock:first', 'mock:second'])

    def test_other_viewer_does_not_leak_context(self):
        _, receiver, order, port, reactions, audit = fixture()
        for sender, text in [('a', 'one'), ('b', 'secret'), ('a', 'two')]:
            receiver.inject('chzzk', sender, text)
        order.sync(); reactions.sync(); audit.enable(); reactions.reply_batch()
        self.assertEqual([r.input.text for r in port.calls[2][1]], ['one'])
        self.assertNotIn('secret', str(port.calls[2][1]))

    def test_same_nickname_other_platform_is_not_same_viewer(self):
        _, receiver, order, port, reactions, audit = fixture('chzzk', 'youtube')
        for platform, text in [('chzzk', 'first'), ('youtube', 'other'), ('chzzk', 'next')]:
            receiver.inject(platform, 'alice', text)
        order.sync(); reactions.sync(); audit.enable(); reactions.reply_batch()
        self.assertEqual([len(x[1]) for x in port.calls], [0, 0, 1])

    def test_same_text_is_not_deduplicated(self):
        _, receiver, order, port, reactions, audit = fixture()
        for _ in range(3):
            receiver.inject('chzzk', 'a', 'same')
        order.sync(); reactions.sync(); audit.enable(); reactions.reply_batch()
        self.assertEqual([len(x[1]) for x in port.calls], [0, 1, 2])
        self.assertEqual([r.event.ordinal for r in reactions.snapshot().responded], [1, 2, 3])

    def test_eight_turn_cap_and_order(self):
        _, receiver, order, port, reactions, audit = fixture()
        for i in range(12):
            receiver.inject('chzzk', 'a', str(i))
        order.sync(); reactions.sync(); audit.enable(); reactions.reply_batch()
        self.assertEqual(MAX_CONTEXT_TURNS, 8)
        self.assertEqual([r.input.text for r in port.calls[-1][1]], [str(i) for i in range(3, 11)])

    def test_preview_is_read_only_and_shows_successful_turns(self):
        _, receiver, order, port, reactions, audit = fixture()
        receiver.inject('chzzk', 'a', 'one')
        receiver.inject('chzzk', 'a', 'two')
        order.sync(); reactions.sync(); audit.enable()
        before = reactions.snapshot()
        report = audit.snapshot()
        self.assertEqual(report.prior_ordinals, ())
        self.assertEqual(before, reactions.snapshot())
        reactions.reply_next()
        report = audit.snapshot()
        self.assertEqual(report.prior_ordinals, (1,))
        self.assertEqual(report.prior_inputs, ('one',))
        self.assertEqual(len(port.calls), 1)

    def test_preview_never_includes_other_viewer(self):
        _, receiver, order, _, reactions, audit = fixture()
        for sender, text in [('a', 'one'), ('b', 'private'), ('a', 'next')]:
            receiver.inject('chzzk', sender, text)
        order.sync(); reactions.sync(); audit.enable()
        reactions.reply_next(); reactions.reply_next()
        report = audit.snapshot()
        self.assertEqual(report.prior_ordinals, (1,))
        self.assertEqual(report.prior_inputs, ('one',))

    def test_failed_response_does_not_enter_history(self):
        _, receiver, order, port, reactions, audit = fixture()
        receiver.inject('chzzk', 'a', 'one'); receiver.inject('chzzk', 'a', 'two')
        order.sync(); reactions.sync(); audit.enable()
        port.fail = True
        with self.assertRaisesRegex(ValueError, '생성 실패') as ctx:
            reactions.reply_next()
        self.assertNotIn('PRIVATE_TOKEN', str(ctx.exception))
        self.assertEqual(audit.snapshot().prior_ordinals, ())
        self.assertEqual(len(reactions.snapshot().pending), 2)
        port.fail = False
        reactions.resume(); reactions.reply_batch()
        self.assertEqual([r.input.text for r in port.calls[-1][1]], ['one'])

    def test_simulated_failure_keeps_pending(self):
        _, receiver, order, port, reactions, audit = fixture()
        receiver.inject('chzzk', 'a', 'one'); order.sync(); reactions.sync(); audit.enable()
        with self.assertRaises(ValueError):
            reactions.reply_next(simulate_failure=True)
        self.assertTrue(audit.snapshot().blocked)
        self.assertEqual(audit.snapshot().pending, 1)
        self.assertEqual(port.calls, [])

    def test_cannot_enable_after_reply(self):
        _, receiver, order, _, reactions, audit = fixture()
        receiver.inject('chzzk', 'a', 'one'); order.sync(); reactions.sync()
        reactions.reply_next()
        with self.assertRaisesRegex(ValueError, '이미 응답'):
            audit.enable()
        self.assertFalse(audit.snapshot().enabled)

    def test_cannot_enable_while_blocked(self):
        _, receiver, order, _, reactions, audit = fixture()
        receiver.inject('chzzk', 'a', 'one'); order.sync(); reactions.sync()
        with self.assertRaises(ValueError):
            reactions.reply_next(simulate_failure=True)
        with self.assertRaisesRegex(ValueError, '수동 재개'):
            audit.enable()
        self.assertFalse(audit.snapshot().enabled)

    def test_enable_twice_before_first_reply_is_idempotent(self):
        _, _, _, _, reactions, audit = fixture()
        audit.enable(); audit.enable()
        self.assertTrue(reactions.viewer_context_enabled)

    def test_unsynced_not_auto_processed(self):
        _, receiver, order, port, reactions, audit = fixture()
        receiver.inject('chzzk', 'a', 'one')
        audit.enable()
        self.assertEqual(audit.snapshot().unsynced, 1)
        self.assertEqual(port.calls, [])
        with self.assertRaisesRegex(ValueError, '동기화'):
            reactions.reply_next()
        order.sync(); reactions.sync(); reactions.reply_next()
        self.assertEqual(len(port.calls), 1)

    def test_stale_source_detected_before_reply(self):
        _, receiver, order, port, reactions, audit = fixture()
        receiver.inject('chzzk', 'a', 'one'); order.sync(); reactions.sync(); audit.enable()
        reactions._staged[0] = MockReceivedChat(999, 'chzzk', 'a', 'one')
        with self.assertRaises(ValueError):
            reactions.reply_next()
        self.assertEqual(port.calls, [])

    def test_separate_sessions_do_not_share_history(self):
        _, receiver, order, port, reactions, audit = fixture()
        receiver.inject('chzzk', 'a', 'one'); order.sync(); reactions.sync(); audit.enable(); reactions.reply_next()
        _, receiver2, order2, port2, reactions2, audit2 = fixture()
        receiver2.inject('chzzk', 'a', 'two'); order2.sync(); reactions2.sync(); audit2.enable(); reactions2.reply_next()
        self.assertEqual(port2.calls[0][1], ())

    def test_all_accepted_chats_replied_in_fifo(self):
        _, receiver, order, port, reactions, audit = fixture('chzzk', 'youtube')
        for platform, sender in [('youtube','b'),('chzzk','a'),('youtube','b'),('chzzk','a')]:
            receiver.inject(platform, sender, 'hello')
        order.sync(); reactions.sync(); audit.enable(); reactions.reply_batch()
        self.assertEqual([r.event.ordinal for r in reactions.snapshot().responded], [1,2,3,4])
        self.assertTrue(reactions.snapshot().all_responded)

    def test_read_only_preview_no_file_or_network(self):
        _, receiver, order, port, reactions, audit = fixture()
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            receiver.inject('chzzk', 'a', 'one')
            order.sync(); reactions.sync(); audit.enable(); audit.snapshot(); reactions.reply_next()
        self.assertEqual(len(port.calls), 1)

    def test_report_explicitly_disclaims_real_identity_and_model(self):
        _, _, _, _, _, audit = fixture()
        report = audit.snapshot()
        self.assertTrue(report.mock_only)
        self.assertIn('실제 계정 인증 ID가 아니', report.describe())
        self.assertIn('실제 플랫폼/AI 모델', report.describe())


if __name__ == '__main__':
    unittest.main()
