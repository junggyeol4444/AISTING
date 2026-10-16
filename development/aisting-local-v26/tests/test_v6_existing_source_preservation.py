"""Offline file-safety regression checks. Synthetic fixture, NOT full original app."""
from __future__ import annotations

from pathlib import Path
import json
import os
import stat
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import apply_to_existing_aisting as patcher
import prepare_local_source_copy as copier


def source_fixture(root: Path) -> None:
    for rel in copier.REQUIRED:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel == patcher.SOURCE_REL:
            path.write_text('"""Existing AISTING desktop stub for file-safety test only."""\n', 'utf8')
        elif str(rel) == 'config/roadmap.json':
            path.write_text(json.dumps({'steps': [{'id': i} for i in range(1, 101)]}), 'utf8')
        else:
            path.write_text('original existing source placeholder\n', 'utf8')
    (root / patcher.OFFLINE_SETTINGS_REL).write_bytes((BASE / 'evidence/original_readonly/offline_settings_main_20261016.py').read_bytes())
    (root / 'private-user-settings.json').write_text('{"character":"saved"}', 'utf8')
    (root / '.git').mkdir()
    (root / '.git/config').write_text('existing git metadata', 'utf8')


class ExistingSourcePreservation(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / 'existing-original'
        self.source.mkdir()
        source_fixture(self.source)
        self.copy = self.base / 'local-work-copy'
        self.blob = patcher.git_blob_sha((self.source / patcher.SOURCE_REL).read_bytes())

    def test_preview_does_not_write_or_modify_user_source(self):
        with patch.object(copier, 'BASELINE_DESKTOP_SHA', self.blob):
            self.assertEqual(copier.prepare_copy(self.source, self.copy), self.copy)
        self.assertFalse(self.copy.exists())
        self.assertEqual((self.source / 'private-user-settings.json').read_text('utf8'), '{"character":"saved"}')

    def test_copy_preserves_existing_data_and_100_step_record_without_git_metadata(self):
        with patch.object(copier, 'BASELINE_DESKTOP_SHA', self.blob):
            copier.prepare_copy(self.source, self.copy, write=True)
        self.assertEqual((self.copy / 'private-user-settings.json').read_bytes(),
                         (self.source / 'private-user-settings.json').read_bytes())
        self.assertEqual((self.copy / 'config/roadmap.json').read_bytes(),
                         (self.source / 'config/roadmap.json').read_bytes())
        self.assertFalse((self.copy / '.git').exists())
        self.assertEqual((self.source / '.git/config').read_text('utf8'), 'existing git metadata')
        self.assertEqual(json.loads((self.copy / copier.PROVENANCE).read_text('utf8'))['desktop_git_blob_sha'], self.blob)
        if os.name != 'nt':
            self.assertEqual(stat.S_IMODE(self.copy.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((self.copy / copier.PROVENANCE).stat().st_mode), 0o600)
        with patch.object(copier, 'BASELINE_DESKTOP_SHA', self.blob):
            with self.assertRaises(ValueError):
                copier.prepare_copy(self.source, self.copy, write=True)

    def test_copy_rejects_external_symlink_before_writing(self):
        try:
            (self.source / 'unsafe-link').symlink_to(self.base)
        except (OSError, NotImplementedError):
            self.skipTest('symlink unavailable')
        with patch.object(copier, 'BASELINE_DESKTOP_SHA', self.blob):
            with self.assertRaisesRegex(ValueError, '링크'):
                copier.prepare_copy(self.source, self.copy, write=True)
        self.assertFalse(self.copy.exists())

    def test_corrupted_user_data_copy_is_detected_and_removed(self):
        real_copy = copier._copy_exact_inventory
        def damage_copy(*args, **kwargs):
            result = real_copy(*args, **kwargs)
            (self.copy / 'private-user-settings.json').write_text('CORRUPTED', 'utf8')
            return result
        with patch.object(copier, 'BASELINE_DESKTOP_SHA', self.blob), \
             patch.object(copier, '_copy_exact_inventory', side_effect=damage_copy):
            with self.assertRaisesRegex(RuntimeError, '무결성'):
                copier.prepare_copy(self.source, self.copy, write=True)
        self.assertFalse(self.copy.exists())
        self.assertEqual((self.source / 'private-user-settings.json').read_text('utf8'), '{"character":"saved"}')

    def test_apply_to_copy_preserves_original_and_private_backup(self):
        with patch.object(copier, 'BASELINE_DESKTOP_SHA', self.blob):
            copier.prepare_copy(self.source, self.copy, write=True)
        with patch.object(patcher, 'BASELINE_DESKTOP_SHA', self.blob), \
             patch.object(patcher, 'modify_existing_desktop', side_effect=lambda text: text + '\n# local patch\n'):
            patcher.apply_existing_source(self.copy, write=False)
            self.assertFalse((self.copy / patcher.MODULE_REL).exists())
            patcher.apply_existing_source(self.copy, write=True)
        self.assertNotIn('local patch', (self.source / patcher.SOURCE_REL).read_text('utf8'))
        self.assertIn('local patch', (self.copy / patcher.SOURCE_REL).read_text('utf8'))
        self.assertEqual((self.copy / 'private-user-settings.json').read_bytes(),
                         (self.source / 'private-user-settings.json').read_bytes())
        backups = list((self.copy / patcher.SOURCE_REL).parent.glob('desktop.py.before-original-plan-*.bak'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), (self.source / patcher.SOURCE_REL).read_bytes())
        if os.name != 'nt':
            self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
        for rel in (patcher.MODULE_REL, *patcher.EXTRA_MODULES):
            self.assertTrue((self.copy / rel).is_file())

    def test_failed_final_replace_rolls_back_new_modules_and_original_desktop(self):
        with patch.object(copier, 'BASELINE_DESKTOP_SHA', self.blob):
            copier.prepare_copy(self.source, self.copy, write=True)
        original = (self.copy / patcher.SOURCE_REL).read_bytes()
        with patch.object(patcher, 'BASELINE_DESKTOP_SHA', self.blob), \
             patch.object(patcher, 'modify_existing_desktop', side_effect=lambda text: text + '\n# local patch\n'), \
             patch.object(patcher.os, 'replace', side_effect=OSError('injected local write failure')):
            with self.assertRaises(OSError):
                patcher.apply_existing_source(self.copy, write=True)
        self.assertEqual((self.copy / patcher.SOURCE_REL).read_bytes(), original)
        for rel in (patcher.MODULE_REL, *patcher.EXTRA_MODULES):
            self.assertFalse((self.copy / rel).exists())


if __name__ == '__main__':
    main()
