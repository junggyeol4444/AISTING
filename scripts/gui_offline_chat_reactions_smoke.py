"""Stage 065 real Tk GUI smoke: existing 062/063 -> manual all-chat mock replies."""
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
            app._tab_nav.set('전체 채팅 모의 응답')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '전체 채팅 모의 응답'
            app._mock_reactions_next()
            assert '차단' in app._mock_reactions_status.get()
            app._platforms['chzzk'].set(True)
            app._platforms['youtube'].set(True)
            app._platform_chat_connect()
            app._mock_receive_attach()
            app._mock_receive_platform.set('youtube')
            app._mock_receive_text.set('same')
            app._mock_receive_inject()
            app._mock_receive_inject()
            app._mock_receive_platform.set('chzzk')
            app._mock_receive_inject()
            app._mock_order_sync()
            app._mock_reactions_sync()
            app._mock_reactions_next()
            app._mock_reactions_fail()
            assert app._mock_reactions.snapshot().blocked
            assert len(app._mock_reactions.snapshot().pending) == 2
            app._mock_reactions_next()
            assert len(app._mock_reactions.snapshot().pending) == 2
            app._mock_reactions_resume()
            app._mock_reactions_batch()
            assert [item.event.ordinal for item in app._mock_reactions.snapshot().responded] == [1, 2, 3]
            assert app._mock_reactions.snapshot().all_responded
            assert app._mock_receiver.snapshot().accepted_count == 3
            assert len(app._mock_order.snapshot().pending) == 3  # stage-063 cursor not consumed
            assert not settings.exists() and sentinel.read_text(encoding='utf8') == 'KEEP'
            print('GUI stage 065 FIFO duplicate all-chat mock response, failure/manual resume, no I/O: PASS')
        finally:
            app.destroy()
