"""Synthetic TREE tests of v19's two-file patch; offline_settings is REAL main source.

The desktop stub is not the user's real desktop. These tests prove only
local patcher transaction and SHA-based preservation, never live functionality.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import apply_to_existing_aisting as patcher
import prepare_local_source_copy as copier
import audit_local_patch_preservation as audit

ACTUAL_SETTINGS = ROOT / 'evidence/original_readonly/offline_settings_main_20261016.py'


class TwoExistingFilesPatchSafety(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.original = self.base / 'existing-source'
        self.original.mkdir()
        for rel in copier.REQUIRED:
            path = self.original / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if rel == patcher.SOURCE_REL:
                path.write_text('"""desktop test-only stub"""\n', encoding='utf-8')
            elif rel.as_posix() == 'config/roadmap.json':
                path.write_text(json.dumps({'steps': list(range(100))}), encoding='utf-8')
            else:
                path.write_text('existing file for copy-safety test\n', encoding='utf-8')
        (self.original / patcher.OFFLINE_SETTINGS_REL).write_bytes(ACTUAL_SETTINGS.read_bytes())
        self.memory = self.original / 'data/private_memory.bin'
        self.memory.parent.mkdir()
        self.memory.write_bytes(b'unchanged user memory')
        self.copy = self.base / 'private-copy'
        desktop_sha = patcher.git_blob_sha((self.original / patcher.SOURCE_REL).read_bytes())
        for hook in (
            patch.object(patcher, 'BASELINE_DESKTOP_SHA', desktop_sha),
            patch.object(copier, 'BASELINE_DESKTOP_SHA', desktop_sha),
            patch.object(audit, 'BASELINE_DESKTOP_SHA', desktop_sha),
            patch.object(patcher, 'modify_existing_desktop', side_effect=lambda s: s + '# v19 only\n'),
            patch.object(audit, 'modify_existing_desktop', side_effect=lambda s: s + '# v19 only\n'),
        ):
            hook.start()
            self.addCleanup(hook.stop)
        copier.prepare_copy(self.original, self.copy, write=True)

    def test_applies_both_existing_files_without_touching_original(self):
        patcher.apply_existing_source(self.copy, write=True)
        self.assertEqual((self.original / patcher.OFFLINE_SETTINGS_REL).read_bytes(), ACTUAL_SETTINGS.read_bytes())
        self.assertEqual((self.original / self.memory.relative_to(self.original)).read_bytes(), b'unchanged user memory')
        self.assertEqual((self.copy / self.memory.relative_to(self.original)).read_bytes(), b'unchanged user memory')
        self.assertNotEqual((self.copy / patcher.OFFLINE_SETTINGS_REL).read_bytes(), ACTUAL_SETTINGS.read_bytes())
        report = audit.audit_applied_copy(self.copy)
        self.assertTrue(report['offline_settings_patch_exact_match'])
        self.assertTrue(report['original_offline_settings_backup_verified'])
        self.assertFalse(report['real_ai_tts_live2d_obs_verified'])

    def test_second_source_replace_failure_restores_first_source(self):
        before_offline = (self.copy / patcher.OFFLINE_SETTINGS_REL).read_bytes()
        before_desktop = (self.copy / patcher.SOURCE_REL).read_bytes()
        real_replace = patcher.os.replace
        calls = 0

        def fail_second(src, dst):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('injected second-file replace failure')
            return real_replace(src, dst)

        with patch.object(patcher.os, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'second-file'):
                patcher.apply_existing_source(self.copy, write=True)
        self.assertGreaterEqual(calls, 3)  # restore must have run
        self.assertEqual((self.copy / patcher.OFFLINE_SETTINGS_REL).read_bytes(), before_offline)
        self.assertEqual((self.copy / patcher.SOURCE_REL).read_bytes(), before_desktop)
        for module in (patcher.MODULE_REL, *patcher.EXTRA_MODULES):
            self.assertFalse((self.copy / module).exists())

    def test_tampered_offline_source_refused_before_backups(self):
        (self.copy / patcher.OFFLINE_SETTINGS_REL).write_text('tampered', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'offline_settings.py 원본 SHA'):
            patcher.apply_existing_source(self.copy, write=True)
        self.assertEqual(list((self.copy / patcher.SOURCE_REL).parent.glob('*.bak')), [])

    def test_audit_rejects_changed_offline_source(self):
        patcher.apply_existing_source(self.copy, write=True)
        (self.copy / patcher.OFFLINE_SETTINGS_REL).write_text('tampered', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '수정된 소스'):
            audit.audit_applied_copy(self.copy)

    def test_audit_rejects_corrupted_offline_backup(self):
        patcher.apply_existing_source(self.copy, write=True)
        backup = next((self.copy / patcher.OFFLINE_SETTINGS_REL).parent.glob('offline_settings.py.before-original-plan-*.bak'))
        backup.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, '원본 백업'):
            audit.audit_applied_copy(self.copy)


if __name__ == '__main__':
    unittest.main()
