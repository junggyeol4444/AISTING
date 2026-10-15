"""Original step 089: end notice and virtual result record, no real broadcast."""
import json
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_closing import OfflineBroadcastClosing
from ai_broadcaster.offline_broadcast_duration import BroadcastDurationRules
from ai_broadcaster.offline_broadcast_schedule import parse_reference
from ai_broadcaster.offline_end_notice import create_offline_end_notice
from ai_broadcaster.offline_settings import DEFAULTS


class EndNoticeTests(TestCase):
    def setUp(self):
        self.settings = deepcopy(DEFAULTS)
        self.when = parse_reference('2026-10-14 19:30')
        self.decision = BroadcastDurationRules().evaluate(10800)
        self.closing = OfflineBroadcastClosing(self.decision, '아이스팅')
        self.closing.advance(lambda _line: None)
        self.closing.advance(lambda _line: None)

    def create(self, *, settings=None, when=None, decision=None, snapshot=None, note=''):
        return create_offline_end_notice(
            self.settings if settings is None else settings,
            self.when if when is None else when,
            self.decision if decision is None else decision,
            self.closing.snapshot() if snapshot is None else snapshot, note)

    def test_basic_notice_only(self):
        output = self.create()
        self.assertTrue(output.simulated_only)
        self.assertFalse(output.published)
        self.assertFalse(output.actual_broadcast_verified)
        self.assertIn('가상 종료', output.text)
        self.assertEqual(output.record['record_type'], 'virtual_ending_only')
        self.assertEqual(output.record['viewer_count'], None)
        self.assertIsNone(output.record['actual_end_time'])

    def test_requires_completed_closing(self):
        session = OfflineBroadcastClosing(self.decision, '아이스팅')
        with self.assertRaises(ValueError):
            self.create(snapshot=session.snapshot())
        session.advance(lambda _: None)
        with self.assertRaises(ValueError):
            self.create(snapshot=session.snapshot())

    def test_invalid_closing_snapshot_rejected(self):
        original = self.closing.snapshot()
        for broken in (replace(original, phase='farewell_pending'),
                       replace(original, virtual_stream_ended=False),
                       replace(original, next_line='pending'),
                       replace(original, delivered_lines=('only one',))):
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                self.create(snapshot=broken)

    def test_before_max_rejected(self):
        for seconds in (0, 3599, 3600, 10799):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                self.create(decision=BroadcastDurationRules().evaluate(seconds))

    def test_inconsistent_duration_rejected(self):
        with self.assertRaises(ValueError):
            self.create(decision=replace(self.decision, minimum_minutes=200))
        with self.assertRaises(ValueError):
            self.create(decision=replace(self.decision, elapsed_seconds=-5))

    def test_custom_rules(self):
        duration = BroadcastDurationRules(10, 20).evaluate(1200)
        output = self.create(decision=duration)
        self.assertEqual(output.record['minimum_minutes'], 10)
        self.assertEqual(output.record['maximum_minutes'], 20)

    def test_settings_and_platforms_reflected(self):
        self.settings['platforms'] = ['youtube', 'chzzk']
        self.settings['content'] = 'chat'
        record = self.create().record
        self.assertEqual(record['platforms_selected'], ['유튜브', '치지직'])
        self.assertIn('수다', record['content_selected'])

    def test_custom_persona_setting(self):
        self.settings['persona_mode'] = 'custom'
        self.settings['persona']['name'] = '가상 진행자'
        self.assertIn('가상 진행자', self.create().text)

    def test_note_sanitization(self):
        self.assertIn('완료', self.create(note='완료').record['operator_note'])
        for bad in ('\n', 'https://a', '@everyone', 'a' * 121):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.create(note=bad)

    def test_wrong_timezone_rejected(self):
        with self.assertRaises(ValueError):
            self.create(when=datetime(2026, 10, 14, 19, 30))
        with self.assertRaises(ValueError):
            self.create(when=datetime(2026, 10, 14, 19, 30, tzinfo=timezone.utc))

    def test_banned_settings_rejected(self):
        for name in ('streaming_enabled', 'scheduled_execution', 'external_publish_enabled'):
            altered = deepcopy(self.settings)
            altered[name] = True
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.create(settings=altered)

    def test_does_not_mutate_input(self):
        original = deepcopy(self.settings)
        self.create(note='a')
        self.assertEqual(self.settings, original)

    def test_not_saved_by_default(self):
        with TemporaryDirectory() as temp, patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            self.create()
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_explicit_export_json(self):
        with TemporaryDirectory() as temp:
            filename = Path(temp) / 'manual.json'
            result = self.create(note='수동 시험')
            result.export_json(filename)
            data = json.loads(filename.read_text(encoding='utf-8'))
            self.assertEqual(data, result.record)
            self.assertEqual(data['actual_stream_status'], 'not_checked')

    def test_never_overwrites_existing_file(self):
        with TemporaryDirectory() as temp:
            filename = Path(temp) / 'existing.json'
            filename.write_text('DO NOT REPLACE', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                self.create().export_json(filename)
            self.assertEqual(filename.read_text(encoding='utf-8'), 'DO NOT REPLACE')

    def test_export_invalid_path_type(self):
        with self.assertRaises(ValueError):
            self.create().export_json('/tmp/fake-file')

    def test_no_autopost_api(self):
        import ai_broadcaster.offline_end_notice as module
        for name in ('publish', 'send', 'post_discord', 'post_cafe', 'auto_schedule'):
            self.assertFalse(hasattr(module, name))

    def test_deterministic_no_clock_access(self):
        self.assertEqual(self.create(), self.create())

    def test_requires_exact_snapshot(self):
        with self.assertRaises(ValueError):
            self.create(snapshot=None if False else 'ended')
