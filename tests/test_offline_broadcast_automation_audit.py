"""Original 090: no real automation, integration boundary and fault injection."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.offline_broadcast_schedule import BroadcastScheduleDraft, parse_reference
from ai_broadcaster.offline_broadcast_scene import BroadcastSceneDraft
from ai_broadcaster.offline_chat_voice_screen_integration import ChatVoiceScreenIntegrationResult
from ai_broadcaster.offline_broadcast_automation_audit import (
    run_offline_broadcast_automation_audit as run,
)


class _IsolatedCanvas:
    def create_text(self, *args, **kwargs):
        return 1


def _chat_ok(*_args):
    return ChatVoiceScreenIntegrationResult(True, 3, 3, 3, 3, (1, 2, 3), ())


class AutomationIntegrationTests(TestCase):
    def setUp(self):
        self.settings = deepcopy(DEFAULTS)
        self.settings.update(platforms=['youtube'], content='chat', voice='windows_system')
        self.when = parse_reference('2026-10-14 19:30')
        self.schedule = BroadcastScheduleDraft().add(2, '19:30')
        self.scene = self.build_scene()
        self.canvas = _IsolatedCanvas()

    def build_scene(self):
        return BroadcastSceneDraft(tuple(self.settings['platforms']), self.settings['content'],
                                   self.settings['avatar'], self.settings['voice'], '아이스팅')

    def audit(self, **kwargs):
        inputs = dict(schedule=self.schedule, when=self.when, settings=self.settings,
                      scene=self.scene, volume=85, canvas=self.canvas,
                      chat_integration=_chat_ok)
        inputs.update(kwargs)
        return run(**inputs)

    def test_complete_virtual_cycle(self):
        report = self.audit()
        self.assertTrue(report.passed, report.describe())
        self.assertEqual(len(report.checks), 15)
        self.assertTrue(all(c.ok for c in report.checks))
        self.assertFalse(report.actual_broadcast_verified)
        self.assertFalse(report.actual_publication_verified)
        self.assertEqual(report.approval, 'pending')

    def test_repeated_checks_are_independent(self):
        self.assertEqual(self.audit().checks, self.audit().checks)

    def test_settings_not_mutated(self):
        prior = deepcopy(self.settings)
        self.audit()
        self.assertEqual(self.settings, prior)

    def test_schedule_not_mutated(self):
        prior = self.schedule
        self.audit()
        self.assertEqual(self.schedule, prior)

    def test_no_implicit_io_or_process_or_network(self):
        with TemporaryDirectory() as temp, patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('builtins.open', side_effect=AssertionError('file IO')):
            self.assertTrue(self.audit().passed)
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_missing_weekly_slot(self):
        report = self.audit(schedule=BroadcastScheduleDraft())
        self.assertFalse(report.passed)
        self.assertEqual(len(report.checks), 1)

    def test_wrong_start_time(self):
        self.assertFalse(self.audit(when=parse_reference('2026-10-14 19:31')).passed)

    def test_wrong_settings_flag(self):
        for flag in ('scheduled_execution', 'external_publish_enabled', 'streaming_enabled'):
            with self.subTest(flag=flag):
                alter = deepcopy(self.settings)
                alter[flag] = True
                self.assertFalse(self.audit(settings=alter).passed)

    def test_setting_scene_changed(self):
        updated = deepcopy(self.settings)
        updated['content'] = 'game'
        result = self.audit(settings=updated)
        self.assertFalse(result.passed)
        self.assertEqual(len(result.checks), 1)

    def test_wrong_platform_rejected(self):
        self.settings['platforms'] = []
        self.scene = self.build_scene()
        self.assertFalse(self.audit().passed)

    def test_unselected_voice_rejected_without_substitution(self):
        self.settings['voice'] = 'undecided'
        self.scene = self.build_scene()
        self.assertFalse(self.audit().passed)

    def test_3d_is_not_silently_downshifted(self):
        self.settings['avatar'] = '3d'
        self.scene = self.build_scene()
        self.assertTrue(self.audit().passed)
        self.assertEqual(self.scene.avatar, '3d')

    def test_wrong_volume(self):
        for value in (-1, 101, True, '85'):
            with self.subTest(value=value):
                self.assertFalse(self.audit(volume=value).passed)

    def test_invalid_canvas(self):
        self.assertFalse(self.audit(canvas=object()).passed)

    def test_mock_display_failure_not_consumed(self):
        def break_it(_):
            raise RuntimeError('expected render failure')
        result = self.audit(display_notice=break_it)
        self.assertFalse(result.passed)
        self.assertIn('가상 공지 표시', result.checks[-1].name)
        self.assertEqual(len(result.checks), 5)

    def test_chat_integration_failure_detected(self):
        fake = lambda *_: replace(_chat_ok(), passed=False, issues=('disconnected',))
        result = self.audit(chat_integration=fake)
        self.assertFalse(result.passed)
        self.assertIn('채팅', result.checks[-1].name)

    def test_chat_count_forgery_detected(self):
        fake = lambda *_: replace(_chat_ok(), received=2)
        self.assertFalse(self.audit(chat_integration=fake).passed)

    def test_chat_real_streaming_claim_detected(self):
        fake = lambda *_: replace(_chat_ok(), actual_streaming=True)
        self.assertFalse(self.audit(chat_integration=fake).passed)

    def test_chat_failure_exception_is_fail_closed(self):
        def bad(*args):
            raise RuntimeError('broken display')
        result = self.audit(chat_integration=bad)
        self.assertFalse(result.passed)
        self.assertEqual(len(result.checks), 7)

    def test_closing_display_failure_detected(self):
        def broken(_):
            raise RuntimeError('closing display failed')
        result = self.audit(display_closing=broken)
        self.assertFalse(result.passed)
        self.assertIn('가상 종료', result.checks[-1].name)
        self.assertEqual(len(result.checks), 10)

    def test_injected_wrong_type(self):
        self.assertFalse(self.audit(schedule=None).passed)
        self.assertFalse(self.audit(scene=None).passed)
        self.assertFalse(self.audit(settings=None).passed)

    def test_disallowed_topic(self):
        self.assertFalse(self.audit(topic='@everyone').passed)

    def test_invalid_date(self):
        self.assertFalse(self.audit(when='not-date').passed)

    def test_report_has_no_success_when_last_check_is_missing(self):
        report = self.audit()
        self.assertFalse(replace(report, checks=report.checks[:-1]).passed)
