"""Roadmap 045: no real voice enumeration or audio; virtual output-path checks."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.voice_output_validation import rehearse_korean_output

PROFILE = {'installed_voice_name': '', 'rate': 0, 'volume': 85}


class TestVoiceOutputRehearsal(unittest.TestCase):
    def rehearse(self, text='안녕하세요', **kwargs):
        return rehearse_korean_output(text, source='windows_system', profile=PROFILE, **kwargs)

    def test_short_sentence(self):
        report = self.rehearse()
        self.assertEqual(report.segments, ('안녕하세요',))
        self.assertEqual(report.completed, report.segments)
        self.assertFalse(report.remaining)
        self.assertEqual(report.state, 'simulated_complete')

    def test_unicode_preserved(self):
        text = '안녕 👋 오늘도 기분 좋아요! ㅋㅋㅋ\n정말이야?'
        self.assertEqual(''.join(self.rehearse(text).segments), text)

    def test_split_long_full_text_preserved(self):
        text = '안녕 ' * 800
        report = self.rehearse(text)
        self.assertGreater(len(report.segments), 1)
        self.assertTrue(all(1 <= len(x) <= 600 for x in report.segments))
        self.assertEqual(''.join(report.completed), text.strip())

    def test_fifo_and_duplicate_segments(self):
        report = self.rehearse('안녕안녕안녕안녕', max_chunk=2)
        self.assertEqual(report.completed, ('안녕', '안녕', '안녕', '안녕'))

    def test_virtual_backend_invoked_in_order(self):
        visited = []
        report = self.rehearse('가나다라마바사', max_chunk=2,
                               virtual_play=lambda s, i: (visited.append((s, i)) or True))
        self.assertEqual(visited, [('가나', 1), ('다라', 2), ('마바', 3), ('사', 4)])
        self.assertEqual(report.completed, report.segments)

    def test_stop_keeps_failed_and_unprocessed(self):
        visited = []
        def backend(part, idx):
            visited.append(idx)
            return idx != 2
        report = self.rehearse('가나다라마바사', max_chunk=2, virtual_play=backend)
        self.assertEqual(visited, [1, 2])
        self.assertEqual(report.state, 'simulated_interrupted')
        self.assertEqual(report.completed, ('가나',))
        self.assertEqual(report.remaining, ('다라', '마바', '사'))

    def test_error_keeps_failed_and_unprocessed(self):
        def backend(_part, idx):
            if idx == 2:
                raise RuntimeError('private-path')
            return True
        report = self.rehearse('가나다라마바사', max_chunk=2, virtual_play=backend)
        self.assertEqual(report.state, 'simulated_error')
        self.assertEqual(report.completed, ('가나',))
        self.assertEqual(''.join(report.remaining), '다라마바사')
        self.assertNotIn('private-path', report.describe())

    def test_bad_virtual_result_is_error(self):
        report = self.rehearse('안녕', virtual_play=lambda _s, _i: 'OK')
        self.assertEqual(report.state, 'simulated_error')
        self.assertEqual(report.completed, ())

    def test_stop_first_segment(self):
        report = self.rehearse('안녕', virtual_play=lambda _s, _i: False)
        self.assertEqual(report.remaining, ('안녕',))
        self.assertEqual(report.completed, ())

    def test_reject_non_windows_source(self):
        for source in ('undecided', 'own_recording', 'licensed_recording', 'consented_recording', 'cloud'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                rehearse_korean_output('안녕', source=source, profile=PROFILE)

    def test_reject_empty_and_whitespace(self):
        for text in ('', ' ', '\n\t'):
            with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                self.rehearse(text)

    def test_reject_long_text(self):
        with self.assertRaises(ValueError):
            self.rehearse('가' * 6001)

    def test_reject_bad_chunk_sizes(self):
        for n in (0, 601, 1.0, True, -2):
            with self.subTest(n=n), self.assertRaises(ValueError):
                self.rehearse('안녕', max_chunk=n)

    def test_reject_invalid_voice_profile(self):
        for bad in ({}, {'installed_voice_name': '', 'rate': 5, 'volume': 85},
                    {'installed_voice_name': '', 'rate': 0, 'volume': 120}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                rehearse_korean_output('안녕', source='windows_system', profile=bad)

    def test_does_not_query_windows_or_network_or_write_data(self):
        with patch('subprocess.Popen', side_effect=AssertionError('process started')), \
             patch('subprocess.run', side_effect=AssertionError('process run')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('pathlib.Path.write_text', side_effect=AssertionError('file')):
            report = self.rehearse('안녕')
        self.assertEqual(report.state, 'simulated_complete')

    def test_report_discloses_simulation(self):
        description = self.rehearse('안녕').describe()
        self.assertIn('실제 음성 출력 없음', description)
        self.assertIn('운영자 수동 검증 대기', description)

    def test_no_automatic_retry_after_error(self):
        calls = []
        def error(part, idx):
            calls.append(idx)
            raise OSError('device')
        report = self.rehearse('가나다라', max_chunk=2, virtual_play=error)
        self.assertEqual(calls, [1])
        self.assertEqual(len(report.remaining), 2)


if __name__ == '__main__':
    unittest.main()
