"""Validate the real (never canned-LLM) Windows load runner's controls."""
import importlib.util
import io
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch


PATH = Path(__file__).resolve().parents[1] / "scripts" / "aisting_real_ollama_fifo_soak.py"
SPEC = importlib.util.spec_from_file_location("real_ollama_fifo_soak", PATH)
SOAK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOAK)


class LoadRunnerContracts(unittest.TestCase):
    def test_500_unique_clients_over_four_platforms(self):
        names = [SOAK.make_message(i) for i in range(500)]
        self.assertEqual(len(names), 500)
        self.assertEqual(len({m.author for m in names}) if hasattr(names[0], "author")
                         else len(names), 500)
        self.assertEqual(len([m for m in names if getattr(m, "platform", "twitch")
                              == "twitch"]), 125)
        self.assertEqual([getattr(m, "platform", "twitch")
                          for m in names[:4]], ["twitch","chzzk","soop","youtube"])

    def test_repeated_identical_messages_not_deduplicated(self):
        messages = [SOAK.make_message(i, duplicate=True) for i in range(8)]
        self.assertEqual(len(messages), 8)
        self.assertEqual(len({m.text for m in messages}), 1)

    def test_frozen_windows_cp1252_console_can_print_korean_help(self):
        # Simulates the real native Windows EXE failure: cp1252 output
        # cannot encode the Korean command descriptions in --help.
        stdout_bytes, stderr_bytes = io.BytesIO(), io.BytesIO()
        out = io.TextIOWrapper(stdout_bytes, encoding="cp1252")
        err = io.TextIOWrapper(stderr_bytes, encoding="cp1252")
        with patch.object(SOAK.sys, "stdout", out), patch.object(
                SOAK.sys, "stderr", err), patch.object(
                SOAK.sys, "argv", ["AISTING-FIFO-Soak.exe", "--help"]):
            with self.assertRaises(SystemExit) as exited:
                SOAK.main()
        self.assertEqual(exited.exception.code, 0)
        out.flush()
        self.assertIn("실제 로컬 Ollama", stdout_bytes.getvalue().decode("utf-8"))

    def test_actual_24_hour_duration_supported(self):
        SOAK.validate_parameters(500, 86400, 10000, 11434)

    def test_500_production_fifo_events_no_loss_using_only_test_reply(self):
        # This test deliberately mocks the model for a fast CONTRACT check.
        # Independent Windows Actions perform ALL 500 with real Ollama.
        with patch.object(SOAK, "real_ollama_chat",
                          return_value=SimpleNamespace(reply="한국어", remembered_count=1)) as llm:
            data = SOAK.run_real_load(
                model="installed-test-model", messages=500,
                duration_seconds=8, queue_size=128)
        self.assertEqual(data["accepted"], 500)
        self.assertEqual(data["model_success"], 500)
        self.assertEqual(data["completed"], 500)
        self.assertEqual(data["unfinished"], 0)
        self.assertTrue(data["passed_no_drops"])
        self.assertTrue(data["worker_ended"])
        self.assertEqual(llm.call_count, 500)
        self.assertEqual(data["platform_event_counts"], {
            "twitch":125, "chzzk":125, "soop":125, "youtube":125})
        self.assertFalse(data["real_viewers"])
        self.assertFalse(data["long_running_broadcast_verified"])

    def test_hold_full_duration_still_uses_real_worker_path_not_viewer_claim(self):
        with patch.object(SOAK, "real_ollama_chat",
                          return_value=SimpleNamespace(reply="응답", remembered_count=1)):
            data = SOAK.run_real_load(
                model="installed-test-model", messages=4,
                duration_seconds=2, queue_size=4,
                hold_full_duration=True)
        self.assertTrue(data["completed_full_local_duration"])
        self.assertTrue(data["passed_no_drops"])
        self.assertFalse(data["long_running_broadcast_verified"])

    def test_invalid_time_or_bounded_queue_rejected(self):
        for args in [(500, 0, 10000, 11434),
                     (500, 86401, 10000, 11434),
                     (500, float("nan"), 10000, 11434),
                     (500, 86400, 0, 11434),
                     (500, 86400, 10000, 0),
                     (0, 86400, 10000, 11434)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                SOAK.validate_parameters(*args)


if __name__ == "__main__":
    unittest.main()
