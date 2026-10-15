"""Stage 066: actual 065 mock FIFO calls timed without intentional waiting."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.platform_chat_connector import OfflinePlatformChatConnector
from ai_broadcaster.offline_chat_receiver import OfflineChatReceiveBuffer
from ai_broadcaster.offline_chat_order import OfflineChatOrder
from ai_broadcaster.offline_chat_reactions import OfflineChatReactions
from ai_broadcaster.offline_chat_latency import OfflineChatLatencyAudit


class Port:
    def __init__(self):
        self.calls = []
        self.fail = False

    def generate(self, item, history):
        self.calls.append(item.text)
        if self.fail:
            raise RuntimeError('PRIVATE SECRET')
        return 'mock:' + item.text


class Clock:
    def __init__(self, *values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


def setup(messages=('hello',), platforms=('chzzk',), *, clock=None):
    connector = OfflinePlatformChatConnector(list(platforms))
    connector.connect()
    receiver = OfflineChatReceiveBuffer()
    receiver.attach(connector)
    for i, message in enumerate(messages):
        receiver.inject(platforms[i % len(platforms)], 'viewer', message)
    order = OfflineChatOrder(receiver)
    order.sync()
    port = Port()
    reactions = OfflineChatReactions(receiver, order, reply_port=port)
    reactions.sync()
    audit = OfflineChatLatencyAudit(reactions, clock_ns=clock)
    return receiver, order, port, reactions, audit


class ChatLatencyTests(unittest.TestCase):
    def test_wrong_source_rejected(self):
        for value in (None, object(), 1):
            with self.assertRaises(ValueError):
                OfflineChatLatencyAudit(value)

    def test_empty_never_success(self):
        *_, audit = setup(())
        report = audit.snapshot()
        self.assertFalse(report.completed)
        self.assertTrue(report.mock_only)
        self.assertEqual((report.received, report.responded, report.pending), (0, 0, 0))
        with self.assertRaises(ValueError):
            audit.measure_batch()

    def test_one_reply_exact_ns(self):
        _, _, port, _, audit = setup(clock=Clock(10, 5010))
        item = audit.measure_next()
        self.assertEqual(item.ordinal, 1)
        self.assertEqual(item.elapsed_ns, 5000)
        self.assertEqual(port.calls, ['hello'])
        self.assertTrue(audit.snapshot().completed)

    def test_fifo_duplicates_and_multiple_platforms(self):
        _, _, port, _, audit = setup(('same', 'same', 'third'), ('chzzk', 'youtube'),
                                     clock=Clock(0, 10, 20, 40, 50, 80))
        report = audit.measure_batch()
        self.assertTrue(report.completed)
        self.assertEqual(port.calls, ['same', 'same', 'third'])
        self.assertEqual([x.ordinal for x in report.samples], [1, 2, 3])
        self.assertEqual([x.reaction.event.platform for x in report.samples],
                         ['chzzk', 'youtube', 'chzzk'])
        self.assertEqual(report.median_ms, 20 / 1e6)
        self.assertEqual(report.p95_ms, 30 / 1e6)

    def test_batch_limit(self):
        _, _, port, _, audit = setup(tuple(map(str, range(53))))
        for bad in (0, 51, -1, True, '2', None):
            with self.assertRaises(ValueError):
                audit.measure_batch(bad)
        self.assertEqual(port.calls, [])
        audit.measure_batch()
        self.assertEqual((len(audit.snapshot().samples), audit.snapshot().pending), (50, 3))
        audit.measure_batch()
        self.assertTrue(audit.snapshot().completed)

    def test_failure_preserves_head_tail_and_no_auto_retry(self):
        _, _, port, reactions, audit = setup(('one', 'two'))
        port.fail = True
        with self.assertRaisesRegex(ValueError, '생성 실패') as error:
            audit.measure_batch()
        self.assertNotIn('SECRET', str(error.exception))
        self.assertEqual(port.calls, ['one'])
        self.assertEqual(audit.snapshot().pending, 2)
        self.assertTrue(audit.snapshot().blocked)
        self.assertEqual(audit.snapshot().failed_attempts, 1)
        port.fail = False
        with self.assertRaisesRegex(ValueError, '수동 재개'):
            audit.measure_next()
        self.assertEqual(port.calls, ['one'])
        reactions.resume()
        audit.measure_batch()
        self.assertTrue(audit.snapshot().completed)
        self.assertEqual(port.calls, ['one', 'one', 'two'])

    def test_no_implicit_sync(self):
        receiver, order, _, reactions, audit = setup(('one',))
        receiver.inject('chzzk', 'viewer', 'two')
        self.assertEqual(audit.snapshot().unsynced, 1)
        audit.measure_next()
        self.assertFalse(audit.snapshot().completed)
        order.sync()
        reactions.sync()
        audit.measure_next()
        self.assertTrue(audit.snapshot().completed)

    def test_existing_replies_not_claimed_measured(self):
        _, _, _, reactions, audit = setup(('one', 'two'))
        reactions.reply_next()
        report = audit.snapshot()
        self.assertEqual(report.unmeasured_ordinals, (1,))
        audit.measure_next()
        self.assertFalse(audit.snapshot().completed)
        self.assertEqual(audit.snapshot().unmeasured_ordinals, (1,))

    def test_direct_reply_after_timed_is_unmeasured(self):
        _, _, _, reactions, audit = setup(('one', 'two'))
        audit.measure_next()
        reactions.reply_next()
        self.assertEqual(audit.snapshot().unmeasured_ordinals, (2,))
        self.assertFalse(audit.snapshot().completed)

    def test_bad_clock_start_never_consumes(self):
        for bad in (-1, 1.0, True, '0', None):
            _, _, port, _, audit = setup(clock=Clock(bad))
            with self.assertRaisesRegex(ValueError, '시작 시계'):
                audit.measure_next()
            self.assertEqual(port.calls, [])
            self.assertEqual(audit.snapshot().pending, 1)
            self.assertEqual(audit.snapshot().clock_faults, 1)

    def test_bad_clock_end_marks_success_unmeasured(self):
        for end in (9, True, None, 11.0):
            _, _, port, _, audit = setup(clock=Clock(10, end))
            with self.assertRaisesRegex(ValueError, '이미 처리됨'):
                audit.measure_next()
            self.assertEqual(port.calls, ['hello'])
            report = audit.snapshot()
            self.assertEqual(report.unmeasured_ordinals, (1,))
            self.assertEqual(report.clock_faults, 1)
            self.assertEqual(report.pending, 0)
            self.assertFalse(report.completed)
            with self.assertRaises(ValueError):
                audit.measure_next()
            self.assertEqual(port.calls, ['hello'])

    def test_clock_exception_start_and_end(self):
        for values, pending in (((RuntimeError('SECRET'),), 1), ((10, RuntimeError('SECRET')), 0)):
            def clock(vals=iter(values)):
                x = next(vals)
                if isinstance(x, Exception):
                    raise x
                return x
            _, _, _, _, audit = setup(clock=clock)
            with self.assertRaises(ValueError) as caught:
                audit.measure_next()
            self.assertNotIn('SECRET', str(caught.exception))
            self.assertEqual(audit.snapshot().pending, pending)

    def test_invalidated_sample_after_reply_tamper(self):
        _, _, _, reactions, audit = setup()
        audit.measure_next()
        self.assertTrue(audit.snapshot().completed)
        old = reactions._replied[0]
        reactions._replied[0] = type(old)(old.event, 'tampered')
        report = audit.snapshot()
        self.assertFalse(report.completed)
        self.assertEqual(report.invalid_samples, (1,))
        self.assertEqual(report.unmeasured_ordinals, (1,))

    def test_blocked_order(self):
        _, order, port, _, audit = setup()
        with self.assertRaises(ValueError):
            order.acknowledge_next(simulate_failure=True)
        with self.assertRaisesRegex(ValueError, '63단계'):
            audit.measure_next()
        self.assertEqual(port.calls, [])
        order.resume()
        audit.measure_next()
        self.assertTrue(audit.snapshot().completed)

    def test_no_added_sleep_or_io(self):
        _, _, _, _, audit = setup(('x', 'y'))
        with patch('time.sleep', side_effect=AssertionError('artificial delay')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('db')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            audit.measure_batch()
        self.assertTrue(audit.snapshot().completed)

    def test_no_threshold_or_false_speed_claim(self):
        _, _, _, _, audit = setup(clock=Clock(0, 100_000_000_000))
        audit.measure_next()
        report = audit.snapshot()
        self.assertTrue(report.completed)
        description = report.describe()
        self.assertIn('속도 합격 기준 없음', description)
        self.assertIn('실제 플랫폼 메시지/AI 모델 0건', description)
        self.assertNotIn('속도 합격:', description)

    def test_batch_stops_at_first_clock_fault(self):
        _, _, port, _, audit = setup(('one', 'two'), clock=Clock(0, 5, 6, 1))
        with self.assertRaisesRegex(ValueError, '이미 처리됨'):
            audit.measure_batch()
        self.assertEqual(port.calls, ['one', 'two'])
        report = audit.snapshot()
        self.assertEqual([x.ordinal for x in report.samples], [1])
        self.assertEqual(report.unmeasured_ordinals, (2,))
        self.assertFalse(report.completed)

    def test_invalid_count_does_not_call_clock(self):
        _, _, port, _, audit = setup(clock=Clock())
        with self.assertRaises(ValueError):
            audit.measure_batch(0)
        self.assertEqual(port.calls, [])

    def test_unmeasured_after_failed_attempt_not_lost(self):
        _, _, port, reactions, audit = setup(('a', 'b'))
        audit.measure_next()
        port.fail = True
        with self.assertRaises(ValueError):
            audit.measure_next()
        self.assertEqual([x.ordinal for x in audit.snapshot().samples], [1])
        self.assertEqual(audit.snapshot().pending, 1)
        port.fail = False
        reactions.resume()
        audit.measure_next()
        self.assertTrue(audit.snapshot().completed)

    def test_no_auto_responses_on_construction_or_snapshot(self):
        _, _, port, _, audit = setup(('one', 'two'))
        audit.snapshot()
        audit.snapshot().describe()
        self.assertEqual(port.calls, [])


if __name__ == '__main__':
    unittest.main()
