"""Stage 050 tests: virtual voice integration cannot grant real approval."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.voice_final_verification import verify_voice_chain, PENDING_REAL_CHECKS

PROFILE = {'installed_voice_name': '가상 한국어', 'rate': -2, 'volume': 75}
SCRIPT = '유저: 안녕\n유저: 안녕\n다른분: 즐거운 하루'

class TestVoiceFinalVerification(unittest.TestCase):
    def run_report(self, script=SCRIPT, **kw):
        args = dict(source='windows_system', selected_name='가상 한국어', profile=PROFILE)
        args.update(kw)
        return verify_voice_chain(script, **args)

    def test_all_offline_checks_pass(self):
        result = self.run_report()
        self.assertEqual(len(result.checks), 8)
        self.assertTrue(result.offline_pass)

    def test_repeated_message_preserved(self):
        result = self.run_report('중복: 안녕\n중복: 안녕')
        self.assertTrue(result.offline_pass)
        self.assertEqual(result.chat_count, 2)

    def test_batch_maximum_thirty(self):
        report = self.run_report('\n'.join(f'시청자{i}: 한글 {i}' for i in range(30)))
        self.assertTrue(report.offline_pass)
        self.assertEqual(report.chat_count, 30)

    def test_one_chat_rejected(self):
        with self.assertRaises(ValueError):
            self.run_report('나: 안녕')

    def test_31_chats_rejected(self):
        with self.assertRaises(ValueError):
            self.run_report('\n'.join('나: 안녕' for _ in range(31)))

    def test_invalid_script_rejected(self):
        for script in ('', 'bad text', '누구:', '누구: 안녕\nbad'):
            with self.subTest(script=script), self.assertRaises(ValueError):
                self.run_report(script)

    def test_non_windows_sources_rejected(self):
        for source in ('undecided', 'own_recording', 'consented_recording', 'licensed_recording'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.run_report(source=source)

    def test_voice_selection_mismatch_fails_without_fallback(self):
        with self.assertRaises(ValueError):
            self.run_report(profile=dict(PROFILE, installed_voice_name='다른 음성'))

    def test_invalid_rates_and_volume_rejected(self):
        for profile in (dict(PROFILE, rate=11), dict(PROFILE, volume=105), dict(PROFILE, rate=True)):
            with self.subTest(profile=profile), self.assertRaises((ValueError, TypeError)):
                self.run_report(profile=profile)

    def test_empty_name_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            self.run_report(selected_name='')

    def test_pending_real_checks_always_present(self):
        report = self.run_report()
        self.assertEqual(report.pending, PENDING_REAL_CHECKS)
        self.assertGreaterEqual(len(report.pending), 5)

    def test_real_approval_never_inferred(self):
        result = self.run_report()
        self.assertFalse(result.real_voice_approved)
        self.assertIn('미완료', result.describe())

    def test_normal_and_interruption_paths_report(self):
        text = self.run_report().describe()
        self.assertIn('가상 중단', text)
        self.assertIn('가상 오류', text)
        self.assertIn('실제 음성 재생 없음', text)

    def test_no_auto_file_write_or_pc_or_network_access(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('db')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('subprocess.run', side_effect=AssertionError('os')), \
             patch('pathlib.Path.write_text', side_effect=AssertionError('file write')):
            self.assertTrue(self.run_report().offline_pass)

    def test_only_accepted_voice_profile_returns_correct_identifier(self):
        report = self.run_report(profile={'installed_voice_name': '가상 한국어', 'rate': 4, 'volume': 100})
        self.assertEqual(report.voice_name, '가상 한국어')
        self.assertTrue(report.offline_pass)

    def test_offline_failure_cannot_be_silent(self):
        from ai_broadcaster.voice_final_verification import VoiceFinalReport
        r = VoiceFinalReport('가상', 2, (('실패', False),))
        self.assertFalse(r.offline_pass)
        self.assertFalse(r.real_voice_approved)
        self.assertIn('FAIL', r.describe())

if __name__ == '__main__':
    unittest.main()
