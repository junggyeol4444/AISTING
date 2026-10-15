"""Stage 061 GUI under Xvfb: operator selections, manual mock lifecycle, no I/O."""
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
            app._tab_nav.set('플랫폼 채팅 연결 모의')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '플랫폼 채팅 연결 모의'
            app._platform_chat_connect()
            assert '차단' in app._platform_chat_status.get()
            assert not app._platform_chat_session.snapshot().connected
            app._platforms['youtube'].set(True)
            app._platforms['twitch'].set(True)
            assert '무효' in app._platform_chat_status.get()
            assert not app._platform_chat_session.snapshot().connected
            app._platform_chat_connect()
            assert app._platform_chat_session.snapshot().connected == ('youtube', 'twitch')
            assert '실제 연결 0개' in app._platform_chat_status.get()
            assert '채팅 수신: 0건' in app._platform_chat_log.get('1.0', 'end')
            app._platform_chat_connect()
            assert '차단' in app._platform_chat_status.get()
            app._platforms['youtube'].set(False)
            assert not app._platform_chat_session.snapshot().connected
            app._platform_chat_connect()
            assert app._platform_chat_session.snapshot().connected == ('twitch',)
            app._platform_chat_disconnect()
            assert not app._platform_chat_session.snapshot().connected
            assert app._platforms['twitch'].get() and not app._platforms['youtube'].get()
            assert not settings.exists() and sentinel.read_text(encoding='utf8') == 'KEEP'
            print('GUI stage 061 platform selection, manual mock connection, invalidation, no external I/O: PASS')
        finally:
            app.destroy()
