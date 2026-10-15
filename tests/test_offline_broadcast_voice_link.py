"""Stage 073 virtual voice-to-scene port: no actual audio output."""
import sqlite3
import subprocess
import unittest
from dataclasses import replace
from unittest.mock import patch

from test_offline_broadcast_scene import FakeCanvas, make
from ai_broadcaster.offline_broadcast_voice_link import OfflineBroadcastVoiceLink


class FailCanvas(FakeCanvas):
    def create_text(self, *args, **kwargs):
        raise RuntimeError('synthetic draw failure')


class OfflineBroadcastVoiceTests(unittest.TestCase):
    def test_prepare_does_not_emit_speech(self):
        voice = OfflineBroadcastVoiceLink(make(), '테스트 문장')
        self.assertEqual(voice.status().state, 'ready')
        self.assertEqual(voice.status().delivered, ())

    def test_all_source_types_fail_closed_without_fallback(self):
        for source in ('undecided', 'own_recording', 'consented_recording', 'licensed_recording'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                OfflineBroadcastVoiceLink(make(voice=source), '가상')

    def test_type_and_text_validation(self):
        for bad in (None, '', '  ', 'a' * 6001):
            with self.subTest(bad=repr(bad)[:10]), self.assertRaises(ValueError):
                OfflineBroadcastVoiceLink(make(), bad)
        with self.assertRaises(ValueError):
            OfflineBroadcastVoiceLink(None, '가상')
        for maximum in (0, 601, True, '20'):
            with self.assertRaises(ValueError):
                OfflineBroadcastVoiceLink(make(), '가상', maximum=maximum)

    def test_manual_segments_preserve_order_and_duplicates(self):
        voice = OfflineBroadcastVoiceLink(make(), '가나' * 12, maximum=5)
        canvas = FakeCanvas()
        expected = voice.chunks
        self.assertGreater(len(expected), 1)
        self.assertEqual(voice.cursor, 0)
        results = [voice.step(canvas, make()) for _ in expected]
        self.assertEqual(tuple(''.join(v) for v in (results[-1].delivered,)), (''.join(expected),))
        self.assertEqual(results[-1].remaining, ())
        self.assertEqual(results[-1].state, 'simulated_complete')
        self.assertTrue('aisting_scene_voice' in canvas.tags())
        self.assertEqual(voice.step(canvas, make()).delivered, expected)

    def test_interrupt_does_not_consume_and_manual_resume(self):
        voice = OfflineBroadcastVoiceLink(make(), '1234567890', maximum=4)
        canvas = FakeCanvas()
        stopped = voice.step(canvas, make(), interrupt=True)
        self.assertEqual(stopped.state, 'simulated_interrupted')
        self.assertEqual(stopped.delivered, ())
        first = voice.step(canvas, make())
        self.assertEqual(first.delivered, voice.chunks[:1])
        stopped = voice.step(canvas, make(), interrupt=True)
        self.assertEqual(stopped.delivered, first.delivered)
        self.assertEqual(stopped.remaining, first.remaining)
        self.assertEqual(voice.step(canvas, make()).delivered, voice.chunks[:2])

    def test_wrong_scene_rejected_even_if_text_same(self):
        voice = OfflineBroadcastVoiceLink(make(), '가상 음성')
        for changed in (make(content='game'), make(show_title=False), make(voice='undecided')):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                voice.step(FakeCanvas(), changed)
            self.assertEqual(voice.cursor, 0)
        with self.assertRaises(ValueError):
            voice.step(FakeCanvas(), object())

    def test_other_platform_selection_invalidates(self):
        voice = OfflineBroadcastVoiceLink(make(), '테스트')
        with self.assertRaises(ValueError):
            voice.step(FakeCanvas(), make(platforms=('youtube',)))

    def test_2d_or_3d_not_forced_to_switch(self):
        for avatar in ('2d', '3d', 'undecided'):
            layout = make().layout if avatar == '2d' else None
            draft = make(avatar=avatar, layout=layout)
            voice = OfflineBroadcastVoiceLink(draft, '테스트')
            self.assertEqual(voice.step(FakeCanvas(), draft).state, 'simulated_complete')
            self.assertEqual(voice.draft.avatar, avatar)

    def test_reject_non_boolean_interrupt(self):
        voice = OfflineBroadcastVoiceLink(make(), '테스트')
        with self.assertRaises(ValueError):
            voice.step(FakeCanvas(), make(), interrupt=1)

    def test_virtual_canvas_error_leaves_chunk_for_retry(self):
        draft = make()
        voice = OfflineBroadcastVoiceLink(draft, '하나 둘 셋', maximum=3)
        with self.assertRaises(RuntimeError):
            voice.step(FailCanvas(), draft)
        self.assertEqual(voice.cursor, 0)
        self.assertEqual(voice.status().state, 'simulated_error')
        good = voice.step(FakeCanvas(), draft)
        self.assertEqual(good.delivered, voice.chunks[:1])

    def test_overlay_discloses_silent_virtual_path(self):
        canvas = FakeCanvas()
        voice = OfflineBroadcastVoiceLink(make(), '소리 안 나는 가상 표시')
        status = voice.step(canvas, make())
        self.assertIn('실제 음성/OBS 송출 0건', status.detail)
        self.assertTrue(any('무음 가상 출력' in str(kwargs.get('text'))
                            for action, args, kwargs in canvas.calls if action == 'create_text'))

    def test_never_touch_external_systems(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('subprocess.run', side_effect=AssertionError('OS')), \
             patch('sqlite3.connect', side_effect=AssertionError('DB')), \
             patch('builtins.open', side_effect=AssertionError('disk')):
            draft = make()
            voice = OfflineBroadcastVoiceLink(draft, '안녕')
            self.assertEqual(voice.step(FakeCanvas(), draft).state, 'simulated_complete')

if __name__ == '__main__':
    unittest.main()
