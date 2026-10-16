"""Guard against patching the original checkout; file safety only, NOT live verification."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import apply_to_existing_aisting as patcher
import prepare_local_source_copy as copier


def source_fixture(root: Path):
    for rel in copier.REQUIRED:
        file = root / rel
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("'''existing source file'''\n" if rel == patcher.SOURCE_REL else 'existing source file\n', encoding='utf8')
    (root / patcher.OFFLINE_SETTINGS_REL).write_bytes((BASE / 'evidence/original_readonly/offline_settings_main_20261016.py').read_bytes())


class OnlyVerifiedCopyCanBePatched(TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.original = self.base / 'original'
        self.original.mkdir()
        source_fixture(self.original)
        self.copy = self.base / 'copy'
        self.blob = patcher.git_blob_sha((self.original / patcher.SOURCE_REL).read_bytes())
        self.patches = (
            patch.object(patcher, 'BASELINE_DESKTOP_SHA', self.blob),
            patch.object(copier, 'BASELINE_DESKTOP_SHA', self.blob),
            patch.object(patcher, 'modify_existing_desktop', side_effect=lambda text: text + '# v7\n'),
        )
        for obj in self.patches:
            obj.start()
            self.addCleanup(obj.stop)

    def test_original_checkout_cannot_be_patched_even_with_matching_sha(self):
        before = (self.original / patcher.SOURCE_REL).read_bytes()
        with self.assertRaisesRegex(ValueError, '기존 원본 직접 패치'):
            patcher.apply_existing_source(self.original, write=True)
        self.assertEqual((self.original / patcher.SOURCE_REL).read_bytes(), before)
        self.assertEqual(list((self.original / patcher.SOURCE_REL).parent.glob('*.bak')), [])

    def test_valid_copy_can_be_patched_and_original_remains_unchanged(self):
        copier.prepare_copy(self.original, self.copy, write=True)
        patcher.apply_existing_source(self.copy, write=True)
        self.assertIn('# v7', (self.copy / patcher.SOURCE_REL).read_text('utf8'))
        self.assertNotIn('# v7', (self.original / patcher.SOURCE_REL).read_text('utf8'))

    def test_tampered_plan_blocks_patch_before_backup(self):
        copier.prepare_copy(self.original, self.copy, write=True)
        (self.copy / 'docs/ORIGINAL_PLAN.txt').write_text('tampered\n', 'utf8')
        with self.assertRaisesRegex(ValueError, '무결성 불일치'):
            patcher.apply_existing_source(self.copy, write=True)
        self.assertFalse(list((self.copy / patcher.SOURCE_REL).parent.glob('*.bak')))

    def test_tampered_copy_marker_blocks_patch(self):
        copier.prepare_copy(self.original, self.copy, write=True)
        marker = self.copy / copier.PROVENANCE
        record = json.loads(marker.read_text('utf8'))
        record['desktop_git_blob_sha'] = '0' * 40
        marker.write_text(json.dumps(record), encoding='utf8')
        with self.assertRaisesRegex(ValueError, '원본 버전'):
            patcher.apply_existing_source(self.copy, write=True)

    def test_git_checkout_like_copy_blocks_patch(self):
        copier.prepare_copy(self.original, self.copy, write=True)
        (self.copy / '.git').mkdir()
        with self.assertRaisesRegex(ValueError, 'Git 메타데이터'):
            patcher.apply_existing_source(self.copy, write=True)

    def test_check_mode_does_not_require_provenance_or_modify_original(self):
        before = (self.original / patcher.SOURCE_REL).read_bytes()
        patcher.apply_existing_source(self.original, write=False)
        self.assertEqual((self.original / patcher.SOURCE_REL).read_bytes(), before)


if __name__ == '__main__':
    main()
