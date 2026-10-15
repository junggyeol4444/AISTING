"""098 multiple independent accelerated virtual broadcasts, not real streaming."""
from dataclasses import FrozenInstanceError, replace
from unittest import TestCase
from unittest.mock import patch

from ai_broadcaster.offline_multisession_stability import (
    ALLOWED_ROUNDS, ALLOWED_HOURS, MAX_ROUND_REPORTS, MultiSessionReport,
    VirtualRound, run_virtual_multisession_stability,
)
from ai_broadcaster.offline_unattended_endurance import run_virtual_unattended_endurance


class MultiSessionStabilityTests(TestCase):
    def test_allowed_ranges(self):
        self.assertEqual(ALLOWED_ROUNDS, (3, 5, 10))
        self.assertEqual(ALLOWED_HOURS, (1, 3))
        self.assertEqual(MAX_ROUND_REPORTS, 10)

    def test_three_1h_rounds(self):
        r = run_virtual_multisession_stability(3, 1)
        self.assertTrue(r.passed, r.describe())
        self.assertEqual((r.total_accepted, r.total_responded), (39, 39))
        self.assertEqual(r.total_ticks, 3 * 3601)
        self.assertEqual([x.ordinal for x in r.rounds], [1, 2, 3])

    def test_five_3h_rounds(self):
        r = run_virtual_multisession_stability(5, 3)
        self.assertTrue(r.passed, r.describe())
        self.assertEqual(r.total_accepted, 185)
        self.assertEqual(r.total_ticks, 5 * 10801)

    def test_ten_1h_rounds_and_bounded_records(self):
        r = run_virtual_multisession_stability(10, 1)
        self.assertTrue(r.passed, r.describe())
        self.assertEqual((len(r.rounds), r.total_accepted), (10, 130))
        self.assertLessEqual(len(r.rounds), MAX_ROUND_REPORTS)

    def test_ten_3h_rounds(self):
        r = run_virtual_multisession_stability(10, 3)
        self.assertTrue(r.passed, r.describe())
        self.assertEqual(r.total_accepted, 370)
        self.assertEqual(r.total_ticks, 108010)

    def test_failing_round_is_not_retried_and_later_rounds_still_independent(self):
        r = run_virtual_multisession_stability(5, 1, fail_round=2)
        self.assertFalse(r.passed)
        self.assertEqual(r.failed_rounds, (2,))
        self.assertEqual(len(r.rounds), 5)
        self.assertEqual([x.passed for x in r.rounds], [True, False, True, True, True])
        self.assertEqual((r.rounds[2].accepted, r.rounds[2].responded), (13, 13))
        self.assertEqual(r.rounds[2].checked_ticks, 3601)
        self.assertIn('자동 재시도하지', r.failure)

    def test_corrupt_second_round_and_subsequent_clean(self):
        r = run_virtual_multisession_stability(3, 1, fail_round=2, failure_mode='corrupt')
        self.assertFalse(r.passed)
        self.assertEqual(r.failed_rounds, (2,))
        self.assertTrue(r.rounds[2].passed)

    def test_reverse_clock_error_is_not_success(self):
        r = run_virtual_multisession_stability(3, 3, fail_round=1, failure_mode='clock')
        self.assertEqual(r.failed_rounds, (1,))
        self.assertTrue(all(x.passed for x in r.rounds[1:]))

    def test_failed_closing_not_success(self):
        r = run_virtual_multisession_stability(3, 1, fail_round=3, failure_mode='closing')
        self.assertFalse(r.passed)
        self.assertFalse(r.rounds[-1].virtual_ended)
        self.assertEqual(r.failed_rounds, (3,))

    def test_failure_does_not_contaminate_new_invocation(self):
        self.assertFalse(run_virtual_multisession_stability(3, 1, fail_round=2).passed)
        self.assertTrue(run_virtual_multisession_stability(3, 1).passed)

    def test_repeated_runs_identical(self):
        self.assertEqual(run_virtual_multisession_stability(3, 1),
                         run_virtual_multisession_stability(3, 1))

    def test_reject_bad_rounds(self):
        for value in (0, 1, 2, 4, 11, -1, 3.0, '3', True, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_virtual_multisession_stability(value, 1)

    def test_reject_bad_hours(self):
        for value in (0, 2, 4, 1.0, '1', True, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_virtual_multisession_stability(3, value)

    def test_reject_bad_failure_ordinal(self):
        for value in (0, -1, 4, 1.0, '1', True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_virtual_multisession_stability(3, 1, fail_round=value)

    def test_reject_unknown_failure_mode(self):
        for value in ('io', '', None, True, 0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_virtual_multisession_stability(3, 1, failure_mode=value)

    def test_report_is_immutable(self):
        r = run_virtual_multisession_stability(3, 1)
        with self.assertRaises(FrozenInstanceError):
            r.total_accepted = 0
        with self.assertRaises(FrozenInstanceError):
            r.rounds[0].passed = False

    def test_corrupted_total_denies_success(self):
        r = run_virtual_multisession_stability(3, 1)
        self.assertFalse(replace(r, total_accepted=38).passed)
        self.assertFalse(replace(r, total_ticks=1).passed)
        self.assertFalse(replace(r, total_responded=0).passed)

    def test_missing_or_duplicated_round_denies_success(self):
        r = run_virtual_multisession_stability(3, 1)
        self.assertFalse(replace(r, rounds=r.rounds[:2]).passed)
        self.assertFalse(replace(r, rounds=(r.rounds[0], r.rounds[0], r.rounds[2])).passed)

    def test_fake_actual_broadcast_claim_denies_success(self):
        r = run_virtual_multisession_stability(3, 1)
        self.assertFalse(replace(r, actual_broadcast_tested=True).passed)
        self.assertFalse(replace(r, mock_only=False).passed)

    def test_forged_single_round_status_denies_success(self):
        r = run_virtual_multisession_stability(3, 1)
        fake = replace(r.rounds[1], virtual_ended=False)
        self.assertFalse(replace(r, rounds=(r.rounds[0], fake, r.rounds[2])).passed)
        fake = replace(r.rounds[1], accepted=12)
        self.assertFalse(replace(r, rounds=(r.rounds[0], fake, r.rounds[2])).passed)

    def test_mock_audit_port_exception_never_claims_success(self):
        with patch('ai_broadcaster.offline_multisession_stability.run_virtual_unattended_endurance',
                   side_effect=RuntimeError('synthetic failure')) as mock:
            r = run_virtual_multisession_stability(3, 1)
        self.assertFalse(r.passed)
        self.assertEqual(r.failed_rounds, (1, 2, 3))
        self.assertEqual(mock.call_count, 3)
        self.assertIn('synthetic failure', r.rounds[0].failure)

    def test_wrong_hours_report_is_rejected(self):
        actual = run_virtual_unattended_endurance(1)
        wrong = replace(actual, requested_hours=3)
        with patch('ai_broadcaster.offline_multisession_stability.run_virtual_unattended_endurance',
                   return_value=wrong):
            r = run_virtual_multisession_stability(3, 1)
        self.assertFalse(r.passed)

    def test_malformed_report_is_rejected(self):
        with patch('ai_broadcaster.offline_multisession_stability.run_virtual_unattended_endurance',
                   return_value=None):
            r = run_virtual_multisession_stability(3, 1)
        self.assertFalse(r.passed)
        self.assertEqual(len(r.rounds), 3)

    def test_no_sleep_socket_subprocess_or_file_io(self):
        with patch('time.sleep', side_effect=AssertionError('sleep')), \
             patch('socket.socket.connect', side_effect=AssertionError('net')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('builtins.open', side_effect=AssertionError('file io')):
            self.assertTrue(run_virtual_multisession_stability(3, 1).passed)

    def test_report_explicit_limits_and_stable_user_safe_output(self):
        r = run_virtual_multisession_stability(3, 1)
        s = r.describe()
        self.assertIn('미검증', s)
        self.assertIn('실제 송출', s)
        self.assertNotIn('실제 방송 성공', s)
        self.assertEqual(s.count('회차 통과'), 3)

    def test_changing_local_report_cannot_change_earlier_reports(self):
        first = run_virtual_multisession_stability(3, 1)
        second = run_virtual_multisession_stability(3, 1, fail_round=1)
        self.assertTrue(first.passed)
        self.assertFalse(second.passed)
        self.assertTrue(all(row.passed for row in first.rounds))
