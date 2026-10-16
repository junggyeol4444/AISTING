"""9단계: GitHub 없이 PC에서 단독 운영하는 경계 및 수동 저장소 점검."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ai_broadcaster.local_runtime import (
    LocalOperationPlan, StorageCheck, check_local_storage, local_operation_plan,
)
from ai_broadcaster.offline_settings import DEFAULTS, load_settings, save_settings
from ai_broadcaster.requirements import load_json, validate


class TestLocalOperation(unittest.TestCase):
    def test_local_only_explicit_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            plan = local_operation_plan(storage_dir=Path(folder))
            self.assertIsInstance(plan, LocalOperationPlan)
            self.assertFalse(plan.github_required)
            self.assertFalse(plan.scheduled_execution)
            self.assertFalse(plan.external_publish_enabled)
            self.assertEqual(plan.settings_path, Path(folder) / "settings.json")
            self.assertEqual(plan.memory_path, Path(folder) / "conversation.sqlite3")
            self.assertIn("미구현", plan.describe())
            self.assertIn("127.0.0.1", plan.describe())
            self.assertIn("GitHub", plan.describe())

    def test_plan_is_pure_and_does_not_create_user_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            d = Path(folder) / "nonexistent"
            with patch("socket.create_connection") as dial, patch("subprocess.Popen") as process:
                plan = local_operation_plan(storage_dir=d)
                self.assertEqual(plan.settings_path.parent, d)
                self.assertFalse(d.exists())
                dial.assert_not_called()
                process.assert_not_called()

    def test_policy_cannot_change_to_cloud(self):
        for field, value in (
            ("host", "cloud"), ("budget", "paid"),
            ("streaming_enabled", True), ("scheduled_execution", True),
            ("external_publish_enabled", True),
        ):
            with self.subTest(field=field):
                cfg = copy.deepcopy(DEFAULTS)
                cfg[field] = value
                with self.assertRaises(ValueError):
                    local_operation_plan(cfg)

    def test_platform_and_avatar_selection_does_not_change_host(self):
        cfg = copy.deepcopy(DEFAULTS)
        cfg["platforms"] = ["chzzk", "youtube", "twitch"]
        cfg["avatar"] = "3d"
        cfg["content"] = "both"
        self.assertFalse(local_operation_plan(cfg).github_required)

    def test_invalid_profile_fails_before_any_io(self):
        cfg = copy.deepcopy(DEFAULTS)
        cfg["voice_profile"]["volume"] = 101
        with patch("socket.create_connection") as dial:
            with self.assertRaises(ValueError):
                local_operation_plan(cfg)
            dial.assert_not_called()

    def test_manual_probe_writes_only_temp_file_and_cleans_it(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "pc-data"
            target.mkdir()
            settings = target / "settings.json"
            memory = target / "conversation.sqlite3"
            settings.write_bytes(b"ORIGINAL-SETTINGS")
            memory.write_bytes(b"ORIGINAL-MEMORY")
            with patch("socket.create_connection") as dial, patch("subprocess.Popen") as proc:
                result = check_local_storage(target)
                dial.assert_not_called()
                proc.assert_not_called()
            self.assertIsInstance(result, StorageCheck)
            self.assertTrue(result.success, result.message)
            self.assertEqual(sorted(p.name for p in target.iterdir()), ["conversation.sqlite3", "settings.json"])
            self.assertEqual(settings.read_bytes(), b"ORIGINAL-SETTINGS")
            self.assertEqual(memory.read_bytes(), b"ORIGINAL-MEMORY")

    def test_manual_probe_creates_its_own_directory_only(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / "data"
            self.assertTrue(check_local_storage(directory).success)
            self.assertTrue(directory.is_dir())
            self.assertEqual(list(directory.iterdir()), [])

    def test_manual_probe_does_not_leave_temp_on_read_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            result = check_local_storage(directory)
            self.assertTrue(result.success)
            self.assertFalse(any(directory.glob("aisting-check-*")))

    def test_bad_directory_does_not_crash(self):
        with tempfile.TemporaryDirectory() as folder:
            not_dir = Path(folder) / "file"
            not_dir.write_text("keep", encoding="utf-8")
            result = check_local_storage(not_dir)
            self.assertFalse(result.success)
            self.assertIn("사용할 수 없습니다", result.message)
            self.assertEqual(not_dir.read_text(encoding="utf-8"), "keep")

    def test_bad_argument_returns_error(self):
        self.assertFalse(check_local_storage(None).success)

    def test_diagnostic_fails_cleanly_if_probe_cannot_create_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("ai_broadcaster.local_runtime.tempfile.NamedTemporaryFile", side_effect=OSError("denied")):
                report = check_local_storage(Path(folder))
                self.assertFalse(report.success)
                self.assertIn("denied", report.message)

    def test_local_settings_roundtrip_without_server(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "settings.json"
            cfg = copy.deepcopy(DEFAULTS)
            cfg["platforms"] = ["youtube"]
            with patch("socket.create_connection") as dial:
                save_settings(cfg, target)
                loaded = load_settings(target)
                plan = local_operation_plan(loaded, storage_dir=target.parent)
                self.assertEqual(plan.settings_path, target)
                self.assertEqual(plan.memory_path.parent, target.parent)
                dial.assert_not_called()

    def test_roadmap_requires_local_host(self):
        config = load_json(ROOT / "config" / "requirements.json")
        roadmap = load_json(ROOT / "config" / "roadmap.json")
        self.assertEqual(config["operator_decisions"]["hosting_option"], "local_pc")
        broken = copy.deepcopy(config)
        broken["operator_decisions"]["hosting_option"] = "cloud"
        errors = validate(broken, roadmap)
        self.assertTrue(any("PC 로컬" in e for e in errors))

    def test_offline_exe_entrypoint_no_github_dependency(self):
        entrypoint = (ROOT / "scripts" / "run_desktop.py").read_text(encoding="utf-8")
        build = (ROOT / "build_exe_windows.bat").read_text(encoding="utf-8")
        self.assertIn("ai_broadcaster.desktop", entrypoint)
        self.assertIn("--onefile", build)
        self.assertNotIn("import github", entrypoint.lower())
        self.assertNotIn("github.com", entrypoint.lower())
        self.assertNotIn("github.com", build.lower())
        # Developer CI may verify a frozen UI, but the ordinary EXE never
        # requires GitHub authentication or network access to open.
        self.assertNotIn("pip install", build.lower())
        workflows = list((ROOT / ".github" / "workflows").glob("*.yml"))
        self.assertTrue(workflows)
        self.assertTrue(all("schedule:" not in p.read_text(encoding="utf-8") for p in workflows))
        self.assertNotIn("github.com", entrypoint.lower())


if __name__ == "__main__":
    unittest.main()
