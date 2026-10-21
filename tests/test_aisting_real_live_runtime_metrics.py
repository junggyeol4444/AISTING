"""Local real-FIFO diagnostic invariants, never simulated viewer latency proof."""
from __future__ import annotations
import math
import queue
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.live_runtime_metrics import LiveLatencyMetrics
from ai_broadcaster.multiplatform_readonly import PlatformChat
from ai_broadcaster.desktop_chat_tab import LocalChatTab


class Value:
    def __init__(self):
        self.value = ""
    def set(self, x):
        self.value = x
    def get(self):
        return self.value


class RuntimeMetricTests(unittest.TestCase):
    def test_queue_wait_and_ai_p95_are_distinct(self):
        m = LiveLatencyMetrics(100)
        for i in range(500):
            m.accept()
            self.assertTrue(m.terminal(0.1 + i * 0.01, 0.2, 0.3 + i * 0.01))
        snap = m.snapshot(200)
        self.assertEqual(snap.accepted, 500)
        self.assertEqual(snap.completed, 500)
        self.assertEqual(snap.failed, 0)
        self.assertGreater(snap.wait_p95, 4.0)
        self.assertAlmostEqual(snap.inference_p95, 0.2)
        self.assertGreater(snap.over_three_seconds, 100)
        self.assertIn("시청자 전달", snap.describe())

    def test_bounded_snapshot_without_message_content_or_secret(self):
        m = LiveLatencyMetrics(10, capacity=4)
        for i in range(10000):
            m.accept()
            m.terminal(0.1, 0.2, 0.3)
        snap = m.snapshot(12)
        self.assertEqual(snap.accepted, 10000)
        self.assertEqual(snap.completed, 10000)
        self.assertEqual(snap.sampled, 4)
        self.assertNotIn("credential", repr(snap))
        self.assertEqual(snap.over_three_seconds, 0)

    def test_24_hours_local_connection_is_never_broadcast_proof(self):
        m = LiveLatencyMetrics(10)
        m.accept()
        m.reader_fault()
        snap = m.snapshot(86410)
        self.assertEqual(snap.local_running_seconds, 86400)
        self.assertEqual(snap.reader_faults, 1)
        self.assertIn("미검증", snap.describe())
        m.stop(86410)
        self.assertFalse(m.terminal(1, 1, 2))
        self.assertEqual(m.snapshot(86499).local_running_seconds, 86400)

    def test_invalid_clock_values_do_not_count_as_success(self):
        m = LiveLatencyMetrics(0)
        m.accept()
        for vals in [(math.nan, 1, 1), (0.2, -1, 1),
                     (1, 1, 5), (0, 0, 0, "yes")]:
            self.assertFalse(m.terminal(*vals))
        self.assertEqual(m.snapshot(9).invalid, 4)
        self.assertEqual(m.snapshot(9).completed, 0)
        with self.assertRaises(ValueError):
            m.snapshot(-1)

    def test_failures_and_duplicates_are_never_dropped(self):
        m = LiveLatencyMetrics(0)
        for i in range(2000):
            m.accept()
            self.assertTrue(m.terminal(1.5, 2, 3.5, failed=i % 2 == 0))
        r = m.snapshot(100)
        self.assertEqual((r.accepted, r.completed, r.failed), (2000, 2000, 1000))
        self.assertEqual(r.over_three_seconds, 2000)
        self.assertEqual(r.sampled, 1024)

    def test_real_worker_emits_timing_event_with_legacy_event_still_intact(self):
        inbox, arrivals, results = queue.SimpleQueue(), queue.SimpleQueue(), queue.SimpleQueue()
        inbox.put(PlatformChat("room", "viewer", "반복", "youtube"))
        inbox.put(None)
        arrivals.put(time.monotonic() - 0.05)
        fake = SimpleNamespace(_results=results, _ai_arrival_times=arrivals,
                               _live_latency_metrics=LiveLatencyMetrics(time.monotonic() - 1))
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                   return_value=SimpleNamespace(reply="안녕", remembered_count=1)):
            LocalChatTab._work_twitch_ai(fake, "installed-model", inbox)
        events = [results.get_nowait() for _ in range(3)]
        self.assertEqual([kind for kind, _ in events],
                         ["twitch_ai_ok", "twitch_ai_latency", "twitch_ai_timing"])
        waiting, processing, total, failed = events[2][1]
        self.assertGreater(waiting, 0.03)
        self.assertGreaterEqual(processing, 0)
        self.assertAlmostEqual(waiting + processing, total, places=3)
        self.assertFalse(failed)

    def test_failed_real_worker_appears_as_failed_terminal_sample(self):
        inbox, arrivals, results = queue.SimpleQueue(), queue.SimpleQueue(), queue.SimpleQueue()
        inbox.put(PlatformChat("room", "viewer", "반복", "chzzk"))
        inbox.put(None)
        arrivals.put(time.monotonic() - 3.2)
        fake = SimpleNamespace(_results=results, _ai_arrival_times=arrivals,
                               _live_latency_metrics=LiveLatencyMetrics(time.monotonic() - 4))
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                   side_effect=RuntimeError("secret should not print")):
            LocalChatTab._work_twitch_ai(fake, "installed-model", inbox)
        events = [results.get_nowait() for _ in range(3)]
        self.assertEqual([kind for kind, _ in events],
                         ["twitch_ai_error", "twitch_ai_latency", "twitch_ai_timing"])
        self.assertTrue(events[2][1][3])
        self.assertNotIn("secret should not print", repr(events))
        self.assertGreater(events[2][1][2], 3)

    def test_native_poll_accepts_real_split_metrics(self):
        meter = LiveLatencyMetrics(time.monotonic() - 2)
        meter.accept()
        results = queue.SimpleQueue()
        results.put(("twitch_ai_timing", (1.0, 2.6, 3.6, False)))
        seen = []
        fake = SimpleNamespace(_closed=False, _results=results,
                               _live_latency_metrics=meter,
                               _append=lambda text: seen.append(text),
                               _poll=lambda: None, after=lambda *_: None)
        LocalChatTab._poll(fake)
        self.assertEqual(meter.snapshot(time.monotonic()).completed, 1)
        self.assertIn("p95", seen[0])
        self.assertIn("3초 초과 1건", seen[0])


if __name__ == "__main__":
    unittest.main()
