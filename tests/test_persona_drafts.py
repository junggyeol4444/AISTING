"""6단계: 선택적으로 적용하는 성격·말투 초안, 로컬 적용, 호환성, 무통신."""
from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ai_broadcaster.persona_drafts import (
    EXAMPLE_DRAFTS, apply_draft_example, compact_persona_preview, preview_persona_guidance,
)
from ai_broadcaster.persona_modes import chosen_persona
from ai_broadcaster.offline_settings import DEFAULTS, load_settings, save_settings
from ai_broadcaster.offline_chat import LocalOllamaGenerator, ChatMessage
from ai_broadcaster.requirements import load_json, status, validate


class TestPersonaDrafts(unittest.TestCase):
    def setUp(self):
        self.custom = {'name': '내 캐릭터', 'style': '내 말투', 'character': '내 성격'}

    def test_all_samples_have_valid_fields(self):
        self.assertGreaterEqual(len(EXAMPLE_DRAFTS), 3)
        for key, sample in EXAMPLE_DRAFTS.items():
            with self.subTest(example=key):
                self.assertIn('예시', key)
                self.assertTrue(sample.explanation)
                self.assertTrue(1 <= len(sample.personality) <= 200)
                self.assertTrue(1 <= len(sample.speech_style) <= 200)

    def test_template_does_not_touch_name(self):
        original = copy.deepcopy(self.custom)
        for name in EXAMPLE_DRAFTS:
            new = apply_draft_example(original, name)
            self.assertEqual(new['name'], '내 캐릭터')
            self.assertNotEqual(new['style'], '내 말투')
            self.assertNotEqual(new['character'], '내 성격')
        self.assertEqual(original, self.custom)

    def test_invalid_example_never_changes_custom(self):
        original = copy.deepcopy(self.custom)
        with self.assertRaises(ValueError):
            apply_draft_example(original, '존재하지 않음')
        self.assertEqual(original, self.custom)

    def test_bad_fields_cannot_be_silently_fixed(self):
        for bad in ({}, {'name': '', 'style': 'ok', 'character': 'ok'},
                    {'name': 'x'*201, 'style': 'ok', 'character': 'ok'},
                    {'name': 'hi', 'style': '', 'character': 'ok'}, None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                apply_draft_example(bad, next(iter(EXAMPLE_DRAFTS)))

    def test_preview_custom_and_default_mode_are_distinct(self):
        draft = apply_draft_example(self.custom, next(iter(EXAMPLE_DRAFTS)))
        view_custom = compact_persona_preview('custom', draft)
        view_default = compact_persona_preview('default', draft)
        self.assertIn('내 캐릭터', view_custom)
        self.assertIn('성격 초안:', view_custom)
        self.assertIn('말투 초안:', view_custom)
        self.assertIn('아이스팅', view_default)
        self.assertNotIn('내 캐릭터', view_default)
        self.assertIn('AI가 생성한 대사는 아닙니다', view_custom)

    def test_full_preview_equals_prompt_persona_guidance(self):
        sample = apply_draft_example(self.custom, list(EXAMPLE_DRAFTS)[1])
        self.assertIn(sample['character'], preview_persona_guidance('custom', sample))
        self.assertIn(sample['style'], preview_persona_guidance('custom', sample))
        self.assertNotIn(sample['style'], preview_persona_guidance('default', sample))

    def test_preview_rejects_bad_length(self):
        for bad in (9, 201, True, None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                compact_persona_preview('custom', self.custom, bad)

    def test_long_draft_preview_truncates_only_display_not_saved_data(self):
        draft = {'name': 'A', 'style': '자'*180, 'character': '차'*175}
        result = compact_persona_preview('custom', draft, max_field=18)
        self.assertIn('…', result)
        self.assertIn('자'*180, preview_persona_guidance('custom', draft))

    def test_preserves_v06_settings_shape(self):
        data = copy.deepcopy(DEFAULTS)
        data['persona_mode'] = 'custom'
        data['persona'] = apply_draft_example(self.custom, list(EXAMPLE_DRAFTS)[0])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            save_settings(data, path)
            read = load_settings(path)
            self.assertEqual(read, data)
            self.assertEqual(set(read), set(DEFAULTS))
            self.assertFalse(read['streaming_enabled'])
            self.assertFalse(read['scheduled_execution'])

    def test_old_v05_settings_compatible(self):
        legacy = copy.deepcopy(DEFAULTS)
        legacy.pop('persona_mode')
        legacy['persona']['name'] = 'v05 이름'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            path.write_text(json.dumps(legacy, ensure_ascii=False), encoding='utf-8')
            migrated = load_settings(path)
        self.assertEqual(migrated['persona_mode'], 'custom')
        self.assertEqual(migrated['persona']['name'], 'v05 이름')

    def test_preview_is_pure_no_network_or_tts(self):
        with patch('socket.create_connection') as network:
            apply_draft_example(self.custom, list(EXAMPLE_DRAFTS)[0])
            preview_persona_guidance('custom', self.custom)
            compact_persona_preview('custom', self.custom)
            network.assert_not_called()

    def test_live_prompt_gets_updated_draft_only_on_user_call(self):
        draft = apply_draft_example(self.custom, list(EXAMPLE_DRAFTS)[0])
        generator = LocalOllamaGenerator('test-local', persona=draft)
        fake_answer = json.dumps({'message': {'content': '테스트 응답'}}, ensure_ascii=False).encode()
        requests = []

        def pretend_open(request, timeout):
            requests.append(json.loads(request.data.decode('utf-8')))
            return io.BytesIO(fake_answer)
        generator._opener.open = pretend_open
        self.assertEqual(requests, [])
        self.assertEqual(generator.generate(ChatMessage('시청자', '질문'), []), '테스트 응답')
        system = requests[0]['messages'][0]['content']
        self.assertIn(draft['character'], system)
        self.assertIn(draft['style'], system)
        self.assertIn('내 캐릭터', system)

    def test_gui_has_manual_draft_controls_and_local_only(self):
        gui = (ROOT / 'src/ai_broadcaster/desktop.py').read_text('utf-8')
        self.assertIn('text="선택한 초안 적용"', gui)
        self.assertIn('settings_scrollbar = ttk.Scrollbar', gui)
        self.assertIn('self._settings_canvas = settings_canvas', gui)
        self.assertIn('text="AI 지침 미리보기"', gui)
        self.assertIn('command=self._apply_persona_example', gui)
        self.assertIn('preview_persona_guidance(', gui)
        self.assertNotIn('StartStream', gui)

    def test_roadmap_stage_six_is_a_draft_not_preselection(self):
        c = load_json(ROOT / 'config' / 'requirements.json')
        r = load_json(ROOT / 'config' / 'roadmap.json')
        self.assertEqual(validate(c, r), [])
        self.assertEqual((status(r)['completed'], status(r)['current']['number']), (9,10))
        self.assertEqual(r['steps'][5]['status'], 'completed')
        self.assertEqual(c['operator_decisions']['persona'], 'runtime_default_or_custom')


if __name__ == '__main__':
    unittest.main()
