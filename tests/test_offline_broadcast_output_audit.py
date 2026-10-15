"""Stage 074 offline nominal-volume and local placeholder-screen audit."""
import sqlite3
import subprocess
import unittest
from unittest.mock import patch

from test_offline_broadcast_scene import FakeCanvas, make
from ai_broadcaster.offline_broadcast_scene import draw_broadcast_scene
from ai_broadcaster.offline_broadcast_voice_link import OfflineBroadcastVoiceLink
from ai_broadcaster.offline_broadcast_output_audit import audit_broadcast_output


class TagCanvas(FakeCanvas):
    def __init__(self):
        super().__init__()
        self.active_tags = set()
        self.width = 640
        self.height = 360

    def __getattr__(self, method):
        f = super().__getattr__(method)
        def record(*args, **kwargs):
            if method == 'delete':
                if args and args[0] == 'all':
                    self.active_tags.clear()
                elif args:
                    self.active_tags.discard(args[0])
            else:
                self.active_tags.update(kwargs.get('tags', ()))
            return f(*args, **kwargs)
        return record

    def find_withtag(self, name):
        return (1,) if name in self.active_tags else ()

    def cget(self, prop):
        return str({'width': self.width, 'height': self.height}[prop])


def scene(**kwargs):
    draft = make(**kwargs)
    canvas = TagCanvas()
    draw_broadcast_scene(canvas, draft)
    return draft, canvas


class BroadcastOutputAuditTests(unittest.TestCase):
    def test_normal_2d_scene_and_nominal_volume(self):
        draft, canvas = scene()
        report = audit_broadcast_output(canvas, draft, draft, 85)
        self.assertTrue(report.screen_ok)
        self.assertEqual(report.volume_setting, 85)
        self.assertFalse(report.silent_by_setting)
        self.assertEqual(report.issues, ())
        self.assertIn('실제 소리 크기', report.description)
        self.assertIn('측정 음압·dB 아님', report.description)

    def test_volume_zero_warns_silent_not_actual_measurement(self):
        draft, canvas = scene()
        report = audit_broadcast_output(canvas, draft, draft, 0)
        self.assertTrue(report.screen_ok)
        self.assertTrue(report.silent_by_setting)
        self.assertIn('음소거', ' '.join(report.cautions))

    def test_volume_100_boundary_accepted(self):
        draft, canvas = scene()
        self.assertEqual(audit_broadcast_output(canvas, draft, draft, 100).volume_setting, 100)

    def test_invalid_volume_rejected_before_canvas_access(self):
        draft, canvas = scene()
        for value in (-1, 101, 85.0, '85', None, True, False):
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit_broadcast_output(canvas, draft, draft, value)

    def test_stale_or_absent_draft_rejected(self):
        draft, canvas = scene()
        for bad in (None, object(), make(content='game'), make(voice='undecided')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                audit_broadcast_output(canvas, draft, bad, 85)
        with self.assertRaises(ValueError):
            audit_broadcast_output(canvas, None, draft, 85)

    def test_required_canvas_elements_detected(self):
        for tag in ('aisting_scene_content', 'aisting_scene_watermark', 'aisting_sample_2d'):
            with self.subTest(tag=tag):
                draft, canvas = scene()
                canvas.active_tags.discard(tag)
                report = audit_broadcast_output(canvas, draft, draft, 85)
                self.assertFalse(report.screen_ok)
                self.assertTrue(report.issues)

    def test_title_selection_checked_both_ways(self):
        for show in (True, False):
            draft, canvas = scene(show_title=show)
            self.assertTrue(audit_broadcast_output(canvas, draft, draft, 85).screen_ok)
            if show:
                canvas.active_tags.discard('aisting_scene_title')
            else:
                canvas.active_tags.add('aisting_scene_title')
            self.assertFalse(audit_broadcast_output(canvas, draft, draft, 85).screen_ok)

    def test_3d_and_undecided_never_use_2d_fallback(self):
        for avatar in ('3d', 'undecided'):
            with self.subTest(avatar=avatar):
                draft, canvas = scene(avatar=avatar, layout=None)
                report = audit_broadcast_output(canvas, draft, draft, 85)
                self.assertTrue(report.screen_ok)
                self.assertIn('실제 렌더링되지', ' '.join(report.cautions))
                canvas.active_tags.add('aisting_sample_2d')
                self.assertFalse(audit_broadcast_output(canvas, draft, draft, 85).screen_ok)

    def test_unexpected_avatar_placeholder_in_2d_rejected(self):
        draft, canvas = scene()
        canvas.active_tags.add('aisting_scene_avatar_placeholder')
        self.assertFalse(audit_broadcast_output(canvas, draft, draft, 85).screen_ok)

    def test_stale_and_error_tags_rejected(self):
        for tag in ('aisting_scene_stale', 'aisting_scene_error'):
            draft, canvas = scene()
            canvas.active_tags.add(tag)
            self.assertFalse(audit_broadcast_output(canvas, draft, draft, 85).screen_ok)

    def test_wrong_canvas_size_rejected(self):
        draft, canvas = scene()
        canvas.width = 800
        self.assertFalse(audit_broadcast_output(canvas, draft, draft, 85).screen_ok)

    def test_incompatible_canvas_fails_closed(self):
        draft, canvas = scene()
        for broken in (object(), None):
            with self.assertRaises(ValueError):
                audit_broadcast_output(broken, draft, draft, 85)
        canvas.height = 'broken'
        with self.assertRaises(ValueError):
            audit_broadcast_output(canvas, draft, draft, 85)

    def test_virtual_voice_marker_matches_completed_manual_step(self):
        draft, canvas = scene()
        link = OfflineBroadcastVoiceLink(draft, '가상 테스트')
        self.assertTrue(audit_broadcast_output(canvas, draft, draft, 85, link).screen_ok)
        link.step(canvas, draft)
        self.assertTrue(audit_broadcast_output(canvas, draft, draft, 85, link).screen_ok)
        self.assertEqual(link.cursor, 1)
        canvas.active_tags.discard('aisting_scene_voice')
        self.assertFalse(audit_broadcast_output(canvas, draft, draft, 85, link).screen_ok)

    def test_stale_voice_overlay_without_active_route_fails(self):
        draft, canvas = scene()
        canvas.active_tags.add('aisting_scene_voice')
        self.assertFalse(audit_broadcast_output(canvas, draft, draft, 85).screen_ok)

    def test_wrong_voice_route_rejected_without_consuming(self):
        draft, canvas = scene()
        link = OfflineBroadcastVoiceLink(make(content='game'), '테스트')
        with self.assertRaises(ValueError):
            audit_broadcast_output(canvas, draft, draft, 85, link)
        self.assertEqual(link.cursor, 0)
        with self.assertRaises(ValueError):
            audit_broadcast_output(canvas, draft, draft, 85, object())

    def test_unconnected_voice_warns_not_auto_replaced(self):
        draft, canvas = scene(voice='licensed_recording')
        report = audit_broadcast_output(canvas, draft, draft, 85)
        self.assertTrue(report.screen_ok)
        self.assertIn('다른 음성으로 대체하지 않습니다', ' '.join(report.cautions))
        self.assertEqual(draft.voice, 'licensed_recording')

    def test_offline_read_only_and_no_system_access(self):
        draft, canvas = scene()
        before = tuple(canvas.calls)
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.run', side_effect=AssertionError('OS')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('sqlite3.connect', side_effect=AssertionError('db')), \
             patch('builtins.open', side_effect=AssertionError('disk')):
            report = audit_broadcast_output(canvas, draft, draft, 85)
        self.assertTrue(report.screen_ok)
        self.assertEqual(tuple(canvas.calls), before)


if __name__ == '__main__':
    unittest.main()
