"""Stage 062 Tk GUI smoke with real widgets but no platform or network I/O."""
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
    sentinel = Path(temp) / 'sentinel.txt'
    sentinel.write_text('KEEP', encoding='utf8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda obj: save_settings(obj, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('db')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('채팅 수신 모의')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '채팅 수신 모의'
            app._mock_receive_attach()
            assert '차단' in app._mock_receive_status.get()
            app._mock_receive_inject()
            assert app._mock_receiver.snapshot().accepted_count == 0
            app._platforms['youtube'].set(True)
            app._platforms['twitch'].set(True)
            app._platform_chat_connect()
            app._mock_receive_attach()
            assert app._mock_receiver.snapshot().attached
            app._mock_receive_platform.set('youtube')
            app._mock_receive_sender.set('사람1')
            app._mock_receive_text.set('안녕')
            app._mock_receive_inject()
            app._mock_receive_inject()
            assert app._mock_receiver.snapshot().accepted_count == 2
            app._mock_receive_platform.set('chzzk')
            app._mock_receive_inject()
            assert '차단' in app._mock_receive_status.get()
            assert app._mock_receiver.snapshot().accepted_count == 2
            app._platforms['youtube'].set(False)
            assert not app._mock_receiver.snapshot().attached
            assert app._mock_receiver.snapshot().accepted_count == 2
            app._platform_chat_connect()
            app._mock_receive_attach()
            app._mock_receive_platform.set('twitch')
            app._mock_receive_inject()
            assert app._mock_receiver.snapshot().accepted_count == 3
            app._platform_chat_disconnect()
            app._mock_receive_inject()
            assert app._mock_receiver.snapshot().accepted_count == 3
            assert '실제 플랫폼에서 받은 메시지: 0건' in app._mock_receive_log.get('1.0', 'end')
            assert not settings.exists() and sentinel.read_text(encoding='utf8') == 'KEEP'
            print('GUI stage 062 manual synthetic receive, duplicate retention, disconnect, selection invalidation: PASS')
        finally:
            app.destroy()
