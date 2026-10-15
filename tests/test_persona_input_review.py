import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.persona_input_review import review_persona_input
from ai_broadcaster.offline_settings import DEFAULTS

class PersonaInputReviewTests(unittest.TestCase):
    def test_default_ignores_unselected_draft(self):
        r = review_persona_input('default', {'name':'x'})
        self.assertEqual(r.fields, DEFAULTS['persona'])
        self.assertIn('기본 캐릭터', r.describe())
    def test_custom_preserves_korean(self):
        p = {'name':'하늘', 'character':'차분하고 다정함', 'style':'편한 한국어'}
        r = review_persona_input('custom', p)
        self.assertEqual(r.fields, p)
        self.assertIn('하늘', r.guidance)
        self.assertIn('9/100', r.describe())
    def test_invalid_custom_rejected(self):
        with self.assertRaises(ValueError):
            review_persona_input('custom', {'name':'', 'character':'좋음', 'style':'말투'})
    def test_no_input_mutation(self):
        p = dict(DEFAULTS['persona'])
        review_persona_input('custom', p)
        self.assertEqual(p, DEFAULTS['persona'])
