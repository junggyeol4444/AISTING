"""14단계 GUI: 안내 표시만 수행, 설치/가격/사용자 PC/네트워크 조회 없음."""
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
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "private_user_data"
        settings = data / "settings.json"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(settings)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda v: save_settings(v, settings)), \
             patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("PC scan")) as probe:
            app = AistingApp()
            try:
                app.update()
                guide = app._cost_view.get("1.0", "end").strip()
                for expected in ("14단계", "Python 3.11 이상", "Ollama", "OBS Studio",
                                 "GPT-SoVITS", "총액: 미산정", "15단계 프로그램 설치 승인"):
                    assert expected in guide, expected
                assert app._cost_view.cget("state") == "disabled"
                assert not app._cost_guide.installation_approved
                assert not app._cost_guide.payment_approved
                assert not app._cost_guide.checked_current_prices
                assert not data.exists(), "탭 생성만으로 사용자 데이터를 읽거나 저장하면 안 됨"
                net.assert_not_called()
                proc.assert_not_called()
                probe.assert_not_called()
            finally:
                app._shutdown()
    print("14단계 프로그램·비용 안내 GUI · 전 항목 표시/조회 없음/설치 없음/결제 없음: 통과")


if __name__ == "__main__":
    main()
