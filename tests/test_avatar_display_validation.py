"""Original 053: canvas-level verification without real screen, OS or model access."""
import unittest
from unittest.mock import patch
from ai_broadcaster.avatar_renderer import AvatarFrame, draw_avatar, draw_unavailable_3d
from ai_broadcaster.avatar_display_validation import audit_avatar_display


class FakeCanvas:
    def __init__(self):
        self.bg = None
        self.items = {}
        self.next_id = 0

    def configure(self, **kw):
        self.bg = kw.get('bg', self.bg)

    def cget(self, option):
        assert option == 'bg'
        return self.bg

    def delete(self, option):
        assert option == 'all'
        self.items.clear()

    def _add(self, **kw):
        self.next_id += 1
        self.items[self.next_id] = kw
        return self.next_id

    def create_oval(self, *a, **kw): return self._add(**kw)
    def create_arc(self, *a, **kw): return self._add(**kw)
    def create_line(self, *a, **kw): return self._add(**kw)
    def create_text(self, *a, **kw): return self._add(**kw)

    def find_withtag(self, tag):
        return tuple(k for k, v in self.items.items() if tag in v.get('tags', ()))

    def itemcget(self, key, option):
        return self.items[key][option]


class AvatarDisplayValidationTests(unittest.TestCase):
    def test_2d_main_closed_window(self):
        canvas = FakeCanvas()
        draw_avatar(canvas, AvatarFrame('아이스팅', False, 2))
        result = audit_avatar_display(avatar='2d', name='아이스팅', speaking=False, frame=2, main_canvas=canvas)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.checks), 5)
        self.assertIn('실제 모델 아님', result.describe())

    def test_undecided_is_sample_not_model(self):
        canvas = FakeCanvas()
        draw_avatar(canvas, AvatarFrame('아이스팅', False, 2))
        result = audit_avatar_display(avatar='undecided', name='아이스팅', speaking=False, frame=2, main_canvas=canvas)
        self.assertTrue(result.passed)
        self.assertIn('미검증', result.describe())

    def test_two_canvases_both_display_custom_name(self):
        main, capture = FakeCanvas(), FakeCanvas()
        p = AvatarFrame('직접 만든 캐릭터', True, 1)
        draw_avatar(main, p)
        draw_avatar(capture, AvatarFrame(p.name, True, 1, '초록색 배경'))
        report = audit_avatar_display(avatar='2d', name=p.name, speaking=True, frame=1,
                                     main_canvas=main, capture_canvas=capture,
                                     capture_background='초록색 배경')
        self.assertTrue(report.passed)
        self.assertEqual(len(report.checks), 8)

    def test_name_mismatch_is_not_approved(self):
        canvas = FakeCanvas()
        draw_avatar(canvas, AvatarFrame('이전 이름', False, 2))
        report = audit_avatar_display(avatar='2d', name='새 이름', speaking=False,
                                      frame=2, main_canvas=canvas)
        self.assertFalse(report.passed)
        self.assertIn('실패', report.describe())

    def test_capture_name_mismatch_is_detected(self):
        main, capture = FakeCanvas(), FakeCanvas()
        draw_avatar(main, AvatarFrame('아이스팅', False, 2))
        draw_avatar(capture, AvatarFrame('잘못된 이름', False, 2))
        self.assertFalse(audit_avatar_display(avatar='2d', name='아이스팅',
                speaking=False, frame=2, main_canvas=main, capture_canvas=capture).passed)

    def test_mouth_mismatch_detected(self):
        canvas = FakeCanvas()
        draw_avatar(canvas, AvatarFrame('아이스팅', False, 1))
        self.assertFalse(audit_avatar_display(avatar='2d', name='아이스팅',
                speaking=True, frame=1, main_canvas=canvas).passed)

    def test_capture_background_mismatch(self):
        main, capture = FakeCanvas(), FakeCanvas()
        draw_avatar(main, AvatarFrame('아이스팅', False, 2))
        draw_avatar(capture, AvatarFrame('아이스팅', False, 2, '남색 스튜디오'))
        self.assertFalse(audit_avatar_display(avatar='2d', name='아이스팅',
                speaking=False, frame=2, main_canvas=main,
                capture_canvas=capture, capture_background='초록색 배경').passed)

    def test_3d_shows_unavailable_and_no_fake_2d(self):
        canvas = FakeCanvas()
        draw_unavailable_3d(canvas)
        result = audit_avatar_display(avatar='3d', name='누구나',
                                      speaking=False, frame=0, main_canvas=canvas)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.checks), 3)
        self.assertIn('렌더러', result.describe())

    def test_3d_capture_window_is_failure(self):
        main, capture = FakeCanvas(), FakeCanvas()
        draw_unavailable_3d(main)
        draw_avatar(capture, AvatarFrame('아이스팅', False, 2))
        self.assertFalse(audit_avatar_display(avatar='3d', name='아이스팅',
            speaking=False, frame=2, main_canvas=main, capture_canvas=capture).passed)

    def test_3d_fake_2d_is_failure(self):
        canvas = FakeCanvas()
        draw_avatar(canvas, AvatarFrame('아이스팅', False, 2))
        self.assertFalse(audit_avatar_display(avatar='3d', name='아이스팅',
            speaking=False, frame=2, main_canvas=canvas).passed)

    def test_2d_unrendered_is_failure(self):
        self.assertFalse(audit_avatar_display(avatar='2d', name='아이스팅',
            speaking=False, frame=2, main_canvas=FakeCanvas()).passed)

    def test_duplicate_character_name_tag_is_failure(self):
        canvas = FakeCanvas()
        draw_avatar(canvas, AvatarFrame('아이스팅', False, 2))
        canvas.create_text(1, 1, text='아이스팅', tags=('aisting_display_name',))
        self.assertFalse(audit_avatar_display(avatar='2d', name='아이스팅',
            speaking=False, frame=2, main_canvas=canvas).passed)

    def test_invalid_avatar_code_and_background(self):
        canvas = FakeCanvas()
        for value in ('vrm', '', None, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit_avatar_display(avatar=value, name='아이스팅', speaking=False, frame=2,
                                    main_canvas=canvas)
        with self.assertRaises(ValueError):
            audit_avatar_display(avatar='2d', name='아이스팅', speaking=False, frame=2,
                                 main_canvas=canvas, capture_background='file:///private')

    def test_blink_frame_does_not_break_display(self):
        for frame in (0, 1, 44, 45, 120):
            with self.subTest(frame=frame):
                canvas = FakeCanvas()
                draw_avatar(canvas, AvatarFrame('아이스팅', True, frame))
                self.assertTrue(audit_avatar_display(avatar='2d', name='아이스팅',
                    speaking=True, frame=frame, main_canvas=canvas).passed)

    def test_no_external_side_effects(self):
        canvas = FakeCanvas()
        draw_avatar(canvas, AvatarFrame('아이스팅', False, 2))
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            self.assertTrue(audit_avatar_display(avatar='2d', name='아이스팅',
                speaking=False, frame=2, main_canvas=canvas).passed)


if __name__ == '__main__':
    unittest.main()
