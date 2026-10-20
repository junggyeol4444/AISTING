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
        # Must import AFTER isolating LOCALAPPDATA: operator_settings.DEFAULT_FILE
        # and conversation_memory.DEFAULT_MEMORY_FILE are evaluated at import.
        from ai_broadcaster.desktop import AistingApp
        from ai_broadcaster.operator_settings import DEFAULT_FILE
        from ai_broadcaster.conversation_memory import DEFAULT_MEMORY_FILE
        assert DEFAULT_FILE.is_relative_to(root / "AppData"), (
            "Windows settings path escaped disposable CI profile")
        assert DEFAULT_MEMORY_FILE.is_relative_to(root / "AppData"), (
            "Windows SQLite memory path escaped disposable CI profile")
        print("GUI_REAL_WINDOWS_PROFILE_PATH_ISOLATED_PASS")
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

            # Windows native Tk integration: Stop must not permit a new AI
            # session or memory deletion while the previous model is still
            # finishing a committed conversation / SQLite write.
            from tkinter import ttk
            from ai_broadcaster.multiplatform_readonly import PlatformChat
            import queue
            class IsolatedReadOnlySession:
                def __init__(self):
                    self._stop = threading.Event()
                def stop(self):
                    self._stop.set()

            existing = IsolatedReadOnlySession()
            pending_inbox = queue.SimpleQueue()
            pending_inbox.put(PlatformChat("room", "시청자", "저장 중", "soop"))
            tab._twitch_session = existing
            tab._twitch_active_workers.add(existing)
            tab._twitch_ai_inbox = pending_inbox
            tab._twitch_start.configure(state="disabled")
            tab._twitch_end.configure(state="normal")
            in_flight, allow_finish = threading.Event(), threading.Event()
            def committed_reply(*args, **kwargs):
                assert kwargs["use_committed_gui_character"]
                in_flight.set()
                assert allow_finish.wait(5)
                return SimpleNamespace(reply="응답", remembered_count=1)
            with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                       side_effect=committed_reply):
                worker = threading.Thread(
                    target=tab._work_twitch_ai,
                    args=("local-model", pending_inbox, False, existing),
                    daemon=True,
                )
                worker.start()
                try:
                    pump_until(app, in_flight.is_set)
                    tab._twitch_end.invoke()
                    app.update()
                    assert existing._stop.is_set() and tab._twitch_session is None
                    assert existing in tab._twitch_active_workers
                    with patch("ai_broadcaster.desktop_chat_tab.messagebox.showwarning") as warn, patch(
                        "ai_broadcaster.desktop_chat_tab.messagebox.askyesno"
                    ) as confirm:
                        memory_buttons = [
                            x for parent in tab.winfo_children()
                            for x in parent.winfo_children()
                            if isinstance(x, ttk.Button)
                            and str(x.cget("text")) == "대화 기억 삭제"
                        ]
                        assert len(memory_buttons) == 1
                        memory_buttons[0].invoke()
                        assert warn.call_count == 1
                        confirm.assert_not_called()
                        tab._twitch_start.invoke()
                        assert warn.call_count == 2
                    print("GUI_STOP_INFLIGHT_SQLITE_DELETE_RECONNECT_BLOCKED_PASS")
                finally:
                    allow_finish.set()
                    worker.join(5)
                assert not worker.is_alive()
                pump_until(app, lambda: not tab._twitch_active_workers)
                assert str(tab._twitch_start.cget("state")) == "normal"
                assert str(tab._twitch_end.cget("state")) == "disabled"
                print("GUI_STOP_INFLIGHT_WORKER_DRAIN_RECONNECT_READY_PASS")

            # Cross-mode race regression on the *actual Windows Tk widgets*:
            # a previous public-chat AI worker may have stopped reading but
            # can still own an in-flight SQLite commit. All three paths share
            # one committed character and must not overlap.
            tab._input.set("중복 금지 사용자 입력")
            tab._model_name.set("existing-local-model")
            orphan = object()
            tab._twitch_active_workers.add(orphan)
            with patch("ai_broadcaster.desktop_chat_tab.messagebox.askyesno") as confirm, patch(
                "ai_broadcaster.desktop_chat_tab.messagebox.showwarning"
            ) as warning, patch(
                "ai_broadcaster.desktop_chat_tab.run_local_chat",
                side_effect=AssertionError("raced with old session")
            ) as llm:
                tab._send.invoke()
                btn.invoke()
                tab._twitch_start.invoke()
                app.update()
                assert not tab._busy and not tab._pipeline_busy
                assert tab._input.get() == "중복 금지 사용자 입력"
                assert "기억 저장" in tab._pipeline_status.get()
                assert warning.call_count == 1
                confirm.assert_not_called()
                llm.assert_not_called()
            tab._twitch_active_workers.discard(orphan)
            print("GUI_MANUAL_OFFICIAL_PUBLIC_AI_CROSSMODE_SQLITE_GUARD_PASS")

            # Real app's actual durable SQLite location survives close/reopen,
            # and the explicitly confirmed character survives full GUI restart.
            # Only the disposable Windows LOCALAPPDATA is written.
            from ai_broadcaster.conversation_memory import ConversationMemory
            from ai_broadcaster.session import ChatMessage
            from ai_broadcaster.offline_settings import (
                load_settings as read_prefs, settings_file as prefs_path)
            from ai_broadcaster.original_plan_persona_store import commit_character_identity
            first_prefs = read_prefs()
            custom_persona = {
                "name": "Windows 실제 재시작 캐릭터", "style": "한국어 자연스러운 말투",
                "character": "기억을 보존하는 사람",
            }
            commit_character_identity(
                first_prefs, "custom", custom_persona, path=prefs_path())
            mem = ConversationMemory()
            mem.append(ChatMessage("persistent-001", "시청자", "중복 문장"), "답변 1")
            mem.append(ChatMessage("persistent-002", "시청자", "중복 문장"), "답변 2")
            assert ConversationMemory().count() == 2
            assert [x.reply for x in ConversationMemory().recent(2)] == [
                "답변 1", "답변 2"]
            assert read_prefs()["persona"] == custom_persona
            print("GUI_NATIVE_CHARACTER_SQLITE_REOPEN_PERSISTENCE_PASS")

            assert sha256(settings) == before_settings
            assert sha256(database) == before_db
            with closing(sqlite3.connect(database)) as db:
                assert db.execute("SELECT note FROM identity_preserve").fetchone()[0] == "기억 보존"
            print("CHARACTER_SETTINGS_SQLITE_BYTES_UNCHANGED_PASS")
        finally:
            app._shutdown()

        # Recreate the same production Windows Tk app in the same isolated
        # user profile, not merely a mock settings loader.
        second = AistingApp()
        try:
            second._goto_page("실제 채팅·AI")
            second.update()
            assert second.settings["persona"] == custom_persona
            assert second.settings["persona_mode"] == "custom"
            assert ConversationMemory().count() == 2
            assert [x.reply for x in ConversationMemory().recent(2)] == [
                "답변 1", "답변 2"]
            assert second._real_chat_tab.winfo_ismapped()
            print("GUI_NATIVE_RESTART_REAL_PERSONA_SQLITE_PERSISTENCE_PASS")
        finally:
            second._shutdown()


if __name__ == "__main__":
    main()
