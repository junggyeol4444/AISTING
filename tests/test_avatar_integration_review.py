"""Stage 060 cross-module avatar checks, with no real voice or network."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.avatar_integration_review import (
    audit_avatar_integration, AvatarIntegrationReport, SAMPLE_SCRIPT, TEST_VOICE_NAME,
)
from ai_broadcaster.avatar_layout import AvatarLayout
from ai_broadcaster.avatar_renderer import AvatarFrame


class NoCanvas:
    def __getattr__(self, name):
        raise AssertionError('canvas should not be touched: ' + name)


class CanvasStub:
    def __init__(self):
        self.drawn = None
        self.draws = 0
    def find_all(self):
        return tuple(range(12))


def fake_draw(canvas, layout, pose):
    canvas.drawn = pose
    canvas.draws += 1


class IntegrationTests(unittest.TestCase):
    def audit(self, **kw):
        opts = dict(avatar='2d', name='아이스팅', expression='smile',
                    layout=AvatarLayout(), voice_source='windows_system', rate=0, volume=85)
        opts.update(kw)
        canvas = CanvasStub()
        with patch('ai_broadcaster.avatar_integration_review.draw_layout_preview', fake_draw), \
             patch('ai_broadcaster.avatar_integration_review.inspect_motion_canvas', return_value=()), \
             patch('ai_broadcaster.avatar_endurance.draw_layout_preview', fake_draw):
            return audit_avatar_integration(canvas, **opts), canvas

    def test_2d_integration_passes(self):
        report, canvas = self.audit()
        self.assertTrue(report.passed)
        self.assertIsInstance(report, AvatarIntegrationReport)
        self.assertFalse(report.failures)
        self.assertEqual(report.virtual_segments, 2)
        self.assertEqual(report.virtual_frames, 3600)
        self.assertEqual(report.canvas_cycles, 60)
        self.assertEqual(canvas.drawn, AvatarFrame('아이스팅', False, 4, expression='smile'))

    def test_check_categories(self):
        report, _ = self.audit()
        self.assertEqual(len(report.checks), 28)
        for term in ('neutral', 'smile', 'surprised', 'concerned', '중단', '재개', '정렬', '반복'):
            self.assertIn(term, report.describe())

    def test_no_actual_certification(self):
        report, _ = self.audit()
        for term in ('미검증', 'OBS', 'Windows', '운영자 승인'):
            self.assertIn(term, report.describe())

    def test_selected_background_and_layout(self):
        layout = AvatarLayout(horizontal=5, vertical=15, size=95, background='초록색 배경')
        report, canvas = self.audit(layout=layout, expression='concerned')
        self.assertTrue(report.passed)
        self.assertEqual(canvas.drawn.background, '초록색 배경')
        self.assertEqual(canvas.drawn.expression, 'concerned')

    def test_character_name_preserved(self):
        report, canvas = self.audit(name='직접 만든 캐릭터')
        self.assertTrue(report.passed)
        self.assertEqual(canvas.drawn.display_name, '직접 만든 캐릭터')

    def test_refuses_3d_without_canvas_mutation(self):
        with self.assertRaisesRegex(ValueError, '3D'):
            audit_avatar_integration(NoCanvas(), avatar='3d', name='A', expression='smile',
                                     layout=AvatarLayout(), voice_source='windows_system')

    def test_refuses_undecided(self):
        with self.assertRaises(ValueError):
            audit_avatar_integration(NoCanvas(), avatar='undecided', name='A', expression='smile',
                                     layout=AvatarLayout(), voice_source='windows_system')

    def test_refuses_unsupported_voice_source(self):
        for source in ('undecided', 'own_recording', 'licensed_recording', 'cloud', ''):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, 'Windows'):
                audit_avatar_integration(NoCanvas(), avatar='2d', name='A', expression='smile',
                                         layout=AvatarLayout(), voice_source=source)

    def test_refuses_invalid_voice_rate(self):
        with self.assertRaises(ValueError):
            self.audit(rate=5)

    def test_refuses_invalid_voice_volume(self):
        with self.assertRaises(ValueError):
            self.audit(volume=101)

    def test_refuses_blank_name(self):
        with self.assertRaises(ValueError):
            self.audit(name='  ')

    def test_refuses_unknown_expression(self):
        with self.assertRaises(ValueError):
            self.audit(expression='invented')

    def test_refuses_nonlayout(self):
        with self.assertRaises(ValueError):
            self.audit(layout=None)

    def test_refuses_bool_volume(self):
        with self.assertRaises(ValueError):
            self.audit(volume=True)

    def test_no_files_network_or_subprocess(self):
        with patch('builtins.open', side_effect=AssertionError('file')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            report, _ = self.audit()
        self.assertTrue(report.passed)

    def test_canvas_failure_is_not_reported_as_pass(self):
        canvas = CanvasStub()
        with patch('ai_broadcaster.avatar_integration_review.draw_layout_preview', fake_draw), \
             patch('ai_broadcaster.avatar_integration_review.inspect_motion_canvas',
                   side_effect=lambda _c, pose: ('tag missing',) if pose.expression == 'smile' else ()), \
             patch('ai_broadcaster.avatar_endurance.draw_layout_preview', fake_draw):
            report = audit_avatar_integration(canvas, avatar='2d', name='A', expression='smile',
                                              layout=AvatarLayout(), voice_source='windows_system')
        self.assertFalse(report.passed)
        self.assertIn('tag missing', report.describe())
        self.assertEqual(canvas.drawn, AvatarFrame('A', False, 4, expression='smile'))

    def test_failure_restores_initial_pose(self):
        canvas = CanvasStub()
        with patch('ai_broadcaster.avatar_integration_review.draw_layout_preview', fake_draw), \
             patch('ai_broadcaster.avatar_integration_review.inspect_motion_canvas', return_value=()), \
             patch('ai_broadcaster.avatar_integration_review.run_virtual_endurance',
                   side_effect=RuntimeError('forced error')):
            with self.assertRaisesRegex(RuntimeError, 'forced error'):
                audit_avatar_integration(canvas, avatar='2d', name='A', expression='neutral',
                                         layout=AvatarLayout(), voice_source='windows_system')
        self.assertEqual(canvas.drawn, AvatarFrame('A', False, 4))

    def test_source_script_fixed_and_local(self):
        self.assertIn('시청자A:', SAMPLE_SCRIPT)
        self.assertIn('시청자B:', SAMPLE_SCRIPT)
        self.assertIn('무음', TEST_VOICE_NAME)


if __name__ == '__main__':
    unittest.main()
