"""Native GUI one-shot authorized GPT-SoVITS -> real OBS connector tests.

The full bridge is already tested separately with isolated OBS clients.
These tests prove the existing Tk control invokes THAT bridge, not a substitute
renderer. No fake output is reported to the user as real inference.
"""
import queue
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop_chat_tab import LocalChatTab
from ai_broadcaster.original_plan_voice_obs_bridge import RealVoiceObsResult


class Value:
    def __init__(self, value=""):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class Button:
    def __init__(self):
        self.state = "normal"
    def configure(self, *, state):
        self.state = state


class ThreadInline:
    def __init__(self, target, args, daemon=True):
        self.target = target
        self.args = args
    def start(self):
        self.target(*self.args)


class ActualVoiceToObsTkTests(unittest.TestCase):
    def native(self, text="한국어 실제 OBS 음성 검사", password="CI-NO-REAL-OBS"):
        fake = SimpleNamespace(
            _closed=False, _busy=False, _pipeline_busy=False,
            _tts_probe_busy=False, _oauth_busy=False,
            _twitch_session=None, _twitch_active_workers=set(),
            _input=Value(text), _pipeline_obs_password=Value(password),
            _tts_probe_status=Value(), _tts_probe_button=Button(),
            _tts_obs_button=Button(), _pipeline_button=Button(),
            _send=Button(), _results=queue.SimpleQueue(),
            _poll=lambda: None, after=lambda *_: None,
        )
        fake._work_real_tts_obs_probe = lambda *args: (
            LocalChatTab._work_real_tts_obs_probe(fake, *args))
        return fake

    def test_no_reference_or_model_means_no_request_and_no_permission_popup(self):
        fake = self.native()
        with patch("ai_broadcaster.original_plan_frontend._native_viewer_project", None), patch(
                "ai_broadcaster.desktop_chat_tab.messagebox.askyesno") as approval, patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.verify_gpt_sovits_to_obs") as bridge:
            LocalChatTab._start_real_tts_obs_probe(fake)
        approval.assert_not_called()
        bridge.assert_not_called()
        self.assertFalse(fake._tts_probe_busy)

    def test_no_obs_password_means_no_request(self):
        fake = self.native(password="")
        with patch("ai_broadcaster.desktop_chat_tab.messagebox.askyesno") as approval:
            LocalChatTab._start_real_tts_obs_probe(fake)
        approval.assert_not_called()
        self.assertIn("OBS", fake._tts_probe_status.get())

    def test_denial_never_synthesizes_or_creates_obs_input(self):
        fake = self.native()
        with patch("ai_broadcaster.original_plan_frontend._native_viewer_project",
                   Path("preexisting-real-project")), patch(
                   "ai_broadcaster.official_tts_readiness.read_saved_korean_gpt_sovits_config",
                   return_value=("http://127.0.0.1:9880/tts", Path("licensed.wav"), "제 음성")), patch(
                   "ai_broadcaster.desktop_chat_tab.messagebox.askyesno",
                   return_value=False), patch(
                   "ai_broadcaster.original_plan_voice_obs_bridge.verify_gpt_sovits_to_obs"
                   ) as bridge:
            LocalChatTab._start_real_tts_obs_probe(fake)
        bridge.assert_not_called()
        self.assertFalse(fake._tts_probe_busy)
        self.assertIn("요청 없음", fake._tts_probe_status.get())

    def test_authorized_tk_worker_calls_existing_real_bridge_once(self):
        fake = self.native()
        proof = RealVoiceObsResult(32000, 1, 32000, "31.0", 14, True)
        with patch("ai_broadcaster.original_plan_frontend._native_viewer_project",
                   Path("preexisting-real-project")), patch(
                   "ai_broadcaster.official_tts_readiness.read_saved_korean_gpt_sovits_config",
                   return_value=("http://127.0.0.1:9880/tts", Path("licensed.wav"), "제 음성")), patch(
                   "ai_broadcaster.desktop_chat_tab.messagebox.askyesno",
                   return_value=True), patch(
                   "ai_broadcaster.desktop_chat_tab.threading.Thread", ThreadInline), patch(
                   "ai_broadcaster.original_plan_voice_obs_bridge.verify_gpt_sovits_to_obs",
                   return_value=proof) as bridge:
            LocalChatTab._start_real_tts_obs_probe(fake)
        bridge.assert_called_once_with(
            Path("licensed.wav"), "제 음성", "한국어 실제 OBS 음성 검사",
            api_url="http://127.0.0.1:9880/tts",
            obs_password="CI-NO-REAL-OBS",
            operator_approved=True, rights_confirmed=True)
        self.assertEqual(fake._tts_obs_button.state, "disabled")
        self.assertEqual(fake._pipeline_button.state, "disabled")
        self.assertEqual(fake._results.get_nowait(), ("tts_obs_ok", proof))

    def test_secret_in_bridge_error_is_not_logged_or_visible(self):
        fake = self.native()
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.verify_gpt_sovits_to_obs",
                   side_effect=RuntimeError("DONT_LOG_THIS_OBS_PASSWORD")):
            LocalChatTab._work_real_tts_obs_probe(
                fake, Path("licensed.wav"), "제 음성", "안녕",
                "http://127.0.0.1:9880/tts", "PRIVATE_PASSWORD")
        self.assertEqual(fake._results.get_nowait(),
                         ("tts_obs_error", "RuntimeError"))

    def test_gui_success_is_limited_to_real_obs_meter_not_live2d(self):
        fake = self.native()
        fake._tts_probe_busy = True
        fake._results.put(("tts_obs_ok", RealVoiceObsResult(
            32000, 1, 32000, "31.0", 14, True)))
        LocalChatTab._poll(fake)
        self.assertFalse(fake._tts_probe_busy)
        self.assertEqual(fake._tts_obs_button.state, "normal")
        self.assertIn("OBS 임시 입력 미터 신호 확인", fake._tts_probe_status.get())
        self.assertIn("Live2D", fake._tts_probe_status.get())

    def test_gui_empty_meter_cannot_claim_real_output(self):
        fake = self.native()
        fake._results.put(("tts_obs_ok", RealVoiceObsResult(
            32000, 1, 32000, "31.0", 0, False)))
        LocalChatTab._poll(fake)
        self.assertIn("실증 미충족", fake._tts_probe_status.get())

    def test_tts_obs_does_not_start_while_other_task_running(self):
        fake = self.native()
        fake._tts_probe_busy = True
        with patch("ai_broadcaster.desktop_chat_tab.messagebox.askyesno") as prompt:
            LocalChatTab._start_real_tts_obs_probe(fake)
        prompt.assert_not_called()
        self.assertIn("종료한 뒤", fake._tts_probe_status.get())


if __name__ == "__main__":
    unittest.main()
