"""Measured local FIFO+AI elapsed time; never claims viewer end-to-end latency.

All external models and streams are isolated fakes. No account or disk writes.
"""
import math
import queue
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop_chat_tab import LocalChatTab
from ai_broadcaster.multiplatform_readonly import PlatformChat


class Value:
    def __init__(self):
        self.content = ""
    def set(self, value):
        self.content = value
    def get(self):
        return self.content


class LocalAIMeasurementTests(unittest.TestCase):
    def test_duplicate_messages_have_individual_measured_queue_plus_ai_times(self):
        inbox, arrivals, results = queue.SimpleQueue(), queue.SimpleQueue(), queue.SimpleQueue()
        texts = [PlatformChat("room", "viewer", "반복", code)
                 for code in ("twitch", "chzzk", "soop", "youtube")]
        for msg in texts:
            arrivals.put(time.monotonic() - 1.0)
            inbox.put(msg)
        inbox.put(None)
        fake = SimpleNamespace(_results=results, _ai_arrival_times=arrivals)
        calls = []
        def model(model_name, text, *, sender, use_committed_gui_character):
            calls.append((model_name, text, sender, use_committed_gui_character))
            return SimpleNamespace(reply="완료", remembered_count=len(calls))
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat", side_effect=model):
            LocalChatTab._work_twitch_ai(fake, "local-model", inbox)
        output = []
        while not results.empty():
            output.append(results.get_nowait())
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(x[1] == "반복" and x[3] for x in calls))
        self.assertEqual([code for code, _ in output],
                         ["twitch_ai_ok", "twitch_ai_latency"] * 4)
        self.assertEqual(len([payload for kind, payload in output
                              if kind == "twitch_ai_ok"]), 4)
        self.assertTrue(all(isinstance(payload, float) and payload >= 1
                            for kind, payload in output if kind == "twitch_ai_latency"))

    def test_failed_model_preserves_error_and_measurement_without_secret(self):
        inbox, arrivals, results = queue.SimpleQueue(), queue.SimpleQueue(), queue.SimpleQueue()
        inbox.put(PlatformChat("room", "viewer", "한 건", "chzzk"))
        inbox.put(None)
        arrivals.put(time.monotonic() - 3.5)
        fake = SimpleNamespace(_results=results, _ai_arrival_times=arrivals)
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                   side_effect=RuntimeError("credential-should-not-display")):
            LocalChatTab._work_twitch_ai(fake, "local-model", inbox)
        items = [results.get_nowait(), results.get_nowait()]
        self.assertEqual([kind for kind, _ in items],
                         ["twitch_ai_error", "twitch_ai_latency"])
        self.assertGreater(items[1][1], 3)
        self.assertNotIn("credential-should-not-display", repr(items))

    def test_legacy_queue_without_timestamps_remains_supported(self):
        inbox, results = queue.SimpleQueue(), queue.SimpleQueue()
        inbox.put(PlatformChat("room", "viewer", "legacy", "twitch"))
        inbox.put(None)
        fake = SimpleNamespace(_results=results)
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                   return_value=SimpleNamespace(reply="ok", remembered_count=1)):
            LocalChatTab._work_twitch_ai(fake, "local-model", inbox)
        self.assertEqual(results.get_nowait()[0], "twitch_ai_ok")
        self.assertTrue(results.empty())

    def test_gui_latency_over_three_seconds_flags_only_measured_section(self):
        results = queue.SimpleQueue()
        results.put(("twitch_ai_latency", 3.6))
        status = Value()
        fake = SimpleNamespace(_closed=False, _results=results, _twitch_status=status,
                               _poll=lambda: None, after=lambda *_: None)
        LocalChatTab._poll(fake)
        self.assertIn("3초 초과", status.get())
        self.assertIn("GUI 접수", status.get())
        self.assertIn("네트워크·시청자 전달 시간은 미측정", status.get())

    def test_missing_metrics_cannot_fabricate_success(self):
        results = queue.SimpleQueue()
        results.put(("twitch_ai_latency", math.nan))
        status = Value()
        fake = SimpleNamespace(_closed=False, _results=results, _twitch_status=status,
                               _poll=lambda: None, after=lambda *_: None)
        LocalChatTab._poll(fake)
        self.assertEqual(status.get(), "")


if __name__ == "__main__":
    unittest.main()
