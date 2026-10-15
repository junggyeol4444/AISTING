"""22단계: 수동 모의 코어의 실제 FIFO 실행/오류 보존/외부 부작용 차단."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.core_execution import (
    MAX_BATCH, MAX_HISTORY, MAX_PENDING, MAX_REPLY, CoreBatchError,
    MockCoreReplyPort, OfflineCoreSession,
)
from ai_broadcaster.core_ports import CoreInput, CoreReply
from ai_broadcaster.offline_settings import DEFAULTS


UNSET = object()


class FailingPort:
    def __init__(self, fail_on=1, result=UNSET):
        self.calls = 0
        self.fail_on = fail_on
        self.result = result
        self.seen = []

    def generate(self, item, history):
        self.calls += 1
        self.seen.append((item, history))
        if self.calls == self.fail_on:
            raise RuntimeError("simulated failure")
        return self.result if self.result is not UNSET else f"reply-{self.calls}"


class CoreExecutionTests(unittest.TestCase):
    def setUp(self):
        self.settings = copy.deepcopy(DEFAULTS)
        self.session = OfflineCoreSession(self.settings)

    def test_empty_session(self):
        self.assertEqual(self.session.pending_count, 0)
        self.assertEqual(self.session.total_processed, 0)
        self.assertEqual(self.session.history, ())

    def test_no_implicit_execution_on_creation(self):
        port = FailingPort()
        OfflineCoreSession(self.settings, port)
        self.assertEqual(port.calls, 0)

    def test_enqueued_but_not_processed(self):
        self.assertEqual(self.session.enqueue("가: 하나\n나: 둘"), 2)
        self.assertEqual(self.session.pending_count, 2)
        self.assertEqual(self.session.history, ())

    def test_process_fifo_duplicates(self):
        self.session.enqueue("가: 같은 내용\n가: 같은 내용\n나: 셋")
        result = self.session.run_batch()
        self.assertEqual([x.input.sender for x in result.processed], ["가", "가", "나"])
        self.assertEqual([x.input.text for x in result.processed], ["같은 내용", "같은 내용", "셋"])
        self.assertEqual(result.remaining, 0)
        self.assertEqual(result.total_processed, 3)

    def test_uses_existing_mock_generator(self):
        self.session.enqueue("철수: 안녕")
        result = self.session.process_one()
        self.assertIn("모의 답변", result.text)
        self.assertIn("철수", result.text)

    def test_contracts(self):
        self.session.enqueue("철수: 안녕")
        result = self.session.process_one()
        self.assertIsInstance(result, CoreReply)
        self.assertIsInstance(result.input, CoreInput)

    def test_mock_adapter_preserves_history(self):
        adapter = MockCoreReplyPort()
        text = adapter.generate(CoreInput("나", "안녕"), (CoreReply(CoreInput("가", "첫"), "첫 답"),))
        self.assertIn("나님", text)

    def test_batch_one_and_remaining(self):
        self.session.enqueue("가: 1\n나: 2\n다: 3")
        result = self.session.run_batch(1)
        self.assertEqual((len(result.processed), result.remaining, result.total_processed), (1, 2, 1))

    def test_empty_batch_no_output(self):
        self.assertEqual(self.session.run_batch().processed, ())
        self.assertIsNone(self.session.process_one())

    def test_invalid_batch_sizes(self):
        for value in (0, -1, 51, True, "2", None, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.session.run_batch(value)

    def test_max_batch_enforced(self):
        self.session.enqueue("\n".join(f"가: {i}" for i in range(MAX_BATCH + 1)))
        result = self.session.run_batch()
        self.assertEqual(len(result.processed), MAX_BATCH)
        self.assertEqual(result.remaining, 1)

    def test_script_atomic_reject(self):
        self.session.enqueue("가: 먼저")
        with self.assertRaises(ValueError):
            self.session.enqueue("나: 좋아\n형식 오류")
        self.assertEqual(self.session.pending_count, 1)

    def test_queue_limit(self):
        self.session.enqueue("\n".join(f"가: {i}" for i in range(MAX_PENDING)))
        with self.assertRaises(ValueError):
            self.session.enqueue("나: 추가")
        self.assertEqual(self.session.pending_count, MAX_PENDING)

    def test_reenqueue_after_processing(self):
        self.session.enqueue("가: 1")
        self.session.process_one()
        self.session.enqueue("나: 2")
        self.assertEqual(self.session.run_batch().total_processed, 2)

    def test_failure_keeps_head_and_history(self):
        port = FailingPort()
        s = OfflineCoreSession(self.settings, port)
        s.enqueue("가: 첫\n나: 둘")
        with self.assertRaises(RuntimeError):
            s.process_one()
        self.assertEqual(s.pending_count, 2)
        self.assertEqual(s.history, ())
        self.assertEqual(s.process_one().input.sender, "가")

    def test_partial_batch_failure_is_explicit(self):
        port = FailingPort(fail_on=2)
        s = OfflineCoreSession(self.settings, port)
        s.enqueue("가: 첫\n나: 둘\n다: 셋")
        with self.assertRaises(CoreBatchError) as ctx:
            s.run_batch(3)
        self.assertEqual(len(ctx.exception.processed), 1)
        self.assertEqual(ctx.exception.remaining, 2)
        self.assertEqual(s.total_processed, 1)
        self.assertEqual(s.process_one().input.sender, "나")

    def test_empty_reply_rejected_without_dequeue(self):
        for reply in ("", "  ", None, 7, "x" * (MAX_REPLY + 1)):
            with self.subTest(reply=str(reply)[:8]):
                port = FailingPort(fail_on=999, result=reply)
                s = OfflineCoreSession(self.settings, port)
                s.enqueue("가: 하나")
                with self.assertRaises(ValueError):
                    s.process_one()
                self.assertEqual(s.pending_count, 1)
                self.assertEqual(s.total_processed, 0)

    def test_generator_history_order(self):
        port = FailingPort(fail_on=999)
        s = OfflineCoreSession(self.settings, port)
        s.enqueue("\n".join(f"가: {i}" for i in range(12)))
        s.run_batch(12)
        self.assertEqual(len(port.seen[0][1]), 0)
        self.assertEqual(len(port.seen[-1][1]), 8)
        self.assertEqual(port.seen[-1][1][0].input.text, "3")

    def test_history_bounded(self):
        self.session.enqueue("\n".join(f"가: {i}" for i in range(500)))
        for _ in range(10):
            self.session.run_batch()
        self.session.enqueue("나: extra")
        self.session.process_one()
        self.assertEqual(len(self.session.history), MAX_HISTORY)
        self.assertEqual(self.session.total_processed, 501)
        self.assertEqual(self.session.history[0].input.text, "1")

    def test_selection_change_preserves_queue(self):
        self.session.enqueue("가: 1")
        self.settings["platforms"] = ["youtube", "twitch"]
        self.settings["content"] = "both"
        self.session.update_selection(self.settings)
        self.assertEqual(self.session.blueprint.platforms, ("youtube", "twitch"))
        self.assertEqual(self.session.pending_count, 1)
        self.assertEqual(self.session.run_batch().total_processed, 1)

    def test_invalid_selection_is_atomic(self):
        old = self.session.blueprint
        with self.assertRaises(ValueError):
            self.session.update_selection({"content": "invalid"})
        self.assertIs(self.session.blueprint, old)

    def test_settings_not_mutated(self):
        old = copy.deepcopy(self.settings)
        self.session.enqueue("가: 1")
        self.session.run_batch()
        self.assertEqual(self.settings, old)

    def test_no_external_ports_activated(self):
        self.session.enqueue("가: 1")
        with patch("socket.create_connection", side_effect=AssertionError("network")) as network, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as process, \
             patch("sqlite3.connect", side_effect=AssertionError("sqlite")) as sqlite, \
             patch("urllib.request.urlopen", side_effect=AssertionError("url")) as url:
            self.session.run_batch()
        network.assert_not_called()
        process.assert_not_called()
        sqlite.assert_not_called()
        url.assert_not_called()

    def test_reset_only_session(self):
        self.session.enqueue("가: 1\n나: 2")
        self.session.process_one()
        self.session.reset()
        self.assertEqual(self.session.pending_count, 0)
        self.assertEqual(self.session.total_processed, 0)
        self.assertEqual(self.session.history, ())

    def test_result_describes_limits(self):
        self.session.enqueue("가: 1")
        report = self.session.run_batch().describe()
        self.assertIn("오프라인 모의", report)
        self.assertIn("OBS", report)
        self.assertIn("AI(모의)", report)

    def test_all_choice_types_accepted(self):
        self.settings["platforms"] = ["chzzk", "youtube", "twitch"]
        self.settings["avatar"] = "3d"
        self.settings["voice"] = "undecided"
        self.settings["content"] = "both"
        self.session.update_selection(self.settings)
        self.assertEqual(self.session.blueprint.avatar, "3d")
        self.assertFalse(self.session.blueprint.streaming_enabled)


if __name__ == "__main__":
    unittest.main()
