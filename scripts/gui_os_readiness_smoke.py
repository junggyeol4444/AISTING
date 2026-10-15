"""11단계 수동 OS 입력 GUI: PC 시스템 조회/네트워크/설치 없음."""
from __future__ import annotations

import json
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
        home = Path(tmp) / "local"
        settings = home / "settings.json"
        note = home / "os_operator_note.json"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(settings)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda s: save_settings(s, settings)), \
             patch("ai_broadcaster.desktop.os_note_path", return_value=note), \
             patch("ai_broadcaster.local_runtime.data_dir", return_value=home), \
             patch("socket.create_connection") as dial, \
             patch("subprocess.Popen") as proc, \
             patch("platform.system", side_effect=AssertionError("OS auto probe")) as probe:
            app = AistingApp()
            try:
                app.update()
                assert not home.exists(), "화면 진입만으로 사용자 폴더를 만들면 안 됨"
                assert "미검사" in app._os_status.get()
                app._assess_os_choice()
                assert "미확인" in app._os_status.get()
                assert not home.exists()
                app._os_choice.set("Windows 11 (직접 입력)")
                app._os_arch.set("64비트 x64 (직접 입력)")
                app._assess_os_choice()
                assert "실제 AISTING.exe" in app._os_status.get()
                assert "실기기 검증: 미완료" in app._os_status.get()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False):
                    app._save_os_choice()
                assert not note.exists(), "취소된 승인에는 파일 작성 금지"
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._save_os_choice()
                assert note.exists()
                data = json.loads(note.read_text(encoding="utf-8"))
                assert data["source"] == "operator_self_report"
                app._os_choice.set("확인하지 않음")
                app._os_arch.set("확인하지 않음")
                app._load_os_choice()
                assert app._os_choice.get() == "Windows 11 (직접 입력)"
                assert app._os_arch.get() == "64비트 x64 (직접 입력)"
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False):
                    app._delete_os_choice()
                assert note.exists()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._delete_os_choice()
                assert not note.exists()
                dial.assert_not_called()
                proc.assert_not_called()
                probe.assert_not_called()
                assert not settings.exists(), "OS 입력은 방송 설정 파일을 건드리지 않음"
            finally:
                app._shutdown()
    print("11단계 OS 수동 입력 GUI · 평가/저장확인/불러오기/삭제/무조회·무전송: 통과")


if __name__ == "__main__":
    main()
