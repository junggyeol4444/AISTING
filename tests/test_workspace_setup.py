"""16단계: 수동 작업 폴더 생성, 기존 파일 보호, 자동 PC 접근 금지."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.workspace_setup import (
    MANIFEST, MANIFEST_NAME, SUBFOLDERS, WORKSPACE_NAME,
    create_workspace, workspace_plan,
)


class TestWorkspaceSetup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name) / "chosen_parent"
        self.parent.mkdir()
        self.plan = workspace_plan(str(self.parent))

    def test_preview_is_pure_and_reports_boundaries(self):
        with patch("pathlib.Path.mkdir", side_effect=AssertionError("write")), \
             patch("pathlib.Path.read_text", side_effect=AssertionError("read")), \
             patch("socket.create_connection", side_effect=AssertionError("network")), \
             patch("subprocess.Popen", side_effect=AssertionError("process")), \
             patch("platform.system", side_effect=AssertionError("PC probe")):
            report = workspace_plan(str(self.parent)).describe()
        self.assertIn("16단계", report)
        self.assertIn("실제 백업은 아직 하지 않습니다", report)
        self.assertIn("프로그램 설치", report)
        self.assertFalse(self.plan.root.exists())

    def test_invalid_path_is_rejected(self):
        for text in ("", "  ", "relative", "../relative", "/", "\x00", "\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                workspace_plan(text)
        with self.assertRaises(ValueError):
            workspace_plan(str(self.parent / ".." / "chosen_parent"))

    def test_explicit_confirmation_required(self):
        with self.assertRaises(PermissionError):
            create_workspace(self.plan)
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_create_only_named_structure(self):
        root = create_workspace(self.plan, confirmed=True)
        self.assertEqual(root, self.parent / WORKSPACE_NAME)
        self.assertEqual(set(p.name for p in root.iterdir()), set(SUBFOLDERS) | {MANIFEST_NAME})
        self.assertTrue(all((root / name).is_dir() for name in SUBFOLDERS))
        self.assertEqual(json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8")), MANIFEST)
        self.assertFalse((root / "backups" / "settings.json").exists())

    def test_repeat_preserves_existing_user_files(self):
        root = create_workspace(self.plan, confirmed=True)
        user_file = root / "notes" / "my_notes.txt"
        user_file.write_text("keep me", encoding="utf-8")
        marker_before = (root / MANIFEST_NAME).read_bytes()
        self.assertEqual(create_workspace(self.plan, confirmed=True), root)
        self.assertEqual(user_file.read_text(encoding="utf-8"), "keep me")
        self.assertEqual((root / MANIFEST_NAME).read_bytes(), marker_before)

    def test_recreate_missing_subfolder_only(self):
        root = create_workspace(self.plan, confirmed=True)
        (root / "logs").rmdir()
        create_workspace(self.plan, confirmed=True)
        self.assertTrue((root / "logs").is_dir())

    def test_unrelated_nonempty_directory_not_modified(self):
        root = self.plan.root
        root.mkdir()
        original = root / "important.txt"
        original.write_text("do not change", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "기존 파일"):
            create_workspace(self.plan, confirmed=True)
        self.assertEqual(original.read_text(encoding="utf-8"), "do not change")
        self.assertEqual([p.name for p in root.iterdir()], ["important.txt"])

    def test_different_manifest_never_overwritten(self):
        root = self.plan.root
        root.mkdir()
        marker = root / MANIFEST_NAME
        marker.write_text('{"app":"OTHER"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "다른 작업 공간"):
            create_workspace(self.plan, confirmed=True)
        self.assertEqual(marker.read_text(encoding="utf-8"), '{"app":"OTHER"}')
        self.assertFalse((root / "source").exists())

    def test_invalid_manifest_is_not_replaced(self):
        root = self.plan.root
        root.mkdir()
        marker = root / MANIFEST_NAME
        marker.write_text("{bad", encoding="utf-8")
        with self.assertRaises(ValueError):
            create_workspace(self.plan, confirmed=True)
        self.assertEqual(marker.read_text(encoding="utf-8"), "{bad")

    def test_existing_file_conflict_prevents_partial_changes(self):
        root = create_workspace(self.plan, confirmed=True)
        (root / "logs").rmdir()
        (root / "notes").rmdir()
        (root / "notes").write_text("not a folder", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "충돌"):
            create_workspace(self.plan, confirmed=True)
        self.assertFalse((root / "logs").exists())
        self.assertEqual((root / "notes").read_text(encoding="utf-8"), "not a folder")

    def test_parent_must_exist(self):
        missing = self.parent / "missing"
        with self.assertRaisesRegex(ValueError, "존재하지"):
            create_workspace(workspace_plan(str(missing)), confirmed=True)
        self.assertFalse(missing.exists())

    def test_symlink_parent_and_child_rejected(self):
        link = Path(self.temp.name) / "linked"
        try:
            link.symlink_to(self.parent, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink not available")
        with self.assertRaisesRegex(ValueError, "링크"):
            create_workspace(workspace_plan(str(link)), confirmed=True)
        root = create_workspace(self.plan, confirmed=True)
        (root / "notes").rmdir()
        (root / "notes").symlink_to(self.parent, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "충돌"):
            create_workspace(self.plan, confirmed=True)

    def test_no_network_process_or_pc_probe_during_creation(self):
        with patch("socket.create_connection", side_effect=AssertionError("network")), \
             patch("subprocess.Popen", side_effect=AssertionError("process")), \
             patch("platform.system", side_effect=AssertionError("probe")):
            create_workspace(self.plan, confirmed=True)

    def test_roadmap_approval_untouched(self):
        roadmap = json.loads((ROOT / "config/roadmap.json").read_text(encoding="utf-8"))
        self.assertEqual(len(roadmap["steps"]), 100)
        self.assertTrue(all(roadmap["steps"][i]["status"] == "pending" for i in range(9, 16)))
        self.assertEqual(roadmap["steps"][15]["title"], "개발용 폴더와 작업 공간 구성")

    def test_original_plan_unchanged(self):
        digest = hashlib.sha256((ROOT / "docs/ORIGINAL_PLAN.txt").read_bytes()).hexdigest()
        self.assertEqual(digest, "d4482d539bf733fddc65263566b436e2547d64d43545ac3279581bc21c58180c")


if __name__ == "__main__":
    unittest.main()
