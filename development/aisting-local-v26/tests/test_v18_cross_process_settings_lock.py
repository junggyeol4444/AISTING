"""Auxiliary real OS-lock tests on disposable settings, NOT AI/live verification.

Uses the same narrow offline_settings fixture as v16/v17. The actual
Windows AISTING app and full source have not been exercised here.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'payload' / 'src'))
from ai_broadcaster.original_plan_persona_store import (
    CharacterCommitConflict, _exclusive_settings_save,
    commit_character_identity, save_broadcast_without_persona,
)
import test_v17_broadcast_save_persona_isolation as v17
from test_v16_committed_persona_persistence import DEFAULT


class CrossProcessSaveLockTest(unittest.TestCase):
    """Reuse only fixture methods, without rerunning earlier tests."""
    setUp = v17.BroadcastSaveIsolationTest.setUp
    write = v17.BroadcastSaveIsolationTest.write

    def test_lock_blocks_ordinary_save_before_original_changes(self):
        self.write(DEFAULT)
        original = self.path.read_bytes()
        changed = deepcopy(DEFAULT)
        changed['content'] = 'chat'
        with _exclusive_settings_save(self.path):
            with self.assertRaisesRegex(CharacterCommitConflict, '다른 AISTING 창'):
                save_broadcast_without_persona(DEFAULT, changed)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(list(self.path.parent.glob('*.bak')))

    def test_lock_blocks_character_commit_before_original_changes(self):
        self.write(DEFAULT)
        original = self.path.read_bytes()
        with _exclusive_settings_save(self.path):
            with self.assertRaisesRegex(CharacterCommitConflict, '다른 AISTING 창'):
                commit_character_identity(DEFAULT, 'custom', self.confirmed)
        self.assertEqual(self.path.read_bytes(), original)

    def test_after_release_both_save_paths_work(self):
        self.write(DEFAULT)
        with _exclusive_settings_save(self.path):
            pass
        committed = commit_character_identity(DEFAULT, 'custom', self.confirmed)
        self.assertEqual(committed['persona'], self.confirmed)
        changed = deepcopy(committed)
        changed['content'] = 'chat'
        saved = save_broadcast_without_persona(committed, changed)
        self.assertEqual(saved['persona'], self.confirmed)
        self.assertEqual(saved['content'], 'chat')

    def test_corrupted_lock_file_is_not_overwritten(self):
        self.write(DEFAULT)
        original = self.path.read_bytes()
        lock = self.path.with_name('.settings.json.aisting-write.lock')
        lock.write_bytes(b'not a lock file')
        with self.assertRaisesRegex(CharacterCommitConflict, '잠금 파일'):
            commit_character_identity(DEFAULT, 'custom', self.confirmed)
        self.assertEqual(lock.read_bytes(), b'not a lock file')
        self.assertEqual(self.path.read_bytes(), original)

    @unittest.skipIf(os.name == 'nt', 'Windows symlink creation needs special privileges')
    def test_symlink_lock_is_rejected_without_following_it(self):
        self.write(DEFAULT)
        secret = self.path.parent / 'other.txt'
        secret.write_text('private', encoding='utf-8')
        lock = self.path.with_name('.settings.json.aisting-write.lock')
        lock.symlink_to(secret)
        with self.assertRaisesRegex(CharacterCommitConflict, '링크'):
            commit_character_identity(DEFAULT, 'custom', self.confirmed)
        self.assertEqual(secret.read_text(encoding='utf-8'), 'private')

    def test_single_byte_unrecognized_lock_is_rejected(self):
        self.write(DEFAULT)
        lock = self.path.with_name('.settings.json.aisting-write.lock')
        lock.write_bytes(b'X')
        with self.assertRaisesRegex(CharacterCommitConflict, '잠금 파일'):
            save_broadcast_without_persona(DEFAULT, DEFAULT)
        self.assertEqual(lock.read_bytes(), b'X')

    @unittest.skipIf(os.name == 'nt', 'POSIX permission bits only')
    def test_world_readable_lock_is_rejected(self):
        self.write(DEFAULT)
        lock = self.path.with_name('.settings.json.aisting-write.lock')
        lock.write_bytes(b'')
        lock.chmod(0o644)
        with self.assertRaisesRegex(CharacterCommitConflict, '권한'):
            commit_character_identity(DEFAULT, 'custom', self.confirmed)
        self.assertEqual(stat.S_IMODE(lock.stat().st_mode), 0o644)

    def test_lock_file_is_private_on_posix(self):
        self.write(DEFAULT)
        save_broadcast_without_persona(DEFAULT, DEFAULT)
        lock = self.path.with_name('.settings.json.aisting-write.lock')
        self.assertTrue(lock.is_file())
        if os.name != 'nt':
            self.assertEqual(stat.S_IMODE(lock.stat().st_mode), 0o600)

    def test_real_second_process_cannot_take_lock_until_release(self):
        self.write(DEFAULT)
        script = (
            "from pathlib import Path; import sys; "
            "sys.path.insert(0, sys.argv[2]); "
            "from ai_broadcaster.original_plan_persona_store import "
            "_exclusive_settings_save, CharacterCommitConflict; "
            "target=Path(sys.argv[1]); "
            "\ntry:\n"
            "    with _exclusive_settings_save(target): pass\n"
            "except CharacterCommitConflict:\n"
            "    sys.exit(17)\n"
        )
        cmd = [sys.executable, '-c', script, str(self.path), str(ROOT / 'payload' / 'src')]
        with _exclusive_settings_save(self.path):
            blocked = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        self.assertEqual(blocked.returncode, 17, blocked.stderr)
        released = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        self.assertEqual(released.returncode, 0, released.stderr)

    def test_contention_from_second_thread_fails_closed(self):
        self.write(DEFAULT)
        proposed = deepcopy(DEFAULT)
        proposed['content'] = 'chat'
        got = []
        with _exclusive_settings_save(self.path):
            def second_window():
                try:
                    save_broadcast_without_persona(DEFAULT, proposed)
                except CharacterCommitConflict as exc:
                    got.append(str(exc))
            thread = threading.Thread(target=second_window)
            thread.start()
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(got), 1)
        self.assertIn('다른 AISTING 창', got[0])
        self.assertEqual(self.fixture.load_settings()['content'], DEFAULT['content'])


if __name__ == '__main__':
    unittest.main()
