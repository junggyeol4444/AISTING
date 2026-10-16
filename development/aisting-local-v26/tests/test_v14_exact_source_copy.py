"""v14 copy-integrity regressions on synthetic local fixtures; NOT live AI tests."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import apply_to_existing_aisting as patcher
import prepare_local_source_copy as copier
import audit_local_patch_preservation as audit


class ExactSourceCopyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.original = self.base / 'original-existing'
        self.original.mkdir()
        for rel in copier.REQUIRED:
            file = self.original / rel
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('"""existing AISTING"""\n' if rel == patcher.SOURCE_REL else 'existing\n', 'utf-8')
        (self.original / patcher.OFFLINE_SETTINGS_REL).write_bytes((BASE / 'evidence/original_readonly/offline_settings_main_20261016.py').read_bytes())
        self.empty = Path('data/empty-user-folder')
        (self.original / self.empty).mkdir(parents=True)
        self.secret = Path('data/character-confirmed.json')
        (self.original / self.secret).write_bytes(b'{"confirmed":"existing"}')
        self.copy = self.base / 'copy'
        self.sha = patcher.git_blob_sha((self.original / patcher.SOURCE_REL).read_bytes())
        for hook in (
            patch.object(copier, 'BASELINE_DESKTOP_SHA', self.sha),
            patch.object(patcher, 'BASELINE_DESKTOP_SHA', self.sha),
            patch.object(audit, 'BASELINE_DESKTOP_SHA', self.sha),
            patch.object(patcher, 'modify_existing_desktop', side_effect=lambda text: text + '# local change\n'),
            patch.object(audit, 'modify_existing_desktop', side_effect=lambda text: text + '# local change\n'),
        ):
            hook.start()
            self.addCleanup(hook.stop)

    def _prepare(self):
        copier.prepare_copy(self.original, self.copy, write=True)

    def test_exact_copy_keeps_empty_user_folder_and_contents(self):
        self._prepare()
        self.assertTrue((self.copy / self.empty).is_dir())
        self.assertEqual((self.copy / self.secret).read_bytes(), (self.original / self.secret).read_bytes())
        proof = json.loads((self.copy / copier.PROVENANCE).read_text('utf-8'))
        self.assertIn(self.empty.as_posix(), proof['original_all_directories'])
        self.assertEqual(proof['all_existing_directories_verified'], len(proof['original_all_directories']))
        self.assertFalse((self.original / copier.PROVENANCE).exists())

    def test_new_empty_folder_before_patch_rejected(self):
        self._prepare()
        (self.copy / 'data/new-unapproved-empty').mkdir()
        with self.assertRaisesRegex(ValueError, '폴더 목록'):
            patcher.require_verified_local_copy(self.copy, (self.copy / patcher.SOURCE_REL).read_bytes())

    def test_deleted_empty_folder_before_patch_rejected(self):
        self._prepare()
        (self.copy / self.empty).rmdir()
        with self.assertRaisesRegex(ValueError, '폴더 목록'):
            patcher.require_verified_local_copy(self.copy, (self.copy / patcher.SOURCE_REL).read_bytes())

    def test_empty_folder_removed_after_patch_rejected_by_audit(self):
        self._prepare()
        patcher.apply_existing_source(self.copy, write=True)
        (self.copy / self.empty).rmdir()
        with self.assertRaisesRegex(ValueError, '폴더 구조'):
            audit.audit_applied_copy(self.copy)

    def test_old_provenance_without_directory_manifest_rejected(self):
        self._prepare()
        marker = self.copy / copier.PROVENANCE
        data = json.loads(marker.read_text('utf-8'))
        data.pop('original_all_directories')
        marker.write_text(json.dumps(data), 'utf-8')
        with self.assertRaisesRegex(ValueError, '폴더 기록'):
            patcher.require_verified_local_copy(self.copy, (self.copy / patcher.SOURCE_REL).read_bytes())

    def test_symlink_swapped_after_inventory_cannot_be_copied(self):
        if os.name != 'posix':
            self.skipTest('POSIX O_NOFOLLOW test')
        outside = self.base / 'outside-sensitive'
        outside.write_bytes(b'never-read-outside')
        original_copy = copier._copy_exact_inventory
        def switch_file(root, target, files, dirs):
            (root / self.secret).unlink()
            (root / self.secret).symlink_to(outside)
            return original_copy(root, target, files, dirs)
        with patch.object(copier, '_copy_exact_inventory', side_effect=switch_file):
            with self.assertRaises(OSError):
                self._prepare()
        self.assertFalse(self.copy.exists())
        self.assertEqual(outside.read_bytes(), b'never-read-outside')

    def test_failed_copy_cleans_read_only_directory(self):
        if os.name != 'posix':
            self.skipTest('POSIX permissions test')
        restricted = self.original / 'data/readonly'
        restricted.mkdir()
        (restricted / 'memory.txt').write_text('preserve', 'utf-8')
        restricted.chmod(0o500)
        self.addCleanup(lambda: restricted.chmod(0o700) if restricted.exists() else None)
        original_check = copier._check_source
        def fail_after_copy(path):
            if Path(path) == self.copy:
                raise RuntimeError('synthetic post-copy verification failure')
            return original_check(path)
        with patch.object(copier, '_check_source', side_effect=fail_after_copy):
            with self.assertRaisesRegex(RuntimeError, 'synthetic post-copy'):
                self._prepare()
        self.assertFalse(self.copy.exists())
        self.assertEqual((restricted / 'memory.txt').read_text('utf-8'), 'preserve')

    def test_tampered_directory_provenance_rejected(self):
        self._prepare()
        marker = self.copy / copier.PROVENANCE
        data = json.loads(marker.read_text('utf-8'))
        data['original_all_directories'].append('../outside')
        data['all_existing_directories_verified'] += 1
        marker.write_text(json.dumps(data), 'utf-8')
        with self.assertRaisesRegex(ValueError, '폴더 기록 형식'):
            patcher.require_verified_local_copy(self.copy, (self.copy / patcher.SOURCE_REL).read_bytes())


if __name__ == '__main__':
    unittest.main()
