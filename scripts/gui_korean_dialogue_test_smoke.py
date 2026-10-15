"""25단계 가상 Tk GUI: 실제 사용자 파일·SQLite·PC/네트워크 접근 없이 모의 한국어 구조 시험."""
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
        path = Path(temp) / "user" / "settings.json"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(path)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda data: save_settings(data, path)), \
             patch("socket.socket.connect", side_effect=AssertionError("network")) as net, \
             patch("sqlite3.connect", side_effect=AssertionError("sqlite")) as sql, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("pc info")) as pc:
            app = AistingApp()
            try:
                app.update()
                app._tab_nav.set("한국어 대화 시험")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "한국어 대화 시험"
                assert "미실행" in app._korean_test_status.get()
                assert not path.exists()
                app._selected_mode.set("로컬 Ollama (수동 선택)")
                app._platforms["youtube"].set(True)
                app._avatar.set("3D")
                app._run_korean_dialogue_test()
                assert "7/7" in app._korean_test_status.get()
                assert "실제 AI 품질" in app._korean_test_view.get("1.0", "end")
                assert app._core_session is None
                assert app._runner.completed == []
                app._korean_test_input.delete("1.0", "end")
                app._korean_test_input.insert("1.0", "별: 안녕\n별: 안녕")
                app._run_korean_dialogue_test()
                assert "2/2" in app._korean_test_status.get()
                app._korean_test_input.delete("1.0", "end")
                app._korean_test_input.insert("1.0", "invalid")
                app._run_korean_dialogue_test()
                assert "오류" in app._korean_test_status.get()
                assert "실행 전 검증 실패" in app._korean_test_view.get("1.0", "end")
                app._korean_test_input.delete("1.0", "end")
                app._korean_test_input.insert("1.0", "a: hello")
                app._run_korean_dialogue_test()
                assert "오류" in app._korean_test_status.get()
                app._content.set("잘못된 콘텐츠")
                app._korean_test_input.delete("1.0", "end")
                app._korean_test_input.insert("1.0", "별: 안녕")
                app._run_korean_dialogue_test()
                assert "오류" in app._korean_test_status.get()
                app._content.set("미정")
                app._reset_korean_test_input()
                assert "하늘: 안녕하세요" in app._korean_test_input.get("1.0", "end")
                assert "실행/저장/연결 없음" in app._korean_test_status.get()
                assert not path.exists()
                for guard in (net, sql, proc, pc):
                    guard.assert_not_called()
            finally:
                app._shutdown()
    print("25단계 GUI · 한국어 모의 시험/중복/입력 오류/초기화/무접속: 통과")


if __name__ == "__main__":
    main()
