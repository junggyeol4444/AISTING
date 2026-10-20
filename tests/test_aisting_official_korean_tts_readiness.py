"""Read-only saved official TTS selection checks; no voice synthesis or network."""
import sys
import tempfile
import unittest
import wave
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
        self.reference = self.folder / "licensed-reference.wav"
        with wave.open(str(self.reference), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes((b"\x02\x00\x04\x00") * 800)

    def check(self, text):
        # The caller's C:/licensed.wav is a placeholder, not a real sample.
        # The preflight must accept only a *real local* disposable WAV file.
        text = text.replace("C:/licensed.wav", self.reference.as_posix())
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

    def test_deleted_reference_blocks_unusable_real_audio_before_send(self):
        self.reference.unlink()
        with self.assertRaisesRegex(StageOneUnavailable, "실제 WAV/FLAC"):
            self.check(VALID)

    def test_invalid_reference_container_blocks_non_audio_data(self):
        self.reference.write_bytes(b"not a real wav file")
        with self.assertRaisesRegex(StageOneUnavailable, "실제 WAV/FLAC"):
            self.check(VALID)

    def test_refuses_relative_reference_to_avoid_wrong_process_workdir(self):
        self.file.write_text(VALID.replace(
            "'C:/licensed.wav'", "'relative.wav'"), encoding="utf-8")
        with patch("ai_broadcaster.official_tts_readiness.check_official_project",
                   return_value=self.folder):
            with self.assertRaisesRegex(StageOneUnavailable, "절대 경로"):
                require_saved_korean_gpt_sovits(self.folder)

    def test_reference_text_control_chars_cannot_inject_real_prompt(self):
        with self.assertRaisesRegex(StageOneUnavailable, "녹음 대사"):
            self.check(VALID.replace(
                "정당하게 사용 가능한 내 음성", "참조\u0001문장"))

    def test_duplicated_engine_key_is_rejected(self):
        with self.assertRaisesRegex(StageOneUnavailable, "누락 또는 중복"):
            self.check(VALID.replace("    gpt_sovits_tts:",
                                     "    tts_model: 'gpt_sovits_tts'\n    gpt_sovits_tts:"))


if __name__ == "__main__":
    unittest.main()
