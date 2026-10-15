"""Stage 076: simulated private-stream procedure; NO real private stream."""
import sqlite3
import subprocess
import unittest
from dataclasses import FrozenInstanceError, replace
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_output_audit import audit_broadcast_output
from ai_broadcaster.offline_broadcast_output_settings import prepare_offline_output_settings
from ai_broadcaster.offline_broadcast_voice_link import OfflineBroadcastVoiceLink
from ai_broadcaster.offline_private_broadcast_rehearsal import (
    PHASES, PrivateRehearsalResult, rehearse_private_broadcast,
)
from test_offline_broadcast_output_audit import scene


def prepared(**kwargs):
    scene_draft, canvas = scene(**kwargs)
    volume = 85
    audit = audit_broadcast_output(canvas, scene_draft, scene_draft, volume)
    contract = prepare_offline_output_settings(canvas, scene_draft, scene_draft, volume, audit)
    return scene_draft, canvas, volume, audit, contract


def run(*, args=None, fault=None, link=None):
    d, c, v, audit, contract = args if args is not None else prepared()
    return rehearse_private_broadcast(c, d, d, v, audit, contract, link,
                                      inject_failure_at=fault)


class PrivateBroadcastRehearsalTests(unittest.TestCase):
    def test_all_local_phases_and_no_actual_broadcast(self):
        report = run()
        self.assertTrue(report.passed)
        self.assertEqual(tuple(name for name, _ in report.phases), PHASES)
        self.assertFalse(report.private_visibility_verified)
        self.assertFalse(report.streaming_performed)
        self.assertEqual(report.user_approval, 'pending')
        self.assertIn('확인 0건', report.describe())
        self.assertIn('미검증', report.describe())

    def test_all_fault_phases_fail_closed_with_no_later_steps(self):
        for index, phase in enumerate(PHASES):
            with self.subTest(phase=phase):
                report = run(fault=phase)
                self.assertFalse(report.passed)
                self.assertEqual(len(report.phases), index+1)
                self.assertEqual(report.phases[-1][0], phase)
                self.assertIn('중단', report.phases[-1][1])
                self.assertFalse(report.streaming_performed)

    def test_unknown_fault_rejected(self):
        with self.assertRaises(ValueError):
            run(fault='실제 송출')

    def test_requires_prior_draft(self):
        d, c, v, audit, _ = prepared()
        for bad in (None, object(), True, 'ready'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                rehearse_private_broadcast(c, d, d, v, audit, bad)

    def test_requires_prior_audit(self):
        d, c, v, _, contract = prepared()
        with self.assertRaises(ValueError):
            rehearse_private_broadcast(c, d, d, v, None, contract)

    def test_stale_content_fails(self):
        d, c, v, audit, contract = prepared()
        other, _ = scene(content='both')
        with self.assertRaises(ValueError):
            rehearse_private_broadcast(c, d, other, v, audit, contract)

    def test_stale_volume_fails(self):
        d, c, v, audit, contract = prepared()
        with self.assertRaises(ValueError):
            rehearse_private_broadcast(c, d, d, v+1, audit, contract)

    def test_changed_canvas_tag_fails(self):
        d, c, v, audit, contract = prepared()
        c.active_tags.remove('aisting_scene_watermark')
        with self.assertRaises(ValueError):
            rehearse_private_broadcast(c, d, d, v, audit, contract)

    def test_tampered_contract_fails(self):
        d, c, v, audit, contract = prepared()
        changed = replace(contract, nominal_volume=0)
        with self.assertRaises(ValueError):
            rehearse_private_broadcast(c, d, d, v, audit, changed)

    def test_2d_3d_and_undecided_unchanged(self):
        for avatar in ('2d', '3d', 'undecided'):
            with self.subTest(avatar=avatar):
                args = prepared(avatar=avatar, **({'layout': None} if avatar != '2d' else {}))
                self.assertTrue(run(args=args).passed)
                self.assertEqual(args[0].avatar, avatar)
                if avatar != '2d':
                    self.assertIn('렌더링되지', run(args=args).describe())

    def test_no_platform_does_not_autoselect(self):
        args = prepared(platforms=())
        report = run(args=args)
        self.assertTrue(report.passed)
        self.assertIn('플랫폼 미선택', report.describe())
        self.assertEqual(args[4].scene.platforms, ())

    def test_multi_platform_order_preserved(self):
        args = prepared(platforms=('youtube', 'twitch'))
        self.assertTrue(run(args=args).passed)
        self.assertEqual(args[4].scene.platforms, ('youtube', 'twitch'))

    def test_zero_volume_warning_and_not_measurement(self):
        d, c, _, _, _ = prepared()
        audit = audit_broadcast_output(c, d, d, 0)
        contract = prepare_offline_output_settings(c, d, d, 0, audit)
        report = run(args=(d, c, 0, audit, contract))
        self.assertTrue(report.passed)
        self.assertIn('음소거', report.describe())
        self.assertIn('음질·화질', report.describe())

    def test_voice_overlay_reused_without_sound(self):
        d, c, v, _, _ = prepared()
        link = OfflineBroadcastVoiceLink(d, '안녕하세요!')
        link.step(c, d)
        audit = audit_broadcast_output(c, d, d, v, link)
        contract = prepare_offline_output_settings(c, d, d, v, audit, link)
        report = run(args=(d, c, v, audit, contract), link=link)
        self.assertTrue(report.passed)
        self.assertFalse(report.streaming_performed)
        self.assertEqual(link.cursor, 1)

    def test_voice_state_changed_after_preflight_fails(self):
        d, c, v, audit, contract = prepared()
        link = OfflineBroadcastVoiceLink(d, '안녕하세요!')
        link.step(c, d)
        with self.assertRaises(ValueError):
            run(args=(d, c, v, audit, contract), link=link)

    def test_report_is_immutable(self):
        report = run()
        self.assertIsInstance(report, PrivateRehearsalResult)
        with self.assertRaises(FrozenInstanceError):
            report.passed = False

    def test_does_not_touch_canvas_or_settings(self):
        d, c, v, audit, contract = prepared()
        before = (tuple(c.calls), d, contract, audit)
        report = run(args=(d, c, v, audit, contract))
        self.assertTrue(report.passed)
        self.assertEqual(before, (tuple(c.calls), d, contract, audit))

    def test_no_network_os_storage_or_file_calls(self):
        args = prepared()
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.run', side_effect=AssertionError('subprocess')), \
             patch('subprocess.Popen', side_effect=AssertionError('subprocess')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')), \
             patch('builtins.open', side_effect=AssertionError('disk')):
            self.assertTrue(run(args=args).passed)


if __name__ == '__main__':
    unittest.main()
