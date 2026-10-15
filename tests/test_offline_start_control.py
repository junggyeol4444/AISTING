"""082 deterministic fail-closed manual start-control rehearsal, NOT actual broadcast."""
import socket
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_schedule import BroadcastScheduleDraft, parse_reference
from ai_broadcaster.offline_start_control import OfflineStartController
from ai_broadcaster.offline_settings import DEFAULTS


class OfflineStartControlTests(unittest.TestCase):
    def setUp(self):
        self.draft = BroadcastScheduleDraft().add(2, '19:30').add(4, '21:00')
        self.control = OfflineStartController(self.draft)
        self.when = parse_reference('2026-10-14 19:30')
        self.settings = dict(DEFAULTS)

    def test_matching_time_is_mock_ready_only(self):
        verdict = self.control.inspect(self.when, self.settings)
        self.assertEqual(verdict.code, 'mock_ready')
        self.assertTrue(verdict.can_mock_start)
        self.assertIn('실제 자동 시작은 비활성', verdict.explanation)

    def test_off_schedule_not_due(self):
        self.assertEqual(self.control.inspect(parse_reference('2026-10-14 19:29'), self.settings).code, 'not_due')

    def test_same_clock_time_wrong_weekday_not_due(self):
        self.assertEqual(self.control.inspect(parse_reference('2026-10-15 19:30'), self.settings).code, 'not_due')

    def test_exact_second_check(self):
        self.assertEqual(self.control.inspect(self.when + timedelta(seconds=1), self.settings).code, 'not_due')

    def test_empty_draft_not_due(self):
        self.assertEqual(OfflineStartController(BroadcastScheduleDraft()).inspect(self.when, self.settings).code,
                         'not_due')

    def test_unapproved_streaming_setting_blocks(self):
        for key in ('scheduled_execution', 'streaming_enabled', 'external_publish_enabled'):
            with self.subTest(key=key):
                unsafe = dict(self.settings, **{key: True})
                self.assertEqual(self.control.inspect(self.when, unsafe).code, 'blocked')
                self.assertEqual(self.control.simulate_start(self.when, unsafe).code, 'blocked')
                self.assertEqual(self.control.simulated_count, 0)

    def test_missing_policy_flags_block(self):
        self.assertEqual(self.control.inspect(self.when, {}).code, 'blocked')

    def test_non_bool_policy_flag_blocks(self):
        for invalid in (0, None, 'false', [], 1):
            with self.subTest(invalid=invalid):
                self.assertEqual(self.control.inspect(self.when, dict(self.settings, streaming_enabled=invalid)).code,
                                 'blocked')

    def test_invalid_settings_type_blocks(self):
        self.assertEqual(self.control.inspect(self.when, None).code, 'blocked')

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            self.control.inspect(datetime(2026, 10, 14, 19, 30), self.settings)

    def test_non_kst_datetime_rejected(self):
        with self.assertRaises(ValueError):
            self.control.inspect(datetime(2026, 10, 14, 10, 30, tzinfo=timezone.utc), self.settings)

    def test_invalid_draft_rejected(self):
        with self.assertRaises(TypeError):
            OfflineStartController(None)

    def test_manual_mock_start_and_finish(self):
        self.assertEqual(self.control.simulate_start(self.when, self.settings).code, 'mock_started')
        self.assertTrue(self.control.active)
        self.assertEqual(self.control.simulated_count, 1)
        self.assertEqual(self.control.simulate_finish().code, 'mock_finished')
        self.assertFalse(self.control.active)

    def test_duplicate_same_occurrence_rejected_even_after_finish(self):
        self.control.simulate_start(self.when, self.settings)
        self.control.simulate_finish()
        self.assertEqual(self.control.inspect(self.when, self.settings).code, 'duplicate')
        self.assertEqual(self.control.simulate_start(self.when, self.settings).code, 'duplicate')
        self.assertEqual(self.control.simulated_count, 1)

    def test_second_mock_while_active_blocked(self):
        self.control.simulate_start(self.when, self.settings)
        second = parse_reference('2026-10-16 21:00')
        self.assertEqual(self.control.inspect(second, self.settings).code, 'mock_active')
        self.assertEqual(self.control.simulate_start(second, self.settings).code, 'mock_active')
        self.assertEqual(self.control.simulated_count, 1)

    def test_mock_finish_without_active_is_noop(self):
        self.assertEqual(self.control.simulate_finish().code, 'not_active')

    def test_mock_display_failure_keeps_event_available(self):
        def fail(_):
            raise RuntimeError('broken canvas')
        verdict = self.control.simulate_start(self.when, self.settings, show_mock_start=fail)
        self.assertEqual(verdict.code, 'display_failed')
        self.assertFalse(self.control.active)
        self.assertEqual(self.control.simulated_count, 0)
        self.assertEqual(self.control.inspect(self.when, self.settings).code, 'mock_ready')

    def test_mock_display_success_receives_occurrence(self):
        observed = []
        self.control.simulate_start(self.when, self.settings, show_mock_start=observed.append)
        self.assertEqual(observed, ['2026-10-14 19:30 KST'])

    def test_second_week_same_slot_allowed(self):
        self.control.simulate_start(self.when, self.settings)
        self.control.simulate_finish()
        other = self.when + timedelta(days=7)
        self.assertEqual(self.control.simulate_start(other, self.settings).code, 'mock_started')
        self.assertEqual(self.control.simulated_count, 2)

    def test_manually_changed_draft_new_controller_does_not_mutate_previous(self):
        amended = self.draft.add(6, '10:30')
        fresh = OfflineStartController(amended)
        self.assertEqual(fresh.inspect(parse_reference('2026-10-18 10:30'), self.settings).code, 'mock_ready')
        self.assertEqual(self.control.inspect(parse_reference('2026-10-18 10:30'), self.settings).code, 'not_due')

    def test_settings_rechecked_between_inspection_and_start(self):
        self.assertTrue(self.control.inspect(self.when, self.settings).can_mock_start)
        unsafe = dict(self.settings, scheduled_execution=True)
        self.assertEqual(self.control.simulate_start(self.when, unsafe).code, 'blocked')

    def test_manual_math_without_clock_file_or_network(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('builtins.open', side_effect=AssertionError('file')), \
             patch('time.sleep', side_effect=AssertionError('sleep')), \
             patch('time.time', side_effect=AssertionError('clock')):
            self.assertEqual(self.control.inspect(self.when, self.settings).code, 'mock_ready')
            self.assertEqual(self.control.simulate_start(self.when, self.settings).code, 'mock_started')
            self.assertEqual(self.control.simulate_finish().code, 'mock_finished')


if __name__ == '__main__':
    unittest.main()
