"""9단계: 실제 네트워크와 PC 하드웨어 사양을 건드리지 않는 GUI 점검."""
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
    with tempfile.TemporaryDirectory() as folder, patch("socket.create_connection") as network:
        data = Path(folder) / "data"
        config = data / "settings.json"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(config)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda value: save_settings(value, config)), \
             patch("ai_broadcaster.local_runtime.data_dir", return_value=data):
            app = AistingApp()
            try:
                app.update()
                assert not data.exists(), "GUI를 열기만 했는데 PC 저장 폴더를 만들면 안 됨"
                assert app._local_plan.settings_path == data / "settings.json"
                assert "검사 전" in app._local_check_status.get()
                assert "GitHub" in app._local_plan.describe()
                assert app._local_plan.github_required is False
                assert app._local_plan.scheduled_execution is False
                app._check_pc_storage()
                app.update()
                assert "통과" in app._local_check_status.get()
                assert data.is_dir() and not list(data.iterdir())
                app._save()
                assert load_settings(config)["host"] == "local_pc"
                assert "127.0.0.1" in app._local_plan.describe()
                network.assert_not_called()
            finally:
                app._shutdown()
    print("9단계 PC 로컬 운영 GUI · 수동 점검 · 원본 보존 · 네트워크 미사용: 통과")


if __name__ == "__main__":
    main()
