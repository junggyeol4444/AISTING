"""13단계 GUI: 현재 화면의 수동 OS·하드웨어 값만으로 오프라인 범위표 생성."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings


def set_field(app, key, value):
    entry = app._hardware_fields[key]
    entry.delete(0, "end")
    entry.insert(0, value)


def report(app):
    return app._scope_view.get("1.0", "end").strip()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / "user_data"
        settings = folder / "settings.json"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(settings)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda v: save_settings(v, settings)), \
             patch("ai_broadcaster.local_runtime.data_dir", return_value=folder), \
             patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("PC probe")) as probe:
            app = AistingApp()
            try:
                app.update()
                assert not folder.exists(), "화면만 열어도 PC 기록이 생성되면 안 됨"
                assert "아직 검토하지" in app._scope_status.get()
                app._review_scope()
                assert "운영체제/시스템 종류가 미입력" in report(app)
                assert "미구현" in report(app)
                assert not folder.exists()
                app._os_choice.set("Windows 11 (직접 입력)")
                app._os_arch.set("64비트 x64 (직접 입력)")
                for k, v in (("cpu_name", "Example CPU"), ("cpu_cores", "8"),
                             ("ram_gb", "16"), ("gpu_name", "Example GPU"), ("gpu_vram_gb", "8")):
                    set_field(app, k, v)
                app._review_scope()
                assert "Windows 10/11 x64 빌드 검토 후보" in report(app)
                assert "실제 실행은 검증되지" in report(app)
                assert "FPS·응답 속도를 예측하지" in report(app)
                assert "실제 방송" in report(app)
                assert "미검증" in app._scope_status.get()
                set_field(app, "ram_gb", "-10")
                app._review_scope()
                assert "입력 오류" in report(app), "잘못된 입력에서 이전 결과를 유지하면 안 됨"
                assert "검토 실패" in app._scope_status.get()
                assert not folder.exists(), "범위표는 저장하거나 PC를 조회하지 않음"
                net.assert_not_called()
                proc.assert_not_called()
                probe.assert_not_called()
            finally:
                app._shutdown()
    print("13단계 범위 검토 GUI · 사용자 입력/미검증 표시/입력 오류/무조회/무전송: 통과")


if __name__ == "__main__":
    main()
