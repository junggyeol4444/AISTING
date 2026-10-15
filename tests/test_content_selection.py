"""4단계: 방송 콘텐츠 4가지 런타임 설정의 저장·변경·로컬 AI 반영 검증."""
from __future__ import annotations

import copy
import io
import itertools
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.content_modes import content_guidance, content_preview, validate_content
from ai_broadcaster.offline_chat import ChatMessage, LocalOllamaGenerator, MockReplyGenerator
from ai_broadcaster.offline_settings import CONTENTS, DEFAULTS, load_settings, save_settings, validate_settings
from ai_broadcaster.requirements import load_json, status, validate


class TestContentSettings(unittest.TestCase):
    def test_four_choices_are_exact(self):
        self.assertEqual(CONTENTS, {
            '미정': 'undecided', '수다': 'chat',
            '게임': 'game', '수다 + 게임': 'both',
        })

    def test_content_is_undecided_until_operator_chooses(self):
        self.assertEqual(DEFAULTS['content'], 'undecided')
        self.assertIn('미선택', content_preview(DEFAULTS['content']))

    def test_each_mode_validated_and_described(self):
        for name, code in CONTENTS.items():
            with self.subTest(name=name):
                self.assertEqual(validate_content(code), code)
                self.assertTrue(content_guidance(code))
                self.assertTrue(content_preview(code))

    def test_invalid_modes_cannot_be_saved_or_injected(self):
        for bad in ('unknown', '', None, True, ['game'], 1):
            with self.subTest(mode=repr(bad)):
                with self.assertRaises(ValueError):
                    validate_content(bad)
                settings = copy.deepcopy(DEFAULTS)
                settings['content'] = bad
                with self.assertRaises(ValueError):
                    validate_settings(settings)

    def test_all_modes_and_changes_roundtrip_local(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'aisting.json'
            with patch('socket.create_connection') as network:
                for content in ('undecided', 'chat', 'game', 'both', 'undecided'):
                    settings = copy.deepcopy(DEFAULTS)
                    settings['content'] = content
                    save_settings(settings, path)
                    saved = load_settings(path)
                    self.assertEqual(saved['content'], content)
                    self.assertFalse(saved['streaming_enabled'])
                    self.assertFalse(saved['external_publish_enabled'])
                    self.assertFalse(saved['scheduled_execution'])
                network.assert_not_called()

    def test_platform_and_content_can_be_mixed_arbitrarily(self):
        codes = ('chzzk', 'youtube', 'twitch')
        for n in range(4):
            for platforms in itertools.combinations(codes, n):
                for content in CONTENTS.values():
                    with self.subTest(platforms=platforms, content=content):
                        settings = copy.deepcopy(DEFAULTS)
                        settings['platforms'] = list(platforms)
                        settings['content'] = content
                        self.assertEqual(validate_settings(settings)['content'], content)

    def test_game_mode_never_claims_actual_game_control(self):
        self.assertIn('실제 게임', content_guidance('game'))
        self.assertIn('실제 게임 조작은 하지', content_preview('game'))

    def test_missing_content_does_not_force_chat_or_game(self):
        self.assertIn('단정하지 마', content_guidance('undecided'))

    def test_planned_stage_four_is_implemented_not_user_preselection(self):
        requirements = load_json(ROOT / 'config' / 'requirements.json')
        roadmap = load_json(ROOT / 'config' / 'roadmap.json')
        self.assertEqual(validate(requirements, roadmap), [])
        self.assertEqual(roadmap['steps'][3]['status'], 'completed')
        self.assertEqual(requirements['operator_decisions']['content_concept'],
                         'runtime_select_chat_game_both')
        self.assertEqual((status(roadmap)['completed'], status(roadmap)['current']['number']),
                         (9, 10))

    def test_must_not_modify_original_plan(self):
        self.assertTrue((ROOT / 'docs' / 'ORIGINAL_PLAN.txt').is_file())


class TestContentLocalModel(unittest.TestCase):
    def setUp(self):
        self.generator = LocalOllamaGenerator('local_model:latest')
        self.requests = []

        def fake_open(request, timeout=30):
            self.requests.append({
                'url': request.full_url,
                'body': json.loads(request.data.decode('utf-8')),
                'timeout': timeout,
            })
            return io.BytesIO(json.dumps({'message': {'content': '로컬 모의 AI 응답'}}).encode())

        self.generator._opener.open = fake_open

    def test_no_request_on_selection_or_initialization(self):
        self.generator.set_content('game')
        self.assertEqual(self.requests, [])

    def test_all_four_modes_are_distinct_system_contexts(self):
        prompts = []
        for code in CONTENTS.values():
            with self.subTest(mode=code):
                self.generator.set_content(code)
                answer = self.generator.generate(ChatMessage('시청자', '안녕'), [])
                self.assertEqual(answer, '로컬 모의 AI 응답')
                req = self.requests[-1]
                self.assertEqual(req['url'], 'http://127.0.0.1:11434/api/chat')
                self.assertFalse(req['body']['stream'])
                self.assertEqual(req['body']['model'], 'local_model:latest')
                self.assertIn('시청자: 안녕', req['body']['messages'][-1]['content'])
                prompt = req['body']['messages'][0]['content']
                self.assertIn(content_guidance(code), prompt)
                prompts.append(prompt)
        self.assertEqual(len(set(prompts)), 4)

    def test_invalid_update_cannot_poison_previous_choice(self):
        self.generator.set_content('chat')
        for value in ('bad', 0, None):
            with self.assertRaises(ValueError):
                self.generator.set_content(value)
        self.assertEqual(self.generator.content, 'chat')

    def test_only_local_url_even_in_both_mode(self):
        self.generator.set_content('both')
        self.generator.generate(ChatMessage('팬', '수다 또는 게임?'), [])
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0]['url'].split('/api')[0], 'http://127.0.0.1:11434')

    def test_mock_mode_stays_offline_and_content_independent(self):
        reply = MockReplyGenerator().generate(ChatMessage('팬', '반가워'), [])
        self.assertIn('모의 답변', reply)
        self.assertEqual(self.requests, [])

    def test_gui_wires_content_to_local_model(self):
        code = (ROOT / 'src/ai_broadcaster/desktop.py').read_text(encoding='utf-8')
        self.assertIn('content=CONTENTS[self._content.get()]', code)
        self.assertIn('self._runner.generator.set_content(CONTENTS[self._content.get()])', code)
        self.assertIn('self._content.trace_add("write", self._content_changed)', code)
        self.assertIn('self._content_preview', code)


if __name__ == '__main__':
    unittest.main()
