"""Stage 063 real Tk widget smoke: manual FIFO, duplicate, failure, resume."""
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
    sentinel = Path(temp) / 'keep.txt'
    sentinel.write_text('KEEP', encoding='utf8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda obj: save_settings(obj, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('db')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('메시지 순서 관리')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '메시지 순서 관리'
            app._mock_order_next()
            assert '차단' in app._mock_order_status.get()
            app._platforms['chzzk'].set(True)
            app._platforms['youtube'].set(True)
            app._platform_chat_connect()
            app._mock_receive_attach()
            app._mock_receive_platform.set('youtube')
            app._mock_receive_text.set('same')
            app._mock_receive_inject()
            app._mock_receive_inject()
            app._mock_receive_platform.set('chzzk')
            app._mock_receive_text.set('third')
            app._mock_receive_inject()
            app._mock_order_sync()
            assert [e.ordinal for e in app._mock_order.snapshot().pending] == [1, 2, 3]
            app._mock_order_next()
            assert [e.ordinal for e in app._mock_order.snapshot().processed] == [1]
            app._mock_order_fail()
            assert app._mock_order.snapshot().paused
            app._mock_order_next()
            assert [e.ordinal for e in app._mock_order.snapshot().pending] == [2, 3]
            app._platform_chat_disconnect()
            app._mock_order_resume()
            app._mock_order_next()
            app._mock_order_next()
            assert [e.ordinal for e in app._mock_order.snapshot().processed] == [1, 2, 3]
            assert app._mock_receiver.snapshot().accepted_count == 3
            assert not settings.exists() and sentinel.read_text(encoding='utf8') == 'KEEP'
            print('GUI stage 063 manual FIFO, duplicate, simulated failure/resume, disconnect retention: PASS')
        finally:
            app.destroy()
