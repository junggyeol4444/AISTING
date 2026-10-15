"""054: in-memory 2D expressions and explicit safe local record controls."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.avatar_renderer import AvatarFrame, draw_avatar, draw_unavailable_3d
from ai_broadcaster.avatar_expressions import (
    EXPRESSIONS, AvatarExpressionChoice, expression_matches, expression_path,
    save_expression, load_expression, delete_expression, validate_expression_record,
)


class CanvasStub:
    def __init__(self):
        self.items = []
        self.bg = None

    def configure(self, **opts): self.bg = opts['bg']
    def delete(self, what):
        assert what == 'all'
        self.items.clear()
    def create_oval(self, *a, **kw): self.items.append(kw)
    def create_line(self, *a, **kw): self.items.append(kw)
    def create_arc(self, *a, **kw): self.items.append(kw)
    def create_text(self, *a, **kw): self.items.append(kw)
    def find_withtag(self, tag):
        return tuple(i for i, opts in enumerate(self.items) if tag in opts.get('tags', ()))


class AvatarExpressionsTests(unittest.TestCase):
    def test_default_neutral(self):
        self.assertEqual(AvatarFrame('아이스팅', False, 0).expression, 'neutral')

    def test_all_four_expressions_have_distinct_tags(self):
        c = CanvasStub()
        for expr in EXPRESSIONS.values():
            draw_avatar(c, AvatarFrame('아이스팅', False, 2, expression=expr))
            self.assertTrue(expression_matches(c, expr), expr)
            for other in EXPRESSIONS.values():
                if other != expr:
                    self.assertFalse(expression_matches(c, other))

    def test_speaking_preserves_mouth_and_expression(self):
        c = CanvasStub()
        for expr in EXPRESSIONS.values():
            draw_avatar(c, AvatarFrame('이름', True, 1, expression=expr))
            self.assertTrue(c.find_withtag('aisting_mouth_open'))
            self.assertTrue(expression_matches(c, expr))

    def test_same_selection_for_both_canvases(self):
        a, b = CanvasStub(), CanvasStub()
        draw_avatar(a, AvatarFrame('이름', True, 1, expression='smile'))
        draw_avatar(b, AvatarFrame('이름', True, 1, '초록색 배경', 'smile'))
        self.assertTrue(expression_matches(a, 'smile'))
        self.assertTrue(expression_matches(b, 'smile'))
        self.assertNotEqual(a.bg, b.bg)

    def test_unavailable_3d_has_no_sample_expression(self):
        c = CanvasStub()
        draw_unavailable_3d(c)
        self.assertFalse(any(expression_matches(c, e) for e in EXPRESSIONS.values()))

    def test_reject_invalid_expression(self):
        for value in ('auto', '', None, False, 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                AvatarFrame('이름', False, 0, expression=value)

    def test_reject_invalid_avatar(self):
        for avatar in ('3d', 'vrm', '', None):
            with self.subTest(avatar=avatar), self.assertRaises(ValueError):
                AvatarExpressionChoice(avatar, 'smile')

    def test_reject_invalid_choice_expression(self):
        with self.assertRaises(ValueError): AvatarExpressionChoice('2d', 'auto')

    def test_manual_save_confirmation_required(self):
        with tempfile.TemporaryDirectory() as d:
            f = expression_path(Path(d))
            with self.assertRaises(PermissionError): save_expression(f, AvatarExpressionChoice('2d', 'smile'))
            self.assertFalse(f.exists())

    def test_manual_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            f = expression_path(Path(d))
            choice = AvatarExpressionChoice('2d', 'concerned')
            save_expression(f, choice, operator_confirmed=True)
            self.assertEqual(load_expression(f, selected_avatar='2d'), choice)
            self.assertIn('표정', choice.describe())

    def test_missing_record_is_none_without_writing(self):
        with tempfile.TemporaryDirectory() as d:
            f = expression_path(Path(d))
            self.assertIsNone(load_expression(f, selected_avatar='2d'))
            self.assertFalse(f.exists())

    def test_undecided_to_2d_record_reuse_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            f = expression_path(Path(d))
            save_expression(f, AvatarExpressionChoice('undecided', 'smile'), operator_confirmed=True)
            with self.assertRaises(ValueError): load_expression(f, selected_avatar='2d')

    def test_3d_load_rejected_without_disk_read(self):
        with patch('pathlib.Path.open', side_effect=AssertionError('disk opened')):
            with self.assertRaises(ValueError): load_expression(Path('notexists'), selected_avatar='3d')

    def test_reject_permission_forgery(self):
        with tempfile.TemporaryDirectory() as d:
            f = expression_path(Path(d))
            save_expression(f, AvatarExpressionChoice('2d', 'smile'), operator_confirmed=True)
            content = json.loads(f.read_text(encoding='utf-8'))
            content['final_approval'] = True
            f.write_text(json.dumps(content), encoding='utf-8')
            with self.assertRaises(ValueError): load_expression(f, selected_avatar='2d')

    def test_reject_unknown_fields(self):
        with tempfile.TemporaryDirectory() as d:
            f = expression_path(Path(d))
            save_expression(f, AvatarExpressionChoice('2d', 'smile'), operator_confirmed=True)
            content = json.loads(f.read_text(encoding='utf-8'))
            content['model_path'] = 'C:/secret'
            with self.assertRaises(ValueError): validate_expression_record(content)

    def test_reject_oversized_record(self):
        with tempfile.TemporaryDirectory() as d:
            f = expression_path(Path(d))
            f.write_bytes(b'a' * 1025)
            with self.assertRaises(ValueError): load_expression(f, selected_avatar='2d')

    def test_reject_symlink_path_for_saving(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'target.json'
            target.write_text('untouched')
            link = Path(d) / 'link.json'
            link.symlink_to(target)
            with self.assertRaises(ValueError): save_expression(link, AvatarExpressionChoice('2d'), operator_confirmed=True)
            self.assertEqual(target.read_text(), 'untouched')

    def test_delete_double_confirmation_is_app_responsibility(self):
        with tempfile.TemporaryDirectory() as d:
            f = expression_path(Path(d))
            save_expression(f, AvatarExpressionChoice('2d'), operator_confirmed=True)
            with self.assertRaises(PermissionError): delete_expression(f)
            self.assertTrue(f.exists())
            self.assertTrue(delete_expression(f, operator_confirmed=True))
            self.assertFalse(delete_expression(f, operator_confirmed=True))

    def test_invalid_canvas_audit_parameter(self):
        with self.assertRaises(ValueError): expression_matches(CanvasStub(), 'unknown')

    def test_no_os_or_network_for_canvas_drawing(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')):
            c = CanvasStub()
            draw_avatar(c, AvatarFrame('이름', False, 0, expression='surprised'))
            self.assertTrue(expression_matches(c, 'surprised'))
