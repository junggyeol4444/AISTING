"""Original 077: synthetic cross-subsystem dataflow and failure checks."""
import sqlite3
import subprocess
import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import patch

from test_offline_broadcast_output_audit import TagCanvas
from test_offline_broadcast_scene import make
from ai_broadcaster.offline_chat_voice_screen_integration import (
    ChatVoiceScreenIntegrationResult, run_offline_chat_voice_screen_integration,
)


class InspectableCanvas(TagCanvas):
    """Fake provides actual per-item tag/text lookup, unlike a tag-only stub."""
    def __init__(self):
        super().__init__()
        self._items = {}
        self._next_id = 0

    def _create(self, method, *args, **kwargs):
        record = super().__getattr__(method)
        record(*args, **kwargs)
        self._next_id += 1
        self._items[self._next_id] = (tuple(kwargs.get('tags', ())), kwargs.get('text', ''), method)
        return self._next_id

    def create_text(self, *args, **kwargs):
        return self._create('create_text', *args, **kwargs)

    def create_rectangle(self, *args, **kwargs):
        return self._create('create_rectangle', *args, **kwargs)

    def __getattr__(self, method):
        if method in ('create_oval', 'create_arc', 'create_line'):
            return lambda *args, **kwargs: self._create(method, *args, **kwargs)
        return super().__getattr__(method)

    def delete(self, tag):
        super().__getattr__('delete')(tag)
        if tag == 'all':
            self._items.clear()
        else:
            self._items = {idx: item for idx, item in self._items.items() if tag not in item[0]}

    def find_withtag(self, tag):
        return tuple(idx for idx, item in self._items.items() if tag in item[0])

    def type(self, item):
        return 'text' if self._items[item][2] == 'create_text' else 'rectangle'

    def itemcget(self, item, name):
        return self._items[item][1] if name == 'text' else ''


class IntegrationTests(unittest.TestCase):
    def run_case(self, draft=None, volume=85, fault_at=None, canvas=None):
        return run_offline_chat_voice_screen_integration(
            canvas or InspectableCanvas(), draft or make(), volume, fault_at=fault_at)

    def test_three_messages_each_correlated_through_visible_text(self):
        result = self.run_case()
        self.assertTrue(result.passed, result.describe())
        self.assertEqual((result.received, result.responded, result.displayed), (3, 3, 3))
        self.assertEqual(result.ordinals, (1, 2, 3))
        self.assertGreaterEqual(result.rendered_segments, 3)
        self.assertFalse(result.actual_audio or result.actual_video or result.actual_streaming)
        self.assertEqual(result.approval, 'pending')

    def test_multi_platform_and_3d_no_fallback(self):
        for avatar in ('2d', '3d', 'undecided'):
            with self.subTest(avatar=avatar):
                draft = make(platforms=('youtube', 'twitch'), avatar=avatar,
                             layout=None if avatar != '2d' else make().layout)
                canvas = InspectableCanvas()
                self.assertTrue(self.run_case(draft=draft, canvas=canvas).passed)
                self.assertEqual(bool(canvas.find_withtag('aisting_sample_2d')), avatar == '2d')
                self.assertEqual(bool(canvas.find_withtag('aisting_scene_avatar_placeholder')), avatar != '2d')

    def test_every_platform_is_accepted_without_autoselection(self):
        for platform in ('chzzk', 'youtube', 'twitch'):
            self.assertTrue(self.run_case(draft=make(platforms=(platform,))).passed)

    def test_missing_platform_fail_closed(self):
        with self.assertRaisesRegex(ValueError, '플랫폼'):
            self.run_case(draft=make(platforms=()))

    def test_unconnected_voice_no_fallback(self):
        for voice in ('undecided', 'licensed_recording', 'local_clone'):
            with self.subTest(voice=voice), self.assertRaises(ValueError):
                self.run_case(draft=make(voice=voice))

    def test_zero_volume_not_claim_audible(self):
        result = self.run_case(volume=0)
        self.assertTrue(result.passed)
        self.assertIn('실제 음성 재생 0', result.describe())

    def test_wrong_volume_and_bool_rejected(self):
        for volume in (-1, 101, True, '85', None):
            with self.subTest(volume=volume), self.assertRaises(ValueError):
                self.run_case(volume=volume)

    def test_fault_at_each_message_never_reports_success(self):
        for step in (1, 2, 3):
            with self.subTest(step=step):
                report = self.run_case(fault_at=step)
                self.assertFalse(report.passed)
                self.assertEqual(report.received, 3)
                self.assertEqual(report.responded, step)
                self.assertEqual(report.displayed, step-1)
                self.assertEqual(report.ordinals, tuple(range(1, step)))

    def test_invalid_fault_rejected(self):
        for fault in (True, 0, 4, '1'):
            with self.assertRaises(ValueError):
                self.run_case(fault_at=fault)

    def test_bad_canvas_fails_closed(self):
        report = self.run_case(canvas=InspectableCanvas())
        self.assertTrue(report.passed)
        with self.assertRaises(ValueError):
            self.run_case(canvas=object())

    def test_canvas_text_tampering_detected(self):
        class LieCanvas(InspectableCanvas):
            def itemcget(self, item, name):
                return 'incorrect text' if name == 'text' else ''
        report = self.run_case(canvas=LieCanvas())
        self.assertFalse(report.passed)
        self.assertIn('표시 불일치', report.describe())

    def test_canvas_drawing_failure_never_passes(self):
        class CrashCanvas(InspectableCanvas):
            def create_text(self, *args, **kwargs):
                if 'aisting_scene_voice' in kwargs.get('tags', ()):
                    raise RuntimeError('simulated Tk canvas draw failure')
                return super().create_text(*args, **kwargs)
        result = self.run_case(canvas=CrashCanvas())
        self.assertFalse(result.passed)
        self.assertEqual(result.displayed, 0)

    def test_reply_generation_failure_never_passes(self):
        with patch('ai_broadcaster.offline_chat_voice_screen_integration.OfflineChatReactions.reply_next',
                   side_effect=ValueError('mock reply failed')):
            report = self.run_case()
        self.assertFalse(report.passed)
        self.assertEqual(report.responded, 0)

    def test_corrupted_canvas_tag_detected(self):
        class LoseWatermark(InspectableCanvas):
            def find_withtag(self, tag):
                return () if tag == 'aisting_scene_watermark' else super().find_withtag(tag)
        report = self.run_case(canvas=LoseWatermark())
        self.assertFalse(report.passed)
        self.assertEqual(report.responded, 0)

    def test_does_not_use_external_resources(self):
        with patch('builtins.open', side_effect=AssertionError('disk')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')):
            self.assertTrue(self.run_case().passed)

    def test_synthetic_run_is_repeatable(self):
        first = self.run_case()
        second = self.run_case()
        self.assertEqual(first, second)

    def test_immutable_report_and_approval_pending(self):
        report = self.run_case()
        with self.assertRaises(FrozenInstanceError):
            report.passed = False
        for word in ('Windows 실기기', 'OBS', '미검증', '사용자 최종 승인'):
            self.assertIn(word, report.describe())


if __name__ == '__main__':
    unittest.main()
