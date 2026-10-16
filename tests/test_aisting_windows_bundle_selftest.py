"""Offline tests for the ORIGINAL program's Windows EXE smoke-check path."""
import importlib.util
import json
import runpy
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ENTRY = Path(__file__).resolve().parents[1] / "scripts" / "run_desktop.py"


class WindowsExeSelftestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        (root / "docs").mkdir()
        (root / "config").mkdir()
        (root / "docs" / "ORIGINAL_PLAN.txt").write_text("원본 기획안", encoding="utf-8")
        (root / "docs" / "ROADMAP_100.md").write_text("원본 단계", encoding="utf-8")
        (root / "config" / "roadmap.json").write_text(json.dumps({
            "total_steps": 100, "steps": [{"number": n} for n in range(1, 101)]
        }), encoding="utf-8")
        self.root = root
        pkg = types.ModuleType("ai_broadcaster")
        pkg.__path__ = []
        desktop = types.ModuleType("ai_broadcaster.desktop")
        desktop.main = lambda: None
        frontend = types.ModuleType("ai_broadcaster.original_plan_frontend")
        frontend.run_native_live2d_window = lambda *a, **kw: None
        self.mods = {"ai_broadcaster": pkg, "ai_broadcaster.desktop": desktop,
                     "ai_broadcaster.original_plan_frontend": frontend}
        with patch.dict(sys.modules, self.mods):
            self.app = runpy.run_path(str(ENTRY), run_name="selftest_module")

    def _check(self, spec_present=True):
        with patch.dict(sys.modules, self.mods), patch.object(
            sys, "platform", "win32"
        ), patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "_MEIPASS", str(self.root), create=True
        ), patch.object(self.app["importlib"].util, "find_spec", return_value=(object() if spec_present else None)):
            return self.app["_verify_frozen_bundle"]()

    def test_frozen_bundle_accepts_valid_original_sources(self):
        self.assertTrue(self._check())

    def test_webview_missing_fails_without_install(self):
        self.assertFalse(self._check(False))

    def test_roadmap_missing_fails(self):
        (self.root / "config" / "roadmap.json").unlink()
        self.assertFalse(self._check())

    def test_original_plan_missing_fails(self):
        (self.root / "docs" / "ORIGINAL_PLAN.txt").unlink()
        self.assertFalse(self._check())

    def test_100_steps_are_required(self):
        (self.root / "config" / "roadmap.json").write_text(json.dumps({
            "total_steps": 100, "steps": [{"number": n} for n in range(1, 100)]
        }), encoding="utf-8")
        self.assertFalse(self._check())

    def test_no_selftest_success_from_source_mode(self):
        with patch.object(sys, "platform", "linux"), patch.dict(sys.modules, self.mods):
            self.assertEqual(self.app["_run"](["--aisting-selftest"]), 2)

    def test_invalid_child_args_do_not_launch_gui(self):
        with patch.dict(sys.modules, self.mods):
            self.assertEqual(self.app["_run"](["--aisting-live2d-viewer"]), 2)
            self.assertEqual(self.app["_run"](["--aisting-selftest", "junk"]), 2)

    def test_default_launch_preserved(self):
        calls = []
        self.mods["ai_broadcaster.desktop"].main = lambda: calls.append("tk")
        with patch.dict(sys.modules, self.mods):
            self.assertEqual(self.app["_run"]([]), 0)
        self.assertEqual(calls, ["tk"])

    def test_child_forwards_selected_project(self):
        calls = []
        self.mods["ai_broadcaster.original_plan_frontend"].run_native_live2d_window = (
            lambda project, **kw: calls.append((project, kw)))
        with patch.dict(sys.modules, self.mods):
            self.assertEqual(self.app["_run"]([
                "--aisting-live2d-viewer", "C:/Open-LLM-VTuber"
            ]), 0)
        self.assertEqual(calls, [("C:/Open-LLM-VTuber", {"operator_approved": True})])


if __name__ == "__main__":
    unittest.main()
