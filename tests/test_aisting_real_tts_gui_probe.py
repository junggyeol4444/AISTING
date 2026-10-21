"""Real GPT-SoVITS inference is reachable in existing native AISTING GUI.

All tests isolate actual user voices and local HTTP. The approved handler itself
uses the existing real /tts implementation, not a replacement or fake renderer.
"""
import queue
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop_chat_tab import LocalChatTab
from ai_broadcaster.official_tts_readiness import synthesize_saved_korean_gpt_sovits
from ai_broadcaster.original_plan_tts import ActualGptSovitsSynthesis


class Value:
    def __init__(self, text=""):
        self.text = text
    def get(self):
        return self.text
    def set(self, text):
        self.text = text


class Button:
    def __init__(self):
        self.state = "normal"
    def configure(self, *, state):
        self.state = state


class RunnerThread:
    def __init__(self, target, args=(), daemon=True):
        self.target = target
        self.args = args
    def start(self):
        self.target(*self.args)


class RealTTSNativeGuiTests(unittest.TestCase):
    def tab(self, text="한국어 실제 음성 합성 검사"):
        return SimpleNamespace(
            _closed=False, _busy=False, _pipeline_busy=False, _tts_probe_busy=False,
            _twitch_session=None, _twitch_active_workers=set(), _input=Value(text),
            _tts_probe_status=Value(), _tts_probe_button=Button(),
            _pipeline_button=Button(), _send=Button(),
            _results=queue.SimpleQueue(), _poll=lambda: None, after=lambda *_: None,
        )

    def test_denied_rights_never_call_real_tts(self):
        tab = self.tab()
        with patch("ai_broadcaster.original_plan_frontend._native_viewer_project",
                   Path("existing-native-project")), patch(
                   "ai_broadcaster.official_tts_readiness.require_saved_korean_gpt_sovits"), patch(
                   "ai_broadcaster.desktop_chat_tab.messagebox.askyesno",
                   return_value=False), patch(
                   "ai_broadcaster.official_tts_readiness.synthesize_saved_korean_gpt_sovits"
                   ) as real:
            LocalChatTab._start_official_tts_probe(tab)
        real.assert_not_called()
        self.assertFalse(tab._tts_probe_busy)
        self.assertIn("승인", tab._tts_probe_status.get())

    def test_preflight_denied_before_any_consent_prompt(self):
        tab = self.tab()
        with patch("ai_broadcaster.original_plan_frontend._native_viewer_project",
                   None), patch(
                   "ai_broadcaster.desktop_chat_tab.messagebox.askyesno") as approval:
            LocalChatTab._start_official_tts_probe(tab)
        approval.assert_not_called()
        self.assertFalse(tab._tts_probe_busy)

    def test_existing_actual_inference_called_only_after_approval(self):
        tab = self.tab()
        actual = ActualGptSovitsSynthesis(
            sample_rate=32000, channels=1, frame_count=32000, wav_bytes=64500)
        with patch("ai_broadcaster.original_plan_frontend._native_viewer_project",
                   Path("existing-native-project")), patch(
                   "ai_broadcaster.official_tts_readiness.require_saved_korean_gpt_sovits"), patch(
                   "ai_broadcaster.desktop_chat_tab.messagebox.askyesno",
                   return_value=True), patch(
                   "ai_broadcaster.desktop_chat_tab.threading.Thread",
                   RunnerThread), patch(
                   "ai_broadcaster.official_tts_readiness.synthesize_saved_korean_gpt_sovits",
                   return_value=actual) as real:
            LocalChatTab._start_official_tts_probe(tab)
            real.assert_called_once()
        self.assertTrue(real.call_args.kwargs["operator_approved"])
        self.assertTrue(real.call_args.kwargs["rights_confirmed"])
        self.assertEqual(tab._tts_probe_button.state, "disabled")
        kind, reply = tab._results.get_nowait()
        self.assertEqual(kind, "tts_probe_ok")
        self.assertIs(reply, actual)

    def test_actual_model_error_does_not_reveal_local_path_or_token(self):
        tab = self.tab()
        with patch("ai_broadcaster.official_tts_readiness.synthesize_saved_korean_gpt_sovits",
                   side_effect=RuntimeError("PRIVATE_REFERENCE_PATH:secret")):
            LocalChatTab._work_official_tts_probe(tab, Path("existing"), "안녕")
        self.assertEqual(tab._results.get_nowait(), ("tts_probe_error", "RuntimeError"))

    def test_rights_gate_prevents_config_read_and_http(self):
        with patch("ai_broadcaster.official_tts_readiness.read_saved_korean_gpt_sovits_config"
                   ) as config, patch(
                   "ai_broadcaster.original_plan_tts.synthesize_local_gpt_sovits"
                   ) as real:
            with self.assertRaises(PermissionError):
                synthesize_saved_korean_gpt_sovits(
                    Path("existing"), "안녕",
                    operator_approved=True, rights_confirmed=False)
        config.assert_not_called()
        real.assert_not_called()

    def test_existing_synthesis_receives_exact_saved_ko_config_and_no_playback(self):
        ref = Path("existing-authorized.wav")
        result = ActualGptSovitsSynthesis(32000, 1, 32000, 64500)
        with patch("ai_broadcaster.official_tts_readiness.read_saved_korean_gpt_sovits_config",
                   return_value=("http://127.0.0.1:9880/tts", ref, "내 음성 원문")), patch(
                   "ai_broadcaster.original_plan_tts.synthesize_local_gpt_sovits",
                   return_value=result) as real:
            got = synthesize_saved_korean_gpt_sovits(
                Path("existing"), "실제 한국어", operator_approved=True,
                rights_confirmed=True, timeout=65)
        self.assertIs(got, result)
        self.assertEqual(real.call_args.args, (ref, "내 음성 원문", "실제 한국어"))
        self.assertFalse(real.call_args.kwargs["play_to_speaker"])
        self.assertFalse(real.call_args.kwargs["return_audio_bytes"])
        self.assertEqual(real.call_args.kwargs["timeout"], 65)


if __name__ == "__main__":
    unittest.main()
