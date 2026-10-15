"""Original roadmap 057: sample expression/animation structural review."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.avatar_motion_review import (
    AvatarMotionReview, MOTION_STEPS, inspect_motion_canvas,
)
from ai_broadcaster.avatar_renderer import AvatarFrame, EXPRESSIONS, draw_avatar, draw_unavailable_3d
from test_avatar_display_validation import FakeCanvas


class AvatarMotionReviewTests(unittest.TestCase):
    def make(self, **kw):
        options = dict(avatar='2d', name='나만의 캐릭터', expression='smile')
        options.update(kw)
        return AvatarMotionReview(**options)

    def test_session_is_inert_until_explicit_audit(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('sqlite3.connect', side_effect=AssertionError('db')):
            s = self.make()
            self.assertEqual(s.index, 0)
            self.assertEqual(s.count, 9)
            self.assertEqual(s.current[0], MOTION_STEPS[0][0])

    def test_step_navigation_does_not_wrap(self):
        s = self.make()
        s.previous(); self.assertEqual(s.index, 0)
        for _ in range(50): s.next()
        self.assertEqual(s.index, s.count-1)
        s.previous(); self.assertEqual(s.index, s.count-2)

    def test_seek_rejects_invalid_types_and_bounds(self):
        s = self.make()
        for bad in (-1, s.count, True, False, '1', 0.5, None):
            with self.subTest(value=bad), self.assertRaises(ValueError): s.seek(bad)

    def test_rejects_3d_or_unselected_without_2d_fallback(self):
        for avatar in ('3d', 'undecided', None, 'fake'):
            with self.subTest(avatar=avatar), self.assertRaises(ValueError):
                self.make(avatar=avatar)

    def test_rejects_invalid_expression(self):
        for expression in (None, '', 'happy', True):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                self.make(expression=expression)

    def test_rejects_empty_name(self):
        for name in (None, '', '  ', 14):
            with self.subTest(name=name), self.assertRaises(ValueError): self.make(name=name)

    def test_rejects_unknown_background(self):
        with self.assertRaises(ValueError): self.make(background='invalid')

    def test_all_expressions_keep_canvas_own_tags(self):
        for exp in EXPRESSIONS:
            with self.subTest(expression=exp):
                s = self.make(expression=exp)
                canvas = FakeCanvas()
                report = s.audit(canvas)
                self.assertTrue(report.passed, report.describe())
                self.assertEqual(len(report.checks), 9)
                self.assertTrue(canvas.find_withtag('aisting_expression_' + exp))

    def test_two_backgrounds(self):
        for bg in ('남색 스튜디오', '초록색 배경'):
            with self.subTest(bg=bg):
                s = self.make(background=bg)
                self.assertTrue(s.audit(FakeCanvas()).passed)

    def test_mouth_varies_on_speaking_and_stays_closed_idle(self):
        s = self.make()
        mouth = [s.seek(i)[1].mouth for i in range(s.count)]
        self.assertEqual(mouth[0], 0)
        self.assertTrue(all(mouth[i] > 0 for i in (1, 2, 3, 6)))
        self.assertTrue(all(mouth[i] == 0 for i in (4, 5, 7, 8)))

    def test_blink_onset_end(self):
        s = self.make()
        blink = [s.seek(i)[1].blink for i in range(s.count)]
        self.assertEqual(blink, [True, True, False, False, False, False, True, True, False])

    def test_audit_restores_selected_frame(self):
        s = self.make()
        s.seek(6)
        canvas = FakeCanvas()
        self.assertTrue(s.audit(canvas).passed)
        self.assertEqual(s.index, 6)
        self.assertEqual(inspect_motion_canvas(canvas, s.current[1]), ())

    def test_detects_wrong_mouth(self):
        canvas = FakeCanvas()
        pose = AvatarFrame('나만의 캐릭터', True, 1, expression='smile')
        draw_avatar(canvas, AvatarFrame(pose.name, False, pose.frame, expression=pose.expression))
        self.assertIn('입', ' '.join(inspect_motion_canvas(canvas, pose)))

    def test_detects_wrong_blink(self):
        canvas = FakeCanvas()
        pose = AvatarFrame('나만의 캐릭터', False, 45, expression='smile')
        draw_avatar(canvas, AvatarFrame(pose.name, False, 44, expression=pose.expression))
        self.assertIn('눈 깜빡임', ' '.join(inspect_motion_canvas(canvas, pose)))

    def test_detects_wrong_expression(self):
        canvas = FakeCanvas()
        pose = AvatarFrame('나만의 캐릭터', False, 4, expression='smile')
        draw_avatar(canvas, AvatarFrame(pose.name, False, pose.frame, expression='neutral'))
        self.assertIn('표정', ' '.join(inspect_motion_canvas(canvas, pose)))

    def test_detects_wrong_name(self):
        canvas = FakeCanvas()
        pose = AvatarFrame('나만의 캐릭터', False, 4, expression='smile')
        draw_avatar(canvas, AvatarFrame('다른 이름', False, 4, expression='smile'))
        self.assertIn('이름', ' '.join(inspect_motion_canvas(canvas, pose)))

    def test_detects_wrong_background(self):
        canvas = FakeCanvas()
        pose = AvatarFrame('나만의 캐릭터', False, 4, expression='smile', background='초록색 배경')
        draw_avatar(canvas, AvatarFrame(pose.name, False, 4, expression='smile'))
        self.assertIn('배경', ' '.join(inspect_motion_canvas(canvas, pose)))

    def test_detects_fake_3d(self):
        canvas = FakeCanvas()
        draw_unavailable_3d(canvas)
        self.assertIn('2D', ' '.join(inspect_motion_canvas(canvas, self.make().current[1])))

    def test_does_not_modify_files_or_device(self):
        with patch('builtins.open', side_effect=AssertionError('file access')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')):
            s = self.make()
            self.assertTrue(s.audit(FakeCanvas()).passed)
            self.assertIn('운영자 평가 대기', s.audit(FakeCanvas()).describe())


if __name__ == '__main__':
    unittest.main()
