"""Actual Tk on Linux virtual display; synthetic elapsed time only."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as temp:
    settings = Path(temp) / 'settings.json'
    marker = Path(temp) / 'operator_data.txt'
    marker.write_text('PRESERVE', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda x: save_settings(x, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('no network')), \
         patch('subprocess.Popen', side_effect=AssertionError('no subprocess')), \
         patch('sqlite3.connect', side_effect=AssertionError('no DB')), \
         patch('time.sleep', side_effect=AssertionError('no timers')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('방송 화면 구성 미리보기')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert (app._duration_minimum.get(), app._duration_maximum.get()) == ('60', '180')
            app._duration_elapsed.set('59')
            app._broadcast_duration_check()
            assert not app._duration_report.minimum_satisfied
            app._duration_elapsed.set('60')
            assert app._duration_report is None
            app._broadcast_duration_check()
            assert app._duration_report.minimum_satisfied
            assert not app._duration_report.maximum_reached
            app._duration_elapsed.set('180')
            app._broadcast_duration_check()
            assert app._duration_report.maximum_reached
            assert '실제 종료하지 않음' in app._duration_status.get()
            app._duration_minimum.set('200')
            app._broadcast_duration_check()
            assert app._duration_report is None
            assert '실패' in app._duration_status.get()
            app._duration_minimum.set('30')
            app._duration_maximum.set('60')
            app._duration_elapsed.set('60')
            app._broadcast_duration_check()
            assert app._duration_report.maximum_reached
            app._avatar.set('3D')
            assert app._duration_report is None
            assert '무효' in app._duration_status.get()
            assert app._duration_minimum.get() == '30'
            assert app._duration_maximum.get() == '60'
            app._broadcast_duration_check()
            assert app._duration_report.maximum_reached
            app._duration_elapsed.set('1.5')
            app._broadcast_duration_check()
            assert app._duration_report is None
            assert not settings.exists() and marker.read_text(encoding='utf-8') == 'PRESERVE'
            print('Stage 078 Tk GUI time bounds/invalidation/3D/no IO: PASS')
        finally:
            app.destroy()
