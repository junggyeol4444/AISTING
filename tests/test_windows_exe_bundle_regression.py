"""Windows one-file EXE frozen-resource regression tests; no user PC access."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ai_broadcaster.development_review import bundled_project_root
from ai_broadcaster.offline_final_acceptance import ALLOWED_FILES, inspect_bundled_project


class TestWindowsFrozenEvidence(unittest.TestCase):
    def test_frozen_resource_root_reads_six_original_evidence_files(self):
        with tempfile.TemporaryDirectory(prefix="aisting_frozen_resources_") as temp:
            bundle = Path(temp)
            for item in ALLOWED_FILES:
                source = ROOT / item
                self.assertTrue(source.is_file(), item)
                target = bundle / item
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            with patch.object(sys, "_MEIPASS", str(bundle), create=True):
                self.assertEqual(bundled_project_root(), bundle)
                archived, pending = inspect_bundled_project(bundled_project_root())
            self.assertEqual(len(archived), len(ALLOWED_FILES))
            for record in archived:
                self.assertTrue(record.digest, record.path)
                self.assertNotIn("파일 없음", record.status)
            self.assertTrue(pending, "Original roadmap stays not approved")

    def test_desktop_acceptance_inspector_uses_frozen_resource_root(self):
        source = (ROOT / "src/ai_broadcaster/desktop.py").read_text(encoding="utf-8")
        self.assertIn("root = bundled_project_root()", source)
        self.assertNotIn("root = Path(__file__).resolve().parents[2]", source)

    def test_windows_batch_and_actions_include_all_six_evidence_paths(self):
        batch = (ROOT / "build_exe_windows.bat").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/build-windows.yml").read_text(encoding="utf-8")
        for snippet in ('"config;config"', '"docs;docs"'):
            self.assertIn(snippet, batch)
            self.assertIn(snippet, workflow)
        for f in ("STAGE100_FINAL_VALIDATION.txt", "STAGE100_UNITTEST.log"):
            self.assertIn(f, batch)
            self.assertIn(f, workflow)
        self.assertIn("windows-latest", workflow)
        self.assertNotIn("continue-on-error: true", workflow)


if __name__ == "__main__":
    unittest.main()
