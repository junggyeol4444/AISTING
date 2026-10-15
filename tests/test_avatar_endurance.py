"""Stage 059: accelerated virtual-time stability checks; no real 24h claim."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.avatar_endurance import (
    run_virtual_endurance, audit_canvas_repetition, ALLOWED_HOURS,
    CHECKPOINT_LIMIT, MAX_CANVAS_ITEMS,
)
from ai_broadcaster.avatar_layout import AvatarLayout


def run(hours=1, **overrides):
    args = dict(avatar='2d', name='아이스팅', expression='smile', hours=hours)
    args.update(overrides)
    return run_virtual_endurance(**args)


class VirtualEnduranceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.one = run(1)
        cls.six = run(6)
        cls.day = run(24)

    def test_allowed_hours(self):
        self.assertEqual(ALLOWED_HOURS, (1, 6, 24))

    def test_frame_count_1h(self):
        self.assertEqual(self.one.inspected_frames, 3600)

    def test_frame_count_6h(self):
        self.assertEqual(self.six.inspected_frames, 21600)

    def test_frame_count_24h(self):
        self.assertEqual(self.day.inspected_frames, 86400)

    def test_virtual_seconds_exact(self):
        for report in (self.one, self.six, self.day):
            self.assertEqual(report.virtual_seconds, report.hours * 3600)

    def test_speaking_count(self):
        self.assertEqual(self.day.speaking_frames, 34560)

    def test_idle_count(self):
        self.assertEqual(self.day.idle_frames, 51840)

    def test_mouth_count(self):
        self.assertEqual(self.day.mouth_open_frames, self.day.speaking_frames)

    def test_blink_count(self):
        self.assertEqual(self.day.blink_frames, 3840)

    def test_bounded_checkpoints(self):
        for report in (self.one, self.six, self.day):
            self.assertEqual(len(report.checkpoints), CHECKPOINT_LIMIT)

    def test_first_and_last_checkpoints(self):
        for report in (self.one, self.six, self.day):
            self.assertEqual(report.checkpoints[0][0], 0)
            self.assertEqual(report.checkpoints[-1][0], report.virtual_seconds - 1)

    def test_checkpoint_order(self):
        times = [time for time, _ in self.day.checkpoints]
        self.assertEqual(times, sorted(set(times)))

    def test_checkpoint_expression(self):
        self.assertTrue(all(p.expression == 'smile' for _, p in self.day.checkpoints))

    def test_checkpoint_name(self):
        self.assertTrue(all(p.display_name == '아이스팅' for _, p in self.day.checkpoints))

    def test_hash_reproducible(self):
        self.assertEqual(self.one.fingerprint, run(1).fingerprint)

    def test_hash_changes_with_profile(self):
        self.assertNotEqual(self.one.fingerprint, run(1, expression='neutral').fingerprint)
        self.assertNotEqual(self.one.fingerprint, run(1, name='다른 캐릭터').fingerprint)

    def test_hash_changes_with_duration(self):
        self.assertNotEqual(self.one.fingerprint, self.six.fingerprint)

    def test_result_reports_virtual_not_real(self):
        self.assertIn('실제 장시간 실행', self.day.summary())
        self.assertIn('검증하지', self.day.summary())

    def test_no_external_io(self):
        with patch('builtins.open', side_effect=AssertionError('file')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            self.assertEqual(run(1).inspected_frames, 3600)

    def test_3d_no_fallback(self):
        for avatar in ('3d', 'undecided', '2D', '', True, None):
            with self.subTest(avatar=avatar), self.assertRaises(ValueError):
                run(avatar=avatar)

    def test_hours_reject_invalid(self):
        for hours in (-1, 0, 2, 25, True, '24', None, 24.0):
            with self.subTest(hours=hours), self.assertRaises(ValueError):
                run(hours)

    def test_invalid_names(self):
        for name in ('', ' ', None, True, 1):
            with self.subTest(name=name), self.assertRaises(ValueError):
                run(name=name)

    def test_invalid_expressions(self):
        for expression in ('angry', '', None, True, '미소'):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                run(expression=expression)

    def test_invalid_backgrounds(self):
        for background in ('blue', '', None, True):
            with self.subTest(background=background), self.assertRaises(ValueError):
                run(background=background)

    def test_other_expressions_and_background(self):
        for expression in ('neutral', 'surprised', 'concerned'):
            with self.subTest(expression=expression):
                report = run(expression=expression, background='초록색 배경')
                self.assertEqual(report.checkpoints[0][1].expression, expression)
                self.assertEqual(report.checkpoints[0][1].background, '초록색 배경')

    def test_bounded_stored_trace_independent_of_duration(self):
        self.assertEqual(len(self.one.checkpoints), len(self.day.checkpoints))

    def test_fingerprint_format(self):
        self.assertEqual(len(self.day.fingerprint), 64)
        int(self.day.fingerprint, 16)

    def test_result_is_immutable(self):
        from dataclasses import FrozenInstanceError
        with self.assertRaises(FrozenInstanceError):
            self.day.hours = 99


class CanvasAuditTests(unittest.TestCase):
    def test_invalid_cycles(self):
        for value in (0, -1, 241, True, '240'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit_canvas_repetition(None, AvatarLayout(), run(1), cycles=value)

    def test_mismatched_background(self):
        with self.assertRaises(ValueError):
            audit_canvas_repetition(None, AvatarLayout(background='초록색 배경'), run(1))

    def test_invalid_layout(self):
        with self.assertRaises(ValueError):
            audit_canvas_repetition(None, None, run(1))

    def test_invalid_result(self):
        with self.assertRaises(ValueError):
            audit_canvas_repetition(None, AvatarLayout(), None)

    def test_canvas_growth_detection_and_restore(self):
        class FakeCanvas:
            def __init__(self): self.count = 0; self.draws = 0
            def find_all(self): return tuple(range(self.count))
        canvas = FakeCanvas()
        def fake_draw(c, layout, pose):
            c.draws += 1
            c.count = 41 if c.draws == 3 else 10
        with patch('ai_broadcaster.avatar_endurance.draw_layout_preview', fake_draw):
            with self.assertRaisesRegex(RuntimeError, '객체 수 비정상'):
                audit_canvas_repetition(canvas, AvatarLayout(), run(1), cycles=10)
        self.assertEqual(canvas.draws, 4)  # three checks and finally restore
        self.assertEqual(canvas.count, 10)

    def test_canvas_bounded_count(self):
        class FakeCanvas:
            def find_all(self): return tuple(range(17))
        with patch('ai_broadcaster.avatar_endurance.draw_layout_preview') as draw:
            self.assertEqual(audit_canvas_repetition(FakeCanvas(), AvatarLayout(), run(1), cycles=240), (17, 17))
            self.assertEqual(draw.call_count, 241)

    def test_max_canvas_items_limit(self):
        self.assertLessEqual(MAX_CANVAS_ITEMS, 40)


if __name__ == '__main__':
    unittest.main()
