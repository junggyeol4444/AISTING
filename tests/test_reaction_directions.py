import unittest
from ai_broadcaster.reaction_directions import review_reaction_directions, SITUATIONS
from ai_broadcaster.offline_settings import DEFAULTS

class ReactionDirectionsTests(unittest.TestCase):
    def test_empty_no_invented_directions(self):
        r = review_reaction_directions('default', DEFAULTS['persona'], {})
        self.assertTrue(r.passed)
        self.assertNotIn('상황별 반응 방향 (선택):', r.guidance)
    def test_custom_selected_only(self):
        p = {'name':'테스트', 'character':'차분함', 'style':'짧게'}
        r = review_reaction_directions('custom', p, {'악성 채팅':'차분하게 응답', '일반 채팅':'반갑게'}, '게임', '스포일러')
        self.assertTrue(r.passed)
        self.assertIn('차분하게 응답', r.guidance)
        self.assertNotIn('- 후원 메시지:', r.guidance)
    def test_reject_unknown_and_oversize(self):
        for data in ({'임의':'내용'}, {'일반 채팅':'a'*501}, {'일반 채팅':None}, {'일반 채팅':'\x00'}):
            with self.assertRaises(ValueError):
                review_reaction_directions('default', DEFAULTS['persona'], data)
    def test_no_mutation(self):
        p = dict(DEFAULTS['persona']); d = {'모르는 질문':'모르면 모른다고 말하기'}
        review_reaction_directions('default', p, d)
        self.assertEqual(p, DEFAULTS['persona']); self.assertEqual(d, {'모르는 질문':'모르면 모른다고 말하기'})
    def test_situations_are_explicit(self):
        self.assertEqual(len(SITUATIONS), 4)
