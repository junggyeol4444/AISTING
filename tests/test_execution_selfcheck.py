"""20단계: 수동 오프라인 개발 환경 샘플 자가점검 단위 테스트."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.execution_selfcheck import (
    ExecutionCheck, ExecutionReport, _bundled_criteria, _selection_policy,
    _temporary_settings, _mock_chat_fifo, _temporary_memory, run_execution_selfcheck,
)
from ai_broadcaster.offline_settings import DEFAULTS


class TestExecutionSelfcheck(unittest.TestCase):
    def test_full_manual_check_succeeds(self):
        result = run_execution_selfcheck(project_root=ROOT)
        self.assertTrue(result.passed, result.describe())
        self.assertEqual(len(result.checks), 5)
        self.assertTrue(all(item.passed for item in result.checks))

    def test_included_development_criteria(self):
        self.assertIn("100단계", _bundled_criteria(ROOT))

    def test_approval_and_pc_steps_stay_pending(self):
        roadmap = json.loads((ROOT / "config" / "roadmap.json").read_text(encoding="utf-8"))
        self.assertEqual(sum(item["status"] == "completed" for item in roadmap["steps"]), 9)
        self.assertTrue(all(item["status"] == "pending" for item in roadmap["steps"][9:20]))

    def test_rejects_missing_or_broken_criteria(self):
        with tempfile.TemporaryDirectory() as temp:
            report = run_execution_selfcheck(project_root=Path(temp))
        self.assertFalse(report.passed)
        self.assertFalse(report.checks[0].passed)
        self.assertTrue(all(check.passed for check in report.checks[1:]))

    def test_rejects_unauthorized_approval(self):
        requirements = json.loads((ROOT / "config" / "requirements.json").read_text(encoding="utf-8"))
        roadmap = json.loads((ROOT / "config" / "roadmap.json").read_text(encoding="utf-8"))
        roadmap["steps"][9]["status"] = "completed"
        with patch("ai_broadcaster.execution_selfcheck.load_review_sources", return_value=(requirements, roadmap)):
            report = run_execution_selfcheck()
        self.assertFalse(report.checks[0].passed)
        self.assertIn("승인", report.checks[0].detail)

    def test_rejects_changed_core_policy(self):
        requirements = json.loads((ROOT / "config" / "requirements.json").read_text(encoding="utf-8"))
        roadmap = json.loads((ROOT / "config" / "roadmap.json").read_text(encoding="utf-8"))
        requirements["operator_decisions"]["hosting_option"] = "cloud"
        with patch("ai_broadcaster.execution_selfcheck.load_review_sources", return_value=(requirements, roadmap)):
            report = run_execution_selfcheck()
        self.assertFalse(report.checks[0].passed)
        self.assertIn("기획 기준 불일치", report.checks[0].detail)

    def test_all_user_selection_options_preserved(self):
        before = copy.deepcopy(DEFAULTS)
        self.assertIn("240", _selection_policy())
        self.assertEqual(before, DEFAULTS)

    def test_rejects_policy_regression(self):
        with patch("ai_broadcaster.execution_selfcheck.local_operation_plan", side_effect=ValueError("policy")):
            report = run_execution_selfcheck()
        self.assertFalse(report.checks[1].passed)
        self.assertIn("policy", report.checks[1].detail)

    def test_temporary_settings_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertIn("저장", _temporary_settings(Path(temp)))
            self.assertTrue((Path(temp) / "sample" / "settings.json").exists())

    def test_temporary_settings_failure_not_masked(self):
        with patch("ai_broadcaster.execution_selfcheck.save_settings", side_effect=OSError("disk full")):
            report = run_execution_selfcheck()
        self.assertFalse(report.passed)
        self.assertFalse(report.checks[2].passed)
        self.assertIn("disk full", report.checks[2].detail)

    def test_mock_chat_fifo_duplicate_retained(self):
        self.assertIn("중복", _mock_chat_fifo())

    def test_mock_chat_failure_not_masked(self):
        with patch("ai_broadcaster.execution_selfcheck.MockReplyGenerator.generate", side_effect=ValueError("bad mock")):
            report = run_execution_selfcheck()
        self.assertFalse(report.checks[3].passed)
        self.assertIn("bad mock", report.checks[3].detail)

    def test_temporary_sqlite_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertIn("2건", _temporary_memory(Path(temp)))
            self.assertTrue((Path(temp) / "sample" / "memory.sqlite3").exists())

    def test_sqlite_failure_not_masked(self):
        with patch("ai_broadcaster.execution_selfcheck.LocalMemory", side_effect=OSError("db failure")):
            report = run_execution_selfcheck()
        self.assertFalse(report.checks[4].passed)
        self.assertIn("db failure", report.checks[4].detail)

    def test_isolated_files_deleted_on_success(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            report = run_execution_selfcheck(scratch_parent=base)
            self.assertTrue(report.passed)
            self.assertEqual(list(base.iterdir()), [])

    def test_isolated_files_deleted_on_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            with patch("ai_broadcaster.execution_selfcheck._temporary_memory", side_effect=OSError("bad")):
                report = run_execution_selfcheck(scratch_parent=base)
            self.assertFalse(report.passed)
            self.assertEqual(list(base.iterdir()), [])

    def test_no_fallback_to_persistent_data_if_temp_unavailable(self):
        with patch("ai_broadcaster.execution_selfcheck.tempfile.TemporaryDirectory", side_effect=PermissionError("temp denied")):
            report = run_execution_selfcheck()
        self.assertFalse(report.passed)
        self.assertEqual(len(report.checks), 5)
        self.assertFalse(report.checks[2].passed)
        self.assertTrue(report.checks[3].passed)
        self.assertFalse(report.checks[4].passed)

    def test_no_network_subprocess_hardware_probe(self):
        with patch("socket.create_connection", side_effect=AssertionError("network")) as network, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as process, \
             patch("platform.system", side_effect=AssertionError("hardware")) as hardware:
            report = run_execution_selfcheck()
        self.assertTrue(report.passed, report.describe())
        network.assert_not_called()
        process.assert_not_called()
        hardware.assert_not_called()

    def test_does_not_touch_operator_settings_or_memory(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "operator"
            folder.mkdir()
            settings = folder / "settings.json"
            memory = folder / "conversation.sqlite3"
            settings.write_bytes(b"KEEP-SETTINGS")
            memory.write_bytes(b"KEEP-SQLITE")
            with patch.dict("os.environ", {"LOCALAPPDATA": str(folder), "HOME": str(folder)}):
                report = run_execution_selfcheck()
            self.assertTrue(report.passed)
            self.assertEqual(settings.read_bytes(), b"KEEP-SETTINGS")
            self.assertEqual(memory.read_bytes(), b"KEEP-SQLITE")
            self.assertEqual(sorted(p.name for p in folder.iterdir()), ["conversation.sqlite3", "settings.json"])

    def test_failure_report_is_explicit(self):
        report = ExecutionReport((ExecutionCheck("샘플", False, "fail"),))
        self.assertFalse(report.passed)
        self.assertIn("[실패]", report.describe())
        self.assertIn("Windows 실기기", report.describe())
        self.assertIn("승인 대기", report.describe())

    def test_result_immutable(self):
        report = run_execution_selfcheck()
        with self.assertRaises(FrozenInstanceError):
            report.checks[0].passed = False

    def test_no_test_runs_at_module_import(self):
        import ai_broadcaster.execution_selfcheck as module
        with patch.object(module, "run_execution_selfcheck", side_effect=AssertionError("automatic")):
            self.assertIsNotNone(module.ExecutionReport)

    def test_cli_returns_success_or_failure(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("manual_environment_cli", ROOT / "scripts" / "run_environment_selfcheck.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, "run_execution_selfcheck", return_value=run_execution_selfcheck()):
            self.assertEqual(module.main(), 0)
        with patch.object(module, "run_execution_selfcheck", return_value=ExecutionReport((ExecutionCheck("x", False, "bad"),))):
            self.assertEqual(module.main(), 1)


if __name__ == "__main__":
    unittest.main()
