"""Local official-configuration contract checks; NOT a real TTS run."""
import sys
import tempfile
import unittest
import wave
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'payload' / 'src'))
from ai_broadcaster.original_plan_tts import (
    VoiceConfigurationError, make_official_gpt_sovits_config,
    apply_official_gpt_sovits, inspect_reference_audio_container,
    validate_local_gpt_sovits_url,
)

# These names and indentation mirror official Open-LLM-VTuber's public
# config_templates/conf.default.yaml (not an invented TTS protocol).
CONF = '''system_config:
  host: 'localhost'
  port: 12393
character_config:
  character_name: 'Mao'
  live2d_model_name: 'mao_pro'
  persona_prompt: |
    Original personality
  tts_config:
    tts_model: 'edge_tts'
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
'''


class OfficialTTSContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.wav = self.root / 'voice-own-rights.wav'
        with wave.open(str(self.wav), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            audio.writeframes(b'\x00\x00' * 100)

    def test_real_official_field_names_and_idempotent(self):
        updated = make_official_gpt_sovits_config(CONF, self.wav, "안녕'하세요")
        self.assertIn("tts_model: 'gpt_sovits_tts'", updated)
        self.assertIn("text_lang: 'ko'", updated)
        self.assertIn("prompt_lang: 'ko'", updated)
        self.assertIn("prompt_text: '안녕''하세요'", updated)
        self.assertIn("live2d_model_name: 'mao_pro'", updated)
        self.assertIn("voice: 'en-US-AvaMultilingualNeural'", updated)
        self.assertIn("vad_model: 'silero_vad'", updated)
        self.assertIn("text_split_method: 'cut5'", updated)
        self.assertEqual(updated, make_official_gpt_sovits_config(updated, self.wav, "안녕'하세요"))

    def test_reject_missing_actual_engine_or_reference(self):
        self.assertRaises(VoiceConfigurationError, make_official_gpt_sovits_config,
                          CONF.replace('gpt_sovits_tts:', 'nonexistent_tts:'), self.wav, '안녕')
        self.assertRaises(VoiceConfigurationError, make_official_gpt_sovits_config,
                          CONF, self.root / 'absent.wav', '안녕')
        self.assertRaises(VoiceConfigurationError, make_official_gpt_sovits_config,
                          CONF, self.wav, '실제 내용\nmodel: injection')

    def test_real_file_change_is_backed_up_but_no_audio_performed(self):
        (self.root / 'run_server.py').write_text('# upstream file\n', encoding='utf8')
        (self.root / 'pyproject.toml').write_text('[project]\n', encoding='utf8')
        (self.root / 'conf.yaml').write_text(CONF, encoding='utf8')
        changed, backup = apply_official_gpt_sovits(self.root, self.wav, '안녕하세요')
        self.assertEqual(backup.read_text(encoding='utf8'), CONF)
        self.assertIn("text_lang: 'ko'", changed.read_text(encoding='utf8'))
        changed_again, no_backup = apply_official_gpt_sovits(self.root, self.wav, '안녕하세요')
        self.assertEqual(changed, changed_again)
        self.assertIsNone(no_backup)

    def test_reference_wav_real_container_header_is_checked(self):
        report = inspect_reference_audio_container(self.wav)
        self.assertIn('24000Hz', report)
        self.assertIn('실제 합성 미검증', report)
        self.wav.write_bytes(b'RIFFdata')
        with self.assertRaisesRegex(VoiceConfigurationError, 'WAV'):
            make_official_gpt_sovits_config(CONF, self.wav, '안녕')

    def test_local_endpoint_can_be_selected_without_silent_default_override(self):
        endpoint = 'http://localhost:9881/tts'
        self.assertEqual(endpoint, validate_local_gpt_sovits_url(endpoint))
        updated = make_official_gpt_sovits_config(CONF, self.wav, '안녕', api_url=endpoint)
        self.assertIn("api_url: 'http://localhost:9881/tts'", updated)
        self.assertNotIn("api_url: 'http://127.0.0.1:9880/tts'", updated)
        for invalid in ('https://paid.example.com/tts', 'http://127.0.0.1:0/tts',
                        'http://127.0.0.1:9880/tts?key=secret', 'http://localhost:9880/admin'):
            with self.subTest(invalid=invalid), self.assertRaises(VoiceConfigurationError):
                make_official_gpt_sovits_config(CONF, self.wav, '안녕', api_url=invalid)

    def test_flac_streaminfo_is_read_without_decoding_or_playing(self):
        path = self.root / 'reference.flac'
        block = (16).to_bytes(2, 'big') + (4096).to_bytes(2, 'big') + b'\x00' * 6
        block += (44100 << 4).to_bytes(3, 'big') + b'\x00' * 21
        self.assertEqual(len(block), 34)
        path.write_bytes(b'fLaC' + b'\x80\x00\x00\x22' + block)
        self.assertIn('44100Hz', inspect_reference_audio_container(path))
        self.assertIn('reference.flac', make_official_gpt_sovits_config(CONF, path, '안녕'))


if __name__ == '__main__':
    unittest.main()
