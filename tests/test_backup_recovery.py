"""19단계 수동 백업 무결성/비파괴 복구 사본 테스트."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.backup_recovery import (
    STAGING_NAME, inspect_backup, stage_recovery,
)
from ai_broadcaster.manual_archive import create_archive, plan_archive, verify_archive, MANIFEST, MAX_SOURCE_BYTES
from ai_broadcaster.offline_settings import DEFAULTS, save_settings
from ai_broadcaster.runtime_profile import RuntimeProfile, save_profile


class TestBackupRecovery(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.project = self.base / "project"
        (self.project / "docs").mkdir(parents=True)
        (self.project / "config").mkdir()
        (self.project / "docs" / "ORIGINAL_PLAN.txt").write_text("원본 기획안 테스트\n", encoding="utf8")
        (self.project / "config" / "requirements.json").write_text('{"version": 1}', encoding="utf8")
        (self.project / "config" / "roadmap.json").write_text('{"steps": []}', encoding="utf8")
        self.user_dir = self.base / "user"
        self.settings = self.user_dir / "settings.json"
        self.runtime = self.user_dir / "runtime_operator_profile.json"
        self.zip_path = self.base / "backup.zip"
        self.target = self.base / STAGING_NAME

    def make_archive(self, include_settings=False, include_runtime=False):
        plan = plan_archive(project_root=self.project, settings=self.settings,
                            runtime=self.runtime, include_settings=include_settings,
                            include_runtime=include_runtime)
        return create_archive(plan, self.zip_path, confirmed=True)

    def test_roadmap_approval_remains_pending(self):
        roadmap = json.loads((ROOT / "config" / "roadmap.json").read_text(encoding="utf8"))
        self.assertEqual(roadmap["total_steps"], 100)
        self.assertEqual(sum(item["status"] == "completed" for item in roadmap["steps"]), 9)
        for number in (10, 15, 18, 19):
            self.assertEqual(roadmap["steps"][number - 1]["status"], "pending")

    def test_no_automatic_read_or_write(self):
        with patch("pathlib.Path.open", side_effect=AssertionError("unexpected read")):
            self.assertFalse(self.zip_path.exists())
        self.assertFalse(self.target.exists())

    def test_confirmation_required_before_inspection_and_write(self):
        self.make_archive()
        with self.assertRaises(PermissionError):
            stage_recovery(self.zip_path, self.base)
        self.assertFalse(self.target.exists())

    def test_readonly_inspection_of_project_backup(self):
        self.make_archive()
        before = self.zip_path.read_bytes()
        report = inspect_backup(self.zip_path)
        self.assertEqual(len(report.members), 3)
        self.assertIn("SHA256", report.describe())
        self.assertEqual(self.zip_path.read_bytes(), before)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.user_dir.exists())

    def test_manual_staging_preserves_originals_and_app_data(self):
        save_settings(DEFAULTS, self.settings)
        save_profile(RuntimeProfile("mock", ""), self.runtime, operator_confirmed=True)
        self.make_archive(include_settings=True, include_runtime=True)
        originals = {p: p.read_bytes() for p in (
            self.settings, self.runtime, self.project / "docs" / "ORIGINAL_PLAN.txt",
        )}
        existing = self.base / "conversation.sqlite3"
        existing.write_bytes(b"NOT A REAL SQLITE DB BUT MUST BE PRESERVED")
        created = stage_recovery(self.zip_path, self.base, confirmed=True)
        self.assertEqual(created, self.target)
        self.assertEqual((created / "operator" / "settings.json").read_bytes(), originals[self.settings])
        self.assertEqual((created / "operator" / "runtime_operator_profile.json").read_bytes(), originals[self.runtime])
        self.assertEqual((created / "project" / "docs" / "ORIGINAL_PLAN.txt").read_bytes(),
                         originals[self.project / "docs" / "ORIGINAL_PLAN.txt"])
        self.assertIn("자동 복원 아님", (created / "RECOVERY_NOTE.txt").read_text(encoding="utf8"))
        self.assertEqual(existing.read_bytes(), b"NOT A REAL SQLITE DB BUT MUST BE PRESERVED")
        for p, before in originals.items():
            self.assertEqual(p.read_bytes(), before)

    def test_optional_settings_never_automatically_added(self):
        save_settings(DEFAULTS, self.settings)
        self.make_archive()
        stage_recovery(self.zip_path, self.base, confirmed=True)
        self.assertFalse((self.target / "operator").exists())
        self.assertEqual(len(inspect_backup(self.zip_path).members), 3)

    def test_existing_staging_folder_never_modified(self):
        self.make_archive()
        self.target.mkdir()
        existing = self.target / "keep.txt"
        existing.write_text("keep", encoding="utf8")
        with self.assertRaises(FileExistsError):
            stage_recovery(self.zip_path, self.base, confirmed=True)
        self.assertEqual(existing.read_text(encoding="utf8"), "keep")

    def test_relative_parent_and_root_rejected(self):
        self.make_archive()
        for parent in (Path("relative"), Path("/"), self.base / ".."):
            with self.subTest(parent=parent), self.assertRaises(ValueError):
                stage_recovery(self.zip_path, parent, confirmed=True)
        self.assertFalse(self.target.exists())

    def test_missing_parent_rejected(self):
        self.make_archive()
        with self.assertRaises(ValueError):
            stage_recovery(self.zip_path, self.base / "missing", confirmed=True)
        self.assertFalse(self.target.exists())

    def test_bad_zip_rejected_without_writes(self):
        self.zip_path.write_bytes(b"not zip")
        with self.assertRaises(ValueError):
            inspect_backup(self.zip_path)
        with self.assertRaises(ValueError):
            stage_recovery(self.zip_path, self.base, confirmed=True)
        self.assertFalse(self.target.exists())

    def test_modified_zip_detected(self):
        self.make_archive()
        with zipfile.ZipFile(self.zip_path, "a") as archive:
            archive.writestr("other.txt", b"unexpected")
        with self.assertRaises(ValueError):
            inspect_backup(self.zip_path)
        self.assertFalse(self.target.exists())

    def test_modified_manifest_hash_detected(self):
        self.make_archive()
        with zipfile.ZipFile(self.zip_path) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        files["project/docs/ORIGINAL_PLAN.txt"] = b"tampered"
        with zipfile.ZipFile(self.zip_path, "w") as archive:
            for name, raw in files.items():
                archive.writestr(name, raw)
        with self.assertRaises(ValueError):
            inspect_backup(self.zip_path)
        self.assertFalse(self.target.exists())

    def test_invalid_operator_settings_even_with_valid_hash_rejected(self):
        self.make_archive()
        with zipfile.ZipFile(self.zip_path) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        files["operator/settings.json"] = b'{"host": "remote"}'
        manifest = json.loads(files[MANIFEST])
        manifest["entries"].append({
            "name": "operator/settings.json", "bytes": len(files["operator/settings.json"]),
            "sha256": hashlib.sha256(files["operator/settings.json"]).hexdigest(),
        })
        files[MANIFEST] = json.dumps(manifest).encode("utf8")
        with zipfile.ZipFile(self.zip_path, "w") as archive:
            for name, raw in files.items():
                archive.writestr(name, raw)
        self.assertEqual(len(verify_archive(self.zip_path)["entries"]), 4)
        with self.assertRaises(ValueError):
            inspect_backup(self.zip_path)
        self.assertFalse(self.target.exists())

    def test_duplicate_manifest_entries_rejected(self):
        self.make_archive()
        with zipfile.ZipFile(self.zip_path) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        manifest = json.loads(files[MANIFEST])
        manifest["entries"].append(manifest["entries"][0])
        files[MANIFEST] = json.dumps(manifest).encode("utf8")
        with zipfile.ZipFile(self.zip_path, "w") as archive:
            for name, raw in files.items():
                archive.writestr(name, raw)
        with self.assertRaises(ValueError):
            inspect_backup(self.zip_path)

    def test_zip_path_traversal_rejected(self):
        self.make_archive()
        with zipfile.ZipFile(self.zip_path, "a") as archive:
            archive.writestr("../escape.txt", b"escape")
        with self.assertRaises(ValueError):
            stage_recovery(self.zip_path, self.base, confirmed=True)
        self.assertFalse((self.base / "escape.txt").exists())
        self.assertFalse(self.target.exists())

    def test_oversized_decompressed_file_rejected(self):
        self.make_archive()
        with zipfile.ZipFile(self.zip_path, "a", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("operator/settings.json", b"X" * (MAX_SOURCE_BYTES + 1))
        with self.assertRaises(ValueError):
            inspect_backup(self.zip_path)

    def test_duplicate_zip_member_rejected(self):
        self.make_archive()
        with zipfile.ZipFile(self.zip_path, "a") as archive:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr("project/docs/ORIGINAL_PLAN.txt", b"duplicate")
        with self.assertRaises(ValueError):
            inspect_backup(self.zip_path)

    def test_zip_symlink_member_rejected(self):
        self.make_archive()
        with zipfile.ZipFile(self.zip_path) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        with zipfile.ZipFile(self.zip_path, "w") as archive:
            for name, raw in files.items():
                if name == "project/docs/ORIGINAL_PLAN.txt":
                    info = zipfile.ZipInfo(name)
                    info.create_system = 3
                    info.external_attr = (0o120777 << 16)
                    archive.writestr(info, raw)
                else:
                    archive.writestr(name, raw)
        with self.assertRaises(ValueError):
            inspect_backup(self.zip_path)
        self.assertFalse(self.target.exists())

    def test_invalid_runtime_profile_even_with_valid_hash_rejected(self):
        self.make_archive()
        with zipfile.ZipFile(self.zip_path) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        raw = json.dumps({"host": "external_server", "mode": "remote"}).encode("utf8")
        files["operator/runtime_operator_profile.json"] = raw
        manifest = json.loads(files[MANIFEST])
        manifest["entries"].append({
            "name": "operator/runtime_operator_profile.json", "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
        files[MANIFEST] = json.dumps(manifest).encode("utf8")
        with zipfile.ZipFile(self.zip_path, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        with self.assertRaises(ValueError):
            inspect_backup(self.zip_path)
        self.assertFalse(self.target.exists())

    def test_symlink_source_rejected(self):
        self.make_archive()
        link = self.base / "linked.zip"
        try:
            link.symlink_to(self.zip_path)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError):
            inspect_backup(link)

    def test_symlink_parent_rejected(self):
        self.make_archive()
        link = self.base / "link-parent"
        try:
            link.symlink_to(self.base, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError):
            stage_recovery(self.zip_path, link, confirmed=True)
        self.assertFalse(self.target.exists())

    def test_partial_write_failure_cleans_new_folder(self):
        self.make_archive()
        original_open = os.open
        calls = 0
        def fail_second(path, flags, mode=0o777, **kwargs):
            nonlocal calls
            if flags & os.O_WRONLY:
                calls += 1
                if calls == 2:
                    raise OSError("disk error")
            return original_open(path, flags, mode, **kwargs)
        with patch("ai_broadcaster.backup_recovery.os.open", side_effect=fail_second):
            with self.assertRaises(OSError):
                stage_recovery(self.zip_path, self.base, confirmed=True)
        self.assertFalse(self.target.exists())
        self.assertTrue(self.zip_path.exists())

    def test_no_network_process_or_pc_probe(self):
        self.make_archive()
        with patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("probe")) as probe:
            inspect_backup(self.zip_path)
            stage_recovery(self.zip_path, self.base, confirmed=True)
        net.assert_not_called()
        proc.assert_not_called()
        probe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
