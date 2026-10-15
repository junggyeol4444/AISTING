"""24단계 GUI: 무승인·취소 상태에서는 PC/네트워크 무조회, 승인 경로는 가짜 전송만."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings
from ai_broadcaster.core_ai_probe import ConnectionCheckResult


def main():
    with tempfile.TemporaryDirectory() as temp:
        settings_path = Path(temp) / "user" / "settings.json"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(settings_path)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda value: save_settings(value, settings_path)), \
             patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("sqlite3.connect", side_effect=AssertionError("sqlite")) as sql, \
             patch("platform.system", side_effect=AssertionError("pc info")) as pc, \
             patch("ai_broadcaster.desktop.probe_local_model", return_value=ConnectionCheckResult(
                 "model_available", "gemma3:4b", False)) as fake_probe:
            app = AistingApp()
            try:
                app.update()
                app._tab_nav.set("AI 연결 시험")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "AI 연결 시험"
                assert app._core_session is None
                assert "미실행" in app._core_probe_status.get()
                assert not settings_path.exists()
                app._simulate_core_ai_probe()
                assert "가상" in app._core_probe_status.get()
                assert "모의 답변" in app._core_probe_view.get("1.0", "end")
                app._run_core_ai_probe()  # mock 모드에서는 확인창도 열지 않음
                assert "불필요" in app._core_probe_status.get()
                app._core_ai_mode.set("로컬 Ollama (수동 선택)")
                app._core_ai_model.set("gemma3:4b")
                app._simulate_core_ai_probe()
                assert "실제 연결 증거 아님" in app._core_probe_view.get("1.0", "end")
                assert app._core_session is None
                app._core_ai_model.set("https://bad.example")
                app._simulate_core_ai_probe()
                assert "실패" in app._core_probe_status.get()
                app._core_ai_model.set("gemma3:4b")
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False) as dialog:
                    app._run_core_ai_probe()
                dialog.assert_called_once()
                assert "취소" in app._core_probe_status.get()
                fake_probe.assert_not_called()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._run_core_ai_probe()
                fake_probe.assert_called_once()
                assert fake_probe.call_args.kwargs == {"operator_confirmed": True}
                assert fake_probe.call_args.args[0].model_name == "gemma3:4b"
                assert "선택 모델 발견" in app._core_probe_status.get()
                assert app._core_session is None
                assert not settings_path.exists()
                assert app._runner.completed == []
                for guard in (net, proc, sql, pc):
                    guard.assert_not_called()
            finally:
                app._shutdown()
    print("24단계 GUI · 가상 응답/오류/승인 취소/가짜 승인/무접속: 통과")


if __name__ == "__main__":
    main()
