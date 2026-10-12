import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.requirements import ROOT, load_json, validate, status

class TestRequirements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_json(ROOT / "config/requirements.json")
        cls.map = load_json(ROOT / "config/roadmap.json")
    def test_valid(self):
        self.assertEqual(validate(self.cfg, self.map), [])
    def test_100_steps(self):
        self.assertEqual([s["number"] for s in self.map["steps"]], list(range(1,101)))
    def test_forced_delay_rejected(self):
        c=copy.deepcopy(self.cfg); c["defaults"]["forced_response_delay"]=True
        self.assertTrue(validate(c,self.map))
    def test_skip_chat_rejected(self):
        c=copy.deepcopy(self.cfg); c["defaults"]["preemptively_skip_chats"]=True
        self.assertTrue(validate(c,self.map))
    def test_unapproved_install_rejected(self):
        c=copy.deepcopy(self.cfg); c["control"]["install_without_operator_approval"]=True
        self.assertTrue(validate(c,self.map))
    def test_broadcast_default_must_be_off(self):
        c=copy.deepcopy(self.cfg); c["control"]["broadcast_enabled_by_default"]=True
        self.assertTrue(validate(c,self.map))
    def test_status_next_third_step(self):
        s=status(self.map)
        self.assertEqual((s["completed"],s["total"],s["current"]["number"]),(2,100,3))
    def test_cannot_remove_step(self):
        r=copy.deepcopy(self.map); r["steps"].pop()
        self.assertTrue(validate(self.cfg,r))
