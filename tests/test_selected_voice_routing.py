"""Original roadmap 046: voice selection reaches virtual synthesis, without OS access."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ai_broadcaster.offline_tts import KoreanVoice
from ai_broadcaster.selected_voice_routing import rehearse_selected_voice

A = KoreanVoice('한국어 A')
B = KoreanVoice('한국어 B')
PROFILE = {'installed_voice_name': '한국어 B', 'rate': -2, 'volume': 67}


class TestSelectedVoiceRouting(unittest.TestCase):
    def run_route(self, text='안녕하세요', **updates):
        args = dict(source='windows_system', selected_name=B.name,
                    available_voices=[A, B], profile=PROFILE)
        args.update(updates)
        return rehearse_selected_voice(text, **args)

    def test_exact_selection_rate_volume_delivered(self):
        calls = []
        report = self.run_route('안녕', virtual_speak=lambda *items: calls.append(items) or True)
        self.assertEqual(calls, [('안녕', B, -2, 67, 1)])
        self.assertEqual(report.voice_name, B.name)
        self.assertEqual(report.state, 'simulated_complete')

    def test_different_choice_not_first_voice(self):
        self.assertEqual(self.run_route(available_voices=[A, B]).voice_name, B.name)
        self.assertEqual(self.run_route(available_voices=[B, A]).voice_name, B.name)

    def test_preserves_unicode_content(self):
        text = '안녕 🤗 한국어 목소리 테스트 ㅋㅋㅋ'
        self.assertEqual(''.join(self.run_route(text).segments), text)

    def test_long_content_fifo_and_duplicate_chunks(self):
        text = '안녕' * 650
        seen = []
        report = self.run_route(text, virtual_speak=lambda part, voice, rate, vol, i: seen.append((i, part, voice, rate, vol)) or True)
        self.assertEqual(''.join(report.delivered), text)
        self.assertEqual(tuple(x[0] for x in seen), tuple(range(1, len(seen)+1)))
        self.assertGreater(len(seen), 1)
        self.assertTrue(all(x[2:] == (B, -2, 67) for x in seen))

    def test_reject_other_sources(self):
        for source in ('undecided', 'own_recording', 'licensed_recording', 'consented_recording', 'cloud'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.run_route(source=source)

    def test_reject_unlisted_voice_no_fallback(self):
        with self.assertRaisesRegex(ValueError, '자동 대체'):
            self.run_route(available_voices=[A])

    def test_reject_empty_choice(self):
        for choice in ('', None):
            with self.subTest(choice=choice), self.assertRaises(ValueError):
                self.run_route(selected_name=choice)

    def test_reject_source_profile_disagreement(self):
        with self.assertRaisesRegex(ValueError, '자동 대체'):
            self.run_route(profile={'installed_voice_name': A.name, 'rate': -2, 'volume': 67})

    def test_reject_duplicate_voice_names(self):
        with self.assertRaises(ValueError):
            self.run_route(available_voices=[A, B, KoreanVoice(B.name)])

    def test_reject_malformed_voice_list(self):
        with self.assertRaises((ValueError, TypeError)):
            self.run_route(available_voices=[B, 'wrong'])

    def test_reject_bad_settings(self):
        for update in ({'rate': True}, {'volume': 101}, {'rate': 5}):
            profile = dict(PROFILE, **update)
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                self.run_route(profile=profile)

    def test_reject_blank_and_long_text(self):
        for text in ('', ' \n ', '가' * 6001):
            with self.subTest(size=len(text)), self.assertRaises(ValueError):
                self.run_route(text)

    def test_virtual_interrupt_does_not_drop_remainder(self):
        seen = []
        text = '가' * 1350
        def stop(part, voice, rate, volume, i):
            seen.append(i)
            return i != 2
        report = self.run_route(text, virtual_speak=stop)
        self.assertEqual(report.state, 'simulated_interrupted')
        self.assertEqual(seen, [1, 2])
        self.assertEqual(''.join(report.delivered + report.pending), text)
        self.assertEqual(len(report.pending), 2)

    def test_virtual_error_does_not_leak_details(self):
        def fault(_part, _voice, _rate, _volume, i):
            if i == 2:
                raise RuntimeError('private\nC:\\secret\\token')
            return True
        report = self.run_route('가' * 1400, virtual_speak=fault)
        self.assertEqual(report.state, 'simulated_error')
        self.assertEqual(''.join(report.delivered + report.pending), '가' * 1400)
        self.assertNotIn('secret', report.describe())
        self.assertEqual(len(report.delivered), 1)

    def test_reject_nonboolean_backend_response(self):
        report = self.run_route(virtual_speak=lambda *_items: 1)
        self.assertEqual(report.state, 'simulated_error')
        self.assertEqual(report.pending, report.segments)

    def test_no_automatic_retry(self):
        calls = []
        def faulty(*items):
            calls.append(items)
            return False
        report = self.run_route('가' * 1500, virtual_speak=faulty)
        self.assertEqual(len(calls), 1)
        self.assertEqual(report.pending, report.segments)

    def test_no_pc_enumeration_write_network_audio(self):
        with patch('subprocess.Popen', side_effect=AssertionError('started process')), \
             patch('subprocess.run', side_effect=AssertionError('PC queried')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('pathlib.Path.write_text', side_effect=AssertionError('write')):
            report = self.run_route()
        self.assertEqual(report.state, 'simulated_complete')
        self.assertIn('실제 출력 없음', report.describe())

    def test_voice_name_not_implicitly_saved(self):
        report = self.run_route()
        self.assertEqual(PROFILE['installed_voice_name'], B.name)
        self.assertEqual(report.source, 'windows_system')


if __name__ == '__main__':
    unittest.main()
