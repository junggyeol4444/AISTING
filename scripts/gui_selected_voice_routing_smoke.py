"""Roadmap 046 offline GUI integration: no OS info, speaker, file or network."""
from pathlib import Path
from unittest.mock import patch
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_tts import KoreanVoice
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'settings.json'
    memory = Path(directory) / 'memory.sqlite3'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(path)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda state: save_settings(state, path)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('memory accessed')), \
         patch('subprocess.Popen', side_effect=AssertionError('audio accessed')), \
         patch('subprocess.run', side_effect=AssertionError('OS accessed')):
        app = AistingApp()
        try:
            app.update()
            assert app._auto_read.get() is False
            app._tab_nav.set('선택 목소리 적용 모의')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '선택 목소리 적용 모의'
            app._run_selected_voice_routing()
            assert '입력 오류' in app._route_status.get()
            assert not path.exists() and not memory.exists()
            app._voice.set('Windows 무료 음성')
            app._run_selected_voice_routing()
            assert '입력 오류' in app._route_status.get()
            app._voice_lookup_done('voices', [KoreanVoice('목소리 A'), KoreanVoice('목소리 B')])
            app._voice_name.set('목소리 B (ko-KR)')
            app._voice_rate.set('-2')
            app._voice_volume.set('67')
            app._run_selected_voice_routing()
            assert 'simulated_complete' in app._route_status.get()
            result = app._route_result.get('1.0', 'end')
            assert '목소리 B' in result and '속도: -2' in result and '음량: 67' in result
            assert '실제 출력 없음' in result
            app._route_text.delete('1.0', 'end')
            app._route_text.insert('1.0', '가' * 1400)
            app._route_mode.set('2번째 구간 중단')
            app._run_selected_voice_routing()
            assert 'simulated_interrupted' in app._route_status.get()
            assert '미처리' in app._route_result.get('1.0', 'end')
            app._route_mode.set('2번째 구간 오류')
            app._run_selected_voice_routing()
            assert 'simulated_error' in app._route_status.get()
            app._voice_name.set('목소리 A (ko-KR)')
            assert '무효' in app._route_status.get()
            assert not app._route_result.get('1.0', 'end').strip()
            app._run_selected_voice_routing()
            assert 'simulated_error' in app._route_status.get()
            app._voice.set('동의받은 목소리 (추후 확보)')
            # Even when a previously selected Windows voice remains cached,
            # the real manual playback path must not activate for a different source.
            assert str(app._speech_play.cget('state')) == 'disabled'
            app._start_speech('테스트')
            assert 'Windows 무료 음성' in app._speech_status.get()
            assert app._speech_busy is False
            app._run_selected_voice_routing()
            assert '입력 오류' in app._route_status.get()
            assert not path.exists() and not memory.exists()
            print('GUI 046 voice routing, selection, invalidation, stop, error, offline: PASS')
        finally:
            app.destroy()
