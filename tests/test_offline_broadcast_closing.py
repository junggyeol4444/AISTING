"""079 closing-sequence unit tests. No real output or I/O."""
import unittest
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_closing import OfflineBroadcastClosing
from ai_broadcaster.offline_broadcast_duration import BroadcastDurationRules


class ClosingTests(unittest.TestCase):
    def ready(self, name='아이스팅'):
        return OfflineBroadcastClosing(BroadcastDurationRules().evaluate(180 * 60), name)

    def test_before_max_not_allowed(self):
        for elapsed in (0, 59*60, 60*60, 179*60):
            with self.subTest(elapsed=elapsed), self.assertRaises(ValueError):
                OfflineBroadcastClosing(BroadcastDurationRules().evaluate(elapsed), 'AI')

    def test_no_decision_rejected(self):
        with self.assertRaises(ValueError):
            OfflineBroadcastClosing(None, 'AI')

    def test_name_invalid(self):
        for name in (None, '', '  ', 'x'*41, '\n\t'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.ready(name)

    def test_name_normalization(self):
        a = self.ready('  AI   STING  ')
        self.assertTrue(a.snapshot().next_line.startswith('AI STING:'))

    def test_initial_pending(self):
        result = self.ready().snapshot()
        self.assertEqual(result.phase, 'notice_pending')
        self.assertEqual(result.delivered_lines, ())
        self.assertFalse(result.virtual_stream_ended)

    def test_advance_one_notice_then_farewell_pending(self):
        session = self.ready()
        items = []
        result = session.advance(items.append)
        self.assertEqual(result.phase, 'farewell_pending')
        self.assertEqual(len(items), 1)
        self.assertIn('마무리', items[0])
        self.assertFalse(result.virtual_stream_ended)

    def test_second_ack_virtual_ends(self):
        session = self.ready()
        lines = []
        session.advance(lines.append)
        result = session.advance(lines.append)
        self.assertEqual(result.phase, 'virtual_ended')
        self.assertTrue(result.virtual_stream_ended)
        self.assertIsNone(result.next_line)
        self.assertEqual(len(result.delivered_lines), 2)
        self.assertIn('다음에', lines[-1])
        self.assertIn('실제 OBS/방송 종료 0건', result.details)

    def test_cannot_advance_after_virtual_end(self):
        session = self.ready()
        session.advance(lambda text: None)
        session.advance(lambda text: None)
        with self.assertRaises(ValueError):
            session.advance(lambda text: None)

    def test_failed_notice_preserved(self):
        session = self.ready()
        first_line = session.snapshot().next_line
        def fail(_):
            raise RuntimeError('display unavailable')
        with self.assertRaises(RuntimeError):
            session.advance(fail)
        self.assertEqual(session.snapshot().next_line, first_line)
        self.assertEqual(session.snapshot().delivered_lines, ())

    def test_failed_farewell_preserved_not_ended(self):
        session = self.ready()
        session.advance(lambda text: None)
        pending = session.snapshot().next_line
        with self.assertRaises(ZeroDivisionError):
            session.advance(lambda text: 1/0)
        state = session.snapshot()
        self.assertEqual(state.phase, 'farewell_pending')
        self.assertFalse(state.virtual_stream_ended)
        self.assertEqual(state.next_line, pending)
        self.assertEqual(len(state.delivered_lines), 1)

    def test_manual_retry_only(self):
        session = self.ready()
        attempts = []
        def display(text):
            attempts.append(text)
            if len(attempts) == 1:
                raise RuntimeError('offline failure')
        with self.assertRaises(RuntimeError):
            session.advance(display)
        self.assertEqual(len(attempts), 1)
        session.advance(display)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0], attempts[1])

    def test_reentrant_advance_blocked(self):
        session = self.ready()
        def display(text):
            with self.assertRaisesRegex(RuntimeError, '중복'):
                session.advance(lambda _: None)
        result = session.advance(display)
        self.assertEqual(result.phase, 'farewell_pending')

    def test_requires_callable(self):
        session = self.ready()
        for invalid in (None, False, 'hi'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                session.advance(invalid)
        self.assertEqual(session.snapshot().phase, 'notice_pending')

    def test_snapshot_immutable_and_no_mutable_leak(self):
        session = self.ready()
        before = session.snapshot()
        self.assertIsInstance(before.delivered_lines, tuple)
        with self.assertRaises((AttributeError, TypeError)):
            before.delivered_lines += ('spoof',)
        self.assertEqual(session.snapshot().delivered_lines, ())

    def test_separate_instances_do_not_share_state(self):
        left, right = self.ready(), self.ready()
        left.advance(lambda _: None)
        self.assertEqual(right.snapshot().delivered_lines, ())

    def test_no_external_interfaces(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('subprocess')), \
             patch('time.sleep', side_effect=AssertionError('sleep')):
            session = self.ready()
            session.advance(lambda _: None)
            session.advance(lambda _: None)
            self.assertTrue(session.snapshot().virtual_stream_ended)

    def test_works_with_operator_changed_duration(self):
        decision = BroadcastDurationRules(10, 20).evaluate(1200)
        session = OfflineBroadcastClosing(decision, '캐릭터')
        self.assertEqual(session.snapshot().phase, 'notice_pending')

    def test_description_never_claims_real_stop(self):
        session = self.ready()
        self.assertIn('실제', session.snapshot().details)
        session.advance(lambda _: None)
        self.assertIn('실제', session.snapshot().details)
        session.advance(lambda _: None)
        self.assertIn('0건', session.snapshot().details)


if __name__ == '__main__':
    unittest.main()
