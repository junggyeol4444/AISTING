"""Original 068: multiple synthetic viewers through the SAME 062-067 FIFO."""
import unittest
from unittest.mock import patch

from ai_broadcaster.core_execution import MAX_CONTEXT_TURNS
from ai_broadcaster.offline_chat_receiver import OfflineChatReceiveBuffer, MockReceivedChat
from ai_broadcaster.offline_chat_order import OfflineChatOrder
from ai_broadcaster.offline_chat_reactions import OfflineChatReactions
from ai_broadcaster.offline_multi_viewer import OfflineMultiViewerDialogue
from ai_broadcaster.platform_chat_connector import OfflinePlatformChatConnector


class SpyPort:
    def __init__(self):
        self.calls = []
        self.fail = False

    def generate(self, item, history):
        self.calls.append((item, tuple(history)))
        if self.fail:
            raise RuntimeError('PRIVATE_SECRET')
        return 'mock:' + item.text


def fixture(*platforms):
    connector = OfflinePlatformChatConnector(list(platforms or ('chzzk',)))
    connector.connect()
    receiver = OfflineChatReceiveBuffer()
    receiver.attach(connector)
    order = OfflineChatOrder(receiver)
    port = SpyPort()
    reactions = OfflineChatReactions(receiver, order, reply_port=port)
    multi = OfflineMultiViewerDialogue(reactions)
    return connector, receiver, order, port, reactions, multi


class MultiViewerTests(unittest.TestCase):
    def test_requires_existing_reaction_session(self):
        for value in (None, 2, object()):
            with self.assertRaises(ValueError):
                OfflineMultiViewerDialogue(value)

    def test_empty_report_no_claim_of_completion(self):
        *_, multi = fixture()
        report = multi.snapshot()
        self.assertFalse(report.active)
        self.assertFalse(report.complete)
        self.assertEqual(report.viewers, ())
        self.assertTrue(report.mock_only)

    def test_explicit_activation_no_automatic_reply(self):
        _, _, _, port, reactions, multi = fixture()
        self.assertTrue(multi.activate().active)
        self.assertTrue(reactions.viewer_context_enabled)
        self.assertEqual(port.calls, [])

    def test_activation_idempotent_when_already_enabled(self):
        _, receiver, _, _, reactions, multi = fixture()
        receiver.inject('chzzk', 'a', 'x')
        multi.activate(); multi.sync(); multi.reply_next()
        self.assertTrue(multi.activate().active)
        self.assertEqual(len(reactions.snapshot().responded), 1)

    def test_activation_after_default_reply_rejected(self):
        _, receiver, order, _, reactions, multi = fixture()
        receiver.inject('chzzk', 'a', 'x'); order.sync(); reactions.sync(); reactions.reply_next()
        with self.assertRaisesRegex(ValueError, '이미 응답'):
            multi.activate()
        self.assertFalse(multi.snapshot().active)

    def test_requires_activation_before_reply(self):
        _, receiver, _, port, _, multi = fixture()
        receiver.inject('chzzk', 'a', 'x'); multi.sync()
        with self.assertRaisesRegex(ValueError, '활성화'):
            multi.reply_next()
        with self.assertRaisesRegex(ValueError, '활성화'):
            multi.reply_batch()
        self.assertEqual(port.calls, [])

    def test_sync_is_explicit_and_does_not_reply(self):
        _, receiver, order, port, reactions, multi = fixture()
        receiver.inject('chzzk', 'a', 'one')
        self.assertEqual(multi.snapshot().unsynced, 1)
        multi.activate()
        report = multi.sync()
        self.assertEqual((report.staged, report.pending, report.unsynced), (1, 1, 0))
        self.assertEqual(len(order.snapshot().queued), 1)
        self.assertEqual(len(reactions.snapshot().staged), 1)
        self.assertEqual(port.calls, [])

    def test_interleaved_viewers_keep_global_fifo(self):
        _, receiver, _, port, reactions, multi = fixture('chzzk', 'youtube')
        inputs = [('chzzk','alice','a1'), ('youtube','bob','b1'),
                  ('chzzk','carol','c1'), ('chzzk','alice','a2'),
                  ('youtube','bob','b2'), ('chzzk','carol','c2')]
        for args in inputs:
            receiver.inject(*args)
        multi.activate(); multi.sync(); report = multi.reply_batch()
        self.assertEqual([x.event.ordinal for x in reactions.snapshot().responded], list(range(1,7)))
        self.assertEqual([x[0].text for x in port.calls], [x[2] for x in inputs])
        self.assertTrue(report.complete)
        self.assertEqual(len(report.viewers), 3)

    def test_per_viewer_history_isolated_and_ordered(self):
        _, receiver, _, port, _, multi = fixture()
        for sender, text in [('a','a1'),('b','b1'),('a','a2'),('b','b2'),('a','a3')]:
            receiver.inject('chzzk', sender, text)
        multi.activate(); multi.sync(); multi.reply_batch()
        self.assertEqual([[x.input.text for x in history] for _, history in port.calls],
                         [[],[],['a1'],['b1'],['a1','a2']])

    def test_same_nickname_across_platforms_separate(self):
        _, receiver, _, port, _, multi = fixture('chzzk','youtube')
        for platform, text in [('chzzk','a'),('youtube','b'),('chzzk','c'),('youtube','d')]:
            receiver.inject(platform, 'same', text)
        multi.activate(); multi.sync(); report = multi.reply_batch()
        self.assertEqual([len(history) for _, history in port.calls], [0,0,1,1])
        self.assertEqual([lane.replied_ordinals for lane in report.viewers], [(1,3),(2,4)])

    def test_duplicate_content_not_dropped(self):
        _, receiver, _, port, _, multi = fixture()
        for _ in range(4):
            receiver.inject('chzzk', 'a', 'same')
        multi.activate(); multi.sync(); report = multi.reply_batch()
        self.assertEqual(report.viewers[0].replied_ordinals, (1,2,3,4))
        self.assertEqual(len(port.calls), 4)

    def test_lanes_are_read_only_projection(self):
        _, receiver, _, _, reactions, multi = fixture()
        for sender in ('a','b','a'):
            receiver.inject('chzzk', sender, 'x')
        multi.activate(); multi.sync(); before = reactions.snapshot()
        report = multi.snapshot()
        self.assertEqual(report.viewers[0].accepted_ordinals, (1,3))
        self.assertEqual(report.viewers[1].accepted_ordinals, (2,))
        self.assertEqual(before, reactions.snapshot())
        with self.assertRaises((AttributeError, TypeError)):
            report.viewers[0].sender = 'other'

    def test_unsynced_viewer_is_not_counted_as_lost(self):
        _, receiver, _, _, _, multi = fixture()
        receiver.inject('chzzk','a','first')
        multi.activate(); multi.sync(); multi.reply_next()
        receiver.inject('chzzk','b','second')
        report = multi.snapshot()
        self.assertEqual(report.unsynced, 1)
        self.assertFalse(report.complete)
        self.assertEqual(report.viewers[1].unsynced_ordinals, (2,))
        self.assertEqual(report.viewers[1].pending_ordinals, ())
        multi.sync(); multi.reply_next()
        self.assertTrue(multi.snapshot().complete)

    def test_failure_keeps_head_and_all_other_viewers(self):
        _, receiver, _, port, _, multi = fixture()
        for sender in ('a','b','c'):
            receiver.inject('chzzk',sender,'x')
        multi.activate(); multi.sync()
        with self.assertRaisesRegex(ValueError, '실패'):
            multi.reply_next(simulate_failure=True)
        report = multi.snapshot()
        self.assertTrue(report.blocked)
        self.assertEqual(report.head.ordinal, 1)
        self.assertEqual(report.pending, 3)
        self.assertEqual(port.calls, [])
        with self.assertRaisesRegex(ValueError, '수동 재개'):
            multi.reply_next()

    def test_manual_resume_does_not_retry(self):
        _, receiver, _, port, _, multi = fixture()
        receiver.inject('chzzk','a','one')
        multi.activate(); multi.sync()
        with self.assertRaises(ValueError):
            multi.reply_next(simulate_failure=True)
        report = multi.resume()
        self.assertFalse(report.blocked)
        self.assertEqual(report.replied, 0)
        self.assertEqual(port.calls, [])
        multi.reply_next()
        self.assertEqual(len(port.calls), 1)

    def test_port_error_private_details_not_exposed(self):
        _, receiver, _, port, _, multi = fixture()
        receiver.inject('chzzk','a','one')
        multi.activate(); multi.sync(); port.fail = True
        with self.assertRaises(ValueError) as err:
            multi.reply_next()
        self.assertNotIn('PRIVATE_SECRET', str(err.exception))
        self.assertTrue(multi.snapshot().blocked)
        self.assertEqual(multi.snapshot().replied, 0)

    def test_after_failure_manual_resume_restores_history(self):
        _, receiver, _, port, _, multi = fixture()
        for text in ('one','two'):
            receiver.inject('chzzk','a',text)
        multi.activate(); multi.sync(); multi.reply_next(); port.fail = True
        with self.assertRaises(ValueError):
            multi.reply_next()
        self.assertEqual(multi.snapshot().head.ordinal, 2)
        port.fail = False
        multi.resume(); multi.reply_next()
        self.assertEqual([x.input.text for x in port.calls[-1][1]], ['one'])
        self.assertTrue(multi.snapshot().complete)

    def test_batch_maximum_fifty_no_discard(self):
        _, receiver, _, port, _, multi = fixture()
        for i in range(55):
            receiver.inject('chzzk',str(i % 3),str(i))
        multi.activate(); multi.sync(); report = multi.reply_batch()
        self.assertEqual((report.replied, report.pending, report.head.ordinal), (50,5,51))
        multi.reply_batch()
        self.assertEqual(len(port.calls), 55)
        self.assertTrue(multi.snapshot().complete)

    def test_batch_invalid_count_rejected(self):
        _, receiver, _, port, _, multi = fixture()
        receiver.inject('chzzk','a','one'); multi.activate(); multi.sync()
        for count in (0, 51, -1, True, 1.5, '2'):
            with self.assertRaises(ValueError):
                multi.reply_batch(count)
        self.assertEqual(port.calls, [])

    def test_no_priority_by_viewer(self):
        _, receiver, _, port, _, multi = fixture()
        for sender in ('b','b','a','b','a'):
            receiver.inject('chzzk',sender,'hello')
        multi.activate(); multi.sync()
        self.assertEqual([multi.reply_next().event.sender for _ in range(5)], ['b','b','a','b','a'])
        self.assertEqual(len(port.calls), 5)

    def test_source_corruption_detected_before_reply(self):
        _, receiver, order, port, reactions, multi = fixture()
        receiver.inject('chzzk','a','x'); multi.activate(); multi.sync()
        reactions._staged[0] = MockReceivedChat(2,'chzzk','a','x')
        self.assertFalse(multi.snapshot().source_consistent)
        with self.assertRaises(ValueError):
            multi.reply_next()
        self.assertEqual(port.calls, [])

    def test_order_pause_blocks_all_viewers(self):
        _, receiver, order, port, _, multi = fixture()
        receiver.inject('chzzk','a','x'); receiver.inject('chzzk','b','y')
        multi.activate(); multi.sync()
        with self.assertRaises(ValueError):
            order.acknowledge_next(simulate_failure=True)
        self.assertTrue(multi.snapshot().order_paused)
        with self.assertRaisesRegex(ValueError, '순서 관리'):
            multi.reply_next()
        self.assertEqual(port.calls, [])
        order.resume(); multi.reply_batch()
        self.assertTrue(multi.snapshot().complete)

    def test_disconnected_platform_preserves_received_messages(self):
        connector, receiver, _, port, _, multi = fixture()
        receiver.inject('chzzk','a','one')
        connector.disconnect()
        multi.activate(); multi.sync(); multi.reply_next()
        self.assertEqual(len(port.calls), 1)
        self.assertTrue(multi.snapshot().complete)

    def test_fifteen_viewers_display_limit_does_not_filter(self):
        _, receiver, _, port, _, multi = fixture()
        for i in range(20):
            receiver.inject('chzzk',f'viewer{i}','hello')
        multi.activate(); multi.sync(); report = multi.reply_batch()
        self.assertEqual(len(report.viewers), 20)
        self.assertEqual(len(port.calls), 20)
        self.assertIn('나머지 5명도', report.describe())
        self.assertTrue(report.complete)

    def test_history_limit_eight_in_interleaved_session(self):
        _, receiver, _, port, _, multi = fixture()
        for i in range(12):
            receiver.inject('chzzk','a',str(i))
            receiver.inject('chzzk','b',f'b{i}')
        multi.activate(); multi.sync(); multi.reply_batch()
        self.assertEqual(len(port.calls[-2][1]), MAX_CONTEXT_TURNS)
        self.assertEqual([x.input.text for x in port.calls[-2][1]], [str(i) for i in range(3,11)])

    def test_capacity_five_hundred_with_multiple_viewers(self):
        _, receiver, _, port, _, multi = fixture()
        for i in range(500):
            receiver.inject('chzzk',f'viewer{i%20}',str(i))
        multi.activate(); multi.sync()
        for _ in range(10):
            multi.reply_batch()
        report = multi.snapshot()
        self.assertEqual(report.accepted, 500)
        self.assertEqual(report.replied, 500)
        self.assertEqual(len(report.viewers), 20)
        self.assertEqual(len(port.calls), 500)
        self.assertTrue(report.complete)

    def test_no_implicit_network_database_or_process(self):
        _, receiver, _, port, _, multi = fixture()
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            receiver.inject('chzzk','a','x')
            multi.activate(); multi.sync(); multi.snapshot(); multi.reply_batch()
        self.assertEqual(len(port.calls), 1)

    def test_manual_repeated_sync_no_duplicate(self):
        _, receiver, _, port, _, multi = fixture()
        receiver.inject('chzzk','a','one')
        multi.activate(); multi.sync(); multi.sync(); multi.reply_batch()
        self.assertEqual(len(port.calls), 1)
        receiver.inject('chzzk','b','two')
        multi.sync(); multi.sync(); multi.reply_batch()
        self.assertEqual(len(port.calls), 2)
        self.assertEqual(multi.snapshot().viewers[1].replied_ordinals, (2,))

    def test_report_explicitly_disclaims_live_viewers(self):
        *_, multi = fixture()
        report = multi.snapshot().describe()
        self.assertIn('실제 계정 ID 아님', report)
        self.assertIn('실제 플랫폼/AI 모델', report)
        self.assertIn('고의 지연/자동 재시도 없음', report)


if __name__ == '__main__':
    unittest.main()
