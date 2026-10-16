"""Auxiliary file-level checks only. Real existing AISTING GUI integration pending."""
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
    save_broadcast_without_persona, CharacterCommitConflict,
)
from test_v16_committed_persona_persistence import DEFAULT, fixture_validate


class BroadcastSaveIsolationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'settings.json'
        self.fixture = types.ModuleType('ai_broadcaster.offline_settings')
        self.fixture.validate_settings = fixture_validate
        self.fixture.settings_file = lambda: self.path
        self.fixture.load_settings = lambda path=None: fixture_validate(json.loads(
            (path or self.path).read_text(encoding='utf-8')))
        module_patch = patch.dict(sys.modules, {'ai_broadcaster.offline_settings': self.fixture})
        module_patch.start()
        self.addCleanup(module_patch.stop)
        self.confirmed = {'name': '확정된 이름', 'style': '확정된 말투', 'character': '확정된 성격'}
        self.draft = {'name': '미저장 초안', 'style': '미저장 말투', 'character': '미저장 성격'}

    def write(self, value):
        self.path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def test_ordinary_save_discards_unconfirmed_editor_persona(self):
        self.write(DEFAULT)
        proposed = deepcopy(DEFAULT)
        proposed['content'] = 'chat'
        proposed['persona_mode'] = 'custom'
        proposed['persona'] = self.draft
        result = save_broadcast_without_persona(DEFAULT, proposed)
        self.assertEqual(result['content'], 'chat')
        self.assertEqual(result['persona_mode'], DEFAULT['persona_mode'])
        self.assertEqual(self.fixture.load_settings()['persona'], DEFAULT['persona'])
        self.assertNotIn('미저장 초안', self.path.read_text(encoding='utf-8'))

    def test_newer_confirmed_character_is_preserved_from_disk(self):
        disk = deepcopy(DEFAULT)
        disk['persona_mode'] = 'custom'
        disk['persona'] = self.confirmed
        self.write(disk)
        proposed = deepcopy(DEFAULT)
        proposed['avatar'] = 'undecided'
        proposed['content'] = 'chat'
        proposed['persona'] = self.draft
        result = save_broadcast_without_persona(DEFAULT, proposed)
        self.assertEqual(result['persona'], self.confirmed)
        self.assertEqual(result['persona_mode'], 'custom')
        self.assertEqual(self.fixture.load_settings()['content'], 'chat')
        self.assertNotIn('미저장 초안', self.path.read_text(encoding='utf-8'))

    def test_newer_broadcast_change_conflicts_instead_of_overwriting(self):
        disk = deepcopy(DEFAULT)
        disk['content'] = 'chat'
        self.write(disk)
        before = self.path.read_bytes()
        with self.assertRaises(CharacterCommitConflict):
            save_broadcast_without_persona(DEFAULT, DEFAULT)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob('*.bak')), [])

    def test_backup_contains_exact_original_before_broadcast_save(self):
        self.write(DEFAULT)
        before = self.path.read_bytes()
        proposed = deepcopy(DEFAULT)
        proposed['content'] = 'chat'
        save_broadcast_without_persona(DEFAULT, proposed)
        backups = list(self.path.parent.glob('settings.json.before-broadcast-*.bak'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before)
        if os.name != 'nt':
            self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)

    def test_no_change_does_not_rewrite_or_create_backup(self):
        self.write(DEFAULT)
        before = self.path.read_bytes()
        mtime = self.path.stat().st_mtime_ns
        save_broadcast_without_persona(DEFAULT, DEFAULT)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.path.stat().st_mtime_ns, mtime)
        self.assertFalse(list(self.path.parent.glob('*.bak')))

    def test_corrupt_existing_file_is_not_overwritten(self):
        self.path.write_text('{broken', encoding='utf-8')
        proposed = deepcopy(DEFAULT)
        proposed['content'] = 'chat'
        with self.assertRaises(json.JSONDecodeError):
            save_broadcast_without_persona(DEFAULT, proposed)
        self.assertEqual(self.path.read_text(encoding='utf-8'), '{broken')

    def test_replace_failure_leaves_original_and_verified_backup(self):
        self.write(DEFAULT)
        before = self.path.read_bytes()
        proposed = deepcopy(DEFAULT)
        proposed['content'] = 'chat'
        with patch('ai_broadcaster.original_plan_persona_store.os.replace',
                   side_effect=OSError('injected failure')):
            with self.assertRaises(OSError):
                save_broadcast_without_persona(DEFAULT, proposed)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(list(self.path.parent.glob('*.before-broadcast-*.bak'))), 1)
        self.assertFalse(list(self.path.parent.glob('*.tmp')))

    def test_missing_settings_starts_with_confirmed_in_memory_identity(self):
        committed = deepcopy(DEFAULT)
        committed['persona_mode'] = 'custom'
        committed['persona'] = self.confirmed
        proposed = deepcopy(DEFAULT)
        proposed['persona'] = self.draft
        proposed['content'] = 'chat'
        result = save_broadcast_without_persona(committed, proposed)
        self.assertEqual(result['persona'], self.confirmed)
        self.assertEqual(self.fixture.load_settings()['persona'], self.confirmed)


if __name__ == '__main__':
    unittest.main()
