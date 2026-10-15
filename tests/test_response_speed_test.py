"""36 original roadmap: repeatable timing with deterministic fake monotonic clock."""
import copy
import unittest
from unittest.mock import patch

from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.response_speed_test import (
    SAMPLE_SPEED_SCRIPT, MAX_REACTION_TURNS, MAX_REACTION_SCRIPT,
    run_response_speed_test,
)


class ScriptedClock:
    def __init__(self, readings):
        self.readings = iter(readings)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return next(self.readings)


class SpyPort:
    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at

    def generate(self, item, history):
        self.calls.append((item, tuple(history)))
        if self.fail_at == len(self.calls):
            raise RuntimeError('sensitive_path=/private/token')
        return '모의 답변 ' + item.text


class SpeedTests(unittest.TestCase):
    def setUp(self):
        self.settings = copy.deepcopy(DEFAULTS)

    def test_basic_sample_timing_and_no_quality_claim(self):
        clock = ScriptedClock([x for pair in [(i * 10_000_000, i * 10_000_000 + (i + 1) * 1_000_000)
                                            for i in range(6)] for x in pair])
        report = run_response_speed_test(self.settings, clock_ns=clock)
        self.assertTrue(report.completed)
        self.assertEqual([round(x.elapsed_ms) for x in report.turns], [1, 2, 3, 4, 5, 6])
        self.assertEqual(report.median_ms, 3.5)
        self.assertEqual(report.p95_ms, 6.0)
        self.assertEqual(report.total_measured_ms, 21.0)
        self.assertEqual((report.total, report.remaining, report.attempts), (6, 0, 6))
        self.assertIn('자연스러움', report.describe())
        self.assertNotIn('자연스러움 통과', report.describe())
        self.assertEqual(clock.calls, 12)

    def test_single_turn_and_zero_elapsed_allowed(self):
        r = run_response_speed_test(self.settings, '가: ㅋㅋㅋ', clock_ns=ScriptedClock([7, 7]))
        self.assertTrue(r.completed)
        self.assertEqual((r.median_ms, r.p95_ms, r.total_measured_ms), (0.0, 0.0, 0.0))

    def test_duplicate_text_and_order_not_deduplicated(self):
        spy = SpyPort()
        r = run_response_speed_test(self.settings, '별: hi\n별: hi\n달: 🌙', reply_port=spy,
                                    clock_ns=ScriptedClock([0, 1, 2, 4, 5, 8]))
        self.assertTrue(r.completed)
        self.assertEqual([x.text for x in r.turns], ['hi', 'hi', '🌙'])
        self.assertEqual([i.sender for i, _ in spy.calls], ['별', '별', '달'])
        self.assertEqual([len(h) for _, h in spy.calls], [0, 1, 2])

    def test_context_is_limited_to_eight(self):
        spy = SpyPort()
        script = '\n'.join(f'가: {i}' for i in range(12))
        report = run_response_speed_test(self.settings, script, reply_port=spy,
                                         clock_ns=ScriptedClock(range(24)))
        self.assertTrue(report.completed)
        self.assertEqual([x.input.text for x in spy.calls[-1][1]], [str(i) for i in range(3, 11)])

    def test_port_failure_stops_without_retry_and_redacts_sensitive_message(self):
        spy = SpyPort(fail_at=2)
        r = run_response_speed_test(self.settings, 'a: 1\na: 2\na: 3', reply_port=spy,
                                    clock_ns=ScriptedClock([0, 5, 6, 50]))
        self.assertFalse(r.completed)
        self.assertEqual((len(r.turns), r.attempts, r.remaining), (1, 2, 2))
        self.assertEqual(len(spy.calls), 2)
        self.assertNotIn('sensitive_path', r.describe())
        self.assertIn('자동 재시도 없음', r.describe())
        self.assertEqual(r.total_measured_ms, .000005)

    def test_clock_decrease_is_failure_never_positive_or_pass(self):
        r = run_response_speed_test(self.settings, '가: 안녕', clock_ns=ScriptedClock([100, 99]))
        self.assertFalse(r.completed)
        self.assertEqual((len(r.turns), r.remaining, r.attempts), (0, 0, 1))
        self.assertIsNone(r.median_ms)
        self.assertIn('시계 오류', r.describe())

    def test_invalid_clock_types_rejected(self):
        for pair in [(True, 10), (-1, 10), (0, True), (0, 1.2), (0, None), (0, 'x')]:
            with self.subTest(pair=pair):
                r = run_response_speed_test(self.settings, '가: 안녕', clock_ns=ScriptedClock(pair))
                self.assertFalse(r.completed)

    def test_broken_clock_and_error_text_redacted(self):
        def broken():
            raise RuntimeError('secret/token')
        r = run_response_speed_test(self.settings, '가: 안녕', clock_ns=broken)
        self.assertFalse(r.completed)
        self.assertEqual((r.attempts, r.remaining), (0, 1))
        self.assertNotIn('secret', r.describe())

    def test_first_valid_then_clock_exception(self):
        clock = ScriptedClock([0, 2, 3])
        r = run_response_speed_test(self.settings, '가: 1\n가: 2', clock_ns=clock)
        self.assertFalse(r.completed)
        self.assertEqual((r.attempts, r.remaining, len(r.turns)), (2, 0, 1))
        self.assertEqual(r.turns[0].elapsed_ns, 2)

    def test_missing_or_oversized_script_rejected_before_clock(self):
        clock = ScriptedClock([])
        for script in ('', '말머리 누락', None, 5, 'a'*(MAX_REACTION_SCRIPT+1),
                       '\n'.join('가: 안녕' for _ in range(MAX_REACTION_TURNS + 1))):
            with self.subTest(invalid=str(script)[:15]), self.assertRaises(ValueError):
                run_response_speed_test(self.settings, script, clock_ns=clock)
        self.assertEqual(clock.calls, 0)

    def test_max_thirty_messages(self):
        pairs = [v for i in range(30) for v in (i*3, i*3+1)]
        r = run_response_speed_test(self.settings, '\n'.join('가: 안녕' for _ in range(30)),
                                    clock_ns=ScriptedClock(pairs))
        self.assertTrue(r.completed)
        self.assertEqual(len(r.turns), 30)
        self.assertEqual(r.p95_ms, 0.000001)

    def test_no_sleep_network_sqlite_process_pc_probe_or_data_mutation(self):
        initial = copy.deepcopy(self.settings)
        with patch('time.sleep', side_effect=AssertionError('delay')) as sleep, \
             patch('socket.socket.connect', side_effect=AssertionError('network')) as network, \
             patch('sqlite3.connect', side_effect=AssertionError('sqlite')) as sqlite, \
             patch('subprocess.Popen', side_effect=AssertionError('install')) as process, \
             patch('platform.system', side_effect=AssertionError('pc info')) as pc:
            self.assertTrue(run_response_speed_test(self.settings,
                            clock_ns=ScriptedClock(range(12))).completed)
            sleep.assert_not_called(); network.assert_not_called(); sqlite.assert_not_called()
            process.assert_not_called(); pc.assert_not_called()
        self.assertEqual(initial, self.settings)

    def test_separate_runs_no_shared_state(self):
        r1 = run_response_speed_test(self.settings, '가: 안녕', clock_ns=ScriptedClock([0, 1]))
        r2 = run_response_speed_test(self.settings, '나: 잘가', clock_ns=ScriptedClock([0, 2]))
        self.assertEqual((r1.turns[0].sender, r2.turns[0].sender), ('가', '나'))
        self.assertEqual((r1.attempts, r2.attempts), (1, 1))


if __name__ == '__main__':
    unittest.main()
