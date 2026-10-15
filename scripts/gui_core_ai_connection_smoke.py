"""23단계 가상 GUI: 모의/로컬 AI 연결 계획 검증, 네트워크/파일 무변경."""
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
        user = Path(temp) / "operator"
        settings_path = user / "settings.json"
        core_profile_path = user / "core_ai_operator_profile.json"
        with patch("ai_broadcaster.desktop.core_ai_profile_path", return_value=core_profile_path), \
             patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(settings_path)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda value: save_settings(value, settings_path)), \
             patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("urllib.request.urlopen", side_effect=AssertionError("url")) as url, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("sqlite3.connect", side_effect=AssertionError("sqlite")) as sql, \
             patch("platform.system", side_effect=AssertionError("pc info")) as pc:
            app = AistingApp()
            try:
                app.update()
                app._tab_nav.set("코어 AI 연결 방식")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "코어 AI 연결 방식"
                assert app._core_session is None
                assert app._core_ai_mode.get() == "모의 답변 (인터넷 불필요)"
                app._preview_core_ai()
                assert "오프라인 계획" in app._core_ai_status.get()
                assert app._core_session is None
                app._core_ai_mode.set("로컬 Ollama (수동 선택)")
                app._core_ai_model.set("gemma3:4b")
                app._preview_core_ai()
                assert "127.0.0.1:11434" in app._core_ai_view.get("1.0", "end")
                assert app._core_session is None
                app._platforms["youtube"].set(True)
                app._core_enqueue()
                assert app._core_session.pending_count == 2
                app._apply_core_ai()
                assert app._core_session.ai_plan.mode == "local_ollama"
                assert app._core_session.blueprint.runtime_mode == "mock"
                assert app._core_session.pending_count == 2
                app._core_run(1)
                assert app._core_session.total_processed == 1
                assert "AI(모의)" in app._core_exec_view.get("1.0", "end")
                app._core_ai_model.set("https://external.example")
                app._apply_core_ai()
                assert "실패" in app._core_ai_status.get()
                assert app._core_session.ai_plan.model_name == "gemma3:4b"
                assert app._core_session.pending_count == 1
                app._reset_core_ai()
                assert app._core_session.ai_plan.mode == "mock"
                assert app._core_session.pending_count == 1
                assert app._core_session.total_processed == 1
                assert not user.exists(), "자동으로 설정/기억 파일을 만들면 안 됨"
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False):
                    app._save_core_ai()
                assert not user.exists(), "취소 시 파일을 만들면 안 됨"
                app._core_ai_mode.set("로컬 Ollama (수동 선택)")
                app._core_ai_model.set("gemma3:4b")
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._save_core_ai()
                assert core_profile_path.exists()
                assert not settings_path.exists()
                app._core_ai_model.set("bad name")
                app._load_core_ai()
                assert app._core_ai_model.get() == "gemma3:4b"
                assert app._core_session.ai_plan.mode == "mock", "불러오기는 자동 적용 아님"
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False):
                    app._delete_core_ai()
                assert core_profile_path.exists()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._delete_core_ai()
                assert not core_profile_path.exists()
                assert not settings_path.exists()
                assert app._runner.completed == []
                for item in (net, url, proc, sql, pc):
                    item.assert_not_called()
            finally:
                app._shutdown()
    print("23단계 GUI · 모의/로컬 계획 선택/미리보기/적용/오류/초기화/무전송: 통과")


if __name__ == "__main__":
    main()
