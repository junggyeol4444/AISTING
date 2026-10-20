"""Real coordinator lifecycle regression (isolated transports; never a live broadcast)."""
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster import multi_platform_session as module
from ai_broadcaster.multiplatform_readonly import PlatformChat


class MockReader:
    instances = []

    def __init__(self, channel, callback, *args):
        self.channel = channel
        self.callback = callback
        self.stopped = threading.Event()
        self.entered = threading.Event()
        self.release = threading.Event()
        type(self).instances.append(self)

    def run(self, *, max_seconds=None):
        self.entered.set()
        self.release.wait(8)

    def stop(self):
        self.stopped.set()


class CoordinatorLifecycle(unittest.TestCase):
    def setUp(self):
        MockReader.instances.clear()
        self._patchers = [
            patch.object(module, name, MockReader)
            for name in ("TwitchReadOnlySession", "ChzzkReadOnlySession",
                         "SoopReadOnlySession", "YouTubeReadOnlySession")
        ]
        for p in self._patchers:
            p.start()
            self.addCleanup(p.stop)

    def session(self, events=None):
        channels = {"twitch": "testchannel", "chzzk": "a" * 32,
                    "soop": "tester/42", "youtube": "existing_chat_id"}
        return module.MultiPlatformReadOnlySession(
            channels, lambda kind, item: events.append((kind, item))
            if events is not None else None, youtube_api_key="offline")

    def tearDown(self):
        for reader in MockReader.instances:
            reader.release.set()

    def test_whole_session_timeout_closes_all_four(self):
        session = self.session()
        before = time.monotonic()
        session.run(max_seconds=0.1)
        self.assertLess(time.monotonic() - before, 4.4)
        self.assertTrue(session._stop.is_set())
        self.assertTrue(all(reader.stopped.wait(1) for reader in MockReader.instances))

    def test_stop_is_idempotent_and_shared_at_request_time(self):
        session = self.session()
        session.stop()
        first = session._stop_started_at
        session.stop()
        self.assertEqual(session._stop_started_at, first)
        self.assertTrue(all(r.stopped.wait(1) for r in MockReader.instances))
        self.assertLessEqual(first, time.monotonic())

    def test_one_broken_close_cannot_hold_other_readers(self):
        class BrokenReader(MockReader):
            def stop(self):
                if self.channel == "testchannel":
                    raise RuntimeError("secret-service-token")
                super().stop()
        with patch.object(module, "TwitchReadOnlySession", BrokenReader):
            session = self.session()
        start = time.monotonic()
        session.stop()
        self.assertLess(time.monotonic() - start, 1)
        self.assertTrue(all(r.stopped.wait(1) for r in MockReader.instances[1:]))

    def test_second_thread_start_failure_closes_all_previous(self):
        original = threading.Thread
        class FailChzzkThread(original):
            def start(self):
                if self.name == "aisting-public-chzzk":
                    raise RuntimeError("secret_transport_data")
                return super().start()
        with patch.object(module.threading, "Thread", FailChzzkThread):
            session = self.session()
            with self.assertRaises(RuntimeError) as caught:
                session.run(max_seconds=1)
        self.assertNotIn("secret_transport_data", str(caught.exception))
        self.assertTrue(session._stop.is_set())
        self.assertTrue(all(r.stopped.wait(1) for r in MockReader.instances))

    def test_events_preserve_duplicates_and_disappear_after_stop(self):
        events = []
        session = self.session(events)
        item = PlatformChat("testchannel", "name", "반복 채팅", "twitch")
        callback = MockReader.instances[0].callback
        callback("chat", item)
        callback("chat", item)
        self.assertEqual([v.text for kind, v in events if kind == "chat"],
                         ["반복 채팅", "반복 채팅"])
        session.stop()
        callback("chat", item)
        self.assertEqual(len(events), 2)


if __name__ == "__main__":
    unittest.main()
