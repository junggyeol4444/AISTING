"""Auxiliary source-copy safety tests only; NOT real upstream integration."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
from fetch_existing_main_snapshot_readonly import (  # noqa: E402
    SNAPSHOT_RECORD, SnapshotError, extract_pinned_snapshot, PINNED_MAIN_COMMIT,
)
from apply_to_existing_aisting import git_blob_sha  # noqa: E402
from prepare_local_source_copy import REQUIRED  # noqa: E402


class ReadOnlySourceSnapshotTests(unittest.TestCase):
    def _archive(self, *, extra=None, omit=None, desktop=b'original existing desktop',
                 bad_root=False):
        archive = io.BytesIO()
        root = 'AISTING-' + (('f' * 40) if bad_root else PINNED_MAIN_COMMIT)
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for path in REQUIRED:
                rel = path.as_posix()
                if rel == omit:
                    continue
                z.writestr(root + '/' + rel,
                           desktop if rel == 'src/ai_broadcaster/desktop.py' else rel.encode())
            for name, content in (extra or {}).items():
                z.writestr(root + '/' + name, content)
        return archive.getvalue()

    def test_extracts_exact_existing_source_bytes_and_records_commit(self):
        desktop = b'original existing desktop'
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'snapshot'
            data = self._archive(extra={'src/ai_broadcaster/other.py': b'original module'})
            result = extract_pinned_snapshot(data, target,
                                             expected_desktop_sha=git_blob_sha(desktop))
            self.assertEqual(result, target)
            self.assertEqual((target / 'src/ai_broadcaster/desktop.py').read_bytes(), desktop)
            self.assertEqual((target / 'src/ai_broadcaster/other.py').read_bytes(), b'original module')
            record = json.loads((target / SNAPSHOT_RECORD).read_text())
            self.assertEqual(record['pinned_main_commit'], PINNED_MAIN_COMMIT)
            self.assertEqual(record['archive_sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(len(record['files']), len(REQUIRED) + 1)

    def test_refuses_overwrite_of_existing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'existing'
            target.mkdir()
            keep = target / 'do_not_touch.txt'
            keep.write_text('keep')
            with self.assertRaises(SnapshotError):
                extract_pinned_snapshot(self._archive(), target)
            self.assertEqual(keep.read_text(), 'keep')

    def test_refuses_missing_existing_original_file_before_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'missing'
            with self.assertRaisesRegex(SnapshotError, '필수 파일 누락'):
                extract_pinned_snapshot(self._archive(omit='docs/ORIGINAL_PLAN.txt'), target)
            self.assertFalse(target.exists())

    def test_refuses_wrong_original_desktop_and_removes_partial_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'wrong'
            with self.assertRaisesRegex(SnapshotError, 'SHA 불일치'):
                extract_pinned_snapshot(self._archive(), target)
            self.assertFalse(target.exists())

    def test_refuses_zip_path_escape_before_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'escape'
            with self.assertRaises(SnapshotError):
                extract_pinned_snapshot(self._archive(extra={'../escape.txt': b'x'}), target)
            self.assertFalse(target.exists())
            self.assertFalse((Path(temp) / 'escape.txt').exists())

    def test_refuses_wrong_commit_root(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'wrongroot'
            with self.assertRaisesRegex(SnapshotError, '커밋 루트'):
                extract_pinned_snapshot(self._archive(bad_root=True), target)
            self.assertFalse(target.exists())

    def test_refuses_casefold_path_collisions(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'collision'
            with self.assertRaisesRegex(SnapshotError, '충돌'):
                extract_pinned_snapshot(self._archive(extra={
                    'src/ai_broadcaster/desktop.PY': b'different'}), target)
            self.assertFalse(target.exists())

    def test_refuses_casefold_directory_collisions(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'collision_dirs'
            with self.assertRaisesRegex(SnapshotError, '충돌'):
                extract_pinned_snapshot(self._archive(extra={
                    'Custom/one.txt': b'1', 'custom/two.txt': b'2'}), target)
            self.assertFalse(target.exists())

    def test_refuses_symlink_entries(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            root = 'AISTING-' + PINNED_MAIN_COMMIT
            for path in REQUIRED:
                z.writestr(root + '/' + path.as_posix(), b'original')
            info = zipfile.ZipInfo(root + '/unsafe')
            info.create_system = 3
            info.external_attr = (0o120777 << 16)
            z.writestr(info, 'outside')
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'link'
            with self.assertRaisesRegex(SnapshotError, '링크 또는 특수'):
                extract_pinned_snapshot(data.getvalue(), target)
            self.assertFalse(target.exists())

    def test_refuses_file_directory_collision(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'collision'
            with self.assertRaisesRegex(SnapshotError, '파일 아래'):
                extract_pinned_snapshot(self._archive(extra={
                    'foo': b'a', 'foo/bar': b'b'}), target)
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
