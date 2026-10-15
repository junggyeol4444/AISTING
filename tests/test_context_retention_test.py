"""26단계 맥락 전달 회귀 시험: 외부 자원 접근 없는 결정적 검증."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.context_retention_test import (
    ContextWitnessPort, SAMPLE_CONTEXT_SCRIPT, MAX_CONTEXT_TEST_TURNS,
    MAX_CONTEXT_SCRIPT, run_context_retention_test,
)
from ai_broadcaster.core_execution import OfflineCoreSession, MAX_CONTEXT_TURNS
from ai_broadcaster.offline_settings import DEFAULTS


class FailPort(ContextWitnessPort):
    def __init__(self, fail_at):
        super().__init__()
        self.fail_at = fail_at

    def generate(self, item, history):
        if len(self.calls) + 1 == self.fail_at:
            raise RuntimeError("테스트용 오류")
        return super().generate(item, history)


class BrokenSession(OfflineCoreSession):
    """결함 주입: 응답 포트에 빈 이력을 전달하는 잘못된 세션."""
    def __init__(self, settings, reply_port):
        class BadPort:
            def generate(self, item, history):
                return reply_port.generate(item, ())
        super().__init__(settings, reply_port=BadPort())


class ContextRetentionTests(unittest.TestCase):
    def setUp(self):
        self.settings = copy.deepcopy(DEFAULTS)

    def test_sample_all_pass(self):
        result = run_context_retention_test(self.settings)
        self.assertTrue(result.passed)
        self.assertEqual(result.total, 11)
        self.assertEqual(result.passed_count, 11)
        self.assertEqual(result.remaining, 0)
        self.assertTrue(result.window_boundary_checked)

    def test_initial_empty_history(self):
        port = ContextWitnessPort()
        run_context_retention_test(self.settings, "가: 첫째\n나: 둘째", reply_port=port)
        self.assertEqual(port.calls[0][1], ())
        self.assertEqual(len(port.calls[1][1]), 1)

    def test_history_contains_original_input_and_answer(self):
        port = ContextWitnessPort()
        run_context_retention_test(self.settings, "가: 안녕\n나: 질문\n가: 또 질문", reply_port=port)
        self.assertEqual([x.input.text for x in port.calls[2][1]], ["안녕", "질문"])
        self.assertIn("모의 응답 1:", port.calls[2][1][0].text)
        self.assertEqual(port.calls[2][1][1].input.sender, "나")

    def test_window_exactly_eight(self):
        port = ContextWitnessPort()
        result = run_context_retention_test(self.settings, "\n".join(f"가: {i}" for i in range(12)), reply_port=port)
        self.assertTrue(result.passed)
        self.assertEqual([len(x[1]) for x in port.calls], [min(i, 8) for i in range(12)])
        self.assertEqual([x.input.text for x in port.calls[-1][1]], [str(i) for i in range(3, 11)])

    def test_duplicates_not_collapsed(self):
        port = ContextWitnessPort()
        self.assertTrue(run_context_retention_test(self.settings, "가: 같은 말\n가: 같은 말\n가: 같은 말", reply_port=port).passed)
        self.assertEqual([x.input.text for x in port.calls[-1][1]], ["같은 말", "같은 말"])
        self.assertNotEqual(port.calls[-1][1][0].text, port.calls[-1][1][1].text)

    def test_mixed_senders_share_ordered_history(self):
        port = ContextWitnessPort()
        run_context_retention_test(self.settings, "가: A\n나: B\n가: C", reply_port=port)
        self.assertEqual([x.input.sender for x in port.calls[-1][1]], ["가", "나"])

    def test_settings_unchanged(self):
        before = copy.deepcopy(self.settings)
        run_context_retention_test(self.settings)
        self.assertEqual(before, self.settings)

    def test_new_run_is_isolated(self):
        a = ContextWitnessPort()
        b = ContextWitnessPort()
        run_context_retention_test(self.settings, "가: 첫째\n나: 둘째", reply_port=a)
        run_context_retention_test(self.settings, "가: 다른 시작\n나: 다른 끝", reply_port=b)
        self.assertEqual(b.calls[0][1], ())

    def test_selection_modes_not_connected(self):
        self.settings["content"] = "game"
        self.assertTrue(run_context_retention_test(self.settings).passed)

    def test_no_network_sqlite_process_or_pc_info(self):
        with patch("socket.socket.connect", side_effect=AssertionError("network")) as net, \
             patch("sqlite3.connect", side_effect=AssertionError("sqlite")) as sql, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("pc info")) as pc:
            self.assertTrue(run_context_retention_test(self.settings).passed)
            for spy in (net, sql, proc, pc):
                spy.assert_not_called()

    def test_no_settings_save(self):
        with patch("ai_broadcaster.offline_settings.save_settings", side_effect=AssertionError("write")) as spy:
            run_context_retention_test(self.settings)
            spy.assert_not_called()

    def test_two_turns_minimum(self):
        self.assertTrue(run_context_retention_test(self.settings, "가: 하나\n나: 둘").passed)

    def test_one_turn_rejected(self):
        with self.assertRaises(ValueError):
            run_context_retention_test(self.settings, "가: 하나")

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            run_context_retention_test(self.settings, "")

    def test_wrong_type_rejected(self):
        for value in (None, b"abc", 123, ["가: 안녕"]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_context_retention_test(self.settings, value)

    def test_oversized_rejected(self):
        with self.assertRaises(ValueError):
            run_context_retention_test(self.settings, "가: " + "가" * MAX_CONTEXT_SCRIPT)

    def test_thirty_accepted(self):
        result = run_context_retention_test(self.settings, "\n".join(f"가: {i}" for i in range(MAX_CONTEXT_TEST_TURNS)))
        self.assertTrue(result.passed)
        self.assertEqual(result.total, MAX_CONTEXT_TEST_TURNS)

    def test_thirty_one_rejected(self):
        with self.assertRaises(ValueError):
            run_context_retention_test(self.settings, "\n".join(f"가: {i}" for i in range(MAX_CONTEXT_TEST_TURNS + 1)))

    def test_invalid_line_rejected(self):
        with self.assertRaises(ValueError):
            run_context_retention_test(self.settings, "가: 첫째\n형식오류")

    def test_invalid_settings_rejected(self):
        self.settings["avatar"] = "unknown"
        with self.assertRaises(ValueError):
            run_context_retention_test(self.settings)

    def test_detects_broken_history_forwarding(self):
        result = run_context_retention_test(self.settings, "가: 첫째\n나: 둘째\n다: 셋째", session_factory=BrokenSession)
        self.assertFalse(result.passed)
        self.assertEqual(result.passed_count, 1)
        self.assertIn("불일치", result.turns[1].reason)

    def test_midrun_failure_preserves_pending(self):
        result = run_context_retention_test(self.settings, "가: 첫째\n나: 둘째\n다: 셋째", reply_port=FailPort(2))
        self.assertFalse(result.passed)
        self.assertEqual(result.passed_count, 1)
        self.assertEqual(result.remaining, 2)
        self.assertIn("RuntimeError", result.error)

    def test_error_not_misreported_success(self):
        report = run_context_retention_test(self.settings, "가: 첫째\n나: 둘째", reply_port=FailPort(1))
        self.assertIn("구조 실패", report.describe())
        self.assertFalse(report.passed)

    def test_report_limit_not_claimed_if_too_few_turns(self):
        report = run_context_retention_test(self.settings, "가: 첫째\n나: 둘째")
        self.assertFalse(report.window_boundary_checked)
        self.assertIn("미실행", report.describe())

    def test_window_boundary_requires_tenth_turn(self):
        nine = run_context_retention_test(self.settings, "\n".join(f"가: {i}" for i in range(9)))
        ten = run_context_retention_test(self.settings, "\n".join(f"가: {i}" for i in range(10)))
        self.assertFalse(nine.window_boundary_checked)
        self.assertTrue(ten.window_boundary_checked)

    def test_long_session_history_pruning_keeps_last_eight(self):
        session = OfflineCoreSession(self.settings)
        for i in range(502):
            session.enqueue(f"가: 메시지{i}")
            session.process_one()
        self.assertEqual(len(session.history), 500)
        self.assertEqual(len(session.context_for_next_turn), 8)
        self.assertEqual(session.context_for_next_turn[0].input.text, "메시지494")
        self.assertEqual(session.context_for_next_turn[-1].input.text, "메시지501")

    def test_report_no_claim_of_ai_comprehension(self):
        text = run_context_retention_test(self.settings).describe()
        self.assertIn("의미 이해", text)
        self.assertIn("승인 대기", text)
        self.assertIn("9/100", text)

    def test_readonly_history_snapshot(self):
        session = OfflineCoreSession(self.settings)
        self.assertEqual(session.context_for_next_turn, ())
        session.enqueue("가: 하나\n나: 둘")
        session.process_one()
        snapshot = session.context_for_next_turn
        self.assertIsInstance(snapshot, tuple)
        self.assertEqual(len(snapshot), 1)
        session.process_one()
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(len(session.context_for_next_turn), 2)

    def test_reset_removes_context_only(self):
        session = OfflineCoreSession(self.settings)
        session.enqueue("가: 하나\n나: 둘")
        session.process_one()
        session.reset()
        self.assertEqual(session.context_for_next_turn, ())
        self.assertEqual(session.pending_count, 0)

    def test_max_context_constant(self):
        self.assertEqual(MAX_CONTEXT_TURNS, 8)

    def test_result_frozen(self):
        from dataclasses import FrozenInstanceError
        result = run_context_retention_test(self.settings)
        with self.assertRaises(FrozenInstanceError):
            result.total = 0


if __name__ == "__main__":
    unittest.main()
