"""Roadmap 055: virtual voice output produces silent 2D mouth cues only on success."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from ai_broadcaster.avatar_voice_mouth import VoiceMouthRehearsal
from ai_broadcaster.avatar_renderer import draw_avatar
from test_avatar_display_validation import FakeCanvas


class VoiceMouthTests(unittest.TestCase):
    def session(self, script='시청자: 안녕\n시청자: 안녕\n다른분: 오늘은?', **kw):
        args = dict(avatar='2d', name='테스트 캐릭터', expression='smile',
                    voice_source='windows_system', voice_name='가상 한국어',
                    rate=0, volume=75)
        args.update(kw)
        return VoiceMouthRehearsal(script, **args)

    def test_inert_on_construct(self):
        with patch('subprocess.Popen', side_effect=AssertionError('process forbidden')), \
             patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
             patch('sqlite3.connect', side_effect=AssertionError('db forbidden')):
            s = self.session()
            self.assertEqual(s.cues, [])
            self.assertEqual(s.status().state, 'ready')
            self.assertEqual(len(s.status().pending), 3)

    def test_single_chat_produces_open_open_close(self):
        s = self.session('A: 안녕')
        state = s.step()
        self.assertEqual(state.state, 'simulated_complete')
        self.assertEqual(len(state.completed), 1)
        self.assertEqual([cue.frame.mouth > 0 for cue in s.cues], [True, True, False])
        self.assertEqual([cue.chat_number for cue in s.cues], [1, 1, 1])
        self.assertEqual([cue.segment_index for cue in s.cues], [1, 1, 1])
        self.assertTrue(all(cue.frame.expression == 'smile' for cue in s.cues))

    def test_every_chat_duplicates_each_get_unique_cycle(self):
        s = self.session()
        for _ in range(3): s.step()
        self.assertEqual(len(s.cues), 9)
        self.assertEqual([s.cues[k].chat_number for k in (0, 3, 6)], [1, 2, 3])
        self.assertEqual([a.original.text for a in s.status().completed], ['안녕', '안녕', '오늘은?'])
        self.assertEqual(len(s.status().pending), 0)

    def test_failure_keeps_chat_and_emits_no_motion(self):
        s = self.session(fail_second_once=True)
        s.step()
        state = s.step()
        self.assertEqual(state.state, 'simulated_interrupted')
        self.assertEqual(len(state.completed), 1)
        self.assertEqual(len(state.pending), 2)
        self.assertEqual(len(s.cues), 3)
        self.assertEqual(s.cues[-1].frame.mouth, 0)

    def test_explicit_retry_resumes_without_duplicate(self):
        s = self.session(fail_second_once=True)
        s.step(); s.step(); s.step()
        self.assertEqual(len(s.status().completed), 2)
        self.assertEqual(len(s.cues), 6)
        self.assertEqual([x.chat_number for x in s.cues], [1]*3+[2]*3)

    def test_no_automatic_retry(self):
        s = self.session(fail_second_once=True)
        s.step(); s.step()
        for _ in range(3):
            self.assertEqual(len(s.cues), 3)
            self.assertEqual(len(s.status().pending), 2)

    def test_end_does_not_repeat_mouth_cues(self):
        s = self.session('A: 안녕')
        s.step(); s.step(); s.step()
        self.assertEqual(len(s.cues), 3)

    def test_visual_canvas_matches_open_close(self):
        s = self.session('A: 안녕', expression='concerned')
        s.step()
        for expected, cue in zip((True, True, False), s.cues):
            canvas = FakeCanvas()
            draw_avatar(canvas, cue.frame)
            self.assertEqual(bool(canvas.find_withtag('aisting_mouth_open')), expected)
            self.assertEqual(bool(canvas.find_withtag('aisting_mouth_closed')), not expected)
            self.assertTrue(canvas.find_withtag('aisting_expression_concerned'))

    def test_does_not_accept_3d_or_undecided(self):
        for avatar in ('3d', 'undecided', ''):
            with self.subTest(avatar=avatar), self.assertRaises(ValueError):
                self.session(avatar=avatar)

    def test_source_not_configured_fails_closed(self):
        with self.assertRaises(ValueError):
            self.session(voice_source='own_recording')

    def test_invalid_expression_rejected(self):
        with self.assertRaises(ValueError):
            self.session(expression='auto')

    def test_invalid_voice_profile_rejected(self):
        with self.assertRaises(ValueError):
            self.session(rate=99)

    def test_invalid_voice_name_rejected(self):
        with self.assertRaises(ValueError):
            self.session(voice_name='')

    def test_empty_script_rejected(self):
        with self.assertRaises(ValueError):
            self.session(script='')

    def test_max_chat_enforced(self):
        with self.assertRaises(ValueError):
            self.session(script='\n'.join('A: 안녕' for _ in range(31)))

    def test_long_reply_multiple_chunks_preserves_segment_cues(self):
        s = self.session('A: 길게')
        s._link._generator.generate = lambda *_args: '가'*1250
        state = s.step()
        self.assertEqual(state.state, 'simulated_complete')
        self.assertEqual([s.cues[k].segment_index for k in (0, 3, 6)], [1, 2, 3])
        self.assertEqual(len(s.cues), 9)

    def test_sanitized_status_never_claims_actual_lipsync(self):
        s = self.session('A: 안녕')
        self.assertIn('무음', s.describe())
        self.assertIn('미검증', s.describe())

    def test_standby_does_not_create_files_or_external_connection(self):
        with patch('builtins.open', side_effect=AssertionError('file access')), \
             patch('subprocess.Popen', side_effect=AssertionError('process forbidden')), \
             patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
            s = self.session('A: 안녕')
            s.step()
            self.assertEqual(len(s.cues), 3)
