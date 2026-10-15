"""Original 087 GUI smoke on Linux Xvfb; never a Naver account/API test."""
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
    directory = Path(temporary)
    settings_file = directory / 'settings.json'
    sentinel = directory / 'marker.txt'
    sentinel.write_text('PRESERVE', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings_file)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, settings_file)), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('process forbidden')), \
         patch('sqlite3.connect', side_effect=AssertionError('database forbidden')):
        app = AistingApp()
        try:
            app.update()
            assert '네이버 카페 공식 연동 검토' in app._tab_nav_widget.cget('values')
            app._tab_nav.set('네이버 카페 공식 연동 검토')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._cafe_review_inspect()
            assert '거부' in app._cafe_review_status.get()
            assert not app._cafe_review_text.get('1.0', 'end').strip()
            app._notice_when.set('2026-10-14 19:30')
            app._notice_topic.set('로컬 수다')
            app._notice_make()
            app._cafe_review_inspect()
            result = json.loads(app._cafe_review_text.get('1.0', 'end'))
            assert result['provider'] == 'naver_cafe'
            assert result['official_api_capability'] == 'unverified'
            assert result['api_payload_ready'] is False
            assert result['published'] is False
            assert result['cafe_target'] is None
            assert '로컬 수다' in result['body_preview']
            assert '미확인' in app._cafe_review_status.get()
            # State changes force another draft, never quietly reuse an old one.
            app.settings['content'] = 'game'
            app._cafe_review_inspect()
            assert '거부' in app._cafe_review_status.get()
            assert not app._cafe_review_text.get('1.0', 'end').strip()
            app.settings['content'] = 'undecided'
            app._notice_make()
            app._cafe_review_inspect()
            assert '미확인' in app._cafe_review_status.get()
            app._notice_topic.set('수정 후 재검토')
            assert '무효' in app._cafe_review_status.get()
            assert not app._cafe_review_text.get('1.0', 'end').strip()
            assert not settings_file.exists()
            assert sentinel.read_text(encoding='utf-8') == 'PRESERVE'
        finally:
            app.destroy()
print('GUI stage 087 PASS — offline review only; no Naver authentication or publishing')
