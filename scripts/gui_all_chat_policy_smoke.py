"""Roadmap 037 GUI smoke on Linux Xvfb; no live chat or real model."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as temp:
    settings_file = Path(temp) / 'settings.json'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings_file)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda d: save_settings(d, settings_file)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('전체 채팅 반응 원칙')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '전체 채팅 반응 원칙'
            assert app._all_chat_session is None
            assert not settings_file.exists()
            app._all_chat_next()
            assert '먼저 채팅' in app._all_chat_status.get()
            app._all_chat_append()
            assert '접수 6건' in app._all_chat_status.get(), app._all_chat_status.get()
            assert '응답 0건' in app._all_chat_status.get()
            app._all_chat_next()
            assert '응답 1건' in app._all_chat_status.get()
            app._all_chat_batch()
            assert '전건 응답' in app._all_chat_status.get()
            assert '응답 6건' in app._all_chat_status.get()
            app._all_chat_input.delete('1.0', 'end')
            app._all_chat_input.insert('1.0', '가: ㅋㅋㅋ\n가: ㅋㅋㅋ')
            app._all_chat_append()
            assert '접수 8건' in app._all_chat_status.get()
            app._all_chat_batch()
            assert '응답 8건' in app._all_chat_status.get()
            desc = app._all_chat_result.get('1.0', 'end')
            assert '#7 가: ㅋㅋㅋ' in desc and '#8 가: ㅋㅋㅋ' in desc
            app._all_chat_input.delete('1.0', 'end')
            app._all_chat_input.insert('1.0', 'invalid')
            app._all_chat_append()
            assert '접수 실패' in app._all_chat_status.get()
            assert app._all_chat_session.audit().accepted == 8
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._all_chat_reset()
            assert app._all_chat_session is not None
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._all_chat_reset()
            assert app._all_chat_session is None
            assert not settings_file.exists()
            print('GUI original roadmap 037 all-chat response policy: PASS')
        finally:
            app.destroy()
