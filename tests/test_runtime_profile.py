"""17단계: 로컬 수동 실행 프로필의 검증/보존/무전송 테스트."""
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

from ai_broadcaster.runtime_profile import (
    MAX_PROFILE_BYTES, MODES, PROFILE_NAME, RuntimeProfile,
    delete_profile, load_profile, profile_path, save_profile,
)


class TestRuntimeProfile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "aisting_user"
        self.path = profile_path(self.home)

    def test_default_mock_is_pure_and_manual(self):
        with patch("pathlib.Path.open", side_effect=AssertionError("read/write")), \
             patch("socket.create_connection", side_effect=AssertionError("network")), \
             patch("subprocess.Popen", side_effect=AssertionError("process")), \
             patch("platform.system", side_effect=AssertionError("probe")):
            profile = RuntimeProfile()
            text = profile.describe()
        self.assertEqual(profile.mode, "mock")
        self.assertIn("17단계", text)
        self.assertIn("127.0.0.1", text)
        self.assertIn("자동 모델 연결: 없음", text)
        self.assertIn("10/15/17단계", text)
        self.assertFalse(self.home.exists())

    def test_supported_modes(self):
        self.assertEqual(MODES["모의 답변 (인터넷 불필요)"], "mock")
        self.assertEqual(MODES["로컬 Ollama (수동 선택)"], "local_ollama")
        self.assertEqual(RuntimeProfile("local_ollama", "qwen2.5:7b").model_name, "qwen2.5:7b")

    def test_invalid_modes_rejected(self):
        for mode in ("remote", "auto", "", 1, None, True):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                RuntimeProfile(mode, "")

    def test_invalid_model_names_rejected(self):
        for name in ("", " ", "../../bad", "https://evil", "/absolute", "qwen 2", "한글", "x" * 121, "bad\nname", None, 5):
            with self.subTest(name=name), self.assertRaises(ValueError):
                RuntimeProfile("local_ollama", name)

    def test_mock_rejects_model_name(self):
        with self.assertRaises(ValueError):
            RuntimeProfile("mock", "llama3")

    def test_missing_file_does_not_create_directory(self):
        self.assertIsNone(load_profile(self.path))
        self.assertFalse(self.home.exists())
        self.assertEqual(self.path.name, PROFILE_NAME)

    def test_save_requires_operator_confirmation(self):
        with self.assertRaises(PermissionError):
            save_profile(RuntimeProfile(), self.path)
        self.assertFalse(self.home.exists())

    def test_delete_requires_operator_confirmation(self):
        save_profile(RuntimeProfile(), self.path, operator_confirmed=True)
        with self.assertRaises(PermissionError):
            delete_profile(self.path)
        self.assertTrue(self.path.exists())

    def test_save_load_mock_and_local_profile(self):
        for choice in (RuntimeProfile(), RuntimeProfile("local_ollama", "llama3.2:3b")):
            save_profile(choice, self.path, operator_confirmed=True)
            self.assertEqual(load_profile(self.path), choice)
            data = json.loads(self.path.read_text(encoding="utf8"))
            self.assertEqual(data["host"], "127.0.0.1")
            self.assertIs(data["manual_start_only"], True)
            self.assertIs(data["streaming_enabled"], False)
            self.assertIs(data["external_publish_enabled"], False)

    def test_profile_file_separate_from_user_settings_and_db(self):
        self.home.mkdir()
        settings = self.home / "settings.json"
        db = self.home / "conversation.sqlite3"
        settings.write_bytes(b"my existing settings")
        db.write_bytes(b"my existing sqlite data")
        save_profile(RuntimeProfile("local_ollama", "qwen2.5"), self.path, operator_confirmed=True)
        delete_profile(self.path, operator_confirmed=True)
        self.assertEqual(settings.read_bytes(), b"my existing settings")
        self.assertEqual(db.read_bytes(), b"my existing sqlite data")
        self.assertEqual(set(p.name for p in self.home.iterdir()), {"settings.json", "conversation.sqlite3"})

    def test_corrupted_json_not_overwritten(self):
        self.home.mkdir()
        self.path.write_bytes(b"{garbled")
        with self.assertRaises(ValueError):
            load_profile(self.path)
        with self.assertRaises(ValueError):
            save_profile(RuntimeProfile(), self.path, operator_confirmed=True)
        with self.assertRaises(ValueError):
            delete_profile(self.path, operator_confirmed=True)
        self.assertEqual(self.path.read_bytes(), b"{garbled")

    def test_unknown_field_and_remote_host_rejected(self):
        save_profile(RuntimeProfile(), self.path, operator_confirmed=True)
        original = json.loads(self.path.read_text(encoding="utf8"))
        for change in ({"host": "example.org"}, {"manual_start_only": False},
                       {"streaming_enabled": True}, {"external_publish_enabled": True},
                       {"source": "automatic_probe"}, {"extra": "unsafe"},
                       {"schema_version": True}, {"mode": "remote"}):
            with self.subTest(change=change):
                data = dict(original, **change)
                self.path.write_text(json.dumps(data), encoding="utf8")
                with self.assertRaises(ValueError):
                    load_profile(self.path)
        self.path.write_text(json.dumps(original), encoding="utf8")
        self.assertEqual(load_profile(self.path), RuntimeProfile())

    def test_oversized_and_non_utf8_record_rejected(self):
        self.home.mkdir()
        self.path.write_bytes(b"x" * (MAX_PROFILE_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "크기"):
            load_profile(self.path)
        self.path.write_bytes(b"\xff")
        with self.assertRaises(ValueError):
            load_profile(self.path)

    def test_symlink_record_rejected_and_target_preserved(self):
        self.home.mkdir()
        target = self.home / "unrelated.txt"
        target.write_text("preserve", encoding="utf8")
        try:
            self.path.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        for operation in (
            lambda: load_profile(self.path),
            lambda: save_profile(RuntimeProfile(), self.path, operator_confirmed=True),
            lambda: delete_profile(self.path, operator_confirmed=True),
        ):
            with self.assertRaisesRegex(ValueError, "링크"):
                operation()
        self.assertEqual(target.read_text(encoding="utf8"), "preserve")

    def test_symlink_parent_rejected(self):
        actual = Path(self.tmp.name) / "actual"
        actual.mkdir()
        linked = Path(self.tmp.name) / "linked"
        try:
            linked.symlink_to(actual, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaisesRegex(ValueError, "링크"):
            save_profile(RuntimeProfile(), linked / PROFILE_NAME, operator_confirmed=True)
        self.assertEqual(list(actual.iterdir()), [])

    def test_directory_conflict_preserved(self):
        self.path.mkdir(parents=True)
        with self.assertRaises((ValueError, OSError)):
            save_profile(RuntimeProfile(), self.path, operator_confirmed=True)
        self.assertTrue(self.path.is_dir())

    def test_manual_save_no_network_process_or_pc_probe(self):
        with patch("socket.create_connection", side_effect=AssertionError("network")) as network, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as process, \
             patch("platform.system", side_effect=AssertionError("probe")) as probe:
            save_profile(RuntimeProfile("local_ollama", "llama3"), self.path, operator_confirmed=True)
            self.assertEqual(load_profile(self.path).mode, "local_ollama")
            delete_profile(self.path, operator_confirmed=True)
        network.assert_not_called()
        process.assert_not_called()
        probe.assert_not_called()

    def test_deleting_missing_record_is_safe(self):
        delete_profile(self.path, operator_confirmed=True)
        self.assertFalse(self.home.exists())

    def test_roadmap_approval_stays_pending(self):
        data = json.loads((ROOT / "config/roadmap.json").read_text(encoding="utf8"))
        self.assertEqual(len(data["steps"]), 100)
        self.assertTrue(all(data["steps"][i]["status"] == "pending" for i in range(9, 17)))
        self.assertEqual(data["steps"][16]["title"], "기본 실행 환경 설정")

    def test_original_plan_preserved(self):
        digest = hashlib.sha256((ROOT / "docs/ORIGINAL_PLAN.txt").read_bytes()).hexdigest()
        self.assertEqual(digest, "d4482d539bf733fddc65263566b436e2547d64d43545ac3279581bc21c58180c")


if __name__ == "__main__":
    unittest.main()
