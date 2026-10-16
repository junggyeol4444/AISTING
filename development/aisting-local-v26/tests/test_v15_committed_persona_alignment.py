"""v15 read-only official persona config comparison; NO actual LLM/audio/Live2D test."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'payload' / 'src'))
from ai_broadcaster.original_plan_studio import (
    StageOneUnavailable, inspect_saved_persona_alignment, save_official_persona,
)

CONFIG = """character_config:
  character_name: '기존 방송인'
  persona_prompt: |
    기존 성격
  tts_config:
    tts_model: 'gpt_sovits_tts'
    gpt_sovits_tts:
      api_url: 'http://127.0.0.1:9880/tts'
"""
SAVED = {'name': '확정된 이름', 'style': '부드러운 한국어', 'character': '밝은 성격'}
DRAFT = {'name': '미확정 초안', 'style': '미확정 말투', 'character': '미확정 성격'}


class CommittedPersonaAlignmentTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'run_server.py').write_text('existing', encoding='utf-8')
        (self.root / 'pyproject.toml').write_text('existing', encoding='utf-8')
        self.conf = self.root / 'conf.yaml'
        self.before = b'\xef\xbb\xbf' + CONFIG.replace('\n', '\r\n').encode('utf-8')
        self.conf.write_bytes(self.before)

    def test_initial_mismatch_does_not_write_anything(self):
        names_before = set(p.name for p in self.root.iterdir())
        self.assertFalse(inspect_saved_persona_alignment(self.root, SAVED))
        self.assertEqual(self.conf.read_bytes(), self.before)
        self.assertEqual(set(p.name for p in self.root.iterdir()), names_before)

    def test_explicit_saved_persona_apply_then_readonly_match(self):
        path, backup = save_official_persona(self.root, SAVED)
        self.assertEqual(path, self.conf)
        self.assertEqual(backup.read_bytes(), self.before)
        after = self.conf.read_bytes()
        self.assertTrue(inspect_saved_persona_alignment(self.root, SAVED))
        self.assertEqual(self.conf.read_bytes(), after)
        self.assertIn(b"tts_model: 'gpt_sovits_tts'", after)
        self.assertNotIn(b'\n', after.replace(b'\r\n', b''))

    def test_unconfirmed_draft_is_not_mistaken_for_saved(self):
        save_official_persona(self.root, SAVED)
        self.assertTrue(inspect_saved_persona_alignment(self.root, SAVED))
        self.assertFalse(inspect_saved_persona_alignment(self.root, DRAFT))

    def test_missing_config_rejected_without_creating_it(self):
        self.conf.unlink()
        with self.assertRaisesRegex(StageOneUnavailable, 'conf.yaml'):
            inspect_saved_persona_alignment(self.root, SAVED)
        self.assertFalse(self.conf.exists())

    def test_invalid_utf8_rejected_without_rewriting(self):
        broken = b'\xff\xfeinvalid'
        self.conf.write_bytes(broken)
        with self.assertRaisesRegex(StageOneUnavailable, '비교를 중단'):
            inspect_saved_persona_alignment(self.root, SAVED)
        self.assertEqual(self.conf.read_bytes(), broken)

    def test_unsupported_official_layout_rejected_without_rewriting(self):
        broken = b'not_character_config: 1\n'
        self.conf.write_bytes(broken)
        with self.assertRaisesRegex(StageOneUnavailable, '비교를 중단'):
            inspect_saved_persona_alignment(self.root, SAVED)
        self.assertEqual(self.conf.read_bytes(), broken)

    def test_persona_control_characters_rejected_without_rewriting(self):
        invalid = {**SAVED, 'style': 'first\nsecond'}
        with self.assertRaisesRegex(StageOneUnavailable, '비교를 중단'):
            inspect_saved_persona_alignment(self.root, invalid)
        self.assertEqual(self.conf.read_bytes(), self.before)


if __name__ == '__main__':
    unittest.main()
