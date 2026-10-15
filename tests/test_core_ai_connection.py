"""23단계 연결 방식 계약: 순수 로컬 계획, 원격/자동 실행 불허."""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.core_ai_connection import (
    CoreAIConnectionPlan, build_core_ai_plan, validate_core_ai_plan,
    core_ai_profile_path, save_core_ai_plan, load_core_ai_plan, delete_core_ai_plan,
)
from ai_broadcaster.core_execution import OfflineCoreSession
from ai_broadcaster.offline_settings import DEFAULTS


class CoreAIPlanTests(unittest.TestCase):
    def test_default_is_mock_no_connection(self):
        plan = build_core_ai_plan()
        self.assertEqual(plan.mode, "mock")
        self.assertEqual(plan.transport, "none")
        self.assertEqual(plan.model_name, "")
        self.assertEqual(plan.request_path, "")
        self.assertFalse(plan.network_enabled)
        self.assertTrue(plan.manual_only)

    def test_local_candidate_is_loopback_only(self):
        plan = build_core_ai_plan("local_ollama", "gemma3:4b")
        self.assertEqual((plan.host, plan.port, plan.request_path),
                         ("127.0.0.1", 11434, "/api/generate"))
        self.assertEqual(plan.transport, "loopback_http_candidate")
        self.assertFalse(plan.network_enabled)
        self.assertIn("실제 연결 아님", plan.describe())

    def test_mock_disallows_model_name(self):
        with self.assertRaises(ValueError):
            build_core_ai_plan("mock", "gemma")

    def test_mode_invalid(self):
        for mode in ("cloud", "https", "local_llm", "", None, 0):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                build_core_ai_plan(mode, "")

    def test_model_restrictions(self):
        for name in ("", "https://example.com", "../evil", "//evil", "/tmp/model",
                     "a/../b", "한글", "a b", "a" * 121, 12):
            with self.subTest(name=name), self.assertRaises(ValueError):
                build_core_ai_plan("local_ollama", name)

    def test_valid_model_variants(self):
        for name in ("llama3.2", "local/model:latest", "abc_12-3.4"):
            self.assertEqual(build_core_ai_plan("local_ollama", name).model_name, name)

    def test_external_host_rejected(self):
        for host in ("0.0.0.0", "localhost", "192.168.0.10", "example.com", "::1"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                validate_core_ai_plan(replace(build_core_ai_plan("local_ollama", "llama3"), host=host))

    def test_port_and_path_rejected(self):
        original = build_core_ai_plan("local_ollama", "llama3")
        for patch_kwargs in ({"port": 443}, {"port": True}, {"request_path": "/api/chat"},
                             {"transport": "https"}, {"request_path": "https://example.com"}):
            with self.subTest(changed=patch_kwargs), self.assertRaises(ValueError):
                validate_core_ai_plan(replace(original, **patch_kwargs))

    def test_fail_closed_flags(self):
        original = build_core_ai_plan("local_ollama", "llama3")
        for field in ("network_enabled", "auto_start_enabled", "streaming_enabled",
                      "external_publish_enabled"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_core_ai_plan(replace(original, **{field: True}))
        with self.assertRaises(ValueError):
            validate_core_ai_plan(replace(original, manual_only=False))

    def test_wrong_schema_rejected(self):
        with self.assertRaises(ValueError):
            validate_core_ai_plan(replace(build_core_ai_plan(), schema_version=2))
        with self.assertRaises(ValueError):
            validate_core_ai_plan(replace(build_core_ai_plan(), schema_version=True))

    def test_wrong_object_rejected(self):
        with self.assertRaises(TypeError):
            validate_core_ai_plan({"mode": "mock"})

    def test_mock_route_cannot_be_ollama(self):
        with self.assertRaises(ValueError):
            validate_core_ai_plan(replace(build_core_ai_plan(), request_path="/api/generate"))

    def test_no_system_calls_while_building_or_describing(self):
        with patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("urllib.request.urlopen", side_effect=AssertionError("url")) as url, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("sqlite3.connect", side_effect=AssertionError("sqlite")) as sql, \
             patch("platform.system", side_effect=AssertionError("pc info")) as pc:
            build_core_ai_plan().describe()
            build_core_ai_plan("local_ollama", "llama3").describe()
        for item in (net, url, proc, sql, pc):
            item.assert_not_called()


class CoreAIPlanPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = core_ai_profile_path(self.root)

    def test_distinct_file_from_runtime_profile(self):
        self.assertEqual(self.path.name, "core_ai_operator_profile.json")
        self.assertNotEqual(self.path.name, "runtime_operator_profile.json")

    def test_no_file_until_confirmed(self):
        with self.assertRaises(PermissionError):
            save_core_ai_plan(build_core_ai_plan(), self.path)
        self.assertFalse(self.path.exists())
        self.assertIsNone(load_core_ai_plan(self.path))

    def test_save_load_roundtrip(self):
        plan = build_core_ai_plan("local_ollama", "gemma3:4b")
        save_core_ai_plan(plan, self.path, operator_confirmed=True)
        self.assertEqual(load_core_ai_plan(self.path), plan)

    def test_replace_valid_existing_profile(self):
        save_core_ai_plan(build_core_ai_plan(), self.path, operator_confirmed=True)
        save_core_ai_plan(build_core_ai_plan("local_ollama", "llama3"), self.path,
                          operator_confirmed=True)
        self.assertEqual(load_core_ai_plan(self.path).model_name, "llama3")

    def test_corrupt_file_not_overwritten_or_deleted(self):
        self.path.write_text("corrupted", encoding="utf-8")
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            save_core_ai_plan(build_core_ai_plan(), self.path, operator_confirmed=True)
        with self.assertRaises(ValueError):
            delete_core_ai_plan(self.path, operator_confirmed=True)
        self.assertEqual(self.path.read_bytes(), before)

    def test_delete_requires_confirmation_and_preserves_other_file(self):
        other = self.root / "runtime_operator_profile.json"
        other.write_text("important", encoding="utf-8")
        save_core_ai_plan(build_core_ai_plan(), self.path, operator_confirmed=True)
        with self.assertRaises(PermissionError):
            delete_core_ai_plan(self.path)
        self.assertTrue(self.path.exists())
        delete_core_ai_plan(self.path, operator_confirmed=True)
        self.assertFalse(self.path.exists())
        self.assertEqual(other.read_text(encoding="utf-8"), "important")

    def test_symlink_rejected(self):
        real = self.root / "real.json"
        real.write_text("untouched", encoding="utf-8")
        try:
            self.path.symlink_to(real)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError):
            save_core_ai_plan(build_core_ai_plan(), self.path, operator_confirmed=True)
        with self.assertRaises(ValueError):
            load_core_ai_plan(self.path)
        self.assertEqual(real.read_text(encoding="utf-8"), "untouched")

    def test_reject_forged_plan_before_writing(self):
        with self.assertRaises(ValueError):
            save_core_ai_plan(replace(build_core_ai_plan(), host="example.com"),
                              self.path, operator_confirmed=True)
        self.assertFalse(self.path.exists())


class CoreSessionAIPlanTests(unittest.TestCase):
    def setUp(self):
        self.settings = copy.deepcopy(DEFAULTS)
        self.session = OfflineCoreSession(self.settings)

    def test_session_starts_mock(self):
        self.assertEqual(self.session.ai_plan.mode, "mock")

    def test_applying_candidate_does_not_switch_mock_reply_port(self):
        self.session.enqueue("가: 첫번째\n나: 두번째")
        self.session.configure_ai_plan(build_core_ai_plan("local_ollama", "llama3"))
        self.assertEqual(self.session.ai_plan.mode, "local_ollama")
        self.assertEqual(self.session.pending_count, 2)
        with patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("urllib.request.urlopen", side_effect=AssertionError("url")) as url:
            output = self.session.run_batch()
        self.assertEqual(len(output.processed), 2)
        self.assertEqual(output.mode, "mock")
        self.assertEqual(self.session.ai_plan.mode, "local_ollama")
        net.assert_not_called()
        url.assert_not_called()

    def test_invalid_plan_preserves_existing_and_pending(self):
        good = build_core_ai_plan("local_ollama", "llama3")
        self.session.configure_ai_plan(good)
        self.session.enqueue("가: 보존")
        with self.assertRaises(ValueError):
            self.session.configure_ai_plan(replace(good, network_enabled=True))
        self.assertEqual(self.session.ai_plan, good)
        self.assertEqual(self.session.pending_count, 1)

    def test_plan_normalized_copy_not_aliased(self):
        plan = build_core_ai_plan("local_ollama", "llama3")
        self.session.configure_ai_plan(plan)
        self.assertIsNot(self.session.ai_plan, plan)
        object.__setattr__(plan, "host", "example.com")
        self.assertEqual(self.session.ai_plan.host, "127.0.0.1")

    def test_switching_plan_preserves_history(self):
        self.session.enqueue("가: 질문")
        self.session.process_one()
        old_history = self.session.history
        self.session.configure_ai_plan(build_core_ai_plan("local_ollama", "llama3"))
        self.session.configure_ai_plan(build_core_ai_plan())
        self.assertEqual(self.session.history, old_history)
        self.assertEqual(self.session.total_processed, 1)

    def test_selection_changes_do_not_clear_plan(self):
        self.session.configure_ai_plan(build_core_ai_plan("local_ollama", "llama3"))
        updated = copy.deepcopy(self.settings)
        updated["platforms"] = ["youtube"]
        self.session.update_selection(updated)
        self.assertEqual(self.session.ai_plan.mode, "local_ollama")
        self.assertEqual(self.session.blueprint.platforms, ("youtube",))

    def test_no_settings_mutation(self):
        before = copy.deepcopy(self.settings)
        self.session.configure_ai_plan(build_core_ai_plan("local_ollama", "llama3"))
        self.assertEqual(self.settings, before)


if __name__ == "__main__":
    unittest.main()
