"""17단계 실행 환경 설정 GUI: 수동 저장/불러오기/적용/삭제, 무연결."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings
from ai_broadcaster.runtime_profile import load_profile


def main():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "appdata"
        settings = home / "settings.json"
        profile_path = home / "runtime_operator_profile.json"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(settings)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda v: save_settings(v, settings)), \
             patch("ai_broadcaster.desktop.profile_path", return_value=profile_path), \
             patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("probe")) as probe:
            app = AistingApp()
            try:
                app.update()
                assert not home.exists(), "앱 시작 시 새 프로필/폴더를 생성하면 안 됨"
                app._tab_nav.set("기본 실행 환경")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "기본 실행 환경"
                app._tab_nav.set("방송 설정")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "방송 설정"
                assert app._selected_mode.get() == "모의 답변 (인터넷 불필요)"
                assert app._runtime_mode.get() == "모의 답변 (인터넷 불필요)"
                app._preview_runtime_profile()
                assert "17단계" in app._runtime_view.get("1.0", "end")
                assert "PC 파일 조회/생성/네트워크 없음" in app._runtime_status.get()
                assert not home.exists()
                app._runtime_mode.set("로컬 Ollama (수동 선택)")
                app._preview_runtime_profile()
                assert "입력 오류" in app._runtime_status.get()
                app._runtime_model.set("llama3.2:3b")
                app._preview_runtime_profile()
                assert "127.0.0.1:11434" in app._runtime_view.get("1.0", "end")
                assert not home.exists()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False):
                    app._save_runtime_profile()
                assert not profile_path.exists()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._save_runtime_profile()
                assert load_profile(profile_path).model_name == "llama3.2:3b"
                assert app._selected_mode.get() == "모의 답변 (인터넷 불필요)", "저장만으로 연습 모드가 바뀌면 안 됨"
                app._runtime_mode.set("모의 답변 (인터넷 불필요)")
                app._runtime_model.set("")
                app._load_runtime_profile()
                assert app._runtime_mode.get() == "로컬 Ollama (수동 선택)"
                app._apply_runtime_profile()
                assert app._selected_mode.get() == "로컬 Ollama (수동 선택)"
                assert app._model_name.get() == "llama3.2:3b"
                assert not app._configured and not app._busy
                app._configured = True
                app._runtime_mode.set("모의 답변 (인터넷 불필요)")
                app._runtime_model.set("")
                app._apply_runtime_profile()
                assert "이미 시작한" in app._runtime_status.get()
                assert app._selected_mode.get() == "로컬 Ollama (수동 선택)"
                app._configured = False
                app._apply_runtime_profile()
                assert app._selected_mode.get() == "모의 답변 (인터넷 불필요)"
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False):
                    app._delete_runtime_profile()
                assert profile_path.exists()
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True):
                    app._delete_runtime_profile()
                assert not profile_path.exists()
                assert not settings.exists(), "기존 방송 설정을 변경하면 안 됨"
                assert not (home / "conversation.sqlite3").exists(), "기억 DB 생성 금지"
                net.assert_not_called()
                proc.assert_not_called()
                probe.assert_not_called()
            finally:
                app._shutdown()
    print("17단계 실행 환경 GUI · 계획/취소/수동 저장/불러오기/적용/삭제/연습중 변경차단/무전송: 통과")


if __name__ == "__main__":
    main()
