"""기획안에 반하는 기능이 기본 설정으로 들어가는 것을 탐지."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.requirements import ROOT, load_json, status, validate


class TestRequirementGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_json(ROOT / 'config' / 'requirements.json')
        cls.roadmap = load_json(ROOT / 'config' / 'roadmap.json')

    def test_current_plan_passes(self):
        self.assertEqual(validate(self.config, self.roadmap), [])

    def test_exactly_100_steps(self):
        self.assertEqual([x['number'] for x in self.roadmap['steps']], list(range(1,101)))

    def test_forced_delay_rejected(self):
        c = copy.deepcopy(self.config)
        c['defaults']['forced_response_delay'] = True
        self.assertTrue(any('forced_response_delay' in msg for msg in validate(c,self.roadmap)))

    def test_skip_chat_rejected(self):
        c = copy.deepcopy(self.config)
        c['defaults']['preemptively_skip_chats'] = True
        self.assertTrue(validate(c,self.roadmap))

    def test_installation_without_approval_rejected(self):
        c = copy.deepcopy(self.config)
        c['control']['install_without_operator_approval'] = True
        self.assertTrue(validate(c,self.roadmap))

    def test_broadcast_default_must_be_off(self):
        c = copy.deepcopy(self.config)
        c['control']['broadcast_enabled_by_default'] = True
        self.assertTrue(validate(c,self.roadmap))

    def test_stage_three_completed_as_runtime_multi_choice(self):
        s = status(self.roadmap)
        self.assertEqual((s['completed'], s['total'], s['current']['number']), (9,100,10))
        self.assertEqual(self.config['operator_decisions']['broadcast_platform'],
                         'runtime_multi_select_optional')

    def test_cannot_reintroduce_platform_preselection_gate(self):
        c = copy.deepcopy(self.config)
        c['operator_decisions']['broadcast_platform'] = None
        self.assertTrue(any('플랫폼' in e for e in validate(c,self.roadmap)))
        r = copy.deepcopy(self.roadmap)
        r['steps'][2]['status'] = 'pending'
        self.assertTrue(any('3단계' in e for e in validate(self.config,r)))

    def test_cannot_reintroduce_content_preselection_gate(self):
        c = copy.deepcopy(self.config)
        c['operator_decisions']['content_concept'] = None
        self.assertTrue(any('content_concept' in e for e in validate(c, self.roadmap)))
        r = copy.deepcopy(self.roadmap)
        r['steps'][3]['status'] = 'pending'
        self.assertTrue(any('4단계' in e for e in validate(self.config, r)))

    def test_cannot_drop_step(self):
        r = copy.deepcopy(self.roadmap)
        r['steps'] = r['steps'][:-1]
        self.assertTrue(validate(self.config, r))


if __name__ == '__main__':
    unittest.main()
