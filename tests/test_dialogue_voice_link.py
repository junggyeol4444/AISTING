"""Roadmap 049: mock dialogue -> virtual speech handoff, never real audio/OS."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ai_broadcaster.dialogue_voice_link import DialogueVoiceLink
from ai_broadcaster.offline_tts import KoreanVoice

V = KoreanVoice('가상 한국어')
PROFILE = {'installed_voice_name': V.name, 'rate': -1, 'volume': 75}
SCRIPT = '같은이: 안녕하세요\n같은이: 안녕하세요\n다른이: 좋은 하루'


class TestDialogueVoiceLink(unittest.TestCase):
    def session(self, script=SCRIPT, **kw):
        options = dict(source='windows_system', selected_name=V.name,
                       available_voices=[V], profile=PROFILE)
        options.update(kw)
        return DialogueVoiceLink(script, **options)

    def test_constructor_is_inert_and_no_auto_process(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('audio')), \
             patch('sqlite3.connect', side_effect=AssertionError('memory')):
            runner = self.session()
            self.assertEqual(runner.status().state, 'ready')
            self.assertEqual(len(runner.status().pending), 3)
            self.assertEqual(runner.status().completed, ())

    def test_every_chat_fifo_even_duplicates(self):
        called = []
        runner = self.session(virtual_speak=lambda t, v, r, vol, i: called.append((t, v, r, vol, i)) or True)
        for i in range(3):
            state = runner.step()
            self.assertEqual(len(state.completed), i + 1)
        self.assertEqual([a.original.sender for a in state.completed], ['같은이', '같은이', '다른이'])
        self.assertEqual([a.original.text for a in state.completed], ['안녕하세요', '안녕하세요', '좋은 하루'])
        self.assertEqual(len(called), 3)
        self.assertTrue(all(c[1:] == (V, -1, 75, 1) for c in called))
        self.assertEqual(state.pending, ())

    def test_manual_batch_processes_all_with_no_auto_delay(self):
        state = self.session().run_manual_batch()
        self.assertEqual(len(state.completed), 3)
        self.assertEqual(state.accepted, 3)
        self.assertEqual(state.pending, ())
        self.assertEqual(state.state, 'simulated_complete')

    def test_failed_head_keeps_all_and_not_committed(self):
        calls = []
        def stop(t, v, r, vol, i):
            calls.append(t)
            return False
        runner = self.session(virtual_speak=stop)
        result = runner.run_manual_batch()
        self.assertEqual(result.state, 'simulated_interrupted')
        self.assertEqual(len(result.completed), 0)
        self.assertEqual(len(result.pending), 3)
        self.assertIsNotNone(result.current)
        self.assertEqual(result.delivered_segments, ())
        self.assertEqual(len(result.remaining_segments), 1)

    def test_exception_sanitized_and_pending_retained(self):
        def fail(*_):
            raise RuntimeError('/Users/private/secret')
        result = self.session(virtual_speak=fail).step()
        self.assertEqual(result.state, 'simulated_error')
        self.assertNotIn('secret', result.reason)
        self.assertEqual(len(result.pending), 3)

    def test_failure_resume_no_regeneration_and_no_repeat_of_delivered_segments(self):
        calls = []
        blocked = [True]
        def speak(text, voice, rate, volume, index):
            calls.append((text, index))
            if index == 2 and blocked[0]:
                blocked[0] = False
                return False
            return True
        runner = self.session('A: 안녕', virtual_speak=speak)
        class LongMock:
            def __init__(self):
                self.calls = 0
            def generate(self, chat, history):
                self.calls += 1
                return '가' * 800
        generator = LongMock()
        runner._generator = generator
        first = runner.step()
        self.assertEqual(first.state, 'simulated_interrupted')
        self.assertEqual(len(first.delivered_segments), 1)
        self.assertEqual(len(first.remaining_segments), 1)
        self.assertEqual(len(first.pending), 1)
        second = runner.step()
        self.assertEqual(second.state, 'simulated_complete')
        self.assertEqual(len(second.completed), 1)
        self.assertEqual(generator.calls, 1)
        self.assertEqual([x[1] for x in calls], [1, 2, 2])

    def test_partial_pending_state_exposes_full_text(self):
        runner = self.session('A: 안녕')
        class LongMock:
            def generate(self, *_):
                return '안' * 710
        runner._generator = LongMock()
        runner._speak = lambda *_: False
        state = runner.step()
        self.assertEqual(''.join(state.remaining_segments), '안' * 710)
        self.assertEqual(state.current.reply, '안' * 710)

    def test_reject_non_windows_source(self):
        for source in ('undecided', 'own_recording', 'licensed_recording', None):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.session(source=source)

    def test_reject_missing_or_mismatched_voice_no_fallback(self):
        for change in ({'available_voices': []}, {'selected_name': '다른 음성'},
                       {'profile': dict(PROFILE, installed_voice_name='다른 음성')}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.session(**change)

    def test_reject_bad_voice_settings(self):
        for profile in (dict(PROFILE, rate=True), dict(PROFILE, volume=101),
                        dict(PROFILE, installed_voice_name='')):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                self.session(profile=profile)

    def test_invalid_script_or_too_many_chats(self):
        for script in ('', 'wrong text', 'A:', '\n'.join('A: 말' for _ in range(31))):
            with self.subTest(script=script[:30]), self.assertRaises(ValueError):
                self.session(script)

    def test_no_extra_work_after_complete(self):
        runner = self.session('A: 안녕')
        result = runner.step()
        self.assertEqual(result, runner.step())

    def test_answer_text_is_mock_not_real_ai(self):
        result = self.session('수험생: 가나다라마바사').step()
        self.assertIn('모의 답변', result.completed[0].reply)
        self.assertIn('가나다라마바사', result.completed[0].reply)

    def test_status_is_immutable(self):
        runner = self.session()
        s = runner.status()
        runner.step()
        self.assertEqual(len(s.pending), 3)
        self.assertEqual(s.completed, ())

    def test_render_contains_explicit_limitations(self):
        txt = self.session().status().describe()
        self.assertIn('실제 음성 출력 없음', txt)
        self.assertIn('별도 사용자 검증 대기', txt)

    def test_new_session_does_not_touch_storage(self):
        with patch('pathlib.Path.write_text', side_effect=AssertionError('file')), \
             patch('sqlite3.connect', side_effect=AssertionError('memory')), \
             patch('subprocess.run', side_effect=AssertionError('OS')):
            runner = self.session()
            self.assertEqual(len(runner.run_manual_batch().completed), 3)


if __name__ == '__main__':
    unittest.main()
