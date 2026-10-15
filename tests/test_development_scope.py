"""13단계: 현재 PC 개발 범위는 수동 입력과 실제 구현 여부만 근거로 설명."""
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

from ai_broadcaster.development_scope import review_development_scope
from ai_broadcaster.hardware_readiness import ManualHardwareChoice
from ai_broadcaster.os_readiness import ManualOsChoice


class TestDevelopmentScope(unittest.TestCase):
    def setUp(self):
        self.os = ManualOsChoice("windows_11", "x64")
        self.hw = ManualHardwareChoice("Example CPU", 8, 16, "Example GPU", 8)

    def test_os_reference_candidate_does_not_mean_verified(self):
        result = review_development_scope(self.os, self.hw)
        self.assertTrue(result.os_reference_candidate)
        self.assertFalse(result.machine_verified)
        self.assertFalse(result.performance_verified)
        self.assertFalse(result.windows_exe_verified)
        self.assertIn("실제 실행은 검증되지", result.describe())

    def test_unknown_os_does_not_claim_supported(self):
        result = review_development_scope(ManualOsChoice("unknown", "unknown"), self.hw)
        self.assertFalse(result.os_reference_candidate)
        self.assertIn("운영체제/시스템 종류가 미입력", result.describe())

    def test_x86_is_not_x64_candidate(self):
        result = review_development_scope(ManualOsChoice("windows_10", "x86"), self.hw)
        self.assertFalse(result.os_reference_candidate)
        self.assertIn("일치하지 않거나 확인되지", result.describe())

    def test_arm64_is_not_claimed_supported(self):
        result = review_development_scope(ManualOsChoice("windows_11", "arm64"), self.hw)
        self.assertFalse(result.os_reference_candidate)

    def test_non_windows_not_claimed_supported(self):
        result = review_development_scope(ManualOsChoice("non_windows", "x64"), self.hw)
        self.assertFalse(result.os_reference_candidate)

    def test_blank_hardware_keeps_missing_and_no_performance_prediction(self):
        result = review_development_scope(self.os, ManualHardwareChoice())
        self.assertGreaterEqual(len(result.hardware_missing), 4)
        self.assertIn("직접 입력이 부족한 항목", result.describe())
        self.assertFalse(result.performance_verified)

    def test_complete_self_report_not_measured(self):
        result = review_development_scope(self.os, self.hw)
        self.assertEqual(result.hardware_missing, ())
        self.assertIn("자가 신고값", result.describe())
        self.assertIn("FPS·응답 속도를 예측하지", result.describe())

    def test_high_ram_does_not_change_ai_model_status(self):
        normal = review_development_scope(self.os, self.hw)
        high = review_development_scope(self.os, ManualHardwareChoice("Test", 32, 1024, "GPU", 128))
        self.assertEqual(normal.items, high.items)
        self.assertIn("모델별 CPU/RAM/VRAM 요구사항", high.describe())

    def test_source_features_distinguished_from_unimplemented(self):
        result = review_development_scope(self.os, self.hw)
        statuses = {item.name: item.source_status for item in result.items}
        self.assertEqual(statuses["설정·모의 채팅·SQLite 대화 기억"], "로컬 소스 구현됨")
        self.assertEqual(statuses["실제 3D VRM·방송 플랫폼 채팅·OBS 송출"], "미구현")
        self.assertIn("미구현", result.describe())

    def test_requires_explicitly_passed_choices(self):
        with self.assertRaises(TypeError):
            review_development_scope(None, self.hw)
        with self.assertRaises(TypeError):
            review_development_scope(self.os, None)
        with self.assertRaises(TypeError):
            review_development_scope({"os": "windows_11"}, self.hw)

    def test_pure_function_does_not_probe_system_or_network(self):
        with patch("platform.system", side_effect=AssertionError("OS scan")), \
             patch("os.cpu_count", side_effect=AssertionError("CPU scan")), \
             patch("subprocess.Popen", side_effect=AssertionError("program exec")), \
             patch("socket.create_connection", side_effect=AssertionError("network")):
            result = review_development_scope(self.os, self.hw)
            self.assertEqual(len(result.items), 6)

    def test_no_filesystem_touch_when_reviewing(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with patch("pathlib.Path.open", side_effect=AssertionError("file open")), \
                 patch("pathlib.Path.write_text", side_effect=AssertionError("file write")):
                review_development_scope(self.os, self.hw)
            self.assertEqual(list(folder.iterdir()), [])

    def test_user_approval_not_overridden(self):
        result = review_development_scope(self.os, self.hw)
        self.assertIn("10단계 운영자 최종 승인", result.describe())
        roadmap = json.loads((ROOT / "config/roadmap.json").read_text(encoding="utf-8"))
        self.assertTrue(all(roadmap["steps"][i]["status"] == "pending" for i in (9, 10, 11, 12)))

    def test_current_stage_name_not_mutated(self):
        roadmap = json.loads((ROOT / "config/roadmap.json").read_text(encoding="utf-8"))
        self.assertEqual(roadmap["steps"][12]["title"], "현재 PC로 가능한 개발 범위 분석")

    def test_gui_scope_tab_is_click_only(self):
        text = (ROOT / "src/ai_broadcaster/desktop.py").read_text(encoding="utf-8")
        self.assertIn('(scope_review, "개발 범위 검토")', text)
        self.assertIn('self._build_scope_review(scope_review)', text)
        self.assertIn('command=self._review_scope', text)
        self.assertNotIn('load_hardware_note(', text.split('def _review_scope(', 1)[1].split('def _build_development_review', 1)[0])

    def test_original_plan_untouched(self):
        original = (ROOT / "docs/ORIGINAL_PLAN.txt").read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         "d4482d539bf733fddc65263566b436e2547d64d43545ac3279581bc21c58180c")


if __name__ == "__main__":
    unittest.main()
