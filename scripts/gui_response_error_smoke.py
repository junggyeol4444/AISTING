"""27단계 GUI: 오프라인 오류 주입·재시도·제외 확인·데이터 무변경."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.core_execution import OfflineCoreSession
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings
from ai_broadcaster.response_error_test import FaultPort


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "settings.json"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(path)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda data: save_settings(data, path)), \
             patch("socket.socket.connect", side_effect=AssertionError("network")) as net, \
             patch("sqlite3.connect", side_effect=AssertionError("sqlite")) as sql, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("pc info")) as pc:
            app = AistingApp()
            try:
                app.update()
                app._tab_nav.set("응답 오류 처리 시험")
                app._tab_nav_widget.event_generate("<<ComboboxSelected>>")
                app.update()
                assert app._tabs.tab(app._tabs.select(), "text") == "응답 오류 처리 시험"
                assert "미실행" in app._response_error_status.get()
                assert app._core_session is None
                assert not path.exists()

                app._selected_mode.set("로컬 Ollama (수동 선택)")
                app._platforms["youtube"].set(True)
                app._avatar.set("3D")
                app._run_response_error_test()
                assert "8/8" in app._response_error_status.get()
                assert "3회" in app._response_error_view.get("1.0", "end")
                assert "실제 Ollama" in app._response_error_view.get("1.0", "end")
                assert app._core_session is None

                app._response_error_choice.set("빈 응답 차단")
                app._run_response_error_test()
                assert "1/1" in app._response_error_status.get()
                app._response_error_choice.set("없는 항목")
                app._run_response_error_test()
                assert "오류" in app._response_error_status.get()
                app._response_error_choice.set("전체 8개 시나리오")
                app._content.set("invalid")
                app._run_response_error_test()
                assert "오류" in app._response_error_status.get()
                app._content.set("미정")

                # 실제 기본 코어 UI에서도 실패한 선두를 직접 재시도하고
                # 별도 확인 없이는 제외하지 못하는지 확인한다.
                session = OfflineCoreSession(app._core_selection(), FaultPort((TimeoutError("private"), "복구 답변")))
                session.enqueue("가: 첫 입력\n나: 다음 입력")
                app._core_session = session
                app._core_run(2)
                assert "실행 오류" in app._core_exec_status.get()
                assert session.pending_count == 2
                assert session.last_failure.code == "timeout"
                assert "private" not in app._core_exec_view.get("1.0", "end")
                app._core_retry_failed()
                assert "성공" in app._core_exec_status.get()
                assert session.pending_count == 1
                assert session.total_processed == 1
                app._core_discard_failed()
                assert "제외할 실패 건 없음" in app._core_exec_status.get()

                # 실패한 선두에 대해 취소/확인 대화상자 분기 모두 검증.
                second = OfflineCoreSession(app._core_selection(), FaultPort((TimeoutError("private"),)))
                second.enqueue("가: 제외 후보\n나: 유지 대상")
                app._core_session = second
                app._core_run(1)
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=False) as no:
                    app._core_discard_failed()
                    no.assert_called_once()
                assert second.pending_count == 2
                assert second.last_failure is not None
                with patch("ai_broadcaster.desktop.messagebox.askyesno", return_value=True) as yes:
                    app._core_discard_failed()
                    yes.assert_called_once()
                assert second.pending_count == 1
                assert second.last_failure is None
                assert second.total_processed == 0
                assert second.process_one().input.text == "유지 대상"
                # 같은 입력의 오류가 3회 누적되면 UI에서도 4번째 포트 호출을 막는다.
                blocked_port = FaultPort((TimeoutError(), TimeoutError(), TimeoutError()))
                blocked = OfflineCoreSession(app._core_selection(), blocked_port)
                blocked.enqueue("가: 반복 실패")
                app._core_session = blocked
                app._core_run(1)
                app._core_retry_failed()
                app._core_retry_failed()
                app._core_retry_failed()
                assert "상한" in app._core_exec_view.get("1.0", "end")
                assert blocked_port.calls == 3 and blocked.pending_count == 1
                app._core_reset()
                assert second.pending_count == 0
                assert not path.exists()
                assert app._runner.completed == []
                for spy in (net, sql, proc, pc):
                    spy.assert_not_called()
            finally:
                app._shutdown()
    print("27단계 GUI · 오류 8종/수동 재시도/확인 후 제외/무접속: 통과")


if __name__ == "__main__":
    main()
