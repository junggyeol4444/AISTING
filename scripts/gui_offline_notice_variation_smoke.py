"""Stage 088 Linux virtual-display GUI validation (no posting, network, local changes)."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as temp:
    directory = Path(temp)
    settings_file = directory / 'settings.json'
    sentinel = directory / 'sentinel.txt'
    sentinel.write_text('KEEP', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings_file)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, settings_file)), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('process forbidden')), \
         patch('sqlite3.connect', side_effect=AssertionError('database forbidden')):
        app = AistingApp()
        try:
            app.update()
            assert '공지 문구 변주 (오프라인)' in app._tab_nav_widget.cget('values')
            app._tab_nav.set('공지 문구 변주 (오프라인)')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._notice_variation_make()
            assert '거부' in app._notice_variation_status.get()
            app._notice_when.set('2026-10-14 19:30')
            app._notice_topic.set('수다')
            app._notice_make()
            base = app._notice_draft
            app._notice_variation_style.set('활기')
            app._notice_variation_length.set('자세히')
            app._notice_variation_number.set('2')
            app._notice_variation_emoji.set(True)
            app._notice_variation_context.set('어제 이야기 이어서')
            app._notice_variation_lead.set('30')
            app._notice_variation_make()
            text = app._notice_variation_text.get('1.0', 'end')
            assert '어제 이야기 이어서' in text and '✨' in text
            assert '2026-10-14 19:00 KST' in text and '예약 아님' in text
            assert '게시/예약 없음' not in text
            assert '규칙 기반' in app._notice_variation_status.get()
            assert app._notice_draft == base
            app._notice_variation_context.set('변경된 내용')
            assert '무효' in app._notice_variation_status.get()
            assert not app._notice_variation_text.get('1.0', 'end').strip()
            app._notice_variation_make()
            assert '변경된 내용' in app._notice_variation_text.get('1.0', 'end')
            app._notice_when.set('2026-10-15 19:30')
            assert not app._notice_variation_text.get('1.0', 'end').strip()
            app._notice_variation_make()
            assert '거부' in app._notice_variation_status.get()
            app._notice_make()
            app._notice_variation_context.set('@everyone')
            app._notice_variation_make()
            assert '거부' in app._notice_variation_status.get()
            app._notice_variation_context.set('')
            app._notice_variation_lead.set('50')
            app._notice_variation_make()
            assert '거부' in app._notice_variation_status.get()
            assert sentinel.read_text(encoding='utf-8') == 'KEEP'
            assert not settings_file.exists()
        finally:
            app.destroy()
print('GUI stage 088 PASS — operator-only deterministic variation, no external access')
