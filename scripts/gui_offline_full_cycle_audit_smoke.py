"""083: isolated actual Tkinter GUI exercise, NEVER runs a real broadcast."""
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
    root = Path(scratch)
    settings_file = root / 'settings.json'
    marker = root / 'sentinel.txt'
    marker.write_text('DO NOT CHANGE', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings_file)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda x: save_settings(x, settings_file)), \
         patch('ai_broadcaster.desktop.schedule_path', side_effect=lambda: schedule_path(root)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')), \
         patch('time.sleep', side_effect=AssertionError('delay')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('방송 시작 일정 초안')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._schedule_reference.set('2026-10-14 19:30')
            app._full_cycle_audit_run()
            assert '미통과' in app._full_cycle_status.get(), app._full_cycle_status.get()
            app._schedule_weekday.set('수')
            app._schedule_add()
            app._full_cycle_audit_run()
            assert '14/14' in app._full_cycle_status.get(), app._full_cycle_status.get()
            assert '통과' in app._full_cycle_status.get()
            assert not app._start_control.active  # isolation from stage 082 UI
            app._schedule_reference.set('2026-10-14 19:31')
            assert '이전 감사 무효' in app._full_cycle_status.get()
            app._full_cycle_audit_run()
            assert '미통과' in app._full_cycle_status.get()
            app._schedule_reference.set('bad')
            app._full_cycle_audit_run()
            assert '미통과' in app._full_cycle_status.get()
            assert marker.read_text(encoding='utf-8') == 'DO NOT CHANGE'
            assert not settings_file.exists()
            assert not schedule_path(root).exists()
            app.update()
        finally:
            app.destroy()
print('GUI 083 PASS — independent virtual start-to-end audit only; no actual streaming')
