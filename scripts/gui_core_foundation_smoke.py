"""21단계 GUI: 수동 구성도, 선택형 설정, 오류 처리, 무연결 확인."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings


def main():
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        user = base / "operator"
        settings = user / "settings.json"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(settings)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda value: save_settings(value, settings)), \
             patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("hardware")) as hardware:
            app = AistingApp()
            try:
                app.update()
                app._tab_nav.set("방송 코어 구성도")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "방송 코어 구성도"
                assert "미검토" in app._core_status.get()
                assert "실제 방송 코어 실행" in app._core_view.get("1.0", "end")
                assert not user.exists(), "탭 열기만으로 사용자 파일을 생성함"
                app._preview_core_foundation()
                assert "7개" in app._core_status.get()
                assert "미선택" in app._core_view.get("1.0", "end")
                assert "실제 방송 송출 [미구현]" in app._core_view.get("1.0", "end")
                assert not user.exists()
                app._platforms["youtube"].set(True)
                app._content.set("수다 + 게임")
                app._avatar.set("3D")
                app._voice.set("Windows 무료 음성")
                app._preview_core_foundation()
                report = app._core_view.get("1.0", "end")
                assert "youtube" in report and "both" in report and "3d" in report
                assert "Windows 음성 수동 미리듣기" in report
                assert "아바타 출력 [미구현]" in report
                app._selected_mode.set("로컬 Ollama (수동 선택)")
                app._preview_core_foundation()
                assert "연결/설치 미검증" in app._core_view.get("1.0", "end")
                app._content.set("잘못된 값")
                app._preview_core_foundation()
                assert "실패" in app._core_status.get()
                assert "구성도 생성 실패" in app._core_view.get("1.0", "end")
                assert not user.exists(), "미리보기로 사용자 설정/기억이 변경됨"
                net.assert_not_called()
                proc.assert_not_called()
                hardware.assert_not_called()
            finally:
                app._shutdown()
    print("21단계 GUI · 선택형 코어 구성도/미구현 구분/오류/무연결: 통과")


if __name__ == "__main__":
    main()
