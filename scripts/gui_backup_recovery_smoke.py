"""19단계 GUI: 선택/검사/취소/수동 복구/중복 차단 및 기존 데이터 보존."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.backup_recovery import STAGING_NAME
from ai_broadcaster.manual_archive import create_archive, plan_archive
from ai_broadcaster.offline_settings import load_settings, save_settings


def main():
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        home = base / "user"
        settings = home / "settings.json"
        zip_path = base / "archive.zip"
        create_archive(plan_archive(), zip_path, confirmed=True)
        archive_bytes = zip_path.read_bytes()
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(settings)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda value: save_settings(value, settings)), \
             patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("probe")) as probe:
            app = AistingApp()
            try:
                app.update()
                app._tab_nav.set("백업·복구 준비")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "백업·복구 준비"
                assert not app._recovery_archive_path.get()
                assert not home.exists()
                assert not (base / STAGING_NAME).exists()
                app._inspect_recovery_zip()
                assert "먼저 선택" in app._recovery_status.get()
                with patch("ai_broadcaster.desktop.filedialog.askopenfilename", return_value=""):
                    app._choose_recovery_zip()
                assert "취소" in app._recovery_status.get()
                with patch("ai_broadcaster.desktop.filedialog.askopenfilename", return_value=str(zip_path)):
                    app._choose_recovery_zip()
                app._inspect_recovery_zip()
                assert "SHA256 검사 완료" in app._recovery_status.get()
                assert "19단계" in app._recovery_view.get("1.0", "end")
                assert not (base / STAGING_NAME).exists()
                with patch("ai_broadcaster.desktop.filedialog.askdirectory", return_value=""):
                    app._stage_recovery()
                assert "취소" in app._recovery_status.get()
                with patch("ai_broadcaster.desktop.filedialog.askdirectory", return_value=str(base)), \
                     patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False):
                    app._stage_recovery()
                assert not (base / STAGING_NAME).exists()
                with patch("ai_broadcaster.desktop.filedialog.askdirectory", return_value=str(base)), \
                     patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._stage_recovery()
                assert (base / STAGING_NAME / "project" / "docs" / "ORIGINAL_PLAN.txt").exists()
                assert "수동 복구 사본 생성 완료" in app._recovery_status.get()
                with patch("ai_broadcaster.desktop.filedialog.askdirectory", return_value=str(base)), \
                     patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._stage_recovery()
                assert "복구 사본 준비 실패" in app._recovery_status.get()
                assert zip_path.read_bytes() == archive_bytes
                assert not home.exists() and not settings.exists()
                net.assert_not_called()
                proc.assert_not_called()
                probe.assert_not_called()
            finally:
                app._shutdown()
    print("19단계 GUI · 탭 이동/검사/취소/수동 복구/중복 차단/원본 보존: 통과")


if __name__ == "__main__":
    main()
