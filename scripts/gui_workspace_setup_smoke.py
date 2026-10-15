"""16단계 Tk GUI: 초기 무접근, 미리보기, 취소, 사용자 승인 후 생성, 재실행."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings
from ai_broadcaster.workspace_setup import MANIFEST_NAME, SUBFOLDERS, WORKSPACE_NAME


def main():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "user_data"
        settings = data / "settings.json"
        parent = Path(tmp) / "manual_parent"
        parent.mkdir()
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(settings)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda v: save_settings(v, settings)), \
             patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("probe")) as probe:
            app = AistingApp()
            try:
                app.update()
                assert not data.exists()
                assert not (parent / WORKSPACE_NAME).exists()
                assert app._workspace_parent.get() == ""
                app._preview_workspace()
                assert "입력 오류" in app._workspace_status.get()
                app._workspace_parent.set(str(parent))
                app._preview_workspace()
                assert "PC 파일 조회/생성 없음" in app._workspace_status.get()
                assert "16단계" in app._workspace_view.get("1.0", "end")
                assert not (parent / WORKSPACE_NAME).exists()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False):
                    app._create_workspace()
                assert "취소" in app._workspace_status.get()
                assert not (parent / WORKSPACE_NAME).exists()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._create_workspace()
                root = parent / WORKSPACE_NAME
                assert root.is_dir()
                assert all((root / name).is_dir() for name in SUBFOLDERS)
                assert (root / MANIFEST_NAME).is_file()
                assert "생성 완료" in app._workspace_status.get()
                (root / "notes" / "user.txt").write_text("keep", encoding="utf-8")
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._create_workspace()
                assert (root / "notes" / "user.txt").read_text(encoding="utf-8") == "keep"
                assert not data.exists(), "기존 사용자 설정을 변경하면 안 됨"
                net.assert_not_called()
                proc.assert_not_called()
                probe.assert_not_called()
            finally:
                app._shutdown()
    print("16단계 작업 공간 GUI · 미리보기/취소/수동 생성/재실행/기존 파일 보존/무전송: 통과")


if __name__ == "__main__":
    main()
