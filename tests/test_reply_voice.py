"""EXE용 무료 AI 답변->한국어 음성 읽기 테스트. 실제 스피커/PC 설치 불필요."""
import sys
import threading
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from ai_broadcaster.reply_voice import (
    ReadingResult, ReplyVoicePlayer, should_auto_read, split_reply,
)
from ai_broadcaster.windows_tts import Voice, SpeechError


class FakeSpeechBackend:
    def __init__(self):
        self.read_parts=[]
        self._started=threading.Event()
        self._release=threading.Event()
        self.block=False
        self.stopped=False

    def speak(self,text,voice):
        self.read_parts.append(text)
        self._started.set()
        if self.block:
            self._release.wait(timeout=3)
        if self.stopped:
            raise SpeechError("stopped")

    def stop(self):
        self.stopped=True
        self._release.set()
        return True


class TestReplySpeech(unittest.TestCase):
    def setUp(self):
        self.voice=Voice("Installed Korean", "ko-KR")
        self.backend=FakeSpeechBackend()
        self.player=ReplyVoicePlayer(self.backend)

    def test_split_short_korean(self):
        self.assertEqual(split_reply("안녕하세요! 반갑습니다."),["안녕하세요! 반갑습니다."])

    def test_split_long_text_no_omitted_letters(self):
        text="가"*1402
        parts=split_reply(text)
        self.assertEqual("".join(parts),text)
        self.assertEqual([len(p) for p in parts],[600,600,202])

    def test_split_prefers_sentence_boundary(self):
        text=("가"*320)+". "+("나"*400)
        result=split_reply(text)
        self.assertEqual(len(result),2)
        self.assertTrue(result[0].endswith("."))
        self.assertTrue(result[1].startswith("나"))

    def test_empty_or_huge_rejected(self):
        for val in ("", "  ", "가"*6001, None):
            with self.subTest(val=str(val)[:20]),self.assertRaises(ValueError):
                split_reply(val)

    def test_segment_limit_enforced(self):
        for val in (0,601,True,2.5):
            with self.subTest(val=val),self.assertRaises(ValueError):
                split_reply("테스트",max_chars=val)

    def test_voice_auto_read_disabled_by_default(self):
        self.assertFalse(should_auto_read(False,self.voice,"안녕"))
        self.assertFalse(should_auto_read(None,self.voice,"안녕"))

    def test_voice_auto_read_requires_installed_ko_voice(self):
        self.assertFalse(should_auto_read(True,None,"안녕"))
        self.assertFalse(should_auto_read(True,self.voice," "))
        self.assertTrue(should_auto_read(True,self.voice,"안녕"))

    def test_no_sound_on_object_construction(self):
        self.assertEqual(self.backend.read_parts,[])
        self.assertFalse(self.player.speaking)

    def test_all_parts_spoken_once_in_order(self):
        text="가"*1250
        result=self.player.read(text,self.voice)
        self.assertEqual(result,ReadingResult(3,3,False))
        self.assertEqual("".join(self.backend.read_parts),text)
        self.assertFalse(self.player.speaking)

    def test_reject_non_voice(self):
        with self.assertRaises(TypeError):
            self.player.read("안녕","bogus")
        self.assertEqual(self.backend.read_parts,[])

    def test_stop_mid_sentence_prevents_following_parts(self):
        self.backend.block=True
        outcomes=[]
        def worker():
            outcomes.append(self.player.read("가"*1250,self.voice))
        thread=threading.Thread(target=worker)
        thread.start()
        self.assertTrue(self.backend._started.wait(timeout=2))
        self.assertTrue(self.player.speaking)
        self.assertTrue(self.player.stop())
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(self.backend.read_parts),1)
        self.assertEqual(outcomes[0],ReadingResult(3,0,True))
        self.assertFalse(self.player.speaking)

    def test_prevent_overlapping_audio(self):
        self.backend.block=True
        thread=threading.Thread(target=lambda: self.player.read("첫 번째",self.voice))
        thread.start()
        self.assertTrue(self.backend._started.wait(timeout=2))
        with self.assertRaises(SpeechError):
            self.player.read("두 번째",self.voice)
        self.player.stop()
        thread.join(timeout=4)
        self.assertFalse(thread.is_alive())
        self.assertEqual(self.backend.read_parts,["첫 번째"])

    def test_voice_after_stop_can_be_used_again(self):
        self.backend.block=True
        thread=threading.Thread(target=lambda: self.player.read("가"*1200,self.voice))
        thread.start()
        self.assertTrue(self.backend._started.wait(timeout=2))
        self.player.stop()
        thread.join(timeout=4)
        self.assertFalse(thread.is_alive())
        self.backend.block=False
        self.backend.stopped=False
        self.backend._started.clear()
        result=self.player.read("다시 시작",self.voice)
        self.assertEqual(result,ReadingResult(1,1,False))

    def test_gui_auto_read_off_initially(self):
        code=(ROOT/"src/ai_broadcaster/desktop_chat_tab.py").read_text(encoding="utf-8")
        self.assertIn("_auto_voice = tk.BooleanVar(value=False)",code)
        self.assertIn('should_auto_read(self._auto_voice.get()',code)
        self.assertNotIn("subprocess.Popen(",code)
