"""10단계 승인 검토 GUI: 실제 PC 사양/서버/결제/OBS 없이 Tk 가상 화면 점검."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.development_review import evaluate_review, approval_status, load_review_sources
from ai_broadcaster.offline_settings import load_settings, save_settings


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        local=Path(folder)/"local"
        config=local/"settings.json"
        receipt=local/"development_criteria_approval.json"
        with patch("ai_broadcaster.desktop.load_settings",side_effect=lambda:load_settings(config)), \
             patch("ai_broadcaster.desktop.save_settings",side_effect=lambda v:save_settings(v,config)), \
             patch("ai_broadcaster.desktop.approval_path",return_value=receipt), \
             patch("ai_broadcaster.local_runtime.data_dir",return_value=local), \
             patch("socket.create_connection") as network, \
             patch("subprocess.Popen") as process:
            app=AistingApp()
            try:
                app.update()
                assert not local.exists(),"검토 탭 열기만으로 PC 파일을 만들면 안 됨"
                assert app._review_report is None
                assert app._review_confirmation.get() is False

                app._refresh_review()
                app.update()
                assert app._review_report.ready
                assert "검토" in app._review_text.get("1.0","end")
                assert not local.exists(),"읽기 전용 검토가 폴더를 만들면 안 됨"

                with patch("ai_broadcaster.desktop.messagebox.showwarning") as warning:
                    app._approve_review()
                    warning.assert_called_once()
                    assert not receipt.exists()

                app._review_confirmation.set(True)
                with patch("ai_broadcaster.desktop.messagebox.askyesno",return_value=False):
                    app._approve_review()
                    assert not receipt.exists()

                app._review_confirmation.set(True)
                with patch("ai_broadcaster.desktop.messagebox.askyesno",return_value=True):
                    app._approve_review()
                    app.update()
                assert receipt.exists()
                assert "수동 승인 기록" in app._review_status.get()
                saved=json.loads(receipt.read_text(encoding="utf-8"))
                assert saved["scope"].startswith("development_criteria_only")

                app._persona_mode.set("직접 만들기")
                app._persona["name"].delete(0,"end")
                app._persona["name"].insert(0,"새 캐릭터")
                # Only explicit character approval invalidates character-sensitive reviews.
                app._save_character_identity()
                app._save()
                app._refresh_review()
                assert "승인 대기" in app._review_status.get(),"PC 설정이 바뀌면 이전 승인을 인정하면 안 됨"
                assert receipt.exists(),"변경으로 승인 효력만 해제하고 기존 파일은 자동 삭제 안 함"

                with patch("ai_broadcaster.desktop.messagebox.askyesno",return_value=False):
                    app._revoke_review()
                    assert receipt.exists()
                with patch("ai_broadcaster.desktop.messagebox.askyesno",return_value=True):
                    app._revoke_review()
                assert not receipt.exists()
                assert config.exists(),"검토 취소가 사용자 설정을 손상시키면 안 됨"
                network.assert_not_called()
                process.assert_not_called()
            finally:
                app._shutdown()
    print("10단계 승인 검토 GUI · 체크/확인/기록/무효화/취소 · 네트워크 없음: 통과")


if __name__=="__main__":
    main()
