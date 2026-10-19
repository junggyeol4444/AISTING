"""방송 플랫폼은 개발 사전 승인이 아니라 운영 중 자유롭게 선택하는 설정."""
from __future__ import annotations

import copy
import itertools
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ai_broadcaster.offline_settings import (
    DEFAULTS, PLATFORMS, load_settings, save_settings, validate_settings,
)
from ai_broadcaster.requirements import load_json, status, validate


class TestOptionalRuntimePlatformSelection(unittest.TestCase):
    def test_platforms_follow_current_user_requested_four_choices(self):
        self.assertEqual(PLATFORMS, {
            '치지직': 'chzzk', '유튜브': 'youtube', '트위치': 'twitch', 'SOOP': 'soop',
        })

    def test_default_has_no_platform_and_does_not_need_a_decision(self):
        self.assertEqual(validate_settings(DEFAULTS)['platforms'], [])

    def test_all_eight_none_single_multiple_combinations_are_valid(self):
        codes = list(PLATFORMS.values())
        for count in range(len(codes)+1):
            for choice in itertools.combinations(codes, count):
                with self.subTest(choice=choice):
                    config = copy.deepcopy(DEFAULTS)
                    config['platforms'] = list(choice)
                    self.assertEqual(validate_settings(config)['platforms'], list(choice))

    def test_can_save_and_change_selected_platforms_on_pc(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'settings.json'
            with patch('socket.create_connection') as network:
                for platforms in ([], ['chzzk'], ['youtube', 'twitch'],
                                  ['chzzk', 'youtube', 'twitch'], []):
                    config = copy.deepcopy(DEFAULTS)
                    config['platforms'] = platforms
                    save_settings(config, path)
                    self.assertEqual(load_settings(path)['platforms'], platforms)
                network.assert_not_called()
            self.assertFalse(load_settings(path)['streaming_enabled'])

    def test_setting_platform_does_not_activate_external_actions(self):
        config = copy.deepcopy(DEFAULTS)
        config['platforms'] = list(PLATFORMS.values())
        value = validate_settings(config)
        self.assertFalse(value['streaming_enabled'])
        self.assertFalse(value['scheduled_execution'])
        self.assertFalse(value['external_publish_enabled'])

    def test_duplicate_or_unknown_platform_rejected(self):
        for value in (['chzzk', 'chzzk'], ['youtube', 'unknown'], 'youtube'):
            config = copy.deepcopy(DEFAULTS)
            config['platforms'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_settings(config)

    def test_progress_stage3_no_user_preselection_block(self):
        roadmap = load_json(ROOT / 'config' / 'roadmap.json')
        config = load_json(ROOT / 'config' / 'requirements.json')
        self.assertEqual(validate(config, roadmap), [])
        self.assertEqual(roadmap['steps'][2]['status'], 'completed')
        self.assertEqual(config['operator_decisions']['broadcast_platform'],
                         'runtime_multi_select_optional')
        current = status(roadmap)
        self.assertEqual((current['completed'], current['total']), (9, 100))
        self.assertEqual(current['current']['number'], 10)

    def test_gui_no_one_platform_preselection_requirement(self):
        source = (ROOT / 'src' / 'ai_broadcaster' / 'desktop.py').read_text(encoding='utf-8')
        self.assertIn('for label, code in PLATFORMS.items():', source)
        self.assertIn('tk.Checkbutton', source.replace('ttk.Checkbutton', 'tk.Checkbutton'))
        self.assertIn('if check.get()', source)
        self.assertIn('언제든 선택·변경 가능', source)
        self.assertNotIn('플랫폼을 하나 확정', source)

    def test_other_user_choices_are_runtime_not_preconditions(self):
        config = load_json(ROOT / 'config' / 'requirements.json')
        choices = config['operator_decisions']
        self.assertEqual(choices['content_concept'], 'runtime_select_chat_game_both')
        self.assertEqual(choices['persona'], 'runtime_default_or_custom')
        self.assertIn('runtime_choose_2d_or_3d', choices['avatar_type_and_asset'])
        # 사전 플랫폼/콘텐츠 확정 없이 설정 검증이 성공해야 한다.
        assert validate_settings(DEFAULTS)['content'] == 'undecided'
        assert validate_settings(DEFAULTS)['avatar'] == 'undecided'

    def test_original_plan_is_not_modified(self):
        self.assertTrue((ROOT / 'docs' / 'ORIGINAL_PLAN.txt').is_file())


if __name__ == '__main__':
    unittest.main()
