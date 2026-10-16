"""Local file-contract tests; NOT a real AI / TTS / Live2D run."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import wave
from unittest import TestCase

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'payload' / 'src'))
from ai_broadcaster.original_plan_readiness import inspect_existing_official_core
from ai_broadcaster.original_plan_studio import StageOneUnavailable

CONF = '''system_config:
  host: '127.0.0.1'
character_config:
  conf_name: 'mao_pro'
  live2d_model_name: 'mao_pro'
  character_name: '내 캐릭터'
  persona_prompt: |
    실제 저장된 설정을 사용
  agent_config:
    conversation_agent_choice: 'basic_memory_agent'
    agent_settings:
      basic_memory_agent:
        llm_provider: 'ollama_llm'
  tts_config:
    tts_model: 'gpt_sovits_tts'
    gpt_sovits_tts:
      ref_audio_path: '__TEST_REFERENCE__'
      prompt_text: '실제 녹음 문장'
'''
MODEL = {
    'Version': 3,
    'FileReferences': {
        'Moc': 'character.moc3',
        'Textures': ['textures/texture.png'],
        'Expressions': [{'Name':'happy','File':'emotions/happy.exp3.json'}],
        'Motions': {'Idle':[{'File':'motions/idle.motion3.json'}]},
    },
}


def make_fixture(root: Path):
    (root / 'run_server.py').write_text('official entry is present', encoding='utf8')
    (root / 'pyproject.toml').write_text('[project]\nname="open-llm-vtuber"\n', encoding='utf8')
    ref = root / 'reference.wav'
    with wave.open(str(ref), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b'\x00\x00' * 100)
    (root / 'conf.yaml').write_text(CONF.replace('__TEST_REFERENCE__', str(ref)), encoding='utf8')
    (root / 'model_dict.json').write_text(json.dumps([{'name':'mao_pro', 'url':'/live2d-models/mao_pro/runtime/mao_pro.model3.json'}]),encoding='utf8')
    base = root / 'live2d-models/mao_pro/runtime'
    base.mkdir(parents=True)
    (base / 'mao_pro.model3.json').write_text(json.dumps(MODEL),encoding='utf8')
    for rel in ('character.moc3', 'textures/texture.png', 'emotions/happy.exp3.json', 'motions/idle.motion3.json'):
        file = base / rel
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b'local existing asset')
    return base


class RealUpstreamFileInspection(TestCase):
    def test_real_selected_files_are_inspected_without_modification(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            make_fixture(root)
            original={(p.relative_to(root)).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
            result=inspect_existing_official_core(root)
            self.assertEqual('내 캐릭터', result.character_name)
            self.assertEqual('basic_memory_agent', result.agent_type)
            self.assertEqual('ollama_llm', result.llm_backend)
            self.assertEqual('gpt_sovits_tts', result.tts_engine)
            self.assertEqual(4, result.live2d_asset_files)
            self.assertFalse(result.issues)
            self.assertEqual(original, {(p.relative_to(root)).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_missing_real_live2d_texture_is_a_failure_not_a_fake_success(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            base=make_fixture(root)
            (base/'textures/texture.png').unlink()
            result=inspect_existing_official_core(root)
            self.assertTrue(result.issues)
            self.assertEqual(0, result.live2d_asset_files)
            self.assertIn('없음', result.issues[0])

    def test_selected_model_must_be_in_model_dict(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            make_fixture(root)
            (root/'conf.yaml').write_text((root/'conf.yaml').read_text('utf8').replace("'mao_pro'", "'not_selected'"), encoding='utf8')
            report=inspect_existing_official_core(root)
            self.assertTrue(report.issues)

    def test_external_file_reference_is_rejected(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            base=make_fixture(root)
            edited=dict(MODEL)
            edited['FileReferences']={**MODEL['FileReferences'], 'Moc':'../../../../outside.moc3'}
            (base/'mao_pro.model3.json').write_text(json.dumps(edited),encoding='utf8')
            report=inspect_existing_official_core(root)
            self.assertTrue(report.issues)
            self.assertIn('밖', report.issues[0])

    def test_missing_official_conf_does_not_create_one(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            make_fixture(root)
            (root/'conf.yaml').unlink()
            with self.assertRaises(StageOneUnavailable):
                inspect_existing_official_core(root)
            self.assertFalse((root/'conf.yaml').exists())

    def test_no_guessed_llm_for_different_agent(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            make_fixture(root)
            (root/'conf.yaml').write_text((root/'conf.yaml').read_text('utf8').replace('basic_memory_agent\'\n    agent_settings', 'other_agent\'\n    agent_settings'),encoding='utf8')
            report=inspect_existing_official_core(root)
            self.assertEqual('other_agent',report.agent_type)
            self.assertIn('확인되지 않음',report.llm_backend)

    def test_real_voice_reference_missing_is_not_reported_as_ready(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            make_fixture(root)
            (root/'reference.wav').unlink()
            result=inspect_existing_official_core(root)
            self.assertIn('참조 음성 파일', str(result.issues))
            self.assertEqual(4, result.live2d_asset_files)

    def test_duplicates_in_critical_config_fail_closed(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            make_fixture(root)
            (root/'conf.yaml').write_text((root/'conf.yaml').read_text('utf8').replace("  character_name: '내 캐릭터'", "  character_name: '내 캐릭터'\n  character_name: '다른 값'"),encoding='utf8')
            with self.assertRaises(StageOneUnavailable):
                inspect_existing_official_core(root)
