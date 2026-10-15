"""097: real execution of accelerated 1/3-hour virtual ticks, NOT real broadcasting."""
from dataclasses import FrozenInstanceError
from unittest import TestCase
from unittest.mock import patch

from ai_broadcaster.offline_unattended_endurance import (
    ALLOWED_HOURS, CHAT_INTERVAL_SECONDS, MAX_SAMPLES,
    EnduranceSample, EnduranceReport, run_virtual_unattended_endurance,
)


class OfflineEnduranceTests(TestCase):
    def test_allowed_hours_are_one_and_three(self):
        self.assertEqual(ALLOWED_HOURS, (1, 3))

    def test_one_hour_all_virtual_ticks(self):
        result = run_virtual_unattended_endurance(1)
        self.assertTrue(result.passed, result.describe())
        self.assertEqual((result.virtual_seconds_checked, result.ticks_checked), (3600, 3601))
        self.assertEqual(result.accepted, 13)
        self.assertEqual(result.responded, 13)
        self.assertEqual(result.delivered_closing_lines, 2)

    def test_three_hours_all_virtual_ticks(self):
        result = run_virtual_unattended_endurance(3)
        self.assertTrue(result.passed, result.describe())
        self.assertEqual((result.virtual_seconds_checked, result.ticks_checked), (10800, 10801))
        self.assertEqual(result.accepted, 37)
        self.assertEqual(result.responded, 37)

    def test_report_has_bounded_samples_not_full_history(self):
        result = run_virtual_unattended_endurance(3)
        self.assertLessEqual(len(result.samples), MAX_SAMPLES)
        self.assertGreaterEqual(len(result.samples), 2)
        self.assertEqual(result.samples[0].virtual_second, 0)
        self.assertEqual(result.samples[-1].virtual_second, 10800)
        self.assertTrue(all(x.pending == 0 for x in result.samples))
        self.assertEqual(result.peak_pending, 1)

    def test_report_does_not_claim_actual_stream_or_real_run(self):
        result = run_virtual_unattended_endurance(3)
        self.assertTrue(result.mock_only)
        self.assertFalse(result.actual_broadcast_tested)
        self.assertEqual(result.real_elapsed_hours, 0)
        self.assertIn('미검증', result.describe())
        self.assertNotIn('실제 방송 완료', result.describe())

    def test_synthetic_duplicate_texts_are_counted_not_deduplicated(self):
        result = run_virtual_unattended_endurance(3)
        self.assertEqual(result.accepted, 1 + 10800 // CHAT_INTERVAL_SECONDS)

    def test_injected_reply_error_fails_closed_and_retains_one_pending(self):
        result = run_virtual_unattended_endurance(1, fault_second=600)
        self.assertFalse(result.passed)
        self.assertIn('자동 재시도 없이 중단', result.failure)
        self.assertEqual((result.accepted, result.responded, result.pending), (3, 2, 1))
        self.assertFalse(result.virtual_end)
        self.assertLess(result.virtual_seconds_checked, 3600)

    def test_fault_at_zero_is_not_ignored(self):
        result = run_virtual_unattended_endurance(1, fault_second=0)
        self.assertFalse(result.passed)
        self.assertEqual((result.accepted, result.responded, result.pending), (1, 0, 1))
        self.assertEqual(result.ticks_checked, 0)

    def test_fault_at_final_tick_does_not_approve_closing(self):
        result = run_virtual_unattended_endurance(1, fault_second=3600)
        self.assertFalse(result.passed)
        self.assertEqual(result.delivered_closing_lines, 0)

    def test_integrity_corruption_causes_hold_not_pass(self):
        result = run_virtual_unattended_endurance(1, corrupt_second=602)
        self.assertFalse(result.passed)
        self.assertIn('불일치', result.failure)
        self.assertFalse(result.virtual_end)

    def test_clock_reverse_fails_without_recovery(self):
        result = run_virtual_unattended_endurance(1, reverse_clock_second=602)
        self.assertFalse(result.passed)
        self.assertIn('시계 역행', result.failure)

    def test_closing_display_failure_prevents_completion(self):
        result = run_virtual_unattended_endurance(1, fail_closing_display=True)
        self.assertFalse(result.passed)
        self.assertEqual(result.delivered_closing_lines, 0)
        self.assertFalse(result.virtual_end)
        self.assertEqual(result.accepted, result.responded)

    def test_invalid_hours_fail_before_work(self):
        for value in (0, 2, 4, 24, 1.0, True, False, '1', None, -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_virtual_unattended_endurance(value)

    def test_invalid_fault_seconds_and_bool_are_rejected(self):
        for value in (-1, 3601, True, 1.5, '600'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_virtual_unattended_endurance(1, fault_second=value)
        with self.assertRaises(ValueError):
            run_virtual_unattended_endurance(1, fault_second=601)
        with self.assertRaises(ValueError):
            run_virtual_unattended_endurance(1, fail_closing_display='false')

    def test_invalid_corruption_seconds_are_rejected(self):
        with self.assertRaises(ValueError):
            run_virtual_unattended_endurance(1, corrupt_second=999999)

    def test_invalid_reverse_clock_seconds_are_rejected(self):
        with self.assertRaises(ValueError):
            run_virtual_unattended_endurance(1, reverse_clock_second=-5)

    def test_two_independent_runs_have_same_output_no_shared_state(self):
        one = run_virtual_unattended_endurance(1)
        two = run_virtual_unattended_endurance(1)
        self.assertEqual(one, two)
        self.assertTrue(one.passed)

    def test_three_sequential_three_hour_runs(self):
        outputs = [run_virtual_unattended_endurance(3) for _ in range(3)]
        self.assertTrue(all(x.passed for x in outputs))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[1], outputs[2])

    def test_a_failed_run_does_not_affect_next(self):
        self.assertFalse(run_virtual_unattended_endurance(1, corrupt_second=50).passed)
        self.assertTrue(run_virtual_unattended_endurance(1).passed)

    def test_immutable_report_and_samples(self):
        report = run_virtual_unattended_endurance(1)
        with self.assertRaises(FrozenInstanceError):
            report.accepted = -1
        with self.assertRaises(FrozenInstanceError):
            report.samples[0].pending = 10

    def test_corrupted_report_denied_by_pass_condition(self):
        good = run_virtual_unattended_endurance(1)
        bad = EnduranceReport(good.requested_hours, good.virtual_seconds_checked,
                              good.ticks_checked, good.accepted, good.responded - 1,
                              good.pending, good.peak_pending, good.samples,
                              good.delivered_closing_lines, good.virtual_end, '')
        self.assertFalse(bad.passed)

    def test_empty_samples_never_pass(self):
        self.assertFalse(EnduranceReport(1, 3600, 3601, 13, 13, 0, 1, (), 2, True, '').passed)

    def test_report_cannot_claim_real_broadcast(self):
        ok = run_virtual_unattended_endurance(1)
        fake = EnduranceReport(ok.requested_hours, ok.virtual_seconds_checked,
                               ok.ticks_checked, ok.accepted, ok.responded,
                               ok.pending, ok.peak_pending, ok.samples,
                               ok.delivered_closing_lines, ok.virtual_end,
                               '', True, True, 0)
        self.assertFalse(fake.passed)

    def test_no_real_clock_sleep_network_or_process(self):
        with patch('time.sleep', side_effect=AssertionError('sleep')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            self.assertTrue(run_virtual_unattended_endurance(1).passed)

    def test_no_external_file_read_write(self):
        with patch('builtins.open', side_effect=AssertionError('file I/O')):
            self.assertTrue(run_virtual_unattended_endurance(1).passed)

    def test_failing_reply_never_reaches_end_even_three_hours(self):
        self.assertFalse(run_virtual_unattended_endurance(3, fault_second=900).passed)

    def test_audit_samples_are_consistent(self):
        report = run_virtual_unattended_endurance(3)
        for sample in report.samples:
            self.assertEqual(sample.accepted, sample.responded)
            self.assertEqual(sample.accepted, sample.virtual_second // 300 + 1)

    def test_unexpected_reply_port_failure_is_reported_not_success(self):
        from ai_broadcaster.core_execution import MockCoreReplyPort
        with patch.object(MockCoreReplyPort, 'generate', side_effect=RuntimeError('injected')):
            r = run_virtual_unattended_endurance(1)
        self.assertFalse(r.passed)
        self.assertGreater(r.pending, 0)
        self.assertIn('응답', r.failure)

    def test_unexpected_duration_failure_is_reported_not_success(self):
        from ai_broadcaster.offline_broadcast_duration import BroadcastDurationSession
        with patch.object(BroadcastDurationSession, 'check', side_effect=ValueError('broken')):
            r = run_virtual_unattended_endurance(1)
        self.assertFalse(r.passed)
        self.assertFalse(r.virtual_end)

    def test_error_fault_mode_does_not_auto_resume(self):
        r = run_virtual_unattended_endurance(1, fault_second=300)
        self.assertEqual(r.accepted - r.responded, 1)
        self.assertEqual(r.delivered_closing_lines, 0)
