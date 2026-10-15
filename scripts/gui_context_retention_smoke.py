"""26단계 가상 GUI: 수동 모의 맥락 검증 및 기존 데이터 무변경."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "settings.json"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(path)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda data: save_settings(data, path)), \
             patch("socket.socket.connect", side_effect=AssertionError("network")) as net, \
             patch("sqlite3.connect", side_effect=AssertionError("sqlite")) as sql, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("pc info")) as pc:
            app = AistingApp()
            try:
                app.update()
                app._tab_nav.set("대화 맥락 전달 시험")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "대화 맥락 전달 시험"
                assert "미실행" in app._context_test_status.get()
                assert not path.exists()
                app._selected_mode.set("로컬 Ollama (수동 선택)")
                app._platforms["youtube"].set(True)
                app._avatar.set("3D")
                app._run_context_retention_test()
                assert "11/11" in app._context_test_status.get()
                assert "잘림" in app._context_test_view.get("1.0", "end")
                assert "실제 AI" in app._context_test_status.get()
                assert app._core_session is None
                assert app._runner.completed == []
                app._context_test_input.delete("1.0", "end")
                app._context_test_input.insert("1.0", "가: 같은 말\n가: 같은 말")
                app._run_context_retention_test()
                assert "2/2" in app._context_test_status.get()
                assert "미실행" in app._context_test_view.get("1.0", "end")
                app._context_test_input.delete("1.0", "end")
                app._context_test_input.insert("1.0", "invalid")
                app._run_context_retention_test()
                assert "오류" in app._context_test_status.get()
                app._context_test_input.delete("1.0", "end")
                app._context_test_input.insert("1.0", "가: 하나")
                app._run_context_retention_test()
                assert "오류" in app._context_test_status.get()
                app._content.set("invalid")
                app._context_test_input.delete("1.0", "end")
                app._context_test_input.insert("1.0", "가: 하나\n나: 둘")
                app._run_context_retention_test()
                assert "오류" in app._context_test_status.get()
                app._content.set("미정")
                app._reset_context_test_input()
                assert "은하예요" in app._context_test_input.get("1.0", "end")
                assert "실행/저장/연결 없음" in app._context_test_status.get()
                assert not path.exists()
                for spy in (net, sql, proc, pc):
                    spy.assert_not_called()
            finally:
                app._shutdown()
    print("26단계 GUI · 맥락 전달/잘림/중복/오류/초기화/무접속: 통과")


if __name__ == "__main__":
    main()
