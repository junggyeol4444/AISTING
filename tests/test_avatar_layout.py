"""Original roadmap 058: offline sample placement and strict manual persistence."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from ai_broadcaster.avatar_layout import (
    AvatarLayout, draw_layout_preview, layout_path, save_layout, load_layout,
    delete_layout, validate_layout_record, _record, PREVIEW_WIDTH, PREVIEW_HEIGHT,
    SOURCE_WIDTH, SOURCE_HEIGHT,
)
from ai_broadcaster.avatar_renderer import AvatarFrame


class PositionTests(unittest.TestCase):
    def test_no_outside_access_on_creation(self):
        with patch('builtins.open', side_effect=AssertionError('file opened')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            d = AvatarLayout()
            self.assertEqual(d.horizontal, 75)

    def test_supported_backgrounds(self):
        for bg in ('남색 스튜디오', '초록색 배경'):
            self.assertEqual(AvatarLayout(background=bg).background, bg)

    def test_strict_avatar(self):
        for invalid in ('3d', 'undecided', '', True, None, '2D'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                AvatarLayout(avatar=invalid)

    def test_strict_x(self):
        for invalid in (-1, 101, True, 50.2, '50', None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                AvatarLayout(horizontal=invalid)

    def test_strict_y(self):
        for invalid in (-1, 101, False, 0.4, '0', None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                AvatarLayout(vertical=invalid)

    def test_strict_size(self):
        for invalid in (0, 39, 101, True, 70.0, '70', None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                AvatarLayout(size=invalid)

    def test_strict_background(self):
        for invalid in ('blue', '', None, True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                AvatarLayout(background=invalid)

    def test_layout_geometry_stays_inside(self):
        for x in (0, 50, 100):
            for y in (0, 50, 100):
                for size in (40, 70, 100):
                    scale, dx, dy = AvatarLayout(horizontal=x, vertical=y, size=size).geometry()
                    self.assertGreater(scale, 0)
                    self.assertGreaterEqual(dx, 0)
                    self.assertGreaterEqual(dy, 0)
                    self.assertLessEqual(dx + SOURCE_WIDTH*scale, PREVIEW_WIDTH+1e-8)
                    self.assertLessEqual(dy + SOURCE_HEIGHT*scale, PREVIEW_HEIGHT+1e-8)

    def test_position_extremes(self):
        scale, dx, dy = AvatarLayout(horizontal=0, vertical=0).geometry()
        self.assertEqual((dx, dy), (0, 0))
        scale, dx, dy = AvatarLayout(horizontal=100, vertical=100).geometry()
        self.assertAlmostEqual(dx+SOURCE_WIDTH*scale, PREVIEW_WIDTH)
        self.assertAlmostEqual(dy+SOURCE_HEIGHT*scale, PREVIEW_HEIGHT)

    def test_size_monotonic(self):
        self.assertLess(AvatarLayout(size=40).geometry()[0], AvatarLayout(size=100).geometry()[0])

    def test_geometry_rejects_invalid(self):
        for wh in ((0, 360), (640, 0), (True, 360), (500.0, 360), ('640', 360)):
            with self.subTest(wh=wh), self.assertRaises(ValueError):
                AvatarLayout().geometry(*wh)

    def test_description_does_not_claim_broadcast(self):
        self.assertIn('OBS', AvatarLayout().describe())
        self.assertIn('아님', AvatarLayout().describe())

    def test_render_reuses_original_renderer(self):
        class Canvas:
            def __init__(self): self.calls = []
            def configure(self, **kwargs): self.calls.append(('configure', kwargs))
            def delete(self, tag): self.calls.append(('delete', tag))
            def create_oval(self, *args, **kwargs): return 1
            def create_line(self, *args, **kwargs): return 1
            def create_arc(self, *args, **kwargs): return 1
            def create_text(self, *args, **kwargs): return 1
            def scale(self, *args): self.calls.append(('scale', args))
            def move(self, *args): self.calls.append(('move', args))
        c = Canvas()
        draft = AvatarLayout(background='초록색 배경')
        pose = AvatarFrame('가상 캐릭터', False, 4, background='초록색 배경')
        draw_layout_preview(c, draft, pose)
        self.assertIn(('configure', {'bg': '#00db53'}), c.calls)
        self.assertEqual(c.calls[-2][0], 'scale')
        self.assertEqual(c.calls[-1][0], 'move')

    def test_render_rejects_mismatched_background(self):
        with self.assertRaises(ValueError):
            draw_layout_preview(None, AvatarLayout(), AvatarFrame('아이스팅', False, 4, background='초록색 배경'))

    def test_record_schema_rejects_tampering_and_extra_fields(self):
        record = _record(AvatarLayout())
        self.assertEqual(validate_layout_record(record), AvatarLayout())
        for change in ({'obs_configured': True}, {'final_approval': True},
                       {'external_model_loaded': 1}, {'broadcasting_authorized': True},
                       {'schema_version': True}, {'kind': 'approved'}, {'size': '70'},
                       {'avatar': '3d'}, {'injected': 'X'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_layout_record({**record, **change})

    def test_no_auto_save(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'layout.json'
            with self.assertRaises(PermissionError): save_layout(p, AvatarLayout())
            self.assertFalse(p.exists())

    def test_save_load_delete(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'layout.json'
            plan = AvatarLayout(horizontal=17, vertical=23, size=63, background='초록색 배경')
            save_layout(p, plan, operator_confirmed=True)
            self.assertEqual(load_layout(p, selected_avatar='2d'), plan)
            self.assertFalse(json.loads(p.read_text('utf8'))['final_approval'])
            with self.assertRaises(PermissionError): delete_layout(p)
            self.assertTrue(p.exists())
            self.assertTrue(delete_layout(p, operator_confirmed=True))
            self.assertIsNone(load_layout(p, selected_avatar='2d'))
            self.assertFalse(delete_layout(p, operator_confirmed=True))

    def test_rejects_other_avatar_load_before_read(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'layout.json'
            save_layout(p, AvatarLayout(), operator_confirmed=True)
            for other in ('3d', 'undecided', ''):
                with self.subTest(other=other), self.assertRaises(ValueError):
                    load_layout(p, selected_avatar=other)

    def test_corrupt_and_oversized_record_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'layout.json'
            for raw in (b'{', b'\xff', b'0' * 1100, b'{"schema_version": 1}'):
                p.write_bytes(raw)
                with self.assertRaises(ValueError): load_layout(p, selected_avatar='2d')
                self.assertEqual(p.read_bytes(), raw)

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            target = base/'real.json'
            target.write_text('untouched', encoding='utf8')
            link = base/'link.json'
            try: link.symlink_to(target)
            except (NotImplementedError, OSError): self.skipTest('symlinks unavailable')
            with self.assertRaises(ValueError): save_layout(link, AvatarLayout(), operator_confirmed=True)
            with self.assertRaises(ValueError): load_layout(link, selected_avatar='2d')
            with self.assertRaises(ValueError): delete_layout(link, operator_confirmed=True)
            self.assertEqual(target.read_text(encoding='utf8'), 'untouched')

    def test_preserves_unrelated_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            existing = root/'settings.json'
            existing.write_bytes(b'original-settings')
            memory = root/'memory.sqlite3'
            memory.write_bytes(b'original-memory')
            p = layout_path(root)
            save_layout(p, AvatarLayout(), operator_confirmed=True)
            self.assertEqual(existing.read_bytes(), b'original-settings')
            self.assertEqual(memory.read_bytes(), b'original-memory')
            self.assertEqual(p.parent, root)


if __name__ == '__main__': unittest.main()
