"""28단계 가상 Tk GUI: 명시적 저장·중복·조회·2회 삭제 확인·기존 데이터 보존."""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        user = Path(tmp) / "user"
        settings_path = user / "settings.json"
        memory_path = user / "conversation.sqlite3"
        record_path = user / "core_response_records.sqlite3"
        user.mkdir()
        settings_path.write_bytes(b"original-settings-unchanged")
        memory_path.write_bytes(b"original-memory-unchanged")
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(Path(tmp) / "absent_settings.json")), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda val: save_settings(val, Path(tmp) / "not_saved.json")), \
             patch("ai_broadcaster.desktop.response_records_path", return_value=record_path), \
             patch("socket.socket.connect", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("PC info")) as pc:
            app = AistingApp()
            try:
                app.update()
                app._tab_nav.set("응답 기록 저장")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "응답 기록 저장"
                assert "미실행" in app._response_record_status.get()
                assert not record_path.exists()

                # 탭 진입/미리보기/취소는 sqlite3.connect를 전혀 호출하지 않는다.
                with patch("sqlite3.connect", side_effect=AssertionError("sqlite without consent")) as sql:
                    app._preview_response_records()
                    assert "저장 후보 없음" in app._response_record_status.get()
                    app._core_enqueue()
                    app._core_run(50)
                    app._preview_response_records()
                    assert "2건 미리보기" in app._response_record_status.get()
                    assert "아직 파일 생성 없음" in app._response_record_view.get("1.0", "end")
                    with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False) as no:
                        app._save_response_records()
                        no.assert_called_once()
                    assert "저장 취소" in app._response_record_status.get()
                    sql.assert_not_called()
                assert not record_path.exists()

                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True) as yes:
                    app._save_response_records()
                    yes.assert_called_once()
                assert "신규 2건" in app._response_record_status.get()
                assert record_path.exists()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._save_response_records()
                assert "기존 중복 2건" in app._response_record_status.get()
                app._load_response_records()
                assert "최근 2건" in app._response_record_status.get()
                assert "AI(모의)" in app._response_record_view.get("1.0", "end")
                assert app._core_session.total_processed == 2
                assert app._core_session.pending_count == 0

                # 2단계 삭제 확인: 두 번째 거절 시에도 기록은 보존.
                with patch("ai_broadcaster.desktop.messagebox.askyesno", side_effect=[True, False]) as no2:
                    app._clear_response_records()
                    assert no2.call_count == 2
                app._load_response_records()
                assert "최근 2건" in app._response_record_status.get()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", side_effect=[True, True]) as yes2:
                    app._clear_response_records()
                    assert yes2.call_count == 2
                assert "2건 삭제" in app._response_record_status.get()
                app._load_response_records()
                assert "최근 0건" in app._response_record_status.get()
                assert app._core_session.total_processed == 2
                assert settings_path.read_bytes() == b"original-settings-unchanged"
                assert memory_path.read_bytes() == b"original-memory-unchanged"
                net.assert_not_called()
                proc.assert_not_called()
                pc.assert_not_called()
            finally:
                app._shutdown()
    print("28단계 GUI · 미리보기/동의 거절/수동 저장/중복/조회/2회 삭제/무접속: 통과")


if __name__ == "__main__":
    main()
