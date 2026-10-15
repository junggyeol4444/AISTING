"""079 real Tk GUI on Linux virtual display; NEVER actual OBS/TTS."""
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
    marker = Path(temp) / 'do_not_touch.txt'
    marker.write_text('PRESERVE', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda x: save_settings(x, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')), \
         patch('sqlite3.connect', side_effect=AssertionError('DB')), \
         patch('time.sleep', side_effect=AssertionError('delay')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('방송 화면 구성 미리보기')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._broadcast_closing_prepare()
            assert app._closing_session is None
            assert '실패' in app._closing_status.get()
            app._broadcast_scene_preview()
            app._duration_elapsed.set('60')
            app._broadcast_duration_check()
            app._broadcast_closing_prepare()
            assert app._closing_session is None
            app._duration_elapsed.set('180')
            app._broadcast_duration_check()
            app._broadcast_closing_prepare()
            assert app._closing_session is not None
            assert app._closing_session.snapshot().phase == 'notice_pending'
            app._broadcast_closing_advance()
            assert '마무리' in app._closing_line.get()
            assert app._closing_session.snapshot().phase == 'farewell_pending'
            app._broadcast_closing_advance()
            assert app._closing_session.snapshot().virtual_stream_ended
            assert 'OBS/방송 종료 0건' in app._closing_status.get()
            app._broadcast_closing_advance()
            assert '실패' in app._closing_status.get()
            app._duration_elapsed.set('200')
            assert app._closing_session is None
            app._duration_elapsed.set('180')
            app._broadcast_duration_check()
            app._broadcast_closing_prepare()
            assert app._closing_session is not None
            app._avatar.set('3D')
            assert app._closing_session is None
            assert app._avatar.get() == '3D'
            assert marker.read_text(encoding='utf-8') == 'PRESERVE'
            assert not settings.exists()
            print('Stage 079 GUI local notice/farewell/mock stop/invalidation/3D/no IO PASS')
        finally:
            app.destroy()
