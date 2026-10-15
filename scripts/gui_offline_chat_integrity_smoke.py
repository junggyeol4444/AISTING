"""Original 064 real Tk smoke: manual, read-only duplicate/gap inspection."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings
from ai_broadcaster.offline_chat_receiver import MockReceivedChat

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
            app._tab_nav.set('채팅 중복·누락 점검')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '채팅 중복·누락 점검'
            app._mock_integrity_run()
            assert '구조 오류 없음' in app._mock_integrity_status.get()
            app._platforms['chzzk'].set(True)
            app._platform_chat_connect()
            app._mock_receive_attach()
            app._mock_receive_text.set('same')
            app._mock_receive_inject()
            app._mock_receive_inject()
            assert '다시 수동 검사' in app._mock_integrity_status.get()
            app._mock_integrity_run()
            assert '반복 내용 1건' in app._mock_integrity_status.get()
            assert '미동기화 2건' in app._mock_integrity_status.get()
            assert '누락 판정 아님' in app._mock_integrity_log.get('1.0', 'end')
            app._mock_order_sync()
            assert '다시 수동 검사' in app._mock_integrity_status.get()
            app._mock_integrity_run()
            assert '미동기화 0건' in app._mock_integrity_status.get()
            app._mock_order_next()
            assert '다시 수동 검사' in app._mock_integrity_status.get()
            app._mock_integrity_run()
            assert len(app._mock_order.snapshot().pending) == 1
            app._mock_receiver._buffer.append(MockReceivedChat(4, 'chzzk', 'viewer', 'gap'))
            app._mock_integrity_run()
            assert '구조 오류 발견' in app._mock_integrity_status.get()
            assert '누락' in app._mock_integrity_log.get('1.0', 'end')
            assert not settings.exists() and sentinel.read_text(encoding='utf8') == 'KEEP'
            print('GUI stage 064 duplicate content preserved, unsynced not lost, gap detection, stale audit, no I/O: PASS')
        finally:
            app.destroy()
