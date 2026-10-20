"""Read-only saved official TTS selection checks; no voice synthesis or network."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.official_tts_readiness import require_saved_korean_gpt_sovits
from ai_broadcaster.original_plan_studio import StageOneUnavailable

VALID = """character_config:
  character_name: '테스트'
  tts_config:
    tts_model: 'gpt_sovits_tts'
    gpt_sovits_tts:
      api_url: 'http://127.0.0.1:9880/tts'
      text_lang: 'ko'
      prompt_lang: 'ko'
      ref_audio_path: 'C:/licensed.wav'
      prompt_text: '정당하게 사용 가능한 내 음성'
"""


class SavedVoiceConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.folder = Path(self.root.name)
        self.file = self.folder / "conf.yaml"

    def check(self, text):
        self.file.write_text(text, encoding="utf-8")
        with patch(
            "ai_broadcaster.official_tts_readiness.check_official_project",
            return_value=self.folder,
        ):
            require_saved_korean_gpt_sovits(self.folder)

    def test_korean_gpt_sovits_with_local_endpoint_is_configured(self):
        self.check(VALID)

    def test_other_engine_is_never_misreported_as_gpt_sovits(self):
        with self.assertRaisesRegex(StageOneUnavailable, "GPT-SoVITS"):
            self.check(VALID.replace("'gpt_sovits_tts'", "'edge_tts'"))

    def test_non_korean_reference_language_is_rejected(self):
        with self.assertRaisesRegex(StageOneUnavailable, "한국어"):
            self.check(VALID.replace("prompt_lang: 'ko'", "prompt_lang: 'en'"))

    def test_remote_voice_api_is_rejected_without_request(self):
        with self.assertRaisesRegex(StageOneUnavailable, "로컬"):
            self.check(VALID.replace("127.0.0.1:9880", "external.example:9880"))

    def test_empty_reference_audio_setting_is_rejected(self):
        with self.assertRaisesRegex(StageOneUnavailable, "참조 음성"):
            self.check(VALID.replace("'C:/licensed.wav'", "''"))

    def test_duplicated_engine_key_is_rejected(self):
        with self.assertRaisesRegex(StageOneUnavailable, "누락 또는 중복"):
            self.check(VALID.replace("    gpt_sovits_tts:",
                                     "    tts_model: 'gpt_sovits_tts'\n    gpt_sovits_tts:"))


if __name__ == "__main__":
    unittest.main()
