"""Existing official conf.yaml preservation tests; no server or voice run."""
from pathlib import Path
import os
import sys
import tempfile
import unittest
import wave
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'payload' / 'src'))
from ai_broadcaster.original_plan_config_io import (
    ExistingConfigChangedError, replace_official_config_with_backup)
from ai_broadcaster.original_plan_studio import save_official_persona
from ai_broadcaster.original_plan_tts import apply_official_gpt_sovits

CONFIG = '''character_config:
  character_name: 'Original'
  persona_prompt: |
    Original prompt
  tts_config:
    tts_model: 'edge_tts'
    gpt_sovits_tts:
      api_url: 'http://127.0.0.1:9880/tts'
      text_lang: 'zh'
      ref_audio_path: ''
      prompt_lang: 'zh'
      prompt_text: ''
      text_split_method: 'cut5'
'''


class OfficialConfigPreservation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'run_server.py').write_text('existing upstream', encoding='utf-8')
        (self.root / 'pyproject.toml').write_text('existing upstream', encoding='utf-8')
        self.conf = self.root / 'conf.yaml'
        self.before = b'\xef\xbb\xbf' + CONFIG.replace('\n', '\r\n').encode('utf-8')
        self.conf.write_bytes(self.before)
        self.wav = self.root / 'owned.wav'
        with wave.open(str(self.wav), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            audio.writeframes(b'\x00\x00' * 100)

    def test_gpt_sovits_keeps_bom_crlf_original_backup(self):
        conf, backup = apply_official_gpt_sovits(self.root, self.wav, '안녕하세요')
        self.assertEqual(conf, self.conf)
        self.assertEqual(backup.read_bytes(), self.before)
        updated = conf.read_bytes()
        self.assertTrue(updated.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n', updated.replace(b'\r\n', b''))
        self.assertIn("tts_model: 'gpt_sovits_tts'".encode(), updated)
        again, no_backup = apply_official_gpt_sovits(self.root, self.wav, '안녕하세요')
        self.assertEqual(again, conf)
        self.assertIsNone(no_backup)

    def test_persona_keeps_bom_crlf_and_existing_tts(self):
        conf, backup = save_official_persona(self.root, {
            'name': '방송인', 'style': '친근한 말투', 'character': '밝은 성격'})
        self.assertEqual(backup.read_bytes(), self.before)
        updated = conf.read_bytes()
        self.assertTrue(updated.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n', updated.replace(b'\r\n', b''))
        self.assertIn("tts_model: 'edge_tts'".encode(), updated)
        self.assertIn('방송인'.encode(), updated)
        _, no_backup = save_official_persona(self.root, {
            'name': '방송인', 'style': '친근한 말투', 'character': '밝은 성격'})
        self.assertIsNone(no_backup)

    def test_refuse_changed_original_before_any_backup(self):
        with self.assertRaisesRegex(ExistingConfigChangedError, '변경'):
            replace_official_config_with_backup(self.conf, self.before + b'old', b'new', label='aisting')
        self.assertEqual(self.conf.read_bytes(), self.before)
        self.assertFalse(list(self.root.glob('*.bak')))

    def test_failed_replace_keeps_original_and_cleans_temp(self):
        with patch('ai_broadcaster.original_plan_config_io.os.replace', side_effect=OSError('denied')):
            with self.assertRaises(OSError):
                replace_official_config_with_backup(self.conf, self.before, b'new', label='aisting')
        self.assertEqual(self.conf.read_bytes(), self.before)
        self.assertFalse(list(self.root.glob('.aisting-conf-*')))
        self.assertEqual(len(list(self.root.glob('*.bak'))), 1)

    def test_reject_symlink_config(self):
        actual = self.root / 'actual.yaml'
        actual.write_bytes(self.before)
        self.conf.unlink()
        try:
            self.conf.symlink_to(actual)
        except (OSError, NotImplementedError):
            self.skipTest('symlink unavailable')
        with self.assertRaisesRegex(ExistingConfigChangedError, '링크'):
            replace_official_config_with_backup(self.conf, self.before, b'new', label='aisting')
        self.assertEqual(actual.read_bytes(), self.before)

    @unittest.skipIf(os.name == 'nt', 'POSIX permission bit test')
    def test_private_backup_permissions_and_original_mode(self):
        self.conf.chmod(0o640)
        backup = replace_official_config_with_backup(self.conf, self.before, b'new', label='aisting')
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.conf.stat().st_mode & 0o777, 0o640)


if __name__ == '__main__':
    unittest.main()
