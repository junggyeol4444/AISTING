"""18단계 GUI: 화면 이동, 무조회 미리보기, 취소, 수동 ZIP, 원본 보존."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.manual_archive import verify_archive
from ai_broadcaster.offline_settings import load_settings, save_settings


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        home = root / "appdata"
        settings = home / "settings.json"
        destination = root / "operator_archive.zip"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(settings)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda value: save_settings(value, settings)), \
             patch("ai_broadcaster.manual_archive.settings_file", return_value=settings), \
             patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("PC probe")) as probe:
            app = AistingApp()
            try:
                app.update()
                assert not home.exists(), "앱 시작 시 설정을 쓰거나 읽어서는 안 됨"
                app._tab_nav.set("기획안·설정 보관")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "기획안·설정 보관"
                assert not app._archive_settings.get()
                assert not app._archive_runtime.get()
                app._preview_manual_archive()
                assert "18단계" in app._archive_view.get("1.0", "end")
                assert "파일 조회/생성/네트워크 없음" in app._archive_status.get()
                assert not destination.exists() and not home.exists()
                with patch("ai_broadcaster.desktop.filedialog.asksaveasfilename", return_value=""):
                    app._create_manual_archive()
                assert "취소" in app._archive_status.get()
                with patch("ai_broadcaster.desktop.filedialog.asksaveasfilename", return_value=str(destination)), \
                     patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False):
                    app._create_manual_archive()
                assert not destination.exists()
                with patch("ai_broadcaster.desktop.filedialog.asksaveasfilename", return_value=str(destination)), \
                     patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._create_manual_archive()
                assert destination.exists()
                assert len(verify_archive(destination)["entries"]) == 3
                assert "수동 ZIP 보관 완료" in app._archive_status.get()
                with patch("ai_broadcaster.desktop.filedialog.asksaveasfilename", return_value=str(destination)), \
                     patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._create_manual_archive()
                assert "보관 실패" in app._archive_status.get()
                assert not home.exists() and not settings.exists()
                net.assert_not_called()
                proc.assert_not_called()
                probe.assert_not_called()
            finally:
                app._shutdown()
    print("18단계 GUI · 탭 이동/무조회 미리보기/취소/수동 보관/중복 차단/무전송: 통과")


if __name__ == "__main__":
    main()
