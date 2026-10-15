"""22단계 가상 Tk 화면: 수동 모의 코어만 실행, 기존 사용자 파일/네트워크 불변."""
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
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(settings_path)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda value: save_settings(value, settings_path)), \
             patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("sqlite3.connect", side_effect=AssertionError("sqlite")) as sql, \
             patch("platform.system", side_effect=AssertionError("PC info")) as pc:
            app = AistingApp()
            try:
                app.update()
                app._tab_nav.set("기본 코어 수동 실행")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "기본 코어 수동 실행"
                assert app._core_session is None
                assert not user.exists()
                # Ollama 선택 상태라도 새 코어는 모의 전용.
                app._selected_mode.set("로컬 Ollama (수동 선택)")
                app._platforms["youtube"].set(True)
                app._avatar.set("3D")
                app._core_enqueue()
                assert app._core_session.pending_count == 2
                assert app._core_session.total_processed == 0
                assert app._core_session.blueprint.runtime_mode == "mock"
                assert app._core_session.blueprint.platforms == ("youtube",)
                app._core_run(1)
                assert app._core_session.pending_count == 1
                assert "AI(모의)" in app._core_exec_view.get("1.0", "end")
                app._core_run(50)
                assert app._core_session.pending_count == 0
                assert app._core_session.total_processed == 2
                app._core_input.insert("1.0", "잘못된 형식")
                app._core_enqueue()
                assert "오류" in app._core_exec_status.get()
                assert app._core_session.total_processed == 2
                app._core_input.delete("1.0", "end")
                app._core_input.insert("1.0", "세라: 다시")
                app._core_enqueue()
                app._content.set("잘못된 값")
                app._core_run(1)
                assert "실행 전 검증 실패" in app._core_exec_status.get()
                assert app._core_session.pending_count == 1
                app._content.set("미정")
                app._core_run(1)
                assert app._core_session.total_processed == 3
                app._core_reset()
                assert app._core_session.total_processed == 0
                assert app._core_session.pending_count == 0
                assert not user.exists(), "모의 코어가 사용자 데이터를 생성함"
                assert app._runner.completed == []
                net.assert_not_called()
                proc.assert_not_called()
                sql.assert_not_called()
                pc.assert_not_called()
            finally:
                app._shutdown()
    print("22단계 GUI · 수동 모의 코어 FIFO/재시도/선택값/오류/무전송: 통과")


if __name__ == "__main__":
    main()
