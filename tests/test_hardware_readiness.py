"""12단계 입력 도구: 사용자 PC 무조회/비승인 기록 금지/기존 데이터 보존."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ai_broadcaster.hardware_readiness import (
    ManualHardwareChoice, review_manual_hardware, hardware_note_path,
    load_hardware_note, save_hardware_note, delete_hardware_note,
)


class TestHardwareReadiness(unittest.TestCase):
    def sample(self):
        return ManualHardwareChoice("CPU test 9000", 8, 16, "GPU test 5000", 8)

    def test_valid_manual_report_not_verified(self):
        r = review_manual_hardware(self.sample())
        self.assertFalse(r.machine_verified)
        self.assertFalse(r.performance_verified)
        self.assertEqual(r.missing, ())
        self.assertIn("CPU test 9000", r.summary)
        self.assertIn("GPU test 5000", r.summary)
        self.assertIn("16 GB", r.summary)

    def test_blank_fields_are_allowed_for_review(self):
        r = review_manual_hardware(ManualHardwareChoice())
        self.assertGreaterEqual(len(r.missing), 4)
        self.assertIn("추가 확인", r.summary)
        self.assertFalse(r.machine_verified)

    def test_partial_unknown_vram_allowed(self):
        r = review_manual_hardware(ManualHardwareChoice(cpu_name="Intel", ram_gb=16))
        self.assertIn("Intel", r.summary)
        self.assertFalse(r.performance_verified)

    def test_integer_limits_strict(self):
        cases = [
            dict(cpu_cores=0), dict(cpu_cores=257), dict(cpu_cores=True),
            dict(ram_gb=0), dict(ram_gb=4097), dict(ram_gb=3.2),
            dict(gpu_vram_gb=-1), dict(gpu_vram_gb=1025), dict(gpu_vram_gb=False),
        ]
        for params in cases:
            with self.subTest(params=params), self.assertRaises(ValueError):
                ManualHardwareChoice(**params)

    def test_model_names_reject_invalid_strings(self):
        for name in ("X" * 121, None, "CPU\nName"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                ManualHardwareChoice(cpu_name=name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                ManualHardwareChoice(gpu_name=name)

    def test_non_choice_rejected(self):
        with self.assertRaises(TypeError):
            review_manual_hardware({"ram": 16})

    def test_pure_report_no_machine_scan_or_network(self):
        with patch("platform.system", side_effect=AssertionError("auto OS probe")), \
             patch("subprocess.Popen", side_effect=AssertionError("exec")), \
             patch("socket.create_connection", side_effect=AssertionError("network")):
            r = review_manual_hardware(self.sample())
            self.assertFalse(r.performance_verified)

    def test_note_path_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = hardware_note_path(Path(tmp) / "not-created")
            self.assertEqual(p.name, "hardware_operator_note.json")
            self.assertFalse(p.parent.exists())

    def test_empty_note_no_side_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing" / "hardware.json"
            self.assertIsNone(load_hardware_note(path))
            self.assertFalse(path.parent.exists())

    def test_save_requires_user_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.json"
            with self.assertRaises(PermissionError):
                save_hardware_note(self.sample(), p)
            self.assertFalse(p.exists())

    def test_empty_input_not_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.json"
            with self.assertRaises(ValueError):
                save_hardware_note(ManualHardwareChoice(), p, operator_confirmed=True)
            self.assertFalse(p.parent.joinpath("a.json").exists())

    def test_save_load_source_and_exact_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "nested" / "hardware.json"
            choice = self.sample()
            with patch("socket.create_connection") as dial, patch("subprocess.Popen") as process:
                save_hardware_note(choice, p, operator_confirmed=True)
                result = load_hardware_note(p)
                dial.assert_not_called()
                process.assert_not_called()
            self.assertEqual(result, choice)
            record = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(record["source"], "operator_self_report")
            self.assertEqual(set(record), {
                "schema_version", "source", "cpu_name", "cpu_cores", "ram_gb", "gpu_name", "gpu_vram_gb",
            })
            self.assertEqual(list(p.parent.glob("aisting-hardware-note-*")), [])

    def test_zero_vram_is_valid_operator_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.json"
            choice = ManualHardwareChoice(gpu_name="integrated", gpu_vram_gb=0)
            save_hardware_note(choice, p, operator_confirmed=True)
            self.assertEqual(load_hardware_note(p), choice)

    def test_invalid_record_source_cannot_claim_machine_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.json"
            for tamper in (
                {"source": "automated_scan"}, {"machine_verified": True},
                {"source": "operator_self_report", "schema_version": True},
                {"source": "operator_self_report", "schema_version": 2},
            ):
                with self.subTest(tamper=tamper):
                    save_hardware_note(self.sample(), p, operator_confirmed=True)
                    d = json.loads(p.read_text(encoding="utf-8"))
                    d.update(tamper)
                    p.write_text(json.dumps(d), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_hardware_note(p)

    def test_corrupted_and_excess_record_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.json"
            for bad in (b"{broken", b"X" * 5000, b"\xff\xfe"):
                with self.subTest(len=len(bad)), self.assertRaises(ValueError):
                    p.write_bytes(bad)
                    load_hardware_note(p)

    def test_replacing_failure_keeps_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.json"
            save_hardware_note(self.sample(), p, operator_confirmed=True)
            before = p.read_bytes()
            with patch("ai_broadcaster.hardware_readiness.os.replace", side_effect=OSError("denied")):
                with self.assertRaises(OSError):
                    save_hardware_note(ManualHardwareChoice(cpu_name="replacement"), p, operator_confirmed=True)
            self.assertEqual(p.read_bytes(), before)
            self.assertEqual(list(p.parent.glob("aisting-hardware-note-*")), [])

    def test_delete_requires_user_confirmation_and_preserves_other_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            p = folder / "hardware.json"
            saved = [folder / "settings.json", folder / "conversation.sqlite3", folder / "os_operator_note.json"]
            for file in saved:
                file.write_bytes(b"KEEP THIS")
            save_hardware_note(self.sample(), p, operator_confirmed=True)
            with self.assertRaises(PermissionError):
                delete_hardware_note(p)
            self.assertTrue(p.exists())
            delete_hardware_note(p, operator_confirmed=True)
            self.assertFalse(p.exists())
            self.assertTrue(all(f.read_bytes() == b"KEEP THIS" for f in saved))

    def test_roadmap_is_not_unblocked_by_operator_self_report(self):
        roadmap = json.loads((ROOT / "config/roadmap.json").read_text(encoding="utf-8"))
        self.assertEqual(roadmap["steps"][9]["status"], "pending")
        self.assertEqual(roadmap["steps"][10]["status"], "pending")
        self.assertEqual(roadmap["steps"][11]["status"], "pending")
        self.assertEqual(roadmap["steps"][11]["title"], "CPU·RAM·그래픽카드 확인")

    def test_manual_hardware_gui_is_available_but_not_automated(self):
        source = (ROOT / "src/ai_broadcaster/desktop.py").read_text(encoding="utf-8")
        self.assertIn('tabs.add(tab, text=label)', source)
        self.assertIn('"PC 사양 입력"', source)
        self.assertIn("self._build_hardware_review(hardware_review)", source)
        self.assertNotIn("psutil", (ROOT / "src/ai_broadcaster/hardware_readiness.py").read_text(encoding="utf-8"))

    def test_original_plan_not_mutated(self):
        import hashlib
        original = (ROOT / "docs/ORIGINAL_PLAN.txt").read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         "d4482d539bf733fddc65263566b436e2547d64d43545ac3279581bc21c58180c")


if __name__ == "__main__":
    unittest.main()
