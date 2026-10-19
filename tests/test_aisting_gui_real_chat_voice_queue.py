"""Regression for real AISTING AI voice queue without starting speech."""
import sys
import unittest
from pathlib import Path
from collections import deque
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop_chat_tab import LocalChatTab

class LiveChatVoiceQueueTests(unittest.TestCase):
    def test_busy_audio_keeps_all_responses_in_fifo_including_duplicates(self):
        started = []
        dummy = SimpleNamespace(_tts_busy=True, _closed=False,
            _queued_voice=deque(),
            _tts_status=SimpleNamespace(set=lambda text: None),
            _begin_read=lambda text,voice: started.append(text))
        voice = object()
        for text in ("첫 답변","두 번째","첫 답변"):
            LocalChatTab._queue_voice_reply(dummy,text,voice)
        self.assertEqual(len(dummy._queued_voice),3)
        self.assertEqual(started,[])
        dummy._tts_busy=False
        # Binding the unbound function to our fake instance only exercises
        # the queue policy, not installed Windows audio or real TTS.
        dummy._start_next_queued_voice=lambda: LocalChatTab._start_next_queued_voice(dummy)
        while dummy._queued_voice:
            dummy._start_next_queued_voice()
        self.assertEqual(started,["첫 답변","두 번째","첫 답변"])
    def test_closing_forbids_new_playback(self):
        dummy=SimpleNamespace(_tts_busy=False,_closed=True,
            _queued_voice=deque(),
            _begin_read=lambda *args: self.fail("closed tab played audio"))
        LocalChatTab._queue_voice_reply(dummy,"안녕",object())
        self.assertFalse(dummy._queued_voice)

if __name__=="__main__":
    unittest.main()
