"""Stage 085 GUI smoke. Tk Xvfb only; DISCORD IS NEVER CONNECTED."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as temporary:
    path = Path(temporary)
    settings_file = path / 'settings.json'
    marker = path / 'sentinel.txt'
    marker.write_text('KEEP', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings_file)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda x: save_settings(x, settings_file)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')):
        app = AistingApp()
        try:
            app.update()
            assert '디스코드 공지 연결 모의' in app._tab_nav_widget.cget('values')
            app._tab_nav.set('디스코드 공지 연결 모의')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._discord_notice_inspect()
            assert '거부' in app._discord_notice_status.get()
            assert not app._discord_notice_text.get('1.0', 'end').strip()
            app._notice_when.set('2026-10-14 19:30')
            app._notice_topic.set('수다')
            app._notice_make()
            app._discord_notice_inspect()
            payload = json.loads(app._discord_notice_text.get('1.0', 'end'))
            assert payload['message']['allowed_mentions']['parse'] == []
            assert payload['message']['tts'] is False
            assert payload['destination'] is None
            assert payload['send_ready'] is False
            assert '수다' in payload['message']['content']
            assert '미게시' in app._discord_notice_status.get()
            # Even a direct settings change must invalidate on next inspection.
            app.settings['content'] = 'game'
            app._discord_notice_inspect()
            assert '거부' in app._discord_notice_status.get()
            assert not app._discord_notice_text.get('1.0', 'end').strip()
            app.settings['content'] = 'undecided'
            app._notice_make()
            app._discord_notice_inspect()
            assert '미게시' in app._discord_notice_status.get()
            app._notice_topic.set('변경')
            assert '무효' in app._discord_notice_status.get()
            assert not app._discord_notice_text.get('1.0', 'end').strip()
            app._discord_notice_inspect()
            assert '거부' in app._discord_notice_status.get()
            assert marker.read_text(encoding='utf-8') == 'KEEP'
            assert not settings_file.exists()
        finally:
            app.destroy()
print('GUI stage 085 PASS — local Discord-shape preview only; no login/delivery')
