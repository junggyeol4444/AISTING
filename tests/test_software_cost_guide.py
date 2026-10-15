"""14단계: 비용 안내만 구현. 실제 설치/가격 확인/승인/송출은 수행하지 않는다."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.software_cost_guide import build_software_cost_guide


class TestSoftwareCostGuide(unittest.TestCase):
    def setUp(self):
        self.guide = build_software_cost_guide()
        self.report = self.guide.describe()

    def test_has_all_groups_in_one_report(self):
        self.assertEqual(len(self.guide.items), 17)
        for heading in ("현재 로컬 소스 실행", "선택형 로컬 AI / 빌드",
                        "향후 실방송 기능 (현재 미구현)", "향후 확장 후보 (미확정)",
                        "기타 실사용 비용"):
            self.assertIn(f"[{heading}]", self.report)

    def test_python_and_bundled_stdlib(self):
        for term in ("Python 3.11 이상", "Tkinter", "sqlite3", "JSON"):
            self.assertIn(term, self.report)

    def test_current_features_not_claimed_installed(self):
        self.assertIn("현재 소스에 포함", self.report)
        self.assertIn("사용자 PC에 설치/모델 다운로드 여부 미확인", self.report)
        self.assertFalse(self.guide.checked_pc_installations)

    def test_os_cost_not_assumed_zero(self):
        self.assertIn("Windows 라이선스", self.report)
        self.assertIn("PC·OS를 무료라고 간주하지 않음", self.report)

    def test_local_llm_not_auto_downloaded(self):
        self.assertIn("Ollama", self.report)
        self.assertIn("모델 미포함", self.report)
        self.assertIn("자동 다운로드 없음", self.report)

    def test_optional_exe_tool_not_claimed_built(self):
        self.assertIn("PyInstaller", self.report)
        self.assertIn("EXE 미제공", self.report)
        self.assertIn("실제 빌드·실행하지 않았", self.report)

    def test_broadcast_is_future_only(self):
        for term in ("OBS Studio", "obs-websocket", "Live2D", "VTube Studio", "3D VRM"):
            self.assertIn(term, self.report)
        self.assertIn("실제 연동/송출 미구현", self.report)
        self.assertFalse(self.guide.live_broadcast_ready)

    def test_original_plan_base_not_misrepresented(self):
        self.assertIn("Open-LLM-VTuber", self.report)
        self.assertIn("현재 AISTING 코드의 실제 기반 아님", self.report)

    def test_voice_rights_and_license_caution(self):
        self.assertIn("GPT-SoVITS", self.report)
        self.assertIn("음성 제공자 동의·라이선스·사용자 승인 없이", self.report)
        self.assertIn("상업적 방송 이용", self.report)

    def test_hidden_running_costs_not_mislabeled_free(self):
        for term in ("전기", "하드웨어", "저장 공간", "전체 예상 총액: 미산정"):
            self.assertIn(term, self.report)
        self.assertNotIn("전체 예상 총액: 0원", self.report)

    def test_no_fake_current_price(self):
        self.assertFalse(self.guide.checked_current_prices)
        self.assertIn("모든 가격은 현재 시세 미확인", self.report)

    def test_no_implicit_install_approval(self):
        self.assertFalse(self.guide.installation_approved)
        self.assertFalse(self.guide.payment_approved)
        self.assertIn("15단계 프로그램 설치 승인", self.report)
        self.assertIn("설치·다운로드·구매", self.report)

    def test_frozen_catalog(self):
        with self.assertRaises(FrozenInstanceError):
            self.guide.installation_approved = True
        with self.assertRaises(FrozenInstanceError):
            self.guide.items[0].cost = "0원 확정"

    def test_each_item_has_real_usage_and_cost_caution(self):
        self.assertEqual(len({item.name for item in self.guide.items}), len(self.guide.items))
        for item in self.guide.items:
            for field in (item.category, item.name, item.purpose, item.usage, item.cost, item.caution):
                self.assertTrue(field.strip())

    def test_pure_no_network_filesystem_or_machine_probing(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("platform.system", side_effect=AssertionError("PC scan")), \
                 patch("os.cpu_count", side_effect=AssertionError("CPU scan")), \
                 patch("subprocess.Popen", side_effect=AssertionError("process exec")), \
                 patch("socket.create_connection", side_effect=AssertionError("network")), \
                 patch("pathlib.Path.open", side_effect=AssertionError("file read")), \
                 patch("pathlib.Path.write_text", side_effect=AssertionError("file write")):
                result = build_software_cost_guide().describe()
            self.assertIn("프로그램·비용", result)
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_gui_integrated_as_static_display(self):
        source = (ROOT / "src/ai_broadcaster/desktop.py").read_text(encoding="utf-8")
        self.assertIn('(software_cost, "프로그램·비용 안내")', source)
        self.assertIn("self._build_software_cost_guide(software_cost)", source)
        self.assertIn('self._cost_view.configure(state="disabled")', source)

    def test_roadmap_10_through_15_pending(self):
        roadmap = json.loads((ROOT / "config/roadmap.json").read_text(encoding="utf-8"))
        self.assertEqual(len(roadmap["steps"]), 100)
        self.assertTrue(all(roadmap["steps"][i]["status"] == "pending" for i in range(9, 15)))
        self.assertEqual(roadmap["steps"][13]["title"], "필요한 프로그램과 비용 일괄 안내")

    def test_original_plan_hash_unchanged(self):
        original = (ROOT / "docs/ORIGINAL_PLAN.txt").read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         "d4482d539bf733fddc65263566b436e2547d64d43545ac3279581bc21c58180c")


if __name__ == "__main__":
    unittest.main()
