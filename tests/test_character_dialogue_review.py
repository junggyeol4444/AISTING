"""Stage 040: operator-led mock character dialogue review, no real model approval."""
import copy
import unittest
from unittest.mock import patch

from ai_broadcaster.character_dialogue_review import (
    SAMPLE_CHARACTER_SCRIPT, VERDICTS, review_character_dialogue,
    assess_character_dialogue, MAX_NOTE,
)
from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.reaction_directions import SITUATIONS


class Port:
    def __init__(self, bad_at=0):
        self.calls = []
        self.bad_at = bad_at

    def generate(self, item, history):
        self.calls.append((item, tuple(history)))
        if self.bad_at == len(self.calls):
            raise RuntimeError('sensitive path/credential MUST NOT APPEAR')
        return '모의: ' + item.text


class CharacterDialogueReviewTests(unittest.TestCase):
    def setUp(self):
        self.settings = copy.deepcopy(DEFAULTS)

    def test_default_structural_mock_without_auto_naturalness(self):
        report = review_character_dialogue(self.settings)
        self.assertTrue(report.structure_passed)
        self.assertEqual((report.mock.total, report.mock.passed_count), (6, 6))
        self.assertIn('운영자 판정 대기', report.describe())
        self.assertIn('실제 AI', report.describe())
        result = assess_character_dialogue(report, [VERDICTS[0]] * 6, [''] * 6)
        self.assertFalse(result.operator_accepted)
        self.assertFalse(result.all_reviewed)

    def test_custom_persona_and_optional_guidance_are_exact(self):
        self.settings['persona_mode'] = 'custom'
        self.settings['persona'] = {'name': '파란별', 'character': '차분함', 'style': '짧고 편한 말투'}
        directions = {SITUATIONS[0]: '운영자가 볼 수 있게 보류', SITUATIONS[2]: '모른다고 말하기'}
        boundaries = ['비공개 개인정보 언급 금지', '실명 요구하지 않기']
        report = review_character_dialogue(self.settings, likes='커피', dislikes='날벌레',
                                          directions=directions, boundaries=boundaries)
        for text in ('파란별', '차분함', '짧고 편한 말투', '커피', '날벌레',
                     *directions.values(), *boundaries):
            self.assertIn(text, report.persona_guidance)
        self.assertEqual((report.boundary_count, report.direction_count), (2, 2))
        self.assertNotIn('후원 메시지:', report.persona_guidance)
        self.assertNotIn('실명 요구하지 않기', report.mock.checks[0].reply)

    def test_default_mode_overrides_unselected_custom_persona(self):
        self.settings['persona']['name'] = '비활성 편집 초안'
        report = review_character_dialogue(self.settings)
        self.assertIn('아이스팅', report.persona_guidance)
        self.assertNotIn('비활성 편집 초안', report.persona_guidance)

    def test_duplicate_fifo_and_recent_eight(self):
        port = Port()
        script = '\n'.join(['가: 중복'] * 12)
        report = review_character_dialogue(self.settings, script, reply_port=port)
        self.assertTrue(report.structure_passed)
        self.assertEqual(len(port.calls), 12)
        self.assertEqual([len(old) for _, old in port.calls], list(range(9)) + [8] * 3)
        self.assertEqual([x.input_text for x in report.mock.checks], ['중복'] * 12)

    def test_mock_port_not_given_private_guidance(self):
        port = Port()
        review_character_dialogue(self.settings, '민: 안녕',
                                  boundaries=('운영자 전용 미리보기',), reply_port=port)
        self.assertEqual(port.calls[0][0].text, '안녕')
        self.assertNotIn('운영자 전용 미리보기', port.calls[0][0].text)

    def test_failure_preserves_remaining_and_redacts(self):
        port = Port(bad_at=2)
        report = review_character_dialogue(self.settings, reply_port=port)
        self.assertFalse(report.structure_passed)
        self.assertEqual((report.mock.passed_count, report.mock.remaining), (1, 5))
        self.assertNotIn('sensitive path/credential', report.describe())

    def test_valid_manual_full_acceptance_is_not_real_ai_certificate(self):
        report = review_character_dialogue(self.settings, '가: 하나\n나: 둘')
        assessment = assess_character_dialogue(report, ['자연스러움 확인'] * 2, ['', '직접 판단함'])
        self.assertTrue(assessment.operator_accepted)
        self.assertIn('모의 응답', assessment.describe())
        self.assertIn('최종 개발 승인', assessment.describe())

    def test_manual_failure_never_overwrites_structure_failure(self):
        report = review_character_dialogue(self.settings, reply_port=Port(bad_at=1))
        assessment = assess_character_dialogue(report, ['자연스러움 확인'] * 6, [''] * 6)
        self.assertFalse(assessment.operator_accepted)
        self.assertTrue(assessment.all_reviewed)

    def test_pending_and_requested_changes(self):
        report = review_character_dialogue(self.settings, '가: 하나\n나: 둘')
        assessment = assess_character_dialogue(report, ['자연스러움 확인', '수정 필요'], ['좋음', '말투 수정'])
        self.assertTrue(assessment.all_reviewed)
        self.assertFalse(assessment.operator_accepted)
        self.assertIn('말투 수정', assessment.describe())

    def test_invalid_operator_ratings_rejected(self):
        report = review_character_dialogue(self.settings, '가: 하나')
        for ratings, notes in [((), ()), (('합격',), ('',)), ((False,), ('',)),
                               ((VERDICTS[0],), (None,)),
                               ((VERDICTS[0],), ('x' * (MAX_NOTE + 1),)),
                               ((VERDICTS[0],), ('nul\x00byte',)),
                               ((VERDICTS[0],), ('', 'extra'))]:
            with self.subTest(ratings=ratings), self.assertRaises(ValueError):
                assess_character_dialogue(report, ratings, notes)

    def test_invalid_script_and_selection_are_prevalidated(self):
        port = Port()
        for text in ('', '잘못된 형식', '가:  ', '\n'.join('가: hi' for _ in range(31))):
            with self.subTest(text=text[:12]), self.assertRaises(ValueError):
                review_character_dialogue(self.settings, text, reply_port=port)
        self.assertEqual(port.calls, [])

    def test_invalid_optional_directions_boundaries(self):
        port = Port()
        for opts in [{'directions': {'미지원 상황': '규칙'}},
                     {'directions': {'악성 채팅': None}},
                     {'boundaries': ['중복', '중복']},
                     {'boundaries': ['x\x00y']},
                     {'directions': []}]:
            with self.subTest(opts=opts), self.assertRaises(ValueError):
                review_character_dialogue(self.settings, reply_port=port, **opts)
        self.assertEqual(port.calls, [])

    def test_no_settings_mutation(self):
        before = copy.deepcopy(self.settings)
        review_character_dialogue(self.settings, likes='좋아요', boundaries=['하지 말기'])
        self.assertEqual(before, self.settings)

    def test_no_network_sqlite_process_system_inspection_or_delay(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')) as network, \
             patch('sqlite3.connect', side_effect=AssertionError('sqlite')) as db, \
             patch('subprocess.Popen', side_effect=AssertionError('process')) as proc, \
             patch('platform.system', side_effect=AssertionError('inspect')) as system, \
             patch('time.sleep', side_effect=AssertionError('delay')) as delay:
            report = review_character_dialogue(self.settings)
            self.assertTrue(report.structure_passed)
            assess_character_dialogue(report, [VERDICTS[0]] * 6, [''] * 6)
            network.assert_not_called(); db.assert_not_called(); proc.assert_not_called()
            system.assert_not_called(); delay.assert_not_called()


if __name__ == '__main__':
    unittest.main()
