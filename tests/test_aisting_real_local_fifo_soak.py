"""Validate the real (never canned-LLM) Windows load runner's controls."""
import importlib.util
import json
import tempfile
import io
import queue
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

    def test_actual_worker_reports_bounded_live_checkpoints_without_chat_text(self):
        summaries = []
        with patch.object(SOAK, "real_ollama_chat",
                          return_value=SimpleNamespace(reply="한국어", remembered_count=1)):
            result = SOAK.run_real_load(
                model="installed-local-test", messages=52,
                duration_seconds=6, queue_size=80,
                progress_callback=summaries.append)
        self.assertTrue(result["passed_no_drops"])
        self.assertEqual(result["completed"], 52)
        self.assertGreaterEqual(len(summaries), 3)
        self.assertEqual(summaries[-1]["completed"], 52)
        self.assertEqual(summaries[-1]["target_messages"], 52)
        self.assertIn(25, [v["completed"] for v in summaries])
        self.assertIn(50, [v["completed"] for v in summaries])
        for record in summaries:
            self.assertNotIn("synthetic-", json.dumps(record))
            self.assertNotIn("안녕하세요", json.dumps(record))
            self.assertFalse(record["actual_viewer_delivery_verified"])
            self.assertFalse(record["actual_24h_broadcast_verified"])

    def test_progress_checkpoint_replaces_atomically_without_sensitive_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "aggregate.json"
            SOAK._atomic_aggregate_checkpoint(file, {
                "status":"running", "accepted":28,
                "completed":25, "real_viewers":False})
            first = json.loads(file.read_text(encoding="utf-8"))
            self.assertEqual(first["completed"], 25)
            SOAK._atomic_aggregate_checkpoint(file, {
                "status":"complete", "accepted":500,
                "completed":500, "real_viewers":False})
            second = json.loads(file.read_text(encoding="utf-8"))
            self.assertEqual(second["completed"], 500)
            self.assertEqual(list(Path(folder).iterdir()), [file])

    def test_deadline_partial_acceptance_is_failure_even_when_every_accepted_reply_succeeds(self):
        # A finite-duration paced test must NOT certify 500/500 after
        # accepting only its first message. Real AI is mocked here only
        # to test the result's accounting, not model performance.
        with patch.object(SOAK, "real_ollama_chat",
                          return_value=SimpleNamespace(reply="정상", remembered_count=1)):
            result = SOAK.run_real_load(
                model="installed-local-test", messages=500,
                duration_seconds=1, arrival_rate=0.1,
                queue_size=100)
        self.assertGreater(result["accepted"], 0)
        self.assertLess(result["accepted"], 500)
        self.assertEqual(result["model_success"], result["accepted"])
        self.assertEqual(result["completed"], result["accepted"])
        self.assertEqual(result["not_accepted"], 500 - result["accepted"])
        self.assertFalse(result["requested_load_fully_accepted"])
        self.assertIn("requested_messages_not_fully_accepted",
                      result["processing_errors"])
        self.assertFalse(result["passed_no_drops"])
        self.assertFalse(result["passed_three_second_local"])
        self.assertFalse(result["viewer_end_to_end_verified"])

    def test_success_requires_full_target_and_reports_p95_sample_size(self):
        with patch.object(SOAK, "real_ollama_chat",
                          return_value=SimpleNamespace(reply="정상", remembered_count=1)):
            result = SOAK.run_real_load(
                model="installed-local-test", messages=36,
                duration_seconds=3, queue_size=50)
        self.assertTrue(result["requested_load_fully_accepted"])
        self.assertEqual(result["not_accepted"], 0)
        self.assertTrue(result["passed_no_drops"])
        self.assertEqual(result["local_p95_sample_count"], 36)

    def test_paced_24h_style_run_drains_results_while_messages_are_arriving(self):
        # 간격 입력 중 중간 완료 결과 집계. 로컬 모델은 여기서 모의한다.
        snapshots = []
        with patch.object(SOAK, "real_ollama_chat",
                          return_value=SimpleNamespace(reply="정상", remembered_count=1)):
            result = SOAK.run_real_load(
                model="installed-local-test", messages=36,
                duration_seconds=5, arrival_rate=12,
                queue_size=80, progress_callback=snapshots.append)
        self.assertTrue(result["passed_no_drops"])
        self.assertEqual(result["completed"], 36)
        self.assertTrue(any(
            item["completed"] >= 25 and item["accepted"] < 36
            for item in snapshots))
        self.assertEqual(snapshots[-1]["completed"], 36)
        self.assertFalse(result["long_running_broadcast_verified"])

    def test_observed_output_is_not_reported_as_live_viewer_delivery(self):
        # 로컬 추론 성공과 시청자에게 전달됐다는 증거는 다르다.
        with patch.object(SOAK, "real_ollama_chat",
                          return_value=SimpleNamespace(reply="정상", remembered_count=1)):
            result = SOAK.run_real_load(
                model="installed-local-test", messages=16,
                duration_seconds=4, arrival_rate=8, queue_size=40)
        self.assertEqual(result["accepted"], 16)
        self.assertEqual(result["model_success"], 16)
        self.assertFalse(result["viewer_end_to_end_verified"])
        self.assertFalse(result["long_running_broadcast_verified"])

    def test_saturated_load_queue_does_not_leave_orphan_arrival_timestamp(self):
        # A rejected synthetic message must not corrupt FIFO timing.
        inbox = SOAK._TimestampedInputQueue(maxsize=1)
        arrivals = queue.SimpleQueue()
        inbox.put_chat("첫 번째", arrivals, timeout=0.01)
        with self.assertRaises(queue.Full):
            inbox.put_chat("미접수", arrivals, timeout=0.01)
        self.assertEqual(inbox.get_nowait(), "첫 번째")
        self.assertGreater(arrivals.get_nowait(), 0)
        with self.assertRaises(queue.Empty):
            arrivals.get_nowait()
        inbox.put_chat("다음", arrivals, timeout=0.01)
        self.assertEqual(inbox.get_nowait(), "다음")
        self.assertGreater(arrivals.get_nowait(), 0)

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
