"""Auxiliary file-level tests; NOT a real AISTING GUI or AI/voice test.

The baseline offline_settings module is not bundled in the revision-only ZIP.
A narrow validator/loader fixture is used here; actual baseline integration
must be retested once the complete existing source is locally available.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'payload' / 'src'))
from ai_broadcaster.original_plan_persona_store import (
    CharacterCommitConflict, commit_character_identity,
)

DEFAULT = {
    'platforms': [], 'content': 'undecided', 'avatar': 'undecided',
    'voice': 'undecided', 'voice_profile': {'installed_voice_name': '', 'rate': 0, 'volume': 85},
    'persona_mode': 'default',
    'persona': {'name': '아이스팅', 'style': '친근하고 명확한 한국어',
                'character': '호기심 많은 AI 방송인'},
    'host': 'local_pc', 'budget': 'free_only', 'streaming_enabled': False,
    'scheduled_execution': False, 'external_publish_enabled': False,
}


def fixture_validate(value):
    if not isinstance(value, dict) or set(value) != set(DEFAULT):
        raise ValueError('설정 필드 구성 오류')
    if value['persona_mode'] not in ('default', 'custom'):
        raise ValueError('모드 오류')
    if (not isinstance(value['persona'], dict) or
            set(value['persona']) != {'name', 'style', 'character'}):
        raise ValueError('캐릭터 형식 오류')
    if any(not isinstance(x, str) or not 1 <= len(x.strip()) <= 200
           for x in value['persona'].values()):
        raise ValueError('캐릭터 문자열 오류')
    return deepcopy(value)


class CharacterCommitFileTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'settings.json'
        self.fixture = types.ModuleType('ai_broadcaster.offline_settings')
        self.fixture.validate_settings = fixture_validate
        self.fixture.settings_file = lambda: self.path
        self.fixture.load_settings = lambda path=None: fixture_validate(json.loads(
            (path or self.path).read_text(encoding='utf-8')))
        patcher = patch.dict(sys.modules, {'ai_broadcaster.offline_settings': self.fixture})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.saved = {'name': '확정된 이름', 'style': '한국어 말투', 'character': '차분한 성격'}

    def write(self, value):
        self.path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def test_first_explicit_commit_persists_for_next_read(self):
        committed = commit_character_identity(DEFAULT, 'custom', self.saved)
        self.assertEqual(committed['persona'], self.saved)
        self.assertEqual(self.fixture.load_settings()['persona'], self.saved)
        self.assertEqual(self.fixture.load_settings()['persona_mode'], 'custom')

    def test_preserves_newer_non_character_disk_settings(self):
        disk = deepcopy(DEFAULT)
        disk['platforms'] = ['chzzk']
        disk['content'] = 'chat'
        self.write(disk)
        old = self.path.read_bytes()
        result = commit_character_identity(DEFAULT, 'custom', self.saved)
        self.assertEqual(result['platforms'], ['chzzk'])
        self.assertEqual(result['content'], 'chat')
        self.assertEqual(self.fixture.load_settings()['persona'], self.saved)
        backups = list(self.root.glob('settings.json.before-character-*.bak'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), old)
        if os.name != 'nt':
            self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)

    def test_repeated_confirmation_does_not_rewrite(self):
        self.write({**DEFAULT, 'persona_mode': 'custom', 'persona': self.saved})
        before = self.path.read_bytes()
        stamp = self.path.stat().st_mtime_ns
        commit_character_identity(DEFAULT, 'custom', self.saved)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.path.stat().st_mtime_ns, stamp)
        self.assertEqual(list(self.root.glob('*.bak')), [])

    def test_unconfirmed_draft_never_persists_without_commit(self):
        self.write(DEFAULT)
        _draft = self.saved
        self.assertEqual(self.fixture.load_settings()['persona'], DEFAULT['persona'])
        self.assertEqual(self.path.read_text(encoding='utf-8').count('확정된 이름'), 0)

    def test_invalid_character_does_not_change_disk(self):
        self.write(DEFAULT)
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            commit_character_identity(DEFAULT, 'custom', {**self.saved, 'name': ''})
        self.assertEqual(self.path.read_bytes(), before)

    def test_symlinked_settings_file_is_refused(self):
        other = self.root / 'other.json'
        other.write_text('private', encoding='utf-8')
        try:
            self.path.symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        with self.assertRaises(CharacterCommitConflict):
            commit_character_identity(DEFAULT, 'custom', self.saved)
        self.assertEqual(other.read_text(encoding='utf-8'), 'private')

    def test_replace_failure_preserves_original_and_backup(self):
        self.write(DEFAULT)
        before = self.path.read_bytes()
        with patch('ai_broadcaster.original_plan_persona_store.os.replace',
                   side_effect=OSError('injected write failure')):
            with self.assertRaises(OSError):
                commit_character_identity(DEFAULT, 'custom', self.saved)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(list(self.root.glob('settings.json.before-character-*.bak'))), 1)
        self.assertEqual(list(self.root.glob('.settings.json.*.tmp')), [])

    def test_corrupt_existing_json_is_never_overwritten(self):
        self.path.write_bytes(b'not-json')
        with self.assertRaises(json.JSONDecodeError):
            commit_character_identity(DEFAULT, 'custom', self.saved)
        self.assertEqual(self.path.read_bytes(), b'not-json')


if __name__ == '__main__':
    unittest.main()
