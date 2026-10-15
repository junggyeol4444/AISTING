"""Original 069 real Tk smoke: simulated outage, failed handshake, manual recovery."""
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
            app._tab_nav.set('채팅 연결 장애 복구 모의')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '채팅 연결 장애 복구 모의'
            app._platforms['chzzk'].set(True)
            app._platform_chat_connect()
            app._mock_receive_attach()
            for msg in ('a1', 'a1', 'a2'):
                app._mock_receive_platform.set('chzzk')
                app._mock_receive_sender.set('viewer')
                app._mock_receive_text.set(msg)
                app._mock_receive_inject()
            app._mock_order_sync()
            app._mock_reactions_sync()
            app._mock_reactions_next()
            app._mock_recovery_outage()
            report = app._mock_chat_recovery.snapshot(app._platform_chat_session)
            assert not report.connected and not report.attached and report.accepted == 3
            app._mock_receive_inject()
            assert app._mock_receiver.snapshot().accepted_count == 3
            app._mock_recovery_fail()
            report = app._mock_chat_recovery.snapshot(app._platform_chat_session)
            assert report.failed_attempts == 1 and not report.connected
            app._mock_recovery_reattach()
            assert not app._mock_chat_recovery.snapshot(app._platform_chat_session).attached
            app._mock_recovery_reconnect()
            assert not app._mock_chat_recovery.snapshot(app._platform_chat_session).attached
            app._mock_recovery_reattach()
            report = app._mock_chat_recovery.snapshot(app._platform_chat_session)
            assert report.recovery_complete and report.accepted == 3 and report.replied == 1
            assert [e.text for e in app._mock_receiver.snapshot().buffered] == ['a1','a1','a2']
            app._mock_reactions_batch()
            assert [item.event.ordinal for item in app._mock_reactions.snapshot().responded] == [1,2,3]
            assert not settings.exists() and sentinel.read_text(encoding='utf8') == 'KEEP'
            print('GUI original 069 offline outage/failure/manual recovery/FIFO: PASS')
        finally:
            app.destroy()
