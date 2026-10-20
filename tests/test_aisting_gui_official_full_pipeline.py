"""Real existing Tk chat-tab button/worker/FIFO UI path. No network.

These checks invoke production Tk callbacks with fake widgets; actual
GPT-SoVITS/Live2D/OBS must still be verified on approved Windows hardware.
"""
import queue
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop_chat_tab import LocalChatTab


class Value:
    def __init__(self, value=""):
        self.value = value
        self.log = []
    def get(self):
        return self.value
    def set(self, value):
        self.value = value
        self.log.append(value)


class Button:
    def __init__(self):
        self.states = []
    def configure(self, **kwargs):
        self.states.append(kwargs)


class RealOfficialPipelineTkTests(unittest.TestCase):
    def fake_tab(self):
        self.calls = []
        tab = SimpleNamespace(
            _closed=False, _pipeline_busy=False, _busy=False,
            _twitch_session=None,
            _input=Value("안녕하세요"),
            _pipeline_audio_input=Value("AISTING-Voice"),
            _pipeline_obs_password=Value("test-secret"),
            _pipeline_status=Value("미실행"),
            _pipeline_button=Button(), _send=Button(),
            _work_official_pipeline=lambda *args: self.calls.append(args),
        )
        return tab

    def test_manual_question_cannot_race_live_or_stopped_worker_sqlite_writes(self):
        for still_listening in (False, True):
            with self.subTest(still_listening=still_listening):
                tab = SimpleNamespace(
                    _closed=False, _busy=False, _pipeline_busy=False,
                    _twitch_session=object() if still_listening else None,
                    _twitch_active_workers={object()},
                    _input=Value("사용자 입력 유지"),
                    _input_info=Value("준비"),
                    _model_name=Value("real-model"),
                )
                with patch("ai_broadcaster.desktop_chat_tab.run_local_chat") as run:
                    LocalChatTab._submit(tab)
                    run.assert_not_called()
                self.assertFalse(tab._busy)
                self.assertEqual(tab._input.get(), "사용자 입력 유지")
                self.assertIn("기억 저장", tab._input_info.get())

    def test_official_probe_denies_during_stopped_chat_worker_memory_write(self):
        tab = self.fake_tab()
        tab._twitch_active_workers = {object()}
        with patch("ai_broadcaster.desktop_chat_tab.messagebox.askyesno") as consent:
            LocalChatTab._start_official_pipeline(tab)
        consent.assert_not_called()
        self.assertFalse(tab._pipeline_busy)
        self.assertEqual(self.calls, [])
        self.assertIn("기억 저장", tab._pipeline_status.get())

    def test_public_chat_waits_for_manual_ai_sqlite_write(self):
        tab = SimpleNamespace(_closed=False, _twitch_session=None,
            _pipeline_busy=False, _busy=True, _twitch_active_workers=set())
        with patch("ai_broadcaster.desktop_chat_tab.messagebox.showwarning") as warn:
            LocalChatTab._start_twitch(tab)
        warn.assert_called_once()
        self.assertIn("수동 AI", warn.call_args.args[0])

    def test_user_refusal_keeps_input_and_does_not_send(self):
        tab = self.fake_tab()
        with tempfile.TemporaryDirectory() as root:
            saved = Path(root) / "character.json"
            saved.write_text("{}", encoding="utf-8")
            fields = {"name": "saved", "style": "style", "character": "traits"}
            with patch("ai_broadcaster.offline_settings.settings_file",
                       return_value=saved), patch(
                 "ai_broadcaster.desktop_chat_tab.load_settings", return_value={}
            ), patch("ai_broadcaster.offline_settings.active_persona",
                     return_value=fields), patch(
                 "ai_broadcaster.original_plan_frontend._native_viewer_project",
                 Path(root)), patch(
                 "ai_broadcaster.original_plan_studio.inspect_saved_persona_alignment",
                 return_value=True), patch(
                 "ai_broadcaster.official_tts_readiness.require_saved_korean_gpt_sovits",
                 return_value=None), patch(
                 "ai_broadcaster.desktop_chat_tab.messagebox.askyesno", return_value=False):
                LocalChatTab._start_official_pipeline(tab)
        self.assertFalse(tab._pipeline_busy)
        self.assertEqual(self.calls, [])
        self.assertEqual(tab._input.get(), "안녕하세요")

    def test_explicit_approval_calls_one_worker_and_disables_button(self):
        tab = self.fake_tab()
        with tempfile.TemporaryDirectory() as root:
            saved = Path(root) / "character.json"
            saved.write_text("{}", encoding="utf-8")
            fields = {"name": "saved", "style": "style", "character": "traits"}
            class Thread:
                def __init__(self, target=None, args=(), **kwargs):
                    self.target, self.args = target, args
                def start(self):
                    self.target(*self.args)
            with patch("ai_broadcaster.offline_settings.settings_file",
                       return_value=saved), patch(
                 "ai_broadcaster.desktop_chat_tab.load_settings", return_value={}
            ), patch("ai_broadcaster.offline_settings.active_persona",
                     return_value=fields), patch(
                 "ai_broadcaster.original_plan_frontend._native_viewer_project",
                 Path(root)), patch(
                 "ai_broadcaster.original_plan_studio.inspect_saved_persona_alignment",
                 return_value=True), patch(
                 "ai_broadcaster.official_tts_readiness.require_saved_korean_gpt_sovits",
                 return_value=None), patch(
                 "ai_broadcaster.desktop_chat_tab.messagebox.askyesno", return_value=True
            ), patch("ai_broadcaster.desktop_chat_tab.threading.Thread", Thread):
                LocalChatTab._start_official_pipeline(tab)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][:3], ("안녕하세요", "test-secret", "AISTING-Voice"))
        self.assertTrue(hasattr(self.calls[0][3], "is_set"))
        self.assertFalse(self.calls[0][3].is_set())
        self.assertTrue(tab._pipeline_busy)
        self.assertIn({"state":"disabled"}, tab._pipeline_button.states)
        self.assertEqual(tab._input.get(), "안녕하세요")

    def test_no_confirmed_persona_file_denies_before_consent(self):
        tab = self.fake_tab()
        with tempfile.TemporaryDirectory() as root:
            missing = Path(root) / "character.json"
            with patch("ai_broadcaster.offline_settings.settings_file",
                       return_value=missing), patch(
                 "ai_broadcaster.desktop_chat_tab.messagebox.askyesno"
            ) as confirm:
                LocalChatTab._start_official_pipeline(tab)
                confirm.assert_not_called()
        self.assertEqual(self.calls, [])
        self.assertIn("확정 저장", tab._pipeline_status.get())

    def test_live_chat_reader_prevents_duplicate_ai_probe(self):
        tab = self.fake_tab()
        tab._twitch_session = object()
        with patch("ai_broadcaster.desktop_chat_tab.messagebox.askyesno") as confirm:
            LocalChatTab._start_official_pipeline(tab)
            confirm.assert_not_called()
        self.assertEqual(self.calls, [])

    def test_platform_reader_does_not_interrupt_approved_full_probe(self):
        # The callback must return before touching model/network UI state.
        stub = SimpleNamespace(_closed=False, _pipeline_busy=True, _twitch_session=None)
        LocalChatTab._start_twitch(stub)

    def test_official_public_chat_requires_committed_character_before_consent(self):
        tab = SimpleNamespace(
            _closed=False, _twitch_session=None, _pipeline_busy=False, _busy=False,
            _model_name=Value(""), _official_live2d=Value(True),
        )
        with tempfile.TemporaryDirectory() as root, patch(
            "ai_broadcaster.offline_settings.settings_file",
            return_value=Path(root) / "missing-character.json"
        ), patch("ai_broadcaster.desktop_chat_tab.messagebox.showwarning") as warn, patch(
            "ai_broadcaster.desktop_chat_tab.messagebox.askyesno"
        ) as confirm:
            LocalChatTab._start_twitch(tab)
            warn.assert_called_once()
            confirm.assert_not_called()

    def test_memory_delete_is_blocked_while_official_probe_runs(self):
        tab = SimpleNamespace(_busy=False, _pipeline_busy=True, _twitch_session=None)
        with patch("ai_broadcaster.desktop_chat_tab.messagebox.showwarning") as warn, patch(
            "ai_broadcaster.desktop_chat_tab.messagebox.askyesno"
        ) as confirm:
            LocalChatTab._clear_memory(tab)
            warn.assert_called_once()
            confirm.assert_not_called()

    def test_cancel_keeps_busy_until_original_worker_has_finished(self):
        import threading
        tab = self.fake_tab()
        tab._pipeline_busy = True
        tab._pipeline_cancel = threading.Event()
        tab._pipeline_cancel_button = Button()
        LocalChatTab._cancel_official_pipeline(tab)
        self.assertTrue(tab._pipeline_cancel.is_set())
        self.assertTrue(tab._pipeline_busy)
        self.assertEqual(tab._pipeline_cancel_button.states[-1], {"state":"disabled"})

    def test_cancelled_worker_discards_late_success_and_preserves_input(self):
        import threading
        event = threading.Event()
        results = queue.SimpleQueue()
        tab = SimpleNamespace(_results=results)
        def fake(*a, **kwargs):
            event.set()
            return SimpleNamespace(verified_observation=True)
        with patch("ai_broadcaster.original_plan_full_pipeline.verify_official_chat_live2d_obs",side_effect=fake) as fn:
            LocalChatTab._work_official_pipeline(tab, "질문", "secret", "Mic", event)
        self.assertEqual(results.get_nowait(), ("pipeline_cancelled", None))
        self.assertIs(fn.call_args.kwargs["cancel_event"], event)

    def test_queued_success_before_stop_is_discarded_when_gui_receives_it(self):
        import threading
        tab = self.fake_tab()
        tab._pipeline_busy = True
        tab._pipeline_cancel = threading.Event()
        tab._pipeline_cancel.set()
        tab._results = queue.SimpleQueue()
        tab._results.put(("pipeline_ok", (
            "안녕하세요", SimpleNamespace(
                verified_observation=True,
                lip=SimpleNamespace(verified_signal=True),
                obs=SimpleNamespace(coherent_media_candidate=True)))))
        tab._append = lambda *_args: self.fail("Cancelled result claimed success")
        tab.after = lambda *_args: None
        tab._poll = lambda: None
        LocalChatTab._poll(tab)
        self.assertFalse(tab._pipeline_busy)
        self.assertIsNone(tab._pipeline_cancel)
        self.assertIn("중지됨", tab._pipeline_status.get())
        self.assertEqual(tab._input.get(), "안녕하세요")

    def test_worker_passes_real_approved_path_and_queues_only_safe_evidence(self):
        events = queue.SimpleQueue()
        tab = SimpleNamespace(_results=events)
        observed = SimpleNamespace(verified_observation=True)
        with patch(
            "ai_broadcaster.original_plan_full_pipeline.verify_official_chat_live2d_obs",
            return_value=observed,
        ) as run:
            LocalChatTab._work_official_pipeline(tab, "질문", "secret", "Mic")
        self.assertEqual(events.get_nowait(), ("pipeline_ok", ("질문", observed)))
        run.assert_called_once_with(
            "질문", obs_password="secret", obs_input_name="Mic",
            operator_approved=True, voice_rights_confirmed=True)

    def test_approved_path_failure_does_not_echo_obs_password(self):
        events = queue.SimpleQueue()
        tab = SimpleNamespace(_results=events)
        with patch(
            "ai_broadcaster.original_plan_full_pipeline.verify_official_chat_live2d_obs",
            side_effect=RuntimeError("secret should not appear in logs"),
        ):
            LocalChatTab._work_official_pipeline(tab, "질문", "secret", "Mic")
        kind, message = events.get_nowait()
        self.assertEqual(kind, "pipeline_error")
        self.assertNotIn("secret", message)

    def test_observed_mouth_without_obs_is_not_reported_as_success(self):
        tab = self.fake_tab()
        tab._pipeline_busy = True
        tab._results = queue.SimpleQueue()
        tab._results.put(("pipeline_ok", (
            "안녕하세요", SimpleNamespace(
                verified_observation=False,
                lip=SimpleNamespace(verified_signal=True),
                obs=SimpleNamespace(coherent_media_candidate=False))
        )))
        tab._append = lambda *_args: self.fail("Unproven output reported as success")
        tab.after = lambda *_args: None
        tab._poll = lambda: None
        LocalChatTab._poll(tab)
        self.assertIn("OBS 화면·음성 경로 미확인", tab._pipeline_status.get())
        self.assertEqual(tab._input.get(), "안녕하세요")


if __name__ == "__main__":
    unittest.main()
