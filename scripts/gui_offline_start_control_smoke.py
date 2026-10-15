"""082 GUI: manually inspect, mock start, finish, reject replay. No real stream."""
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
    temp = Path(scratch)
    sentinel = temp / 'unchanged.txt'
    sentinel.write_text('ORIGINAL', encoding='utf-8')
    settings = temp / 'settings.json'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda x: save_settings(x, settings)), \
         patch('ai_broadcaster.desktop.schedule_path', side_effect=lambda: schedule_path(temp)), \
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
            app._start_control_inspect()
            assert 'not_due' in app._start_control_status.get()
            app._schedule_weekday.set('수')
            app._schedule_add()
            assert len(app._schedule_draft.slots) == 1
            app._start_control_inspect()
            assert 'mock_ready' in app._start_control_status.get()
            app._start_control_simulate()
            assert 'mock_started' in app._start_control_status.get()
            assert app._start_control.active
            app._start_control_simulate()
            assert 'mock_active' in app._start_control_status.get()
            app._start_control_finish()
            assert 'mock_finished' in app._start_control_status.get()
            app._start_control_simulate()
            assert 'duplicate' in app._start_control_status.get()
            app._schedule_reference.set('2026-10-14 19:29')
            assert '입력 변경' in app._start_control_status.get()
            app._start_control_inspect()
            assert 'not_due' in app._start_control_status.get()
            app._schedule_reference.set('bad time')
            app._start_control_simulate()
            assert '거부' in app._start_control_status.get()
            assert not settings.exists()
            assert not schedule_path(temp).exists()
            assert sentinel.read_text(encoding='utf-8') == 'ORIGINAL'
            assert not app.settings['scheduled_execution']
            assert not app.settings['streaming_enabled']
            print('082 local-only GUI: due/dedup/manual mock/invalid input/no network PASS')
        finally:
            app.destroy()
