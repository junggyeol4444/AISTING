"""Original 056: synthetic virtual speech windows and mouth-pose timing."""
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.avatar_voice_sync import VirtualVoiceMouthSync, VirtualVoiceWindow
from ai_broadcaster.avatar_renderer import draw_avatar
from test_avatar_display_validation import FakeCanvas


class VirtualSyncTests(unittest.TestCase):
    def new(self, script='A: 안녕\nA: 안녕\nB: 다음!', **kwargs):
        options = dict(avatar='2d', name='모의 2D', expression='concerned',
                       voice_source='windows_system', voice_name='가상 한국어',
                       rate=0, volume=80)
        options.update(kwargs)
        return VirtualVoiceMouthSync(script, **options)

    def test_construct_inert(self):
        with patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('db')):
            s = self.new()
            self.assertEqual(s.duration_ms, 0)
            self.assertEqual(s.windows, [])
            self.assertEqual(s.seek(0).frame.mouth, 0)

    def test_requires_manual_dispatch(self):
        s = self.new()
        self.assertEqual(len(s.rehearsal.status().pending), 3)
        self.assertEqual(s.windows, [])
        self.assertEqual(s.seek(0).phase, '가상 구간 밖 · 입 닫힘')

    def test_time_alignment_open_open_close(self):
        s = self.new('A: 안녕')
        s.step()
        w = s.windows[0]
        self.assertGreaterEqual(w.end_ms-w.start_ms, 240)
        self.assertGreater(s.seek(w.start_ms).frame.mouth, 0)
        self.assertGreater(s.seek(w.start_ms + (w.end_ms-w.start_ms)//2).frame.mouth, 0)
        self.assertEqual(s.seek(w.end_ms-1).frame.mouth, 0)
        self.assertEqual(s.seek(w.end_ms).frame.mouth, 0)
        self.assertTrue(s.audit()[0])

    def test_duplicate_chats_are_independent_no_gap(self):
        s = self.new()
        for _ in range(3): s.step()
        self.assertEqual(len(s.windows), 3)
        self.assertEqual([w.chat_number for w in s.windows], [1, 2, 3])
        self.assertEqual(s.windows[0].text, s.windows[1].text)
        self.assertEqual(s.windows[1].start_ms, s.windows[0].end_ms)
        self.assertEqual(s.windows[2].start_ms, s.windows[1].end_ms)
        self.assertTrue(s.audit()[0])

    def test_failure_adds_no_window_and_retry_only_on_click(self):
        s = self.new(fail_second_once=True)
        s.step()
        first_end = s.duration_ms
        status = s.step()
        self.assertEqual(status.state, 'simulated_interrupted')
        self.assertEqual(s.duration_ms, first_end)
        self.assertEqual(len(status.pending), 2)
        self.assertEqual(s.seek(first_end).frame.mouth, 0)
        status = s.step()
        self.assertEqual(len(status.completed), 2)
        self.assertEqual(len(s.windows), 2)
        self.assertEqual(s.windows[1].start_ms, first_end)
        self.assertTrue(s.audit()[0])

    def test_no_automatic_next_chat_on_seek(self):
        s = self.new()
        s.step()
        for tick in (0, s.duration_ms // 2, s.duration_ms):
            s.seek(tick)
        self.assertEqual(len(s.rehearsal.status().pending), 2)
        self.assertEqual(len(s.windows), 1)

    def test_manual_advance_capped_at_end(self):
        s = self.new('A: 안녕'); s.step()
        for _ in range(50): s.advance(100)
        self.assertEqual(s.clock_ms, s.duration_ms)
        self.assertEqual(s.advance(100).frame.mouth, 0)

    def test_seek_boundaries_rejected(self):
        s = self.new('A: 안녕'); s.step()
        for ms in (-1, s.duration_ms+1, True, 4.5, '0'):
            with self.subTest(ms=ms), self.assertRaises(ValueError):
                s.seek(ms)

    def test_advance_input_boundaries(self):
        s = self.new()
        for milliseconds in (-1, 0, 10001, True, 2.2):
            with self.subTest(milliseconds=milliseconds), self.assertRaises(ValueError):
                s.advance(milliseconds)

    def test_timing_parameters_checked(self):
        for value in (0, 19, 501, -1, True, 80.5, '90'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.new(milliseconds_per_character=value)

    def test_user_determined_timing_changes_virtual_duration(self):
        short = self.new('A: 안녕하세요', milliseconds_per_character=20)
        long = self.new('A: 안녕하세요', milliseconds_per_character=180)
        short.step(); long.step()
        self.assertGreater(long.duration_ms, short.duration_ms)

    def test_segment_split_preserves_voice_window_identity(self):
        s = self.new('A: 길게')
        s.rehearsal._link._generator.generate = lambda *_: '가'*1250
        s.step()
        self.assertEqual(len(s.windows), 3)
        self.assertEqual([w.segment_index for w in s.windows], [1, 2, 3])
        self.assertEqual(len(''.join(w.text for w in s.windows)), 1250)
        self.assertTrue(s.audit()[0])

    def test_audit_detects_noncontiguous_or_forged_windows(self):
        s = self.new('A: 안녕'); s.step()
        old = s.windows[0]
        s.windows[0] = replace(old, start_ms=1)
        self.assertFalse(s.audit()[0])

    def test_audit_detects_wrong_voice_text(self):
        s = self.new('A: 안녕'); s.step()
        s.windows[0] = replace(s.windows[0], text='바뀐 출력')
        self.assertFalse(s.audit()[0])

    def test_audit_detects_missing_segment(self):
        s = self.new('A: 안녕'); s.step()
        s.windows.clear()
        self.assertFalse(s.audit()[0])

    def test_3d_fails_closed_and_no_fallback(self):
        for avatar in ('3d', 'undecided'):
            with self.subTest(avatar=avatar), self.assertRaises(ValueError):
                self.new(avatar=avatar)

    def test_voice_source_fails_closed(self):
        with self.assertRaises(ValueError):
            self.new(voice_source='own_recording')

    def test_expression_preserved_in_canvas(self):
        s = self.new('A: 안녕'); s.step()
        for t, open_expected in ((0, True),(s.duration_ms-1, False)):
            canvas = FakeCanvas()
            draw_avatar(canvas, s.seek(t).frame)
            self.assertEqual(bool(canvas.find_withtag('aisting_mouth_open')), open_expected)
            self.assertTrue(canvas.find_withtag('aisting_expression_concerned'))

    def test_no_files_audio_or_external_calls(self):
        with patch('builtins.open', side_effect=AssertionError('file')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')):
            s = self.new('A: 안녕'); s.step(); self.assertTrue(s.audit()[0])

    def test_explicit_mock_disclaimer(self):
        s = self.new('A: 안녕'); s.step()
        self.assertIn('실제 TTS', s.describe())
        self.assertIn('미검증', s.describe())
