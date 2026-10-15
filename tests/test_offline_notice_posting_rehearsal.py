"""Original 086: offline start-notice display only, never remote publication."""
import unittest
from dataclasses import FrozenInstanceError, replace
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_schedule import BroadcastScheduleDraft, parse_reference
from ai_broadcaster.offline_notice_posting_rehearsal import OfflineNoticePostingRehearsal
from ai_broadcaster.offline_prebroadcast_notice import make_prebroadcast_notice
from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.offline_start_control import OfflineStartController


class OfflinePostingTests(unittest.TestCase):
    def setUp(self):
        self.settings = dict(DEFAULTS)
        self.when = parse_reference('2026-10-14 19:30')
        self.control = OfflineStartController(BroadcastScheduleDraft().add(2, '19:30'))
        self.notice = make_prebroadcast_notice(self.settings, self.when)
        self.audit = OfflineNoticePostingRehearsal()
        self.shown = []

    def begin(self):
        self.assertEqual(self.control.simulate_start(self.when, self.settings).code, 'mock_started')

    def display(self):
        return self.audit.simulate_display(self.notice, self.control, self.settings,
                                           show_local=self.shown.append)

    def test_not_started(self):
        self.assertEqual(self.audit.inspect(self.notice, self.control, self.settings).code, 'not_started')

    def test_started_readiness(self):
        self.begin()
        r = self.audit.inspect(self.notice, self.control, self.settings)
        self.assertEqual(r.code, 'mock_ready')
        self.assertEqual(r.occurrence, '2026-10-14 19:30 KST')

    def test_display_once_only(self):
        self.begin()
        self.assertEqual(self.display().code, 'mock_displayed')
        self.assertEqual(self.shown, [self.notice.text])
        self.assertEqual(self.audit.simulated_count, 1)

    def test_duplicate_never_displays(self):
        self.begin()
        self.display()
        self.assertEqual(self.display().code, 'duplicate')
        self.assertEqual(len(self.shown), 1)

    def test_failure_no_consumption(self):
        self.begin()
        def fail(_text):
            raise RuntimeError('unavailable canvas')
        r = self.audit.simulate_display(self.notice, self.control, self.settings, show_local=fail)
        self.assertEqual(r.code, 'display_failed')
        self.assertEqual(self.audit.simulated_count, 0)
        self.assertEqual(self.display().code, 'mock_displayed')

    def test_no_callback_refused(self):
        self.begin()
        with self.assertRaises(ValueError):
            self.audit.simulate_display(self.notice, self.control, self.settings, show_local=None)
        self.assertEqual(self.audit.simulated_count, 0)

    def test_finished_session_blocked(self):
        self.begin()
        self.control.simulate_finish()
        self.assertEqual(self.audit.inspect(self.notice, self.control, self.settings).code, 'not_started')

    def test_wrong_time_blocked(self):
        self.begin()
        other = make_prebroadcast_notice(self.settings, parse_reference('2026-10-15 19:30'))
        self.assertEqual(self.audit.inspect(other, self.control, self.settings).code, 'not_started')

    def test_other_active_occurrence_blocked(self):
        self.begin()
        other = make_prebroadcast_notice(self.settings, parse_reference('2026-10-16 21:00'))
        self.assertEqual(self.audit.inspect(other, self.control, self.settings).code, 'not_started')

    def test_bad_controller_rejected(self):
        with self.assertRaises(ValueError):
            self.audit.inspect(self.notice, None, self.settings)

    def test_bad_notice_rejected(self):
        for bad in (None, '', {}, 5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.audit.inspect(bad, self.control, self.settings)

    def test_unsafe_message_rejected(self):
        self.begin()
        with self.assertRaises(ValueError):
            self.audit.inspect(replace(self.notice, text='@everyone'), self.control, self.settings)

    def test_published_or_scheduled_rejected(self):
        self.begin()
        for kw in ('published', 'scheduled', 'ai_generated'):
            with self.subTest(field=kw), self.assertRaises(ValueError):
                self.audit.inspect(replace(self.notice, **{kw: True}), self.control, self.settings)

    def test_unsafe_flag_blocks(self):
        self.begin()
        for name in ('streaming_enabled', 'scheduled_execution', 'external_publish_enabled'):
            with self.subTest(flag=name):
                unsafe = dict(self.settings, **{name: True})
                self.assertEqual(self.audit.inspect(self.notice, self.control, unsafe).code, 'blocked')

    def test_missing_policy_blocks(self):
        self.begin()
        self.assertEqual(self.audit.inspect(self.notice, self.control, {}).code, 'blocked')

    def test_forged_wrong_time_rejected(self):
        self.begin()
        for time in ('xyz KST', '2026-10-14 19:30 UTC', '2026-10-14 19:30 KST KST'):
            with self.subTest(time=time), self.assertRaises(ValueError):
                self.audit.inspect(replace(self.notice, announcement_time=time), self.control, self.settings)

    def test_not_real_published(self):
        self.begin()
        result = self.display()
        self.assertFalse(result.published)
        self.assertFalse(result.scheduled)
        self.assertFalse(result.transport_used)
        self.assertIn('실제 게시/예약/전송 없음', result.describe())

    def test_immutable_result(self):
        self.begin()
        with self.assertRaises(FrozenInstanceError):
            self.display().published = True

    def test_no_io_or_network(self):
        self.begin()
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('program')), \
             patch('builtins.open', side_effect=AssertionError('file')):
            self.assertEqual(self.display().code, 'mock_displayed')

    def test_separate_sessions_are_only_in_memory(self):
        self.begin()
        self.display()
        second = OfflineNoticePostingRehearsal()
        self.assertEqual(second.simulated_count, 0)
        self.assertEqual(second.inspect(self.notice, self.control, self.settings).code, 'mock_ready')

    def test_no_publishing_api(self):
        import ai_broadcaster.offline_notice_posting_rehearsal as module
        for name in ('send', 'publish', 'post_to_discord', 'connect', 'login', 'schedule', 'webhook'):
            self.assertFalse(hasattr(module, name))


if __name__ == '__main__':
    unittest.main()
