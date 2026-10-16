"""v19 integration of SHA-pinned REAL main offline_settings.py with v18 store.

No desktop process, network, audio, OBS, model or broadcasting is run.
The original AISTING source file is used, not a simulated settings module.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / 'evidence/original_readonly/offline_settings_main_20261016.py'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'payload/src'))
from apply_to_existing_aisting import (  # noqa: E402
    BASELINE_OFFLINE_SHA, git_blob_sha, modify_existing_offline_settings,
)
from ai_broadcaster.original_plan_persona_store import (  # noqa: E402
    CharacterCommitConflict, _exclusive_settings_save, commit_character_identity,
)


def original_and_patched_module():
    source = ORIGINAL.read_bytes()
    assert git_blob_sha(source) == BASELINE_OFFLINE_SHA
    patched = modify_existing_offline_settings(source.decode('utf-8'))
    assert patched != source.decode('utf-8')
    spec = importlib.util.spec_from_loader('ai_broadcaster.offline_settings', loader=None)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    exec(compile(patched, str(ORIGINAL), 'exec'), module.__dict__)
    return source.decode('utf-8'), patched, module


class ActualOriginalWriterV19Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'settings.json'
        self.source, self.patched, self.actual = original_and_patched_module()
        patcher = patch.dict(sys.modules, {'ai_broadcaster.offline_settings': self.actual})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.default = deepcopy(self.actual.DEFAULTS)
        self.identity = {'name': '확정 이름', 'style': '한국어', 'character': '확정 성격'}

    def test_original_main_sha_exact(self):
        self.assertEqual(git_blob_sha(ORIGINAL.read_bytes()),
                         '769ea22a59b490d9eeb27913aa569550f3b57da3')

    def test_patch_only_replaces_original_writer(self):
        prefix = self.source.split('def save_settings(', 1)[0]
        self.assertEqual(self.patched.split('def save_settings(', 1)[0], prefix)
        self.assertEqual(self.patched.count('def save_settings('), 1)

    def test_original_source_tamper_fails_closed(self):
        with self.assertRaises(ValueError):
            modify_existing_offline_settings(self.source.replace('temporary.unlink(missing_ok=True)',
                                                                  'temporary.unlink(missing_ok=False)'))

    def test_ordinary_legacy_save_preserves_confirmed_character(self):
        self.actual.save_settings(self.default, self.path)
        committed = commit_character_identity(self.default, 'custom', self.identity, path=self.path)
        stale = deepcopy(self.default)
        stale['content'] = 'chat'
        stale['persona_mode'] = 'default'
        stale['persona'] = {'name': '미확정 초안', 'style': '미확정', 'character': '미확정'}
        self.assertEqual(self.actual.save_settings(stale, self.path), self.path)
        reopened = self.actual.load_settings(self.path)
        self.assertEqual(reopened['content'], 'chat')
        self.assertEqual(reopened['persona'], committed['persona'])
        self.assertEqual(reopened['persona_mode'], 'custom')
        self.assertNotIn('미확정 초안', self.path.read_text('utf-8'))

    def test_unsaved_invalid_character_does_not_block_broadcast_save(self):
        self.actual.save_settings(self.default, self.path)
        proposed = deepcopy(self.default)
        proposed['content'] = 'chat'
        proposed['persona'] = {'unexpected': object()}
        proposed['persona_mode'] = 'invalid draft'
        self.actual.save_settings(proposed, self.path)
        saved = self.actual.load_settings(self.path)
        self.assertEqual(saved['content'], 'chat')
        self.assertEqual(saved['persona'], self.default['persona'])

    def test_first_save_cannot_confirm_character(self):
        proposed = deepcopy(self.default)
        proposed['persona_mode'] = 'custom'
        proposed['persona'] = self.identity
        self.actual.save_settings(proposed, self.path)
        reopened = self.actual.load_settings(self.path)
        self.assertEqual(reopened['persona_mode'], 'default')
        self.assertEqual(reopened['persona'], self.default['persona'])

    def test_existing_legacy_custom_character_preserved(self):
        old = deepcopy(self.default)
        old['persona'] = self.identity
        old.pop('persona_mode')
        old.pop('voice_profile')
        self.path.write_text(json.dumps(old, ensure_ascii=False), encoding='utf-8')
        update = deepcopy(self.default)
        update['content'] = 'chat'
        self.actual.save_settings(update, self.path)
        reopened = self.actual.load_settings(self.path)
        self.assertEqual(reopened['persona'], self.identity)
        self.assertEqual(reopened['persona_mode'], 'custom')
        self.assertEqual(reopened['content'], 'chat')

    def test_lock_competition_blocks_legacy_writer(self):
        self.actual.save_settings(self.default, self.path)
        original = self.path.read_bytes()
        changed = deepcopy(self.default)
        changed['content'] = 'chat'
        with _exclusive_settings_save(self.path):
            with self.assertRaises(CharacterCommitConflict):
                self.actual.save_settings(changed, self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_original_settings_backup_is_exact_and_private(self):
        self.actual.save_settings(self.default, self.path)
        before = self.path.read_bytes()
        changed = deepcopy(self.default)
        changed['content'] = 'chat'
        self.actual.save_settings(changed, self.path)
        backups = list(self.path.parent.glob('settings.json.before-broadcast-*.bak'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before)
        if sys.platform != 'win32':
            self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)

    def test_unauthorized_streaming_flag_rejected_without_change(self):
        self.actual.save_settings(self.default, self.path)
        before = self.path.read_bytes()
        changed = deepcopy(self.default)
        changed['streaming_enabled'] = True
        with self.assertRaises(ValueError):
            self.actual.save_settings(changed, self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_corrupt_settings_not_overwritten(self):
        self.path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(json.JSONDecodeError):
            self.actual.save_settings(self.default, self.path)
        self.assertEqual(self.path.read_text('utf-8'), '{broken')

    def test_symlink_settings_path_refused(self):
        if not hasattr(self.path, 'symlink_to'):
            self.skipTest('symlink unsupported')
        target = Path(self.temp.name) / 'other.json'
        target.write_text('sensitive', encoding='utf-8')
        try:
            self.path.symlink_to(target)
        except OSError:
            self.skipTest('symlink creation unavailable')
        with self.assertRaises((CharacterCommitConflict, ValueError, json.JSONDecodeError)):
            self.actual.save_settings(self.default, self.path)
        self.assertEqual(target.read_text('utf-8'), 'sensitive')


if __name__ == '__main__':
    unittest.main()
