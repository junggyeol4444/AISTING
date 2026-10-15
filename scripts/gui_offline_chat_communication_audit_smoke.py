"""Original 070: real Tk GUI smoke on a virtual screen, offline only."""
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
            app._tab_nav.set('채팅 소통 통합 모의 검증')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '채팅 소통 통합 모의 검증'
            app._mock_communication_run()
            assert app._mock_communication_report is None
            assert '미실행' in app._mock_communication_status.get()
            app._platforms['chzzk'].set(True)
            app._platforms['youtube'].set(True)
            app._platform_chat_connect()
            app._mock_receive_attach()
            app._mock_receive_platform.set('chzzk')
            app._mock_receive_sender.set('보존')
            app._mock_receive_text.set('기존 메시지')
            app._mock_receive_inject()
            old = (app._platform_chat_session.snapshot(), app._mock_receiver.snapshot(),
                   app._mock_order.snapshot(), app._mock_reactions.snapshot())
            app._mock_communication_run()
            report = app._mock_communication_report
            assert report is not None and report.passed and report.received == report.responded == 6
            assert '오프라인 통합 시험 통과' in app._mock_communication_status.get()
            assert old == (app._platform_chat_session.snapshot(), app._mock_receiver.snapshot(),
                           app._mock_order.snapshot(), app._mock_reactions.snapshot())
            assert '실제 플랫폼' in app._mock_communication_log.get('1.0', 'end')
            app._platforms['twitch'].set(True)
            assert app._mock_communication_report is None
            assert '무효' in app._mock_communication_status.get()
            app._mock_communication_run()
            assert app._mock_communication_report.passed
            assert len(app._mock_communication_report.selected) == 3
            assert not settings.exists() and sentinel.read_text(encoding='utf8') == 'KEEP'
            print('GUI original 070 isolated offline chat chain + selection invalidation: PASS')
        finally:
            app.destroy()
