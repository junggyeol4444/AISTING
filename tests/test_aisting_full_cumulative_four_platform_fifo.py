"""AISTING cumulative 4-platform fan-in -> existing single-AI FIFO regression.

These are isolated fake transport/model tests, not viewer or actual broadcast tests.
No external network, account, OBS streaming, TTS training or user data access.
"""
from __future__ import annotations
import queue
import sys
import threading
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster import multi_platform_session as multi
from ai_broadcaster.desktop_chat_tab import LocalChatTab
from ai_broadcaster.multiplatform_readonly import PlatformChat
from ai_broadcaster.twitch_readonly import TwitchChatLine


class EmittingReader:
    def __init__(self, channel, emit, *extra):
        self.channel = channel
        self.emit = emit
        self.stopped = threading.Event()
        self.calls = 0

    def stop(self):
        self.stopped.set()

    def run(self, *, max_seconds=None):
        code = ("twitch" if self.channel == "twitch-test" else
                "chzzk" if self.channel.startswith("a") else
                "soop" if self.channel.startswith("soop") else "youtube")
        for i in range(500):
            if self.stopped.is_set():
                break
            chat = (TwitchChatLine(self.channel, "viewer", "중복 문장")
                    if code == "twitch" else
                    PlatformChat(self.channel, "viewer", "중복 문장", code))
            self.emit("chat", chat)
            self.calls += 1


class FullCumulativeFanIn(unittest.TestCase):
    def test_two_thousand_duplicates_reach_single_fifo_with_platform_identity(self):
        result_queue = queue.SimpleQueue()
        session_holder = [None]
        def received(kind, message):
            LocalChatTab._enqueue_public_event(
                ui, session_holder[0], kind, message)
        ui = SimpleNamespace(
            _closed=False, _results=result_queue, _twitch_ai_inbox=queue.SimpleQueue())
        values = {"twitch": "twitch-test", "chzzk": "a" * 32,
                  "soop": "soop/123", "youtube": "existingChatId"}
        with patch.object(multi, "TwitchReadOnlySession", EmittingReader), patch.object(
                multi, "ChzzkReadOnlySession", EmittingReader), patch.object(
                multi, "SoopReadOnlySession", EmittingReader), patch.object(
                multi, "YouTubeReadOnlySession", EmittingReader):
            session = multi.MultiPlatformReadOnlySession(
                values, received, youtube_api_key="test-only")
            session_holder[0] = session
            session.run(max_seconds=15)

        events = []
        while not result_queue.empty():
            events.append(result_queue.get_nowait())
        chats = [event[1][2] for event in events
                 if event[0] == "twitch_scoped" and event[1][1] == "twitch_chat"]
        self.assertEqual(len(chats), 2000)
        self.assertTrue(all(x.text == "중복 문장" for x in chats))
        self.assertEqual(Counter(x.platform for x in chats),
                         {"twitch": 500, "chzzk": 500, "soop": 500, "youtube": 500})
        self.assertTrue(all(event[1][0] is session for event in events))
        # The Tk results FIFO is the only point where the existing AI worker
        # may receive these messages; no platform-specific AI is created.
        for chat in chats:
            ui._twitch_ai_inbox.put(chat)
        ui._twitch_ai_inbox.put(None)
        output = queue.SimpleQueue()
        ai = SimpleNamespace(_results=output)
        calls = []
        def model(model_name, text, *, sender, use_committed_gui_character):
            calls.append((text, sender, use_committed_gui_character))
            return SimpleNamespace(reply="답변", remembered_count=len(calls))
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat", side_effect=model):
            LocalChatTab._work_twitch_ai(ai, "local-test-model",
                                         ui._twitch_ai_inbox, False, None)
        self.assertEqual(len(calls), 2000)
        self.assertTrue(all(c[0] == "중복 문장" and c[2] for c in calls))
        self.assertEqual(len([1 for c in calls if c[1].startswith("[트위치]")]), 500)
        self.assertEqual(len([1 for c in calls if c[1].startswith("[치지직]")]), 500)
        self.assertEqual(len([1 for c in calls if c[1].startswith("[SOOP]")]), 500)
        self.assertEqual(len([1 for c in calls if c[1].startswith("[유튜브]")]), 500)
        self.assertEqual(len([output.get_nowait() for _ in range(2000)]), 2000)

    def test_no_emission_after_operator_stop(self):
        events = []
        with patch.object(multi, "TwitchReadOnlySession", EmittingReader):
            reader = multi.MultiPlatformReadOnlySession(
                {"twitch": "twitch-test"}, lambda k, v: events.append((k, v)))
        reader.stop()
        reader._readers["twitch"].emit(
            "chat", TwitchChatLine("twitch-test", "viewer", "늦은 메시지"))
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
