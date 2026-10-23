# -*- coding: utf-8 -*-
"""138회차: 4플랫폼 AI FIFO의 수신 시각을 해당 연결에만 결속한다.

외부 계정·방송·OBS·음성 합성은 실행하지 않는 로컬 계약 검사.
로컬 시각 측정은 실제 시청자 종단간 1~3초 달성 증거가 아니다.
"""
import queue
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop_chat_tab import LocalChatTab
from ai_broadcaster.multiplatform_readonly import PlatformChat


class 세션별수신시각격리검사(unittest.TestCase):
    @staticmethod
    def _execute(messages, old_times, replacement_times, *, explicit=True):
        inbox = queue.SimpleQueue()
        previous = queue.SimpleQueue()
        current = queue.SimpleQueue()
        events = queue.SimpleQueue()
        for msg in messages:
            inbox.put(msg)
        inbox.put(None)
        for value in old_times:
            previous.put(value)
        for value in replacement_times:
            current.put(value)
        session = SimpleNamespace(_stop=threading.Event())
        dummy = SimpleNamespace(
            _results=events, _ai_arrival_times=current,
            _live_latency_metrics=object(), _twitch_active_workers=())
        def reply(model, text, *, sender, use_committed_gui_character):
            return SimpleNamespace(reply="확인: " + text)
        options = {"arrival_times": previous} if explicit else {}
        LocalChatTab._work_twitch_ai(
            dummy, "로컬 테스트 모델", inbox, session=session,
            reply_function=reply, **options)
        captured = []
        while not events.empty():
            captured.append(events.get_nowait())
        return captured, previous, current

    def test_새연결이_교체해도_이전작업자는_자기수신시각만_소비(self):
        now = time.monotonic()
        chat = PlatformChat("방", "시청자", "첫 질문", "chzzk")
        events, old, new = self._execute(
            [chat], [now - 0.5], [now - 100.0])
        names = [event[1][1] for event in events]
        self.assertIn("twitch_ai_ok", names)
        self.assertIn("twitch_ai_timing", names)
        timing = next(event[1][2] for event in events
                      if event[1][1] == "twitch_ai_timing")
        self.assertGreaterEqual(timing[2], 0.5)
        self.assertLess(timing[2], 10)
        self.assertTrue(old.empty())
        self.assertEqual(new.get_nowait(), now - 100.0)

    def test_같은세션의_두_채팅은_두_수신시각을_FIFO로_소비(self):
        now = time.monotonic()
        chats = [PlatformChat("방", "A", str(n), "soop") for n in range(2)]
        events, old, new = self._execute(
            chats, [now - 1.0, now - 0.25], [now - 500.0])
        times = [event[1][2][2] for event in events
                 if event[1][1] == "twitch_ai_timing"]
        self.assertEqual(len(times), 2)
        self.assertGreater(times[0], times[1])
        self.assertTrue(old.empty())
        self.assertEqual(new.get_nowait(), now - 500.0)

    def test_해당세션_시각누락은_다음세션의_시각으로_채우지않음(self):
        now = time.monotonic()
        chat = PlatformChat("방", "A", "질문", "youtube")
        events, old, new = self._execute(
            [chat], [], [now - 30.0])
        names = [event[1][1] for event in events]
        self.assertIn("twitch_ai_ok", names)
        self.assertNotIn("twitch_ai_timing", names)
        self.assertTrue(old.empty())
        self.assertEqual(new.get_nowait(), now - 30.0)

    def test_기존_인자없는_직접호출_계약은_그대로_유지(self):
        now = time.monotonic()
        chat = PlatformChat("방", "A", "질문", "twitch")
        events, _, new = self._execute(
            [chat], [], [now - 0.3], explicit=False)
        self.assertIn("twitch_ai_timing", [event[1][1] for event in events])
        self.assertTrue(new.empty())


if __name__ == "__main__":
    unittest.main()
