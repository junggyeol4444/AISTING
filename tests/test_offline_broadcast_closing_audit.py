"""080: independent error-path audit of stage079. No real broadcast interface."""
import unittest
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_closing import OfflineBroadcastClosing
from ai_broadcaster.offline_broadcast_closing_audit import (
    ClosingAuditItem, ClosingAuditReport, run_offline_closing_audit,
)
from ai_broadcaster.offline_broadcast_duration import BroadcastDurationRules


class Stage80ClosingAuditTests(unittest.TestCase):
    def test_default_all_twelve_cases(self):
        result = run_offline_closing_audit()
        self.assertEqual((result.total, result.passed_count, result.passed), (12, 12, True))

    def test_all_scenarios_named_and_unique(self):
        names = [item.name for item in run_offline_closing_audit().checks]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn('중복 종료 호출 차단', names)
        self.assertIn('인사 표시 실패 시 가상 종료 차단', names)

    def test_localized_description_never_certifies_real_stop(self):
        description = run_offline_closing_audit().describe()
        self.assertIn('오프라인', description)
        self.assertIn('실제 음성·OBS·방송 자동 종료 미검증', description)
        self.assertIn('승인 대기', description)

    def test_custom_min_max(self):
        r = run_offline_closing_audit(5, 9, 'AI 인물')
        self.assertTrue(r.passed, r.describe())

    def test_equal_min_max(self):
        self.assertTrue(run_offline_closing_audit(1, 1).passed)

    def test_name_spaces_normalized_and_accepted(self):
        self.assertTrue(run_offline_closing_audit(5, 7, '  AI   방송인  ').passed)

    def test_invalid_duration_not_silently_changed(self):
        for args in ((0, 180), (181, 180), (60, 0), (True, 100), ('60', 180)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                run_offline_closing_audit(*args)

    def test_invalid_persona_not_silently_fallback(self):
        for name in ('', '   ', None, 'x'*41):
            with self.subTest(name=name), self.assertRaises(ValueError):
                run_offline_closing_audit(60, 180, name)

    def test_factory_must_be_callable(self):
        with self.assertRaises(ValueError):
            run_offline_closing_audit(session_factory='remote')

    def test_factory_failure_not_claimed_as_success(self):
        def broken(decision, name):
            raise RuntimeError('injected constructor failure')
        with self.assertRaises(RuntimeError):
            run_offline_closing_audit(session_factory=broken)

    def test_factory_logic_error_detected_as_incomplete(self):
        class BrokenClosing:
            def __init__(self, decision, name):
                self.calls = 0
            def snapshot(self):
                class Incorrect:
                    phase = 'virtual_ended'
                    delivered_lines = ()
                    virtual_stream_ended = True
                    next_line = None
                    details = 'wrong'
                return Incorrect()
            def advance(self, callback):
                self.calls += 1
                return self.snapshot()
        report = run_offline_closing_audit(session_factory=BrokenClosing)
        self.assertFalse(report.passed)
        self.assertLess(report.passed_count, report.total)
        self.assertIn('미통과', report.describe())

    def test_broken_advance_failure_produces_failed_checks(self):
        class BrokenClosing(OfflineBroadcastClosing):
            def advance(self, callback):
                raise AssertionError('stage079 regression')
        report = run_offline_closing_audit(session_factory=BrokenClosing)
        self.assertFalse(report.passed)
        self.assertTrue(any('AssertionError' in item.explanation for item in report.checks))

    def test_report_immutable(self):
        report = run_offline_closing_audit()
        self.assertIsInstance(report.checks, tuple)
        self.assertIsInstance(report.checks[0], ClosingAuditItem)
        with self.assertRaises((AttributeError, TypeError)):
            report.passed = True

    def test_manual_failed_report_describes_failed_check(self):
        r = ClosingAuditReport((ClosingAuditItem('display ack', False, 'failure'),))
        self.assertFalse(r.passed)
        self.assertIn('display ack', r.describe())

    def test_empty_report_fails_closed(self):
        self.assertFalse(ClosingAuditReport(()).passed)

    def test_separate_runs_not_shared(self):
        a, b = run_offline_closing_audit(), run_offline_closing_audit()
        self.assertIsNot(a, b)
        self.assertIsNot(a.checks, b.checks)
        self.assertTrue(a.passed and b.passed)

    def test_no_remote_process_sleep_or_file_io(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('time.sleep', side_effect=AssertionError('delay')), \
             patch('builtins.open', side_effect=AssertionError('file access')):
            self.assertTrue(run_offline_closing_audit().passed)

    def test_correct_source_duration_contract(self):
        decision = BroadcastDurationRules(60, 180).evaluate(180*60)
        obj = OfflineBroadcastClosing(decision, '아이스팅')
        self.assertEqual(obj.snapshot().phase, 'notice_pending')
        self.assertTrue(run_offline_closing_audit(60, 180).passed)


if __name__ == '__main__':
    unittest.main()
