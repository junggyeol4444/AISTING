import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.personality_preferences import review_preferences
class PreferencesTests(unittest.TestCase):
    def setUp(self):
        self.draft = {'name':'하늘','character':'차분하고 다정함','style':'편한 한국어'}
    def test_explicit(self):
        r = review_preferences('custom', self.draft, '퍼즐', '소음')
        self.assertIn('퍼즐', r.guidance)
        self.assertIn('소음', r.guidance)
    def test_unset(self):
        r = review_preferences('custom', self.draft)
        self.assertNotIn('좋아하는 것:', r.guidance)
    def test_immutable(self):
        before = dict(self.draft)
        review_preferences('custom', self.draft, '음악')
        self.assertEqual(before, self.draft)
    def test_too_long(self):
        with self.assertRaises(ValueError): review_preferences('custom', self.draft, '가'*301)
    def test_nul(self):
        with self.assertRaises(ValueError): review_preferences('custom', self.draft, 'a\x00b')
    def test_invalid_persona(self):
        with self.assertRaises(ValueError): review_preferences('custom', {'name':''}, '음악')
