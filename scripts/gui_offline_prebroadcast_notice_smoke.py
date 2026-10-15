"""Stage 084 isolated Tk preview. Must not send, persist, or launch anything."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    settings_file = root / 'settings.json'
    marker = root / 'sentinel.txt'
    marker.write_text('KEEP', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings_file)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda x: save_settings(x, settings_file)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('subprocess.Popen', side_effect=AssertionError('external process')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('방송 전 공지 초안')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._notice_make()
            assert '거부' in app._notice_status.get()
            app._notice_when.set('2026-10-14 19:30')
            app._notice_topic.set('오늘의 수다')
            app._notice_make()
            text = app._notice_text.get('1.0', 'end')
            assert '아이스팅' in text and '오늘의 수다' in text and '2026-10-14 19:30' in text
            assert '미게시' in app._notice_status.get()
            app._notice_topic.set('변경됨')
            assert '이전 초안 무효' in app._notice_status.get()
            assert not app._notice_text.get('1.0', 'end').strip()
            app._notice_make()
            assert '변경됨' in app._notice_text.get('1.0', 'end')
            app._notice_topic.set('@everyone')
            app._notice_make()
            assert '거부' in app._notice_status.get()
            assert not app._notice_text.get('1.0', 'end').strip()
            assert marker.read_text(encoding='utf-8') == 'KEEP'
            assert not settings_file.exists()
        finally:
            app.destroy()
print('GUI stage 084 PASS — review-only local notice preview; no external publishing')
