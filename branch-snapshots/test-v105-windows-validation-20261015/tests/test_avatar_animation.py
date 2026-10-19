"""2D 기본 캐릭터 애니메이션 제어와 EXE 음성 이벤트 연결 테스트.

CI에서 화면 표시 장치나 TTS 설치 없이 실행된다.
"""
import sys
import threading
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from ai_broadcaster.avatar_animation import SpeechActivity, blink_frame, mouth_frame


class TestSpeechActivity(unittest.TestCase):
    def setUp(self):
        self.activity=SpeechActivity()

    def test_idle_by_default(self):
        self.assertFalse(self.activity.talking)
        self.assertEqual(self.activity.active_sources,frozenset())

    def test_start_and_finish(self):
        self.activity.start("chat_reply")
        self.assertTrue(self.activity.talking)
        self.activity.finish("chat_reply")
        self.assertFalse(self.activity.talking)

    def test_overlapping_voice_sources(self):
        self.activity.start("chat_reply")
        self.activity.start("voice_preview")
        self.activity.finish("chat_reply")
        self.assertTrue(self.activity.talking)
        self.assertEqual(self.activity.active_sources,frozenset({"voice_preview"}))
        self.activity.finish("voice_preview")
        self.assertFalse(self.activity.talking)

    def test_duplicate_start_is_idempotent(self):
        self.activity.start("chat_reply")
        self.activity.start("chat_reply")
        self.activity.finish("chat_reply")
        self.assertFalse(self.activity.talking)

    def test_finish_unknown_is_safe(self):
        self.activity.finish("unknown")
        self.assertFalse(self.activity.talking)

    def test_invalid_sources_rejected(self):
        for source in ("",None,1,"x"*81):
            with self.subTest(value=str(source)),self.assertRaises(ValueError):
                self.activity.start(source)

    def test_status_snapshot_is_immutable(self):
        self.activity.start("chat_reply")
        snapshot=self.activity.active_sources
        self.activity.finish("chat_reply")
        self.assertEqual(snapshot,frozenset({"chat_reply"}))
        self.assertFalse(self.activity.talking)

    def test_concurrent_starts_and_stops(self):
        def worker(n):
            for _ in range(100):
                self.activity.start(f"s{n}")
                self.activity.finish(f"s{n}")
        threads=[threading.Thread(target=worker,args=(i,)) for i in range(6)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=3)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertFalse(self.activity.talking)


class TestAvatarAnimation(unittest.TestCase):
    def test_idle_mouth_always_closed(self):
        self.assertEqual({mouth_frame(False,f) for f in range(250)},{0})

    def test_talking_mouth_animates(self):
        frames=[mouth_frame(True,i) for i in range(12)]
        self.assertEqual(frames,[1,2,3,2,1,2]*2)
        self.assertTrue(all(f>0 for f in frames))

    def test_bad_frame_rejected(self):
        for f in (-1,True,1.2):
            with self.subTest(frame=f),self.assertRaises(ValueError):
                mouth_frame(True,f)

    def test_non_boolean_talking_rejected(self):
        with self.assertRaises(TypeError):
            mouth_frame("yes",1)

    def test_blink_pattern(self):
        self.assertTrue(blink_frame(0))
        self.assertTrue(blink_frame(1))
        self.assertFalse(blink_frame(2))
        self.assertFalse(blink_frame(46))
        self.assertTrue(blink_frame(47))

    def test_negative_blink_frame_rejected(self):
        with self.assertRaises(ValueError):
            blink_frame(-1)

    def test_2d_preview_uses_only_tkinter_canvas(self):
        code=(ROOT/"src/ai_broadcaster/avatar_preview.py").read_text(encoding="utf-8")
        self.assertIn("tk.Canvas(",code)
        self.assertIn("mouth_frame(",code)
        self.assertIn("self.activity.talking",code)
        self.assertNotIn("requests.",code)
        self.assertNotIn("http://",code)
        self.assertNotIn("PhotoImage(",code)

    def test_desktop_wires_local_voice_and_avatar_state(self):
        code=(ROOT/"src/ai_broadcaster/desktop.py").read_text(encoding="utf-8")
        self.assertIn("self._speaker = WindowsKoreanSpeech()",code)
        self.assertIn("self._speech_pending: deque[str] = deque()",code)
        self.assertIn("self._avatar_capture_window",code)
        self.assertIn("self._close_avatar_capture()",code)

    def test_audio_events_set_and_clear_avatar_state(self):
        for module,marker in (
            ("desktop_chat_tab.py","chat_reply"),
            ("desktop_voice_tab.py","voice_preview"),
        ):
            code=(ROOT/"src/ai_broadcaster"/module).read_text(encoding="utf-8")
            with self.subTest(module=module):
                self.assertIn(f'self._activity.start("{marker}")',code)
                self.assertIn(f'self._activity.finish("{marker}")',code)

    def test_manual_animation_demo_does_not_claim_audio(self):
        code=(ROOT/"src/ai_broadcaster/avatar_preview.py").read_text(encoding="utf-8")
        self.assertIn("음성 없이 입 움직임 테스트",code)
        self.assertIn("speaking = is_voice_active or self._demo.get()",code)
        self.assertNotIn('self.activity.start("demo")',code)
