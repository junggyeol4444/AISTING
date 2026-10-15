import unittest
from ai_broadcaster.style_consistency import check_style_consistency
from ai_broadcaster.offline_settings import DEFAULTS
class StyleConsistencyTests(unittest.TestCase):
    def test_default(self):
        r=check_style_consistency('default',DEFAULTS['persona']);self.assertTrue(r.passed)
    def test_custom_duplicates(self):
        p={'name':'테스트','character':'명랑함','style':'친근한 말투'}
        r=check_style_consistency('custom',p,'게임','스포일러',('안녕','안녕'))
        self.assertTrue(r.passed);self.assertEqual(r.samples,('안녕','안녕'))
    def test_blank(self):
        self.assertFalse(check_style_consistency('default',DEFAULTS['persona'],samples=(' ',)).passed)
    def test_invalid(self):
        for samples in (('a'*2001,),tuple('a' for _ in range(21)),(None,)):
            with self.assertRaises(ValueError):check_style_consistency('default',DEFAULTS['persona'],samples=samples)
    def test_no_mutation(self):
        p=dict(DEFAULTS['persona']);check_style_consistency('default',p);self.assertEqual(p,DEFAULTS['persona'])
