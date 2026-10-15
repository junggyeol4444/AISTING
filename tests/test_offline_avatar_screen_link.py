import unittest
from test_offline_broadcast_scene import FakeCanvas, make
from ai_broadcaster.offline_avatar_screen_link import inspect_avatar_screen_link

class LinkedCanvas(FakeCanvas):
    def find_all(self):
        return range(len(self.calls))
    def gettags(self, item):
        return self.calls[item][2].get('tags', ())

class LinkTests(unittest.TestCase):
    def test_3d_no_fallback(self):
        report = inspect_avatar_screen_link(LinkedCanvas(), make(avatar='3d', layout=None))
        self.assertFalse(report.linked_sample)
        self.assertIn('2D 대체 없음', report.detail)
    def test_undecided_no_fallback(self):
        report = inspect_avatar_screen_link(LinkedCanvas(), make(avatar='undecided', layout=None))
        self.assertFalse(report.linked_sample)
    def test_invalid_expression(self):
        with self.assertRaises(ValueError):
            inspect_avatar_screen_link(LinkedCanvas(), make(), 'invalid')
    def test_2d_scene_inspected(self):
        report = inspect_avatar_screen_link(LinkedCanvas(), make())
        self.assertEqual(report.avatar, '2d')
        self.assertTrue(report.linked_sample)
        self.assertIn('Canvas', report.detail)
