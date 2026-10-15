"""089 real Tkinter virtual display, no external access or implicit storage."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    settings_file = root / 'settings.json'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings_file)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, settings_file)), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
        app = AistingApp()
        try:
            app.update()
            assert '방송 종료 공지·결과 기록' in app._tab_nav_widget.cget('values')
            app._tab_nav.set('방송 종료 공지·결과 기록')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._end_notice_start.set('2026-10-14 19:30')
            app._end_notice_make()
            assert '거부' in app._end_notice_status.get()
            app._broadcast_scene_preview()
            app._duration_elapsed.set('180')
            app._broadcast_duration_check()
            app._broadcast_closing_prepare()
            app._broadcast_closing_advance()
            app._end_notice_make()
            assert '거부' in app._end_notice_status.get()
            app._broadcast_closing_advance()
            app._end_notice_note.set('가상 종료 확인')
            app._end_notice_make()
            assert app._end_notice_result is not None, app._end_notice_status.get()
            assert '가상 종료' in app._end_notice_text.get('1.0', 'end')
            filename = root / 'result.json'
            with patch('tkinter.filedialog.asksaveasfilename', return_value=str(filename)):
                app._end_notice_export()
            result = json.loads(filename.read_text(encoding='utf-8'))
            assert result['actual_broadcast_verified'] is False
            assert result['published'] is False
            assert result['virtual_end_confirmed'] is True
            with patch('tkinter.filedialog.asksaveasfilename', return_value=str(filename)):
                app._end_notice_export()
            assert '실패' in app._end_notice_status.get()
            app._end_notice_note.set('변경')
            assert app._end_notice_result is None
            app._end_notice_export()
            assert '먼저' in app._end_notice_status.get()
            assert not settings_file.exists()
        finally:
            app.destroy()
print('GUI stage 089 PASS - virtual ending, explicit JSON export, safe invalidation')
