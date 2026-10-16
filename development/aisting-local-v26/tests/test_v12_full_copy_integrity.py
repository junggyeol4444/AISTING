"""v12 whole-copy safety checks. Synthetic fixtures, NOT actual AI/broadcast."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import apply_to_existing_aisting as patcher
import prepare_local_source_copy as copier


class FullCopyManifest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'original'
        self.source.mkdir()
        for rel in copier.REQUIRED:
            path = self.source / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('"""Existing desktop test fixture."""\n' if rel == patcher.SOURCE_REL
                            else 'existing file\n', encoding='utf-8')
        (self.source / patcher.OFFLINE_SETTINGS_REL).write_bytes((BASE / 'evidence/original_readonly/offline_settings_main_20261016.py').read_bytes())
        self.private = Path('data/memory/session.db')
        (self.source / self.private).parent.mkdir(parents=True)
        (self.source / self.private).write_bytes(b'\x00memory\x01do-not-change')
        (self.source / 'src/ai_broadcaster/old_module.py').write_text('OLD_CODE = True\n', 'utf-8')
        self.original_digest = hashlib.sha256((self.source / self.private).read_bytes()).hexdigest()
        self.copy = self.base / 'verified-copy'
        sha = patcher.git_blob_sha((self.source / patcher.SOURCE_REL).read_bytes())
        self.patchers = [
            patch.object(copier, 'BASELINE_DESKTOP_SHA', sha),
            patch.object(patcher, 'BASELINE_DESKTOP_SHA', sha),
            patch.object(patcher, 'modify_existing_desktop', side_effect=lambda s: s + '\n# local patch\n'),
        ]
        for p in self.patchers:
            p.start()
            self.addCleanup(p.stop)
        copier.prepare_copy(self.source, self.copy, write=True)

    def assert_patch_rejected_without_backup(self):
        with self.assertRaisesRegex(ValueError, '전체.*무결성|전체 기존 파일'):
            patcher.apply_existing_source(self.copy, write=True)
        self.assertFalse(list((self.copy / patcher.SOURCE_REL).parent.glob('*.bak')))
        self.assertEqual(hashlib.sha256((self.source / self.private).read_bytes()).hexdigest(),
                         self.original_digest)

    def test_manifest_contains_all_source_files_including_private_memory(self):
        record = json.loads((self.copy / copier.PROVENANCE).read_text('utf-8'))
        manifest = record['original_all_sha256']
        self.assertEqual(manifest[self.private.as_posix()], self.original_digest)
        self.assertEqual(record['all_existing_files_verified'], len(manifest))
        self.assertIn('src/ai_broadcaster/old_module.py', manifest)
        self.assertNotIn(copier.PROVENANCE, manifest)

    def test_unmodified_copy_can_still_be_patched(self):
        patcher.apply_existing_source(self.copy, write=True)
        self.assertIn('# local patch', (self.copy / patcher.SOURCE_REL).read_text('utf-8'))
        self.assertEqual((self.copy / self.private).read_bytes(),
                         (self.source / self.private).read_bytes())

    def test_readonly_preflight_verifies_whole_copy(self):
        patcher.apply_existing_source(self.copy, write=False)
        self.assertFalse(list((self.copy / patcher.SOURCE_REL).parent.glob('*.bak')))
        (self.copy / self.private).write_bytes(b'changed after copy')
        with self.assertRaisesRegex(ValueError, '전체.*무결성'):
            patcher.apply_existing_source(self.copy, write=False)

    def test_tampered_nonrequired_memory_blocks_patch(self):
        (self.copy / self.private).write_bytes(b'tampered')
        self.assert_patch_rejected_without_backup()

    def test_deleted_nonrequired_module_blocks_patch(self):
        (self.copy / 'src/ai_broadcaster/old_module.py').unlink()
        self.assert_patch_rejected_without_backup()

    def test_unrecorded_extra_file_blocks_patch(self):
        (self.copy / 'extra-not-in-original.txt').write_text('injected', 'utf-8')
        self.assert_patch_rejected_without_backup()

    def test_missing_legacy_manifest_blocks_patch(self):
        path = self.copy / copier.PROVENANCE
        record = json.loads(path.read_text('utf-8'))
        record.pop('original_all_sha256')
        path.write_text(json.dumps(record), encoding='utf-8')
        self.assert_patch_rejected_without_backup()

    def test_forged_path_traversal_in_manifest_blocks_patch(self):
        path = self.copy / copier.PROVENANCE
        record = json.loads(path.read_text('utf-8'))
        record['original_all_sha256']['../outside.txt'] = '0' * 64
        record['all_existing_files_verified'] += 1
        path.write_text(json.dumps(record), encoding='utf-8')
        self.assert_patch_rejected_without_backup()

    def test_link_in_copy_blocks_patch(self):
        try:
            (self.copy / 'link-to-outside').symlink_to(self.source)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        with self.assertRaisesRegex(ValueError, '링크/특수'):
            patcher.apply_existing_source(self.copy, write=True)
        self.assertFalse(list((self.copy / patcher.SOURCE_REL).parent.glob('*.bak')))


if __name__ == '__main__':
    unittest.main()
