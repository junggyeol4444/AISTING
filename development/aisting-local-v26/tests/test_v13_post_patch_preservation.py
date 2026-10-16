"""Read-only post-apply preservation checks on SYNTHETIC fixtures only."""
from __future__ import annotations

import hashlib
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


class PostPatchAudit(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / 'existing'
        self.original.mkdir()
        for rel in copier.REQUIRED:
            f = self.original / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text('"""existing program"""\n' if rel == patcher.SOURCE_REL else 'preserve this\n', 'utf-8')
        (self.original / patcher.OFFLINE_SETTINGS_REL).write_bytes((BASE / 'evidence/original_readonly/offline_settings_main_20261016.py').read_bytes())
        self.private = Path('data/private_memory.db')
        (self.original / self.private).parent.mkdir()
        (self.original / self.private).write_bytes(b'original memory contents')
        self.copy = self.root / 'copy'
        self.sha = patcher.git_blob_sha((self.original / patcher.SOURCE_REL).read_bytes())
        self.hooks = [
            patch.object(copier, 'BASELINE_DESKTOP_SHA', self.sha),
            patch.object(patcher, 'BASELINE_DESKTOP_SHA', self.sha),
            patch.object(audit, 'BASELINE_DESKTOP_SHA', self.sha),
            patch.object(patcher, 'modify_existing_desktop', side_effect=lambda s: s + '# changed locally\n'),
            patch.object(audit, 'modify_existing_desktop', side_effect=lambda s: s + '# changed locally\n'),
        ]
        for hook in self.hooks:
            hook.start(); self.addCleanup(hook.stop)
        copier.prepare_copy(self.original, self.copy, write=True)
        patcher.apply_existing_source(self.copy, write=True)

    def test_valid_applied_copy_passes_and_does_not_write(self):
        before = {p.relative_to(self.copy).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.copy.rglob('*') if p.is_file()}
        result = audit.audit_applied_copy(self.copy)
        self.assertEqual(result['integration_modules_verified'], len(audit.MODULES))
        self.assertTrue(result['original_desktop_backup_verified'])
        self.assertFalse(result['real_ai_tts_live2d_obs_verified'])
        self.assertEqual(before, {p.relative_to(self.copy).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in self.copy.rglob('*') if p.is_file()})

    def test_user_memory_mutation_detected(self):
        (self.copy / self.private).write_bytes(b'changed memory')
        with self.assertRaisesRegex(ValueError, '기존 파일이 변경'):
            audit.audit_applied_copy(self.copy)

    def test_roadmap_mutation_detected(self):
        (self.copy / 'config/roadmap.json').write_text('changed', 'utf-8')
        with self.assertRaisesRegex(ValueError, '기존 파일이 변경'):
            audit.audit_applied_copy(self.copy)

    def test_modified_integration_module_detected(self):
        (self.copy / audit.MODULES[0]).write_bytes(b'fake replacement')
        with self.assertRaisesRegex(ValueError, '연결 모듈'):
            audit.audit_applied_copy(self.copy)

    def test_tampered_desktop_detected(self):
        (self.copy / patcher.SOURCE_REL).write_bytes(b'fake desktop')
        with self.assertRaisesRegex(ValueError, '수정된 소스'):
            audit.audit_applied_copy(self.copy)

    def test_corrupted_backup_detected(self):
        backup = next((self.copy / patcher.SOURCE_REL).parent.glob('*.bak'))
        backup.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, '백업'):
            audit.audit_applied_copy(self.copy)

    def test_unexpected_extra_file_detected(self):
        (self.copy / 'unapproved_file.txt').write_text('extra', 'utf-8')
        with self.assertRaisesRegex(ValueError, '누락/추가'):
            audit.audit_applied_copy(self.copy)

    def test_missing_existing_file_detected(self):
        (self.copy / self.private).unlink()
        with self.assertRaisesRegex(ValueError, '누락/추가'):
            audit.audit_applied_copy(self.copy)

    def test_missing_module_detected(self):
        (self.copy / audit.MODULES[-1]).unlink()
        with self.assertRaisesRegex(ValueError, '누락/추가'):
            audit.audit_applied_copy(self.copy)

    def test_symlink_detected(self):
        link = self.copy / 'new_link'
        try:
            link.symlink_to(self.original)
        except (OSError, NotImplementedError):
            self.skipTest('symlink unavailable')
        with self.assertRaisesRegex(ValueError, '링크'):
            audit.audit_applied_copy(self.copy)


if __name__ == '__main__':
    unittest.main()
