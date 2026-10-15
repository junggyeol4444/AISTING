"""Tests configuration editing against the documented upstream YAML layout.

Unit coverage only. These checks NEVER count as actual voice/model/avatar pass.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from configure_original_stage2 import build_upstream_config, configure


# Direct field names, indentation and expected schema from
# Open-LLM-VTuber/Open-LLM-VTuber/config_templates/conf.default.yaml.
OFFICIAL_YAML_SECTION = """system_config:
  port: 12393
character_config:
  conf_name: 'mao_pro'
  character_name: 'Mao'
  live2d_model_name: 'mao_pro'
  persona_prompt: |
    Original upstream character speech.
  agent_config:
    conversation_agent_choice: 'basic_memory_agent'
  tts_config:
    tts_model: 'edge_tts'
    # original upstream engine still retained
    edge_tts:
      voice: 'en-US-AvaMultilingualNeural'
    gpt_sovits_tts:
      api_url: 'http://127.0.0.1:9880/tts'
      text_lang: 'zh'
      ref_audio_path: ''
      prompt_lang: 'zh'
      prompt_text: ''
      text_split_method: 'cut5'
      batch_size: '1'
      media_type: 'wav'
      streaming_mode: 'false'
  vad_config:
    vad_model: 'silero_vad'
"""

IDENTITY = {
    "name": "내방송인",
    "character": "명랑하고 솔직함",
    "style": "자연스러운 한국어",
}


class OfficialStage2Config(unittest.TestCase):
    def test_real_upstream_yaml_paths_and_preserve_unrelated_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            wav = Path(directory) / "user-licensed.wav"
            wav.write_bytes(b"RIFFtest")
            result = build_upstream_config(
                OFFICIAL_YAML_SECTION, IDENTITY, wav, "안녕하세요."
            )
            self.assertIn("tts_model: 'gpt_sovits_tts'", result)
            self.assertIn("text_lang: 'ko'", result)
            self.assertIn("prompt_lang: 'ko'", result)
            self.assertIn("prompt_text: '안녕하세요.'", result)
            self.assertIn("character_name: '내방송인'", result)
            self.assertIn("성격: 명랑하고 솔직함", result)
            self.assertIn("말투: 자연스러운 한국어", result)
            self.assertIn("live2d_model_name: 'mao_pro'", result)
            self.assertIn("agent_config:", result)
            self.assertIn("vad_model: 'silero_vad'", result)
            self.assertNotIn("Original upstream character speech.", result)

    def test_reject_unrecognized_upstream_config_instead_of_guessing(self):
        with tempfile.TemporaryDirectory() as directory:
            wav = Path(directory) / "licensed.wav"
            wav.write_bytes(b"RIFFtest")
            self.assertRaises(
                ValueError, build_upstream_config,
                OFFICIAL_YAML_SECTION.replace(
                    "gpt_sovits_tts:", "a_different_engine:"
                ), IDENTITY, wav, "안녕하세요."
            )

    def test_safe_yaml_quoting_and_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            wav = Path(directory) / "licensed.wav"
            wav.write_bytes(b"RIFFtest")
            identity = dict(IDENTITY, name="앨리스'방송인")
            changed = build_upstream_config(
                OFFICIAL_YAML_SECTION, identity, wav, "오늘의 '대사'"
            )
            self.assertIn("character_name: '앨리스''방송인'", changed)
            self.assertIn("prompt_text: '오늘의 ''대사'''", changed)
            self.assertEqual(
                changed,
                build_upstream_config(changed, identity, wav, "오늘의 '대사'")
            )
            self.assertRaises(
                ValueError, build_upstream_config,
                OFFICIAL_YAML_SECTION, identity, wav, "음성\n새로운키: yes"
            )

    def test_preview_does_not_edit_real_existing_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "run_server.py").write_text("pass\n", encoding="utf-8")
            config = root / "conf.yaml"
            config.write_text(OFFICIAL_YAML_SECTION, encoding="utf-8")
            wav = root / "licensed.wav"
            wav.write_bytes(b"RIFFtest")
            from unittest.mock import patch
            from ai_broadcaster.offline_settings import DEFAULTS
            with patch("configure_original_stage2.load_settings", return_value=DEFAULTS):
                self.assertFalse(configure(
                    root, wav, "안녕하세요.", apply=False
                ))
            self.assertEqual(config.read_text(encoding="utf-8"), OFFICIAL_YAML_SECTION)
            self.assertEqual(len(list(root.glob("*.bak"))), 0)


if __name__ == "__main__":
    unittest.main()
