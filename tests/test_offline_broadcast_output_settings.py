"""Original stage 075: local-only, immutable broadcast output review bridge."""
import json
import sqlite3
import subprocess
import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import patch

from test_offline_broadcast_output_audit import scene
from ai_broadcaster.offline_broadcast_output_audit import audit_broadcast_output
from ai_broadcaster.offline_broadcast_output_settings import (
    OfflineOutputSettingsDraft, prepare_offline_output_settings,
)
from ai_broadcaster.offline_broadcast_voice_link import OfflineBroadcastVoiceLink


def prepared(**kwargs):
    draft, canvas = scene(**kwargs)
    audit = audit_broadcast_output(canvas, draft, draft, 85)
    return prepare_offline_output_settings(canvas, draft, draft, 85, audit)


class OutputSettingsBridgeTests(unittest.TestCase):
    def test_valid_scene_binds_without_activating_output(self):
        contract = prepared()
        data = contract.review_mapping()
        self.assertEqual(data['schema'], 'aisting.offline_output_settings.review.v1')
        self.assertEqual(data['source_canvas']['width'], 640)
        self.assertEqual(data['source_canvas']['height'], 360)
        self.assertEqual(data['selected_platforms'], ['chzzk'])
        self.assertEqual(data['nominal_voice']['volume_setting_0_100'], 85)
        self.assertEqual(data['approval'], 'pending_user_and_windows_real_device_verification')
        self.assertTrue(all(x is False for key, x in data['outputs'].items() if key != 'destination'))
        self.assertIsNone(data['outputs']['destination'])

    def test_multiple_platforms_preserved_without_endpoint(self):
        contract = prepared(platforms=('twitch', 'youtube', 'chzzk'))
        self.assertEqual(contract.scene.platforms, ('twitch', 'youtube', 'chzzk'))
        self.assertEqual(contract.review_mapping()['selected_platforms'], ['twitch', 'youtube', 'chzzk'])
        self.assertNotIn('url', contract.review_json().lower())
        self.assertNotIn('token', contract.review_json().lower())

    def test_no_platform_allowed_does_not_autoselect(self):
        contract = prepared(platforms=())
        self.assertEqual(contract.review_mapping()['selected_platforms'], [])
        self.assertIn('미선택', contract.describe())

    def test_3d_does_not_substitute_2d(self):
        for avatar in ('3d', 'undecided'):
            with self.subTest(avatar=avatar):
                data = prepared(avatar=avatar, layout=None).review_mapping()
                self.assertEqual(data['composition']['avatar'], avatar)

    def test_voice_source_unchanged_no_speaker_connected(self):
        data = prepared(voice='own_recording').review_mapping()
        self.assertEqual(data['nominal_voice']['selected_source'], 'own_recording')
        self.assertFalse(data['nominal_voice']['speaker_connected'])

    def test_volume_zero_and_hundred_preserved_and_no_physical_measurement(self):
        for volume in (0, 100):
            with self.subTest(volume=volume):
                draft, canvas = scene()
                report = audit_broadcast_output(canvas, draft, draft, volume)
                contract = prepare_offline_output_settings(canvas, draft, draft, volume, report)
                self.assertEqual(contract.nominal_volume, volume)
                self.assertIn('실측값 아님', contract.describe())

    def test_requires_existing_audit(self):
        draft, canvas = scene()
        for report in (None, True, 'ok', object()):
            with self.subTest(report=report), self.assertRaises(ValueError):
                prepare_offline_output_settings(canvas, draft, draft, 85, report)

    def test_rejects_stale_scene(self):
        draft, canvas = scene()
        audit = audit_broadcast_output(canvas, draft, draft, 85)
        stale, _ = scene(content='game')
        with self.assertRaises(ValueError):
            prepare_offline_output_settings(canvas, draft, stale, 85, audit)

    def test_rejects_volume_change_after_audit(self):
        draft, canvas = scene()
        audit = audit_broadcast_output(canvas, draft, draft, 85)
        with self.assertRaises(ValueError):
            prepare_offline_output_settings(canvas, draft, draft, 86, audit)

    def test_rejects_damaged_canvas_after_successful_audit(self):
        draft, canvas = scene()
        audit = audit_broadcast_output(canvas, draft, draft, 85)
        canvas.active_tags.remove('aisting_scene_watermark')
        with self.assertRaises(ValueError):
            prepare_offline_output_settings(canvas, draft, draft, 85, audit)

    def test_rejects_failed_prior_audit(self):
        draft, canvas = scene()
        canvas.active_tags.remove('aisting_sample_2d')
        report = audit_broadcast_output(canvas, draft, draft, 85)
        self.assertFalse(report.screen_ok)
        with self.assertRaises(ValueError):
            prepare_offline_output_settings(canvas, draft, draft, 85, report)

    def test_invalid_nominal_volume_rejected(self):
        draft, canvas = scene()
        audit = audit_broadcast_output(canvas, draft, draft, 85)
        for volume in (True, 85.0, '85', -1, 101):
            with self.subTest(volume=volume), self.assertRaises(ValueError):
                prepare_offline_output_settings(canvas, draft, draft, volume, audit)

    def test_voice_overlay_snapshot_after_manually_displayed_chunk(self):
        draft, canvas = scene()
        link = OfflineBroadcastVoiceLink(draft, '안녕하세요! 반갑습니다.')
        link.step(canvas, draft)
        report = audit_broadcast_output(canvas, draft, draft, 85, link)
        contract = prepare_offline_output_settings(canvas, draft, draft, 85, report, link)
        self.assertTrue(contract.review_mapping()['nominal_voice']['virtual_text_overlay_visible'])
        self.assertFalse(contract.review_mapping()['nominal_voice']['speaker_connected'])

    def test_reject_voice_route_changed_since_audit(self):
        draft, canvas = scene()
        report = audit_broadcast_output(canvas, draft, draft, 85)
        link = OfflineBroadcastVoiceLink(draft, '안녕하세요!')
        link.step(canvas, draft)
        with self.assertRaises(ValueError):
            prepare_offline_output_settings(canvas, draft, draft, 85, report, link)

    def test_snapshot_frozen(self):
        c = prepared()
        with self.assertRaises(FrozenInstanceError):
            c.nominal_volume = 5

    def test_review_data_copy_cannot_mutate_snapshot(self):
        c = prepared()
        data = c.review_mapping()
        data['selected_platforms'].append('twitch')
        data['outputs']['streaming_enabled'] = True
        self.assertEqual(c.review_mapping()['selected_platforms'], ['chzzk'])
        self.assertFalse(c.review_mapping()['outputs']['streaming_enabled'])
        self.assertEqual(json.loads(c.review_json()), c.review_mapping())

    def test_no_storage_process_network_or_readback(self):
        draft, canvas = scene()
        audit = audit_broadcast_output(canvas, draft, draft, 85)
        before = tuple(canvas.calls)
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.run', side_effect=AssertionError('OS')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')), \
             patch('builtins.open', side_effect=AssertionError('file IO')):
            c = prepare_offline_output_settings(canvas, draft, draft, 85, audit)
            json.loads(c.review_json())
        self.assertEqual(tuple(canvas.calls), before)

    def test_prior_audit_wrong_type_rejected_even_when_true(self):
        draft, canvas = scene()
        with self.assertRaises(ValueError):
            prepare_offline_output_settings(canvas, draft, draft, 85, {'screen_ok': True})


if __name__ == '__main__':
    unittest.main()
