import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.requirements import ROOT, load_json, validate_features

class TestFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.features=load_json(ROOT / "config/features.json")
    def test_scope_valid(self):
        self.assertEqual(validate_features(self.features), [])
    def test_missing_required_rejected(self):
        f=copy.deepcopy(self.features); f["required"].pop()
        self.assertTrue(validate_features(f))
    def test_optional_games_are_not_required(self):
        ids=[x["id"] for x in self.features["required"]]
        self.assertNotIn("game",ids)
    def test_operator_approval_required_for_broadcast(self):
        self.assertIn("실제 방송 시작",self.features["no_default_actions"])
