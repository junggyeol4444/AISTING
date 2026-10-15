"""18단계: 기획안/설정 선택형 수동 보관 안전성 및 무결성 테스트."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.manual_archive import (
    ArchivePlan, MAX_SOURCE_BYTES, create_archive, plan_archive, verify_archive,
)
from ai_broadcaster.offline_settings import DEFAULTS, save_settings
from ai_broadcaster.runtime_profile import RuntimeProfile, save_profile


class TestManualArchive(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.project = self.base / "project"
        (self.project / "docs").mkdir(parents=True)
        (self.project / "config").mkdir()
        (self.project / "docs" / "ORIGINAL_PLAN.txt").write_text("사용자 원본 기획안\n", encoding="utf-8")
        (self.project / "config" / "requirements.json").write_text('{"version":1}', encoding="utf-8")
        (self.project / "config" / "roadmap.json").write_text('{"steps":[]}', encoding="utf-8")
        self.home = self.base / "user"
        self.settings = self.home / "settings.json"
        self.runtime = self.home / "runtime_operator_profile.json"
        self.target = self.base / "manual.zip"

    def plan(self, **kwargs):
        return plan_archive(project_root=self.project, settings=self.settings, runtime=self.runtime, **kwargs)

    def test_plan_no_file_read_or_write(self):
        with patch("pathlib.Path.open", side_effect=AssertionError("file access")), \
             patch("socket.create_connection", side_effect=AssertionError("network")), \
             patch("subprocess.Popen", side_effect=AssertionError("process")), \
             patch("platform.system", side_effect=AssertionError("PC probe")):
            plan = self.plan(include_settings=True, include_runtime=True)
            self.assertIn("18단계", plan.describe())
            self.assertEqual(len(plan.sources), 5)
        self.assertFalse(self.home.exists())

    def test_default_plan_only_project_files(self):
        plan = self.plan()
        self.assertEqual(len(plan.sources), 3)
        self.assertNotIn("settings.json", [str(path) for _, path in plan.sources])
        self.assertFalse(self.target.exists())

    def test_confirmation_required(self):
        with self.assertRaises(PermissionError):
            create_archive(self.plan(), self.target)
        self.assertFalse(self.target.exists())

    def test_project_only_archive_verified(self):
        original = (self.project / "docs" / "ORIGINAL_PLAN.txt").read_bytes()
        created = create_archive(self.plan(), self.target, confirmed=True)
        self.assertEqual(created, self.target)
        result = verify_archive(self.target)
        self.assertEqual(len(result["entries"]), 3)
        with zipfile.ZipFile(self.target) as z:
            self.assertEqual(z.read("project/docs/ORIGINAL_PLAN.txt"), original)
            self.assertNotIn("operator/settings.json", z.namelist())
        self.assertEqual((self.project / "docs" / "ORIGINAL_PLAN.txt").read_bytes(), original)
        self.assertFalse(self.home.exists())

    def test_optional_settings_and_runtime(self):
        save_settings(DEFAULTS, self.settings)
        save_profile(RuntimeProfile("local_ollama", "llama3.2:3b"), self.runtime, operator_confirmed=True)
        before = {p: p.read_bytes() for p in (self.settings, self.runtime)}
        create_archive(self.plan(include_settings=True, include_runtime=True), self.target, confirmed=True)
        self.assertEqual(len(verify_archive(self.target)["entries"]), 5)
        with zipfile.ZipFile(self.target) as z:
            self.assertEqual(z.read("operator/settings.json"), before[self.settings])
            self.assertEqual(z.read("operator/runtime_operator_profile.json"), before[self.runtime])
            self.assertNotIn("conversation.sqlite3", z.namelist())
        for p, original in before.items():
            self.assertEqual(p.read_bytes(), original)

    def test_missing_opt_in_settings_fails_without_archive(self):
        with self.assertRaises(ValueError):
            create_archive(self.plan(include_settings=True), self.target, confirmed=True)
        self.assertFalse(self.target.exists())

    def test_missing_opt_in_runtime_fails_without_archive(self):
        with self.assertRaises(ValueError):
            create_archive(self.plan(include_runtime=True), self.target, confirmed=True)
        self.assertFalse(self.target.exists())

    def test_invalid_settings_rejected_without_overwriting(self):
        self.home.mkdir()
        self.settings.write_text('{"host":"remote"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            create_archive(self.plan(include_settings=True), self.target, confirmed=True)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), '{"host":"remote"}')
        self.assertFalse(self.target.exists())

    def test_invalid_runtime_rejected(self):
        self.home.mkdir()
        self.runtime.write_text('{"host":"remote"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            create_archive(self.plan(include_runtime=True), self.target, confirmed=True)
        self.assertFalse(self.target.exists())

    def test_existing_destination_never_overwritten(self):
        self.target.write_bytes(b"EXISTING ARCHIVE")
        with self.assertRaises(FileExistsError):
            create_archive(self.plan(), self.target, confirmed=True)
        self.assertEqual(self.target.read_bytes(), b"EXISTING ARCHIVE")

    def test_wrong_extension_and_missing_parent(self):
        for path in (self.base / "a.txt", self.base / "missing" / "a.zip"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                create_archive(self.plan(), path, confirmed=True)
            self.assertFalse(path.exists())

    def test_oversized_source_rejected(self):
        (self.project / "docs" / "ORIGINAL_PLAN.txt").write_bytes(b"A" * (MAX_SOURCE_BYTES + 1))
        with self.assertRaises(ValueError):
            create_archive(self.plan(), self.target, confirmed=True)
        self.assertFalse(self.target.exists())

    def test_bad_json_rejected(self):
        (self.project / "config" / "roadmap.json").write_text("{broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            create_archive(self.plan(), self.target, confirmed=True)
        self.assertFalse(self.target.exists())

    def test_reject_symlink_source(self):
        target = self.project / "docs" / "ORIGINAL_PLAN.txt"
        original = target.read_bytes()
        target.unlink()
        try:
            target.symlink_to(self.base / "real.txt")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        (self.base / "real.txt").write_bytes(original)
        with self.assertRaises(ValueError):
            create_archive(self.plan(), self.target, confirmed=True)
        self.assertFalse(self.target.exists())

    def test_reject_symlink_destination(self):
        existing = self.base / "other.zip"
        existing.write_bytes(b"SAFE")
        try:
            self.target.symlink_to(existing)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError):
            create_archive(self.plan(), self.target, confirmed=True)
        self.assertEqual(existing.read_bytes(), b"SAFE")

    def test_verify_detects_modified_archive_content(self):
        create_archive(self.plan(), self.target, confirmed=True)
        with zipfile.ZipFile(self.target, "a") as z:
            z.writestr("unexpected.txt", b"bad")
        with self.assertRaises(ValueError):
            verify_archive(self.target)

    def test_duplicate_plan_rejected(self):
        plan = self.plan()
        broken = ArchivePlan(plan.sources + (plan.sources[0],))
        with self.assertRaises(ValueError):
            create_archive(broken, self.target, confirmed=True)
        self.assertFalse(self.target.exists())

    def test_no_external_or_install_calls(self):
        with patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("install")) as proc, \
             patch("platform.system", side_effect=AssertionError("PC probe")) as probe:
            create_archive(self.plan(), self.target, confirmed=True)
        net.assert_not_called()
        proc.assert_not_called()
        probe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
