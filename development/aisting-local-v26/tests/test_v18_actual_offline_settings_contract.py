"""Integrate v18 persona saving with SHA-verified *actual main offline_settings.py*.

This tests a genuine existing AISTING settings module snapshot (Git blob SHA
769ea22a59b490d9eeb27913aa569550f3b57da3), not a fixture. It does
NOT run desktop.py, AI, TTS, Live2D, OBS, or a real Windows application.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'evidence/original_readonly/offline_settings_main_20261016.py'
EXPECTED_SHA = '769ea22a59b490d9eeb27913aa569550f3b57da3'
sys.path.insert(0, str(ROOT / 'payload' / 'src'))
from ai_broadcaster.original_plan_persona_store import (
    CharacterCommitConflict, commit_character_identity, save_broadcast_without_persona,
)


def verified_original_settings_module():
    content = SOURCE.read_bytes()
    sha = hashlib.sha1(f'blob {len(content)}\0'.encode('ascii') + content).hexdigest()
    if sha != EXPECTED_SHA:
        raise AssertionError('원본 offline_settings.py 스냅샷 SHA 불일치')
    spec = importlib.util.spec_from_file_location('ai_broadcaster.offline_settings', SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ActualOfflineSettingsContractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'settings.json'
        self.actual = verified_original_settings_module()
        patcher = patch.dict(sys.modules, {'ai_broadcaster.offline_settings': self.actual})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.identity = {'name': '실제 설정 연동', 'style': '명확한 한국어', 'character': '차분한 성격'}
        self.default = deepcopy(self.actual.DEFAULTS)

    def write(self, data):
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def test_exact_original_source_git_blob_sha(self):
        self.assertEqual(self.actual.DEFAULTS['budget'], 'free_only')
        self.assertEqual(self.actual.DEFAULTS['persona_mode'], 'default')

    def test_explicit_character_commit_survives_real_loader_restart(self):
        self.write(self.default)
        saved = commit_character_identity(self.default, 'custom', self.identity, path=self.path)
        restarted = self.actual.load_settings(self.path)
        self.assertEqual(saved['persona'], self.identity)
        self.assertEqual(self.actual.active_persona(restarted), self.identity)
        self.assertEqual(restarted['persona_mode'], 'custom')

    def test_ordinary_save_keeps_confirmed_identity_with_real_validator(self):
        self.write(self.default)
        confirmed = commit_character_identity(self.default, 'custom', self.identity, path=self.path)
        draft = deepcopy(self.default)
        draft['persona'] = {'name': '미저장 초안', 'style': '미저장', 'character': '미저장'}
        draft['persona_mode'] = 'default'
        draft['content'] = 'chat'
        saved = save_broadcast_without_persona(self.default, draft, path=self.path)
        restarted = self.actual.load_settings(self.path)
        self.assertEqual(saved['content'], 'chat')
        self.assertEqual(restarted['persona'], confirmed['persona'])
        self.assertEqual(restarted['persona_mode'], 'custom')
        self.assertNotIn('미저장 초안', self.path.read_text(encoding='utf-8'))

    def test_old_v05_character_settings_migrate_without_loss(self):
        legacy = deepcopy(self.default)
        legacy['persona'] = self.identity
        del legacy['persona_mode']
        del legacy['voice_profile']
        self.write(legacy)
        current = self.actual.load_settings(self.path)
        self.assertEqual(current['persona_mode'], 'custom')
        updated = commit_character_identity(current, 'custom', self.identity, path=self.path)
        self.assertEqual(updated['persona'], self.identity)
        self.assertEqual(updated['voice_profile'], self.default['voice_profile'])

    def test_rejects_unauthorized_streaming_flag_without_file_change(self):
        self.write(self.default)
        old = self.path.read_bytes()
        illegal = deepcopy(self.default)
        illegal['streaming_enabled'] = True
        with self.assertRaises(ValueError):
            save_broadcast_without_persona(self.default, illegal, path=self.path)
        self.assertEqual(self.path.read_bytes(), old)

    def test_external_broadcast_change_conflicts_using_real_loader(self):
        disk = deepcopy(self.default)
        disk['platforms'] = ['chzzk']
        self.write(disk)
        old = self.path.read_bytes()
        with self.assertRaises(CharacterCommitConflict):
            save_broadcast_without_persona(self.default, self.default, path=self.path)
        self.assertEqual(self.path.read_bytes(), old)

    def test_corrupt_real_settings_not_replaced(self):
        self.path.write_text('{invalid', encoding='utf-8')
        with self.assertRaises(json.JSONDecodeError):
            commit_character_identity(self.default, 'custom', self.identity, path=self.path)
        self.assertEqual(self.path.read_text(encoding='utf-8'), '{invalid')


if __name__ == '__main__':
    unittest.main()
