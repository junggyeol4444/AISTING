"""27단계: 실제 코어 오류 처리, 명시적 복구, 실패 시 데이터 보존."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.core_execution import (
    MAX_REPLY, MAX_RESPONSE_ATTEMPTS, CoreBatchError, CoreGenerationError,
    CoreInvalidReplyError, CoreRetryLimitError, OfflineCoreSession,
)
from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.response_error_test import (
    SCENARIOS, FaultPort, run_response_error_test,
)


class ResponseHandlingTests(unittest.TestCase):
    def setUp(self):
        self.settings = copy.deepcopy(DEFAULTS)

    def session(self, *outcomes):
        port = FaultPort(tuple(outcomes))
        session = OfflineCoreSession(self.settings, port)
        session.enqueue("가: 같은 입력\n가: 같은 입력\n나: 셋")
        return session, port

    def test_initial_no_failure(self):
        s, _ = self.session("답변")
        self.assertIsNone(s.last_failure)

    def test_creation_does_not_call_port(self):
        _, port = self.session("답변")
        self.assertEqual(port.calls, 0)

    def test_timeout_classification_and_fifo(self):
        s, _ = self.session(TimeoutError("SECRET"))
        with self.assertRaises(CoreGenerationError) as ctx:
            s.process_one()
        self.assertNotIn("SECRET", str(ctx.exception))
        self.assertEqual((s.last_failure.code, s.last_failure.attempts), ("timeout", 1))
        self.assertEqual((s.pending_count, s.total_processed, s.history), (3, 0, ()))

    def test_connection_classification(self):
        s, _ = self.session(ConnectionError("SECRET"))
        with self.assertRaises(CoreGenerationError):
            s.process_one()
        self.assertEqual(s.last_failure.code, "connection")

    def test_generic_generation_error_sanitized(self):
        s, _ = self.session(RuntimeError("api_key=secret"))
        with self.assertRaises(CoreGenerationError) as ctx:
            s.process_one()
        self.assertEqual(s.last_failure.code, "generation")
        self.assertNotIn("secret", str(ctx.exception))
        self.assertNotIn("secret", repr(s.last_failure))

    def test_wrong_type_classification(self):
        for value in (None, 1, True, [], {}, b"bytes"):
            with self.subTest(value=value):
                s, _ = self.session(value)
                with self.assertRaises(CoreInvalidReplyError):
                    s.process_one()
                self.assertEqual(s.last_failure.code, "invalid_type")

    def test_blank_classification(self):
        for value in ("", " ", "\t\n"):
            with self.subTest(value=value):
                s, _ = self.session(value)
                with self.assertRaises(CoreInvalidReplyError):
                    s.process_one()
                self.assertEqual(s.last_failure.code, "empty_reply")

    def test_oversize_classification(self):
        s, _ = self.session("가" * (MAX_REPLY + 1))
        with self.assertRaises(CoreInvalidReplyError):
            s.process_one()
        self.assertEqual(s.last_failure.code, "oversized_reply")

    def test_maximum_reply_is_valid(self):
        s, _ = self.session("가" * MAX_REPLY)
        self.assertEqual(len(s.process_one().text), MAX_REPLY)
        self.assertIsNone(s.last_failure)

    def test_manual_retry_no_auto_loop(self):
        s, port = self.session(TimeoutError("secret"), "정상")
        with self.assertRaises(CoreGenerationError):
            s.process_one()
        self.assertEqual(port.calls, 1)
        self.assertEqual(s.retry_failed().text, "정상")
        self.assertEqual(port.calls, 2)
        self.assertEqual(s.total_processed, 1)
        self.assertIsNone(s.last_failure)

    def test_retry_requires_failure(self):
        s, port = self.session("정상")
        with self.assertRaises(ValueError):
            s.retry_failed()
        self.assertEqual(port.calls, 0)

    def test_failure_attempts_increment(self):
        s, port = self.session(*[TimeoutError("secret") for _ in range(3)])
        for count in range(1, 4):
            with self.assertRaises(CoreGenerationError):
                s.process_one() if count == 1 else s.retry_failed()
            self.assertEqual(s.last_failure.attempts, count)
        self.assertEqual(port.calls, MAX_RESPONSE_ATTEMPTS)

    def test_retry_limit_blocks_all_execution_paths(self):
        s, port = self.session(*[TimeoutError("secret") for _ in range(3)])
        for _ in range(3):
            with self.assertRaises(CoreGenerationError):
                s.process_one()
        with self.assertRaises(CoreRetryLimitError):
            s.retry_failed()
        with self.assertRaises(CoreRetryLimitError):
            s.process_one()
        with self.assertRaises(CoreBatchError) as ctx:
            s.run_batch()
        self.assertIn("상한", str(ctx.exception))
        self.assertEqual((port.calls, s.pending_count, s.total_processed), (3, 3, 0))

    def test_no_discard_without_confirmation(self):
        s, _ = self.session(TimeoutError())
        with self.assertRaises(CoreGenerationError):
            s.process_one()
        for confirm in (False, 1, "yes", None):
            with self.subTest(confirm=confirm), self.assertRaises(PermissionError):
                s.discard_failed(confirmed=confirm)
        self.assertEqual(s.pending_count, 3)

    def test_discard_only_failed_head_and_keep_duplicates(self):
        s, _ = self.session(TimeoutError(), "정상")
        with self.assertRaises(CoreGenerationError):
            s.process_one()
        removed = s.discard_failed(confirmed=True)
        self.assertEqual((removed.sender, removed.text), ("가", "같은 입력"))
        self.assertEqual(s.pending_count, 2)
        self.assertEqual(s.process_one().input.text, "같은 입력")
        self.assertEqual(s.total_processed, 1)
        self.assertIsNone(s.last_failure)

    def test_discard_requires_failure_even_if_confirmed(self):
        s, _ = self.session("정상")
        with self.assertRaises(ValueError):
            s.discard_failed(confirmed=True)

    def test_success_resets_retry_counter(self):
        s, _ = self.session(TimeoutError(), "정상", TimeoutError(), "정상2")
        with self.assertRaises(CoreGenerationError):
            s.process_one()
        s.retry_failed()
        with self.assertRaises(CoreGenerationError):
            s.process_one()
        self.assertEqual(s.last_failure.attempts, 1)
        s.retry_failed()
        self.assertEqual(s.total_processed, 2)

    def test_enqueue_after_failure_keeps_failed_head(self):
        s, _ = self.session(TimeoutError(), "정상")
        with self.assertRaises(CoreGenerationError):
            s.process_one()
        s.enqueue("다: 뒤에 추가")
        self.assertEqual(s.last_failure.attempts, 1)
        self.assertEqual(s.pending_count, 4)
        self.assertEqual(s.retry_failed().input.sender, "가")

    def test_selection_change_after_failure_preserves_error(self):
        s, _ = self.session(TimeoutError(), "정상")
        with self.assertRaises(CoreGenerationError):
            s.process_one()
        settings = copy.deepcopy(self.settings)
        settings["platforms"] = ["youtube", "twitch"]
        settings["content"] = "both"
        settings["avatar"] = "3d"
        s.update_selection(settings)
        self.assertEqual(s.last_failure.code, "timeout")
        self.assertEqual(s.pending_count, 3)
        self.assertEqual(s.retry_failed().input.sender, "가")
        self.assertEqual(s.blueprint.avatar, "3d")

    def test_partial_batch_preserves_history(self):
        s, _ = self.session("첫 답변", TimeoutError(), "복구", "셋")
        with self.assertRaises(CoreBatchError) as ctx:
            s.run_batch(3)
        self.assertEqual((len(ctx.exception.processed), ctx.exception.remaining), (1, 2))
        self.assertEqual(s.history[0].text, "첫 답변")
        self.assertEqual(s.retry_failed().text, "복구")
        s.run_batch()
        self.assertEqual([x.text for x in s.history], ["첫 답변", "복구", "셋"])

    def test_reset_clears_failure_and_queue_only(self):
        s, _ = self.session(TimeoutError())
        with self.assertRaises(CoreGenerationError):
            s.process_one()
        s.reset()
        self.assertIsNone(s.last_failure)
        self.assertEqual(s.pending_count, 0)
        self.assertEqual(s.history, ())

    def test_error_does_not_modify_settings(self):
        original = copy.deepcopy(self.settings)
        s, _ = self.session(TimeoutError())
        with self.assertRaises(CoreGenerationError):
            s.process_one()
        self.assertEqual(self.settings, original)

    def test_no_network_or_sqlite_or_pc_read_on_error(self):
        s, _ = self.session(TimeoutError(), "정상")
        with patch("socket.socket.connect", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("sqlite3.connect", side_effect=AssertionError("sqlite")) as sql, \
             patch("platform.system", side_effect=AssertionError("PC info")) as pc:
            with self.assertRaises(CoreGenerationError):
                s.process_one()
            s.retry_failed()
        for spy in (net, proc, sql, pc):
            spy.assert_not_called()

    def test_simulation_all_scenarios(self):
        report = run_response_error_test(self.settings)
        self.assertTrue(report.passed, report.describe())
        self.assertEqual(len(report.checks), len(SCENARIOS))

    def test_simulation_single_scenario(self):
        for code in SCENARIOS:
            with self.subTest(code=code):
                report = run_response_error_test(self.settings, code)
                self.assertEqual(len(report.checks), 1)
                self.assertTrue(report.passed, report.describe())

    def test_simulation_invalid_scenario(self):
        for code in ("unknown", "", None, 1):
            with self.subTest(code=code), self.assertRaises(ValueError):
                run_response_error_test(self.settings, code)

    def test_simulation_invalid_settings_fails_not_pass(self):
        report = run_response_error_test({"content": "invalid"})
        self.assertFalse(report.passed)
        self.assertEqual(report.passed_count, 0)

    def test_simulation_bad_factory_fails(self):
        def broken(*args, **kwargs):
            raise RuntimeError("deliberate")
        report = run_response_error_test(self.settings, session_factory=broken)
        self.assertFalse(report.passed)
        self.assertIn("실패", report.describe())

    def test_simulation_no_external_access(self):
        with patch("socket.socket.connect", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("sqlite3.connect", side_effect=AssertionError("sqlite")) as sql, \
             patch("platform.system", side_effect=AssertionError("PC info")) as pc:
            report = run_response_error_test(self.settings)
        self.assertTrue(report.passed)
        for spy in (net, proc, sql, pc):
            spy.assert_not_called()

    def test_simulation_does_not_change_settings(self):
        original = copy.deepcopy(self.settings)
        run_response_error_test(self.settings)
        self.assertEqual(self.settings, original)

    def test_report_distinguishes_mock_from_real(self):
        report = run_response_error_test(self.settings)
        self.assertIn("실제 Ollama", report.describe())
        self.assertIn("9/100", report.describe())
        self.assertIn("8/8", report.describe())


if __name__ == "__main__":
    unittest.main()
