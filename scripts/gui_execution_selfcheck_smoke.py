"""20단계 가상 GUI: 탭 이동, 클릭 전 무동작, 명시적 점검, 오류 표시."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.execution_selfcheck import ExecutionCheck, ExecutionReport
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
             patch("platform.system", side_effect=AssertionError("hardware probe")) as hardware:
            app = AistingApp()
            try:
                app.update()
                app._tab_nav.set("개발 환경 자가점검")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "개발 환경 자가점검"
                assert "검사 전" in app._selfcheck_status.get()
                assert "20단계" in app._selfcheck_view.get("1.0", "end")
                assert not user.exists(), "탭 표시만으로 사용자 설정 경로를 생성함"
                with patch("ai_broadcaster.desktop.run_execution_selfcheck", wraps=__import__(
                    "ai_broadcaster.execution_selfcheck", fromlist=["run_execution_selfcheck"]
                ).run_execution_selfcheck) as check:
                    assert check.call_count == 0
                    app._run_execution_selfcheck()
                    app.update()
                    assert check.call_count == 1
                assert "5/5 통과" in app._selfcheck_status.get()
                assert "240개" in app._selfcheck_view.get("1.0", "end")
                assert not user.exists(), "자가점검 중 사용자 데이터 경로를 생성함"
                fail = ExecutionReport((ExecutionCheck("실패 주입", False, "검증 실패"),))
                with patch("ai_broadcaster.desktop.run_execution_selfcheck", return_value=fail):
                    app._run_execution_selfcheck()
                assert "실패" in app._selfcheck_status.get()
                assert "[실패]" in app._selfcheck_view.get("1.0", "end")
                with patch("ai_broadcaster.desktop.run_execution_selfcheck", side_effect=RuntimeError("internal")):
                    app._run_execution_selfcheck()
                assert "실패" in app._selfcheck_status.get()
                assert "완료 처리하지" in app._selfcheck_view.get("1.0", "end")
                assert not user.exists()
                net.assert_not_called()
                proc.assert_not_called()
                hardware.assert_not_called()
            finally:
                app._shutdown()
    print("20단계 GUI · 수동 자가점검/오류/탭 이동/기존 데이터 보존: 통과")


if __name__ == "__main__":
    main()
