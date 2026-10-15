"""11단계 준비 기능이 OS 스캔/외부 연결 없이 수동 입력만 처리하는지 검증."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.os_readiness import (
    ManualOsChoice, assess_manual_os, os_note_path, load_os_note, save_os_note,
    delete_os_note, OS_LABELS, ARCH_LABELS,
)


class TestOsReadiness(unittest.TestCase):
    def test_all_25_manual_choices_no_crash(self):
        for oscode in OS_LABELS.values():
            for arch in ARCH_LABELS.values():
                with self.subTest(os=oscode, arch=arch):
                    result = assess_manual_os(ManualOsChoice(oscode, arch))
                    self.assertFalse(result.machine_verified)
                    self.assertIn("자동 PC 조회", result.description)
                    self.assertTrue(result.description)

    def test_only_windows10_11_x64_are_build_candidates(self):
        candidates = [(oscode, arch) for oscode in OS_LABELS.values()
                      for arch in ARCH_LABELS.values()
                      if assess_manual_os(ManualOsChoice(oscode, arch)).candidate]
        self.assertEqual(candidates, [("windows_11", "x64"), ("windows_10", "x64")])

    def test_candidates_not_verified(self):
        for code in ("windows_10", "windows_11"):
            report = assess_manual_os(ManualOsChoice(code, "x64"))
            self.assertFalse(report.machine_verified)
            self.assertIn("검증", report.description)

    def test_unconfirmed_is_not_success(self):
        self.assertFalse(assess_manual_os(ManualOsChoice("unknown", "x64")).candidate)
        self.assertFalse(assess_manual_os(ManualOsChoice("windows_11", "unknown")).candidate)

    def test_architecture_warning(self):
        msg = assess_manual_os(ManualOsChoice("windows_11", "x86")).description
        self.assertIn("32비트", msg)
        self.assertIn("x64", msg)
        self.assertIn("ARM64", assess_manual_os(ManualOsChoice("windows_11", "arm64")).description)

    def test_bad_input_rejected(self):
        for code in ("windows_12", "", None, 1):
            with self.subTest(code=code), self.assertRaises(ValueError):
                ManualOsChoice(code, "x64")
        for arch in ("amd64-later", "", None, True):
            with self.subTest(arch=arch), self.assertRaises(ValueError):
                ManualOsChoice("windows_11", arch)

    def test_no_os_probe_in_pure_analysis(self):
        with patch("platform.system", side_effect=AssertionError("device probe")), \
             patch("subprocess.Popen", side_effect=AssertionError("program start")), \
             patch("socket.create_connection", side_effect=AssertionError("network")):
            result = assess_manual_os(ManualOsChoice("windows_11", "x64"))
            self.assertTrue(result.candidate)

    def test_path_does_not_create_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os_note_path(Path(tmp) / "missing")
            self.assertEqual(p.name, "os_operator_note.json")
            self.assertFalse(p.parent.exists())

    def test_no_record_no_side_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "missing" / "operator.json"
            self.assertIsNone(load_os_note(p))
            self.assertFalse(p.parent.exists())

    def test_cannot_save_without_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "operator.json"
            with self.assertRaises(PermissionError):
                save_os_note(ManualOsChoice("windows_11", "x64"), p)
            self.assertFalse(p.exists())

    def test_cannot_save_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "operator.json"
            with self.assertRaises(ValueError):
                save_os_note(ManualOsChoice("unknown", "x64"), p, operator_confirmed=True)
            self.assertFalse(p.exists())

    def test_save_load_data_is_operator_input_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "operator.json"
            choice = ManualOsChoice("windows_11", "x64")
            with patch("socket.create_connection") as dial, patch("subprocess.Popen") as proc:
                self.assertEqual(save_os_note(choice, p, operator_confirmed=True), p)
                loaded = load_os_note(p)
                dial.assert_not_called()
                proc.assert_not_called()
            self.assertEqual(loaded, choice)
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(data["source"], "operator_self_report")
            self.assertEqual(set(data), {"schema_version", "source", "os_code", "architecture"})
            self.assertEqual(list(p.parent.glob("aisting-os-note-*")), [])

    def test_save_preserves_unrelated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            place = Path(tmp)
            personal = [place / "settings.json", place / "conversation.sqlite3"]
            for file in personal:
                file.write_bytes(b"DO NOT TOUCH")
            choice = ManualOsChoice("windows_10", "arm64")
            save_os_note(choice, place / "operator.json", operator_confirmed=True)
            delete_os_note(place / "operator.json", operator_confirmed=True)
            self.assertEqual([f.read_bytes() for f in personal], [b"DO NOT TOUCH"] * 2)
            self.assertEqual(sorted(p.name for p in place.iterdir()),
                             ["conversation.sqlite3", "settings.json"])

    def test_delete_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "operator.json"
            save_os_note(ManualOsChoice("windows_11", "x64"), p, operator_confirmed=True)
            with self.assertRaises(PermissionError):
                delete_os_note(p)
            self.assertTrue(p.exists())
            delete_os_note(p, operator_confirmed=True)
            self.assertFalse(p.exists())

    def test_rejects_tampered_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "operator.json"
            for content in (
                '{"schema_version":1,"source":"automatic_probe","os_code":"windows_11","architecture":"x64"}',
                '{"schema_version":1,"source":"operator_self_report","os_code":"windows_11","architecture":"x64","verified":true}',
                '{"schema_version":true,"source":"operator_self_report","os_code":"windows_11","architecture":"x64"}',
                '{broken',
            ):
                with self.subTest(content=content), self.assertRaises(ValueError):
                    p.write_text(content, encoding="utf-8")
                    load_os_note(p)

    def test_rejects_oversized_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "operator.json"
            p.write_bytes(b"X" * 5000)
            with self.assertRaises(ValueError):
                load_os_note(p)

    def test_atomic_failure_does_not_destroy_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "operator.json"
            save_os_note(ManualOsChoice("windows_11", "x64"), p, operator_confirmed=True)
            before = p.read_bytes()
            with patch("ai_broadcaster.os_readiness.os.replace", side_effect=OSError("blocked")):
                with self.assertRaises(OSError):
                    save_os_note(ManualOsChoice("windows_10", "arm64"), p, operator_confirmed=True)
            self.assertEqual(p.read_bytes(), before)
            self.assertEqual(list(p.parent.glob("aisting-os-note-*")), [])

    def test_roadmap_approval_not_auto_advanced(self):
        roadmap=json.loads((ROOT / "config/roadmap.json").read_text(encoding="utf-8"))
        self.assertEqual(roadmap["steps"][9]["status"], "pending")
        self.assertEqual(roadmap["steps"][10]["status"], "pending")
        self.assertEqual(roadmap["steps"][10]["title"], "PC 운영체제 확인")


if __name__ == "__main__":
    unittest.main()
