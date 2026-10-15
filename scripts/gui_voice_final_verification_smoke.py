"""Stage 050 UI smoke: no real audio, OS enumeration, network or file changes."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as folder:
    settings = Path(folder) / 'settings.json'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda obj: save_settings(obj, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('SQLite')), \
         patch('subprocess.Popen', side_effect=AssertionError('audio')), \
         patch('subprocess.run', side_effect=AssertionError('PC lookup')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('목소리 통합 최종 점검')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '목소리 통합 최종 점검'
            assert '미실행' in app._voice_final_status.get()
            app._run_voice_final_verification()  # undecided voice source must be denied
            assert '오류' in app._voice_final_status.get()
            app._voice.set('Windows 무료 음성')
            app._run_voice_final_verification()
            assert '통과' in app._voice_final_status.get()
            output = app._voice_final_result.get('1.0', 'end')
            assert output.count('PASS · ') == 8
            assert '실제 목소리 최종 승인: 미완료' in output
            assert '사용자/실기기 확인 대기:' in output
            app._voice_final_script.insert('end', '\n한분: 추가 채팅')
            app.update()
            assert '무효' in app._voice_final_status.get()
            assert not app._voice_final_result.get('1.0', 'end').strip()
            app._run_voice_final_verification()
            assert '모의 채팅 4건' in app._voice_final_result.get('1.0', 'end')
            app._voice_final_name.set('')
            app._run_voice_final_verification()
            assert '오류' in app._voice_final_status.get()
            app._voice_final_name.set('모의 한국어 음성')
            app._voice_volume.set('101')
            app._run_voice_final_verification()
            assert '오류' in app._voice_final_status.get()
            assert not settings.exists()
            print('GUI stage 050 PASS: virtual voice final checklist, invalidation, safety gates')
        finally:
            app._shutdown()
