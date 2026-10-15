"""081: actual Tk local-only schedule draft CRUD. Uses disposable temp settings/files."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings
from ai_broadcaster.offline_broadcast_schedule import schedule_path

with tempfile.TemporaryDirectory() as scratch:
    local = Path(scratch)
    settings = local / 'settings.json'
    sentinel = local / 'keep.txt'
    sentinel.write_text('ORIGINAL', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda x: save_settings(x, settings)), \
         patch('ai_broadcaster.desktop.schedule_path', side_effect=lambda: schedule_path(local)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('subprocess.Popen', side_effect=AssertionError('external program')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')), \
         patch('time.sleep', side_effect=AssertionError('delay')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('방송 시작 일정 초안')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '방송 시작 일정 초안'
            assert len(app._schedule_draft.slots) == 0
            app._schedule_add()
            assert len(app._schedule_draft.slots) == 1
            app._schedule_add()
            assert len(app._schedule_draft.slots) == 1 and '거부' in app._schedule_status.get()
            app._schedule_reference.set('2026-10-14 09:00')
            app._schedule_preview()
            assert '2026-10-19 19:30 KST' in app._schedule_next.get()
            app._schedule_start_time.set('25:30')
            app._schedule_add()
            assert len(app._schedule_draft.slots) == 1 and '거부' in app._schedule_status.get()
            app._schedule_save()
            saved = schedule_path(local)
            assert saved.exists()
            app._schedule_list.selection_set(0)
            app._schedule_remove()
            assert len(app._schedule_draft.slots) == 0
            app._schedule_load()
            assert len(app._schedule_draft.slots) == 1
            app._schedule_delete()
            assert not saved.exists() and len(app._schedule_draft.slots) == 1
            app._schedule_reference.set('invalid')
            app._schedule_preview()
            assert '거부' in app._schedule_status.get()
            assert not settings.exists()
            assert sentinel.read_text(encoding='utf-8') == 'ORIGINAL'
            assert not app.settings['scheduled_execution']
            assert not app.settings['streaming_enabled']
            print('Stage 081 GUI schedule add/remove/save/load/manual preview/no auto-start/no network PASS')
        finally:
            app.destroy()
