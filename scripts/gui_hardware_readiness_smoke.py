"""12단계 GUI 실제 Tk 테스트: 확인 없이 자동 하드웨어 조회/저장 하지 않음."""
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


def set_field(app, key, value):
    field = app._hardware_fields[key]
    field.delete(0, "end")
    field.insert(0, value)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "appdata"
        settings_path = home / "settings.json"
        note = home / "hardware_operator_note.json"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(settings_path)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda cfg: save_settings(cfg, settings_path)), \
             patch("ai_broadcaster.desktop.hardware_note_path", return_value=note), \
             patch("ai_broadcaster.local_runtime.data_dir", return_value=home), \
             patch("socket.create_connection") as network, \
             patch("subprocess.Popen") as process, \
             patch("platform.system", side_effect=AssertionError("machine probe")) as probe:
            app = AistingApp()
            try:
                app.update()
                assert not home.exists(), "화면 생성만으로 PC 설정을 저장하지 않아야 함"
                assert "확인하지 않았습니다" in app._hardware_status.get()
                app._assess_hardware_choice()
                assert "추가 확인 참고" in app._hardware_status.get()
                set_field(app, "cpu_name", "Test x64 CPU")
                set_field(app, "cpu_cores", "8")
                set_field(app, "ram_gb", "16")
                set_field(app, "gpu_name", "Test GPU")
                set_field(app, "gpu_vram_gb", "0")
                app._assess_hardware_choice()
                assert "16 GB" in app._hardware_status.get()
                assert "성능 또는 실행 가능 여부" in app._hardware_status.get()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False):
                    app._save_hardware_choice()
                assert not note.exists()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._save_hardware_choice()
                assert note.exists()
                assert json.loads(note.read_text(encoding="utf-8"))["source"] == "operator_self_report"
                set_field(app, "cpu_name", "")
                set_field(app, "ram_gb", "")
                app._load_hardware_choice()
                assert app._hardware_fields["cpu_name"].get() == "Test x64 CPU"
                assert app._hardware_fields["ram_gb"].get() == "16"
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False):
                    app._delete_hardware_choice()
                assert note.exists()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._delete_hardware_choice()
                assert not note.exists()
                assert not settings_path.exists()
                network.assert_not_called()
                process.assert_not_called()
                probe.assert_not_called()
            finally:
                app._shutdown()
    print("12단계 하드웨어 수동 입력 GUI · 확인/저장/복원/삭제/무조회/무전송: 통과")


if __name__ == "__main__":
    main()
