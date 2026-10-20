"""Windows real-Tk user-click integration for existing official OBS button.

This deliberately substitutes ONLY external model/OBS services.  No GPT-
SoVITS, account, audio, chat or streaming occurs.  It tests actual native
widgets and callbacks, consent, UI visibility, error state and data safety.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from contextlib import closing, ExitStack
import sqlite3
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp


def pump_until(app, predicate, seconds=6):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.update()
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("실제 Tk 버튼 작업 완료/화면 복구 시간 초과")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    with tempfile.TemporaryDirectory(prefix="aisting_real_tk_click_") as tmp:
        root = Path(tmp)
        # Only isolated CI app state; never use the operator's LOCALAPPDATA.
        os.environ["LOCALAPPDATA"] = str(root / "AppData")
        (root / "AppData").mkdir()
        settings = root / "original_persona.json"
        settings.write_text('{"preserve":"캐릭터/설정은 변경하지 않습니다"}', encoding="utf-8")
        database = root / "user_memory.sqlite3"
        with closing(sqlite3.connect(database)) as db:
            with db:
                db.execute("CREATE TABLE identity_preserve(id INTEGER PRIMARY KEY, note TEXT)")
                db.execute("INSERT INTO identity_preserve(note) VALUES (?)", ("기억 보존",))
        before_settings, before_db = sha256(settings), sha256(database)

        app = AistingApp()
        try:
            app.geometry("1280x768+0+0")
            app._goto_page("실제 채팅·AI")
            app.update()
            tab = app._real_chat_tab
            assert tab.winfo_ismapped(), "실제 채팅 Tk 페이지가 화면에 열리지 않았습니다"
            btn = tab._pipeline_button
            assert btn.winfo_ismapped(), "공식 AI·Live2D·OBS 버튼이 실제 표시되지 않았습니다"
            # A live operator has to be able to see/click the control, not
            # only invoke a hidden widget programmatically.
            top = btn.winfo_rooty() - app.winfo_rooty()
            bottom = top + btn.winfo_height()
            print("NATIVE_BUTTON_GEOMETRY", top, bottom, app.winfo_height())
            assert top >= 0 and bottom <= app.winfo_height(), (
                "1280x768 Windows 앱에서 실제 검사 버튼이 화면 아래로 잘렸습니다"
            )

            tab._input.set("안녕하세요. 실제 음성 검사인가요?")
            tab._pipeline_audio_input.set("AISTING Voice")
            tab._pipeline_obs_password.set("CI-only-secret")
            project = root / "local-project"
            project.mkdir()
            persona = {"name":"독립 캐릭터","style":"자연스러운 한국어","character":"차분함"}
            shared = [
                patch("ai_broadcaster.offline_settings.settings_file",return_value=settings),
                patch("ai_broadcaster.offline_settings.active_persona",return_value=persona),
                patch("ai_broadcaster.desktop_chat_tab.load_settings",return_value={}),
                patch("ai_broadcaster.original_plan_frontend._native_viewer_project",project),
                patch("ai_broadcaster.original_plan_studio.inspect_saved_persona_alignment",return_value=True),
                patch("ai_broadcaster.official_tts_readiness.require_saved_korean_gpt_sovits",return_value=None),
            ]

            # Declined operator confirmation cannot send a prompt or clear text.
            calls = []
            def simulated_pipeline(text, **kwargs):
                calls.append(text)
                return SimpleNamespace(
                    verified_observation=True,
                    lip=SimpleNamespace(verified_signal=True),
                    obs=SimpleNamespace(coherent_media_candidate=True),
                )
            with ExitStack() as st:
                for p in shared: st.enter_context(p)
                st.enter_context(patch("ai_broadcaster.desktop_chat_tab.messagebox.askyesno",return_value=False))
                st.enter_context(patch("ai_broadcaster.original_plan_full_pipeline.verify_official_chat_live2d_obs",side_effect=simulated_pipeline))
                btn.invoke()
                app.update()
                assert calls == [] and not tab._pipeline_busy
                assert tab._input.get().startswith("안녕하세요.")
                assert "취소" in tab._pipeline_status.get()
            print("GUI_DECLINE_NO_SEND_PASS")

            # Approved real widget invocation travels through production
            # thread, actual Tk queue/poll and enabled UI state.
            with ExitStack() as st:
                for p in shared: st.enter_context(p)
                st.enter_context(patch("ai_broadcaster.desktop_chat_tab.messagebox.askyesno",return_value=True))
                st.enter_context(patch("ai_broadcaster.original_plan_full_pipeline.verify_official_chat_live2d_obs",side_effect=simulated_pipeline))
                btn.invoke()
                pump_until(app, lambda: not tab._pipeline_busy)
                assert calls == ["안녕하세요. 실제 음성 검사인가요?"]
                assert "실제 입 움직임 확인" in tab._pipeline_status.get()
                assert "OBS 영상·음성 후보 확인" in tab._pipeline_status.get()
                assert tab._input.get() == ""
                assert str(btn.cget("state")) == "normal"
                assert str(tab._send.cget("state")) == "normal"
            print("GUI_BUTTON_THREAD_EVENT_SUCCESS_ROUTE_PASS (SIMULATED OBS/MODEL)")

            # Fail closed: a transport error must not echo the OBS password,
            # clear user input, or leave the button disabled forever.
            tab._input.set("두 번째 사용자 질문")
            with ExitStack() as st:
                for p in shared: st.enter_context(p)
                st.enter_context(patch("ai_broadcaster.desktop_chat_tab.messagebox.askyesno",return_value=True))
                st.enter_context(patch("ai_broadcaster.original_plan_full_pipeline.verify_official_chat_live2d_obs",
                    side_effect=RuntimeError("CI-only-secret must NEVER appear")))
                btn.invoke()
                pump_until(app, lambda: not tab._pipeline_busy)
                assert "실패/미확인" in tab._pipeline_status.get()
                assert "CI-only-secret" not in tab._pipeline_status.get()
                assert tab._input.get() == "두 번째 사용자 질문"
                assert str(btn.cget("state")) == "normal"
            print("GUI_FAILURE_RECOVERY_PASSWORD_REDACTED_PASS")

            # A slow external model is simulated, but native Windows Tk buttons,
            # event loop and cancellation handshake are the production ones.
            import threading
            tab._input.set("취소된 발화")
            started = threading.Event()
            release = threading.Event()
            def slow_output(text, **kwargs):
                started.set()
                assert release.wait(3)
                return SimpleNamespace(verified_observation=True,
                    lip=SimpleNamespace(verified_signal=True),
                    obs=SimpleNamespace(coherent_media_candidate=True))
            with ExitStack() as st:
                for p in shared: st.enter_context(p)
                st.enter_context(patch("ai_broadcaster.desktop_chat_tab.messagebox.askyesno",return_value=True))
                st.enter_context(patch("ai_broadcaster.original_plan_full_pipeline.verify_official_chat_live2d_obs",side_effect=slow_output))
                btn.invoke()
                pump_until(app, started.is_set)
                stop_btn = tab._pipeline_cancel_button
                assert str(stop_btn.cget("state")) == "normal"
                stop_btn.invoke()
                app.update()
                assert tab._pipeline_busy
                assert str(btn.cget("state")) == "disabled"
                release.set()
                pump_until(app, lambda: not tab._pipeline_busy)
                assert tab._input.get() == "취소된 발화"
                assert "중지됨" in tab._pipeline_status.get()
            print("GUI_NATIVE_CANCEL_NO_LATE_SUCCESS_PASS (SIMULATED MODEL)")

            assert sha256(settings) == before_settings
            assert sha256(database) == before_db
            with closing(sqlite3.connect(database)) as db:
                assert db.execute("SELECT note FROM identity_preserve").fetchone()[0] == "기억 보존"
            print("CHARACTER_SETTINGS_SQLITE_BYTES_UNCHANGED_PASS")
        finally:
            app._shutdown()


if __name__ == "__main__":
    main()
