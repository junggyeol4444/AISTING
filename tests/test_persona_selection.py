"""Stage 5: Runtime persona selection, v05 data migration, free local Ollama instructions."""
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

from ai_broadcaster.offline_settings import (
    DEFAULTS, PERSONA_MODES, active_persona, load_settings, save_settings,
    validate_settings,
)
from ai_broadcaster.offline_chat import ChatMessage, LocalOllamaGenerator, MockReplyGenerator
from ai_broadcaster.persona_modes import (
    chosen_persona, persona_guidance, validate_persona_fields,
)
from ai_broadcaster.requirements import load_json, status, validate


class TestPersonaSelection(unittest.TestCase):
    def test_two_runtime_modes_with_default(self):
        self.assertEqual(PERSONA_MODES, {"기본 캐릭터": "default", "직접 만들기": "custom"})
        self.assertEqual(DEFAULTS['persona_mode'], 'default')
        self.assertEqual(DEFAULTS['persona']['name'], '아이스팅')
        self.assertEqual(active_persona(DEFAULTS)['name'], '아이스팅')

    def test_mode_default_ignores_saved_draft(self):
        value = copy.deepcopy(DEFAULTS)
        value['persona']['name'] = '사용자 직접 만든 캐릭터'
        self.assertEqual(active_persona(value)['name'], '아이스팅')
        self.assertEqual(chosen_persona('default', value['persona']), DEFAULTS['persona'])
        self.assertEqual(value['persona']['name'], '사용자 직접 만든 캐릭터')

    def test_custom_mode_uses_all_fields(self):
        value = copy.deepcopy(DEFAULTS)
        value['persona_mode'] = 'custom'
        value['persona'] = {'name': '자유', 'style': '침착한 한국어', 'character': '문학을 좋아함'}
        self.assertEqual(active_persona(value), value['persona'])
        self.assertIn('자유', persona_guidance(active_persona(value)))
        self.assertIn('침착한 한국어', persona_guidance(active_persona(value)))

    def test_persona_field_validation_boundaries(self):
        for invalid in ({}, {'name': 'a', 'style': '', 'character': 'b'},
                        {'name': 'a' * 201, 'style': 'b', 'character': 'c'},
                        {'name': 123, 'style': 'b', 'character': 'c'}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_persona_fields(invalid)
        self.assertEqual(validate_persona_fields({'name': ' A ', 'style': ' B ', 'character': ' C '}),
                         {'name': 'A', 'style': 'B', 'character': 'C'})

    def test_invalid_mode_rejected(self):
        for bad in ('unknown', '', None, True, 123):
            with self.subTest(bad=bad):
                data = copy.deepcopy(DEFAULTS)
                data['persona_mode'] = bad
                with self.assertRaises((ValueError, TypeError)):
                    validate_settings(data)
                with self.assertRaises(ValueError):
                    chosen_persona(bad, {})

    def test_save_switch_modes_preserves_custom_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'settings.json'
            data = copy.deepcopy(DEFAULTS)
            data['persona_mode'] = 'custom'
            data['persona'] = {'name': '은하', 'style': '정중함', 'character': '우주 탐험'}
            with patch('socket.create_connection') as network:
                for mode in ('custom', 'default', 'custom'):
                    data['persona_mode'] = mode
                    save_settings(data, file)
                    saved = load_settings(file)
                    self.assertEqual(saved['persona_mode'], mode)
                    self.assertEqual(saved['persona']['name'], '은하')
                    self.assertEqual(active_persona(saved)['name'],
                                     '아이스팅' if mode == 'default' else '은하')
                    self.assertFalse(saved['streaming_enabled'])
                    self.assertFalse(saved['scheduled_execution'])
                network.assert_not_called()

    def test_legacy_v05_unchanged_settings_open_in_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            legacy = copy.deepcopy(DEFAULTS)
            legacy.pop('persona_mode')
            original = json.dumps(legacy, ensure_ascii=False)
            path.write_text(original, encoding='utf-8')
            current = load_settings(path)
            self.assertEqual(current['persona_mode'], 'default')
            self.assertEqual(path.read_text(encoding='utf-8'), original)

    def test_legacy_v05_custom_input_not_lost(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            legacy = copy.deepcopy(DEFAULTS)
            legacy.pop('persona_mode')
            legacy['persona']['name'] = '이전 캐릭터'
            legacy['persona']['style'] = '경쾌함'
            original = json.dumps(legacy, ensure_ascii=False)
            path.write_text(original, encoding='utf-8')
            current = load_settings(path)
            self.assertEqual(current['persona_mode'], 'custom')
            self.assertEqual(active_persona(current)['name'], '이전 캐릭터')
            self.assertEqual(path.read_text(encoding='utf-8'), original)
            save_settings(current, path)
            self.assertEqual(load_settings(path)['persona_mode'], 'custom')

    def test_unexpected_legacy_shape_rejected_without_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            path.write_text('{"surprise": true}', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_settings(path)
            self.assertEqual(path.read_text(encoding='utf-8'), '{"surprise": true}')

    def test_default_persona_returns_copy(self):
        actual = chosen_persona('default', {})
        actual['name'] = '변경'
        self.assertEqual(DEFAULTS['persona']['name'], '아이스팅')

    def test_mock_ai_never_connects_to_persona_service(self):
        with patch('socket.create_connection') as network:
            result = MockReplyGenerator().generate(ChatMessage('시청자', '안녕'), [])
            network.assert_not_called()
        self.assertIn('모의 답변', result)

    def test_local_llm_prompt_reflects_custom_and_default(self):
        recorded = []
        fake_answer = json.dumps({'message': {'content': '응답'}}, ensure_ascii=False).encode()
        generator = LocalOllamaGenerator('test-local', persona={
            'name': '해솔', 'style': '차분한 말투', 'character': '과학자',
        })

        def fake_open(request, timeout):
            recorded.append((request.full_url, json.loads(request.data.decode('utf-8'))))
            return io.BytesIO(fake_answer)

        generator._opener.open = fake_open
        self.assertEqual(recorded, [])
        self.assertEqual(generator.generate(ChatMessage('테스트', '안녕'), []), '응답')
        self.assertIn('해솔', recorded[-1][1]['messages'][0]['content'])
        self.assertIn('과학자', recorded[-1][1]['messages'][0]['content'])
        self.assertIn('차분한 말투', recorded[-1][1]['messages'][0]['content'])
        generator.set_persona(chosen_persona('default', {}))
        self.assertEqual(generator.generate(ChatMessage('테스트', '다시'), []), '응답')
        self.assertIn('아이스팅', recorded[-1][1]['messages'][0]['content'])
        self.assertNotIn('해솔', recorded[-1][1]['messages'][0]['content'])
        self.assertEqual({url for url, _ in recorded}, {'http://127.0.0.1:11434/api/chat'})

    def test_invalid_persona_update_does_not_override_old(self):
        generator = LocalOllamaGenerator('test-local')
        before = copy.deepcopy(generator.persona)
        with self.assertRaises(ValueError):
            generator.set_persona({'name': 'hi', 'style': '', 'character': 'valid'})
        self.assertEqual(generator.persona, before)

    def test_roadmap_stage5_completion_not_user_preselection(self):
        roadmap = load_json(ROOT / 'config' / 'roadmap.json')
        requirements = load_json(ROOT / 'config' / 'requirements.json')
        self.assertEqual(validate(requirements, roadmap), [])
        self.assertEqual(requirements['operator_decisions']['persona'], 'runtime_default_or_custom')
        self.assertEqual((status(roadmap)['completed'], status(roadmap)['current']['number']), (9, 10))
        self.assertEqual(roadmap['steps'][4]['status'], 'completed')
        self.assertEqual(roadmap['steps'][5]['status'], 'completed')

    def test_roadmap_rejects_reintroduction_of_gate(self):
        roadmap = load_json(ROOT / 'config' / 'roadmap.json')
        requirements = load_json(ROOT / 'config' / 'requirements.json')
        roadmap['steps'][4]['status'] = 'pending'
        self.assertTrue(any('5단계' in err for err in validate(requirements, roadmap)))

    def test_gui_has_persona_mode_and_active_avatar(self):
        ui = (ROOT / 'src/ai_broadcaster/desktop.py').read_text(encoding='utf-8')
        self.assertIn('self._persona_mode = self._choice(', ui)
        self.assertIn('self._current_persona()["name"]', ui)
        self.assertIn('persona=self._current_persona()', ui)
        self.assertIn('"직접 만들기"', ui)
        self.assertNotIn('StartStream', ui)


if __name__ == '__main__':
    unittest.main()
