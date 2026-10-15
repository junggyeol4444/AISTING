"""067 real Tk GUI smoke test with no network, DB, process or settings writes."""
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
         patch('sqlite3.connect', side_effect=AssertionError('database')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('시청자 대화 맥락 연결')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '시청자 대화 맥락 연결'
            assert not app._mock_viewer_context.snapshot().enabled
            app._mock_viewer_context_enable()
            assert app._mock_viewer_context.snapshot().enabled
            app._platforms['chzzk'].set(True)
            app._platforms['youtube'].set(True)
            app._platform_chat_connect()
            app._mock_receive_attach()
            app._mock_receive_platform.set('chzzk')
            app._mock_receive_sender.set('alice')
            app._mock_receive_text.set('first')
            app._mock_receive_inject()
            app._mock_receive_platform.set('youtube')
            app._mock_receive_text.set('other')
            app._mock_receive_inject()
            app._mock_receive_platform.set('chzzk')
            app._mock_receive_text.set('second')
            app._mock_receive_inject()
            app._mock_order_sync()
            app._mock_reactions_sync()
            app._mock_reactions_next()
            app._mock_reactions_next()
            app._mock_viewer_context_refresh()
            report = app._mock_viewer_context.snapshot()
            assert report.next_event.ordinal == 3
            assert report.prior_ordinals == (1,)
            app._mock_reactions_next()
            assert app._mock_reactions.snapshot().all_responded
            assert app._mock_viewer_context.snapshot().next_event is None
            assert not settings.exists() and sentinel.read_text(encoding='utf8') == 'KEEP'
            print('GUI stage 067 opt-in viewer history + actual FIFO replies + isolation: PASS')
        finally:
            app.destroy()
