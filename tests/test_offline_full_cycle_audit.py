"""Stage 083: full offline start/duration/closing protocol integration."""
import unittest
from dataclasses import FrozenInstanceError
from datetime import timedelta
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_schedule import BroadcastScheduleDraft, parse_reference
from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.offline_start_control import OfflineStartController, StartDecision
from ai_broadcaster.offline_broadcast_closing import OfflineBroadcastClosing
from ai_broadcaster.offline_full_cycle_audit import run_offline_full_cycle_audit


class CycleAuditTests(unittest.TestCase):
    def setUp(self):
        self.draft = BroadcastScheduleDraft().add(2, '19:30')
        self.when = parse_reference('2026-10-14 19:30')
        self.settings = {**DEFAULTS}

    def run_audit(self, **kwargs):
        return run_offline_full_cycle_audit(self.draft, self.when, self.settings,
                                             '아이스팅', **kwargs)

    def test_happy_path_four_ordered_events_and_14_checks(self):
        report = self.run_audit()
        self.assertTrue(report.passed, report.describe())
        self.assertEqual(len(report.checks), 14)
        self.assertEqual(report.events, ('가상 시작 기록', '마무리 예고 표시',
                                         '작별 인사 표시', '가상 종료 기록'))

    def test_report_is_explicitly_virtual_only(self):
        report = self.run_audit()
        self.assertTrue(report.simulated_only)
        self.assertIn('실제 자동 방송', report.describe())
        self.assertNotIn('실제 방송 성공', report.describe())

    def test_schedule_missing_is_failure_not_fake_pass(self):
        report = run_offline_full_cycle_audit(BroadcastScheduleDraft(), self.when,
                                               self.settings, '아이스팅')
        self.assertFalse(report.passed)
        self.assertEqual(report.events, ())
        self.assertFalse(report.checks[0].passed)

    def test_wrong_minute_fails(self):
        self.when = parse_reference('2026-10-14 19:31')
        self.assertFalse(self.run_audit().passed)

    def test_wrong_weekday_fails(self):
        self.when += timedelta(days=1)
        self.assertFalse(self.run_audit().passed)

    def test_existing_auto_execution_flag_blocks(self):
        self.settings['scheduled_execution'] = True
        self.assertFalse(self.run_audit().passed)

    def test_existing_streaming_enabled_blocks(self):
        self.settings['streaming_enabled'] = True
        self.assertFalse(self.run_audit().passed)

    def test_external_publish_blocks(self):
        self.settings['external_publish_enabled'] = True
        self.assertFalse(self.run_audit().passed)

    def test_missing_off_switch_blocks(self):
        self.settings.pop('streaming_enabled')
        self.assertFalse(self.run_audit().passed)

    def test_invalid_minimum_and_maximum_rejected(self):
        with self.assertRaises(ValueError):
            self.run_audit(minimum_minutes=180, maximum_minutes=60)

    def test_equal_minimum_and_maximum_handled(self):
        self.assertTrue(self.run_audit(minimum_minutes=60, maximum_minutes=60).passed)

    def test_custom_minutes_handled(self):
        self.assertTrue(self.run_audit(minimum_minutes=1, maximum_minutes=2).passed)

    def test_invalid_persona_fails_closed(self):
        report = run_offline_full_cycle_audit(self.draft, self.when, self.settings, '')
        self.assertFalse(report.passed)
        self.assertNotIn('가상 종료 기록', report.events)

    def test_start_controller_wrong_status_is_failure(self):
        class BadStart(OfflineStartController):
            def simulate_start(self, *a, **kw):
                return StartDecision('mock_started', 'wrong', 'fake')
        report = self.run_audit(start_factory=BadStart)
        self.assertFalse(report.passed)
        self.assertNotIn('가상 종료 기록', report.events)

    def test_rejected_finish_not_called_success(self):
        class BadFinish(OfflineStartController):
            def simulate_finish(self):
                return StartDecision('not_active', 'wrong')
        report = self.run_audit(start_factory=BadFinish)
        self.assertFalse(report.passed)
        self.assertEqual(report.checks[-1].name, '가상 시작 세션 안전하게 마무리')

    def test_close_notice_failure_does_not_claim_end(self):
        class BadClosing(OfflineBroadcastClosing):
            def advance(self, callback):
                raise RuntimeError('offline display failed')
        report = self.run_audit(closing_factory=BadClosing)
        self.assertFalse(report.passed)
        self.assertNotIn('가상 종료 기록', report.events)
        self.assertIn('RuntimeError', report.checks[-1].detail)

    def test_close_skips_notice_is_failure(self):
        class BadOrder(OfflineBroadcastClosing):
            def __init__(self, *args):
                super().__init__(*args)
                self._phase = 'farewell_pending'
        report = self.run_audit(closing_factory=BadOrder)
        self.assertFalse(report.passed)
        self.assertEqual(report.events, ('가상 시작 기록',))

    def test_factory_crashes_report_failed(self):
        def crash(_draft):
            raise AssertionError('controller unavailable')
        report = self.run_audit(start_factory=crash)
        self.assertFalse(report.passed)
        self.assertIn('controller unavailable', report.checks[-1].detail)

    def test_invalid_factory_rejected(self):
        with self.assertRaises(ValueError):
            self.run_audit(start_factory=None)

    def test_user_draft_and_settings_unchanged(self):
        original = dict(self.settings)
        original_draft = self.draft
        self.run_audit()
        self.assertEqual(self.settings, original)
        self.assertEqual(self.draft, original_draft)

    def test_repeated_invocations_isolated(self):
        self.assertTrue(self.run_audit().passed)
        self.assertTrue(self.run_audit().passed)

    def test_report_is_immutable(self):
        report = self.run_audit()
        with self.assertRaises(FrozenInstanceError):
            report.checks[0].passed = False

    def test_never_accesses_clock_disk_network_sleep_or_process(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('builtins.open', side_effect=AssertionError('file')), \
             patch('time.sleep', side_effect=AssertionError('sleep')), \
             patch('time.time', side_effect=AssertionError('clock')):
            report = self.run_audit()
        self.assertTrue(report.passed)


if __name__ == '__main__':
    unittest.main()
