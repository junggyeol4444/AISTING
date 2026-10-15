"""Original 078 duration decision checks; NEVER ends an actual stream."""
import math
import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_duration import (
    BroadcastDurationRules, BroadcastDurationSession,
    DEFAULT_MINIMUM_MINUTES, DEFAULT_MAXIMUM_MINUTES,
)


class DurationRulesTests(unittest.TestCase):
    def test_plan_defaults(self):
        self.assertEqual((DEFAULT_MINIMUM_MINUTES, DEFAULT_MAXIMUM_MINUTES), (60, 180))

    def test_before_minimum_blocks_end(self):
        for seconds in (0, 1, 3599.999):
            with self.subTest(seconds=seconds):
                d = BroadcastDurationRules().evaluate(seconds)
                self.assertFalse(d.can_consider_ending)
                self.assertFalse(d.maximum_reached)
                self.assertEqual(d.action, 'continue')

    def test_exact_minimum_enables_only_eligibility(self):
        d = BroadcastDurationRules().evaluate(3600)
        self.assertTrue(d.can_consider_ending)
        self.assertFalse(d.maximum_reached)
        self.assertEqual(d.action, 'continue')

    def test_just_below_and_equal_maximum(self):
        a = BroadcastDurationRules().evaluate(10799.999)
        b = BroadcastDurationRules().evaluate(10800)
        self.assertFalse(a.maximum_reached)
        self.assertTrue(b.maximum_reached)
        self.assertEqual(b.action, 'wrap_up_requested')
        self.assertIn('실제 종료하지 않음', b.description)

    def test_over_maximum_still_no_termination(self):
        d = BroadcastDurationRules().evaluate(1_000_000)
        self.assertTrue(d.maximum_reached)
        self.assertNotIn('terminated', d.action)

    def test_changed_operator_limits_respected(self):
        r = BroadcastDurationRules(20, 45)
        self.assertFalse(r.evaluate(19*60).can_consider_ending)
        self.assertTrue(r.evaluate(20*60).can_consider_ending)
        self.assertFalse(r.evaluate(44*60).maximum_reached)
        self.assertTrue(r.evaluate(45*60).maximum_reached)

    def test_equal_limits(self):
        r = BroadcastDurationRules(10, 10)
        self.assertFalse(r.evaluate(599).can_consider_ending)
        self.assertTrue(r.evaluate(600).can_consider_ending)
        self.assertTrue(r.evaluate(600).maximum_reached)

    def test_reject_zero_and_negative_limits(self):
        for a, b in ((0, 180), (1, 0), (-1, 10), (10, -20)):
            with self.subTest(a=a, b=b), self.assertRaises(ValueError):
                BroadcastDurationRules(a, b)

    def test_reject_inverted_limits(self):
        with self.assertRaises(ValueError):
            BroadcastDurationRules(181, 180)

    def test_reject_excessive_limits(self):
        for a, b in ((1, 1441), (1441, 1441)):
            with self.subTest(a=a, b=b), self.assertRaises(ValueError):
                BroadcastDurationRules(a, b)

    def test_reject_non_integer_limits_and_bools(self):
        for value in (True, False, 30.5, '60', None, math.nan, 1e100):
            with self.subTest(value=value), self.assertRaises(ValueError):
                BroadcastDurationRules(value, 180)

    def test_reject_invalid_elapsed(self):
        for value in (-0.01, '0', None, True, False, math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                BroadcastDurationRules().evaluate(value)

    def test_precision_seconds(self):
        self.assertFalse(BroadcastDurationRules().evaluate(3599.999999).minimum_satisfied)
        self.assertTrue(BroadcastDurationRules().evaluate(3600.0).minimum_satisfied)

    def test_data_immutable(self):
        obj = BroadcastDurationRules()
        d = obj.evaluate(60)
        with self.assertRaises(FrozenInstanceError):
            obj.minimum_minutes = 5
        with self.assertRaises(FrozenInstanceError):
            d.maximum_reached = True

    def test_no_io_network_process_or_wait(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('time.sleep', side_effect=AssertionError('delay')):
            for second in (0, 3600, 10800):
                BroadcastDurationRules().evaluate(second)

    def test_description_discloses_mock(self):
        d = BroadcastDurationRules().evaluate(10800)
        for word in ('가상', 'OBS', '사용자 승인', '마무리'):
            self.assertIn(word, d.description)


class DurationSessionTests(unittest.TestCase):
    def test_time_progression_monotonic(self):
        s = BroadcastDurationSession(BroadcastDurationRules(), 100.0)
        self.assertFalse(s.check(100).minimum_satisfied)
        self.assertTrue(s.check(3700).minimum_satisfied)
        self.assertFalse(s.check(3700).maximum_reached)
        self.assertTrue(s.check(10900).maximum_reached)

    def test_clock_rollback_rejected(self):
        s = BroadcastDurationSession(BroadcastDurationRules(), 42)
        s.check(100)
        with self.assertRaisesRegex(ValueError, '역행'):
            s.check(99)
        self.assertEqual(s.check(101).elapsed_seconds, 59)

    def test_session_invalid_inputs(self):
        for rules in (None, '60/180'):
            with self.assertRaises(ValueError):
                BroadcastDurationSession(rules, 1)
        for value in (True, None, math.inf, math.nan, 'clock'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                BroadcastDurationSession(BroadcastDurationRules(), value)

    def test_future_clock_invalid_keeps_last_state(self):
        s = BroadcastDurationSession(BroadcastDurationRules(), 10)
        for value in (math.nan, math.inf, True, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                s.check(value)
        self.assertEqual(s.check(11).elapsed_seconds, 1)

    def test_without_real_clock_or_scheduler(self):
        with patch('time.monotonic', side_effect=AssertionError('real clock forbidden')), \
             patch('time.sleep', side_effect=AssertionError('sleep forbidden')):
            s = BroadcastDurationSession(BroadcastDurationRules(), 100)
            self.assertTrue(s.check(10900).maximum_reached)


if __name__ == '__main__':
    unittest.main()
