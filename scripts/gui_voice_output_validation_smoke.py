"""Roadmap 045: manual Tk interaction on Linux virtual display, zero audio."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import VOICES, load_settings, save_settings

with tempfile.TemporaryDirectory() as temp:
    home = Path(temp)
    settings = home/'settings.json'
    memory = home/'conversation.sqlite3'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda s: save_settings(s, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('sqlite3.connect', side_effect=AssertionError('database forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('OS audio forbidden')):
        app = AistingApp()
        try:
            app.update()
            assert app._auto_read.get() is False
            app._tab_nav.set('한국어 음성 출력 모의 검증')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '한국어 음성 출력 모의 검증'
            assert not settings.exists() and not memory.exists()
            app._run_voice_output_validation()
            assert '입력 오류' in app._voice_output_status.get()  # default source undecided
            windows = next(k for k,v in VOICES.items() if v == 'windows_system')
            app._voice.set(windows)
            app._run_voice_output_validation()
            assert 'simulated_complete' in app._voice_output_status.get()
            assert '실제 음성 출력 없음' in app._voice_output_result.get('1.0','end')
            app._voice_output_text.delete('1.0','end')
            app._voice_output_text.insert('1.0','안녕'*370)
            app._voice_output_mode.set('2번째 구간 중단')
            app._run_voice_output_validation()
            assert 'simulated_interrupted' in app._voice_output_status.get()
            assert '미처리' in app._voice_output_result.get('1.0','end')
            app._voice_output_mode.set('2번째 구간 오류')
            app._run_voice_output_validation()
            assert 'simulated_error' in app._voice_output_status.get()
            app._voice_rate.set('1')
            assert '무효' in app._voice_output_status.get()
            assert not app._voice_output_result.get('1.0','end').strip()
            app._voice_output_mode.set('전부 전달')
            app._run_voice_output_validation()
            assert 'simulated_complete' in app._voice_output_status.get()
            app._voice_output_text.delete('1.0','end')
            app._run_voice_output_validation()
            assert '입력 오류' in app._voice_output_status.get()
            assert not settings.exists() and not memory.exists()
            # Regression: backend saying False is an interruption, never a success.
            from ai_broadcaster.offline_tts import KoreanVoice
            app._speaker.speak = lambda _part, _voice: False
            app._speech_worker(['안녕'], KoreanVoice('가상 음성'))
            event, _ = app._events.get_nowait()
            assert event == 'speech_stopped', event
            print('GUI original 045 Korean virtual output + interrupted worker: PASS')
        finally:
            app.destroy()
