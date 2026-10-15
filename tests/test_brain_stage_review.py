import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.brain_stage_review import review_brain
from ai_broadcaster.offline_settings import DEFAULTS

class BrainReviewTests(unittest.TestCase):
    def test_mock_review(self):
        result = review_brain(DEFAULTS)
        self.assertTrue(result.mock_ready)
        self.assertEqual(len(result.checks), 5)
        self.assertFalse(result.actual_model_verified)
        self.assertFalse(result.windows_verified)
        self.assertFalse(result.operator_approved)
    def test_no_false_certification(self):
        text = review_brain(DEFAULTS).describe()
        self.assertIn('미검증', text)
        self.assertIn('9/100', text)
    def test_invalid_settings(self):
        with self.assertRaises((ValueError, TypeError, KeyError)):
            review_brain({'invalid': 'value'})
if __name__ == '__main__': unittest.main()
