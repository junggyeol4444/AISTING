"""Original roadmap 038: Xvfb GUI smoke, no real network/AI/PC/stream."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as temp:
    setting_path = Path(temp) / 'settings.json'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(setting_path)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda d: save_settings(d, setting_path)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('무채팅 자발 발화 모의')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '무채팅 자발 발화 모의'
            assert app._idle_session is None
            assert not app._idle_enabled.get()
            assert not setting_path.exists()
            app._idle_configure()
            app._idle_advance()
            app._idle_preview()
            assert app._idle_session.audit().suggestions == ()
            app._idle_enabled.set(True)
            app._idle_configure()
            app._idle_preview()
            assert app._idle_session.audit().suggestions == ('오늘은 어떤 이야기를 나눠볼까요?',)
            app._idle_preview()
            assert len(app._idle_session.audit().suggestions) == 1
            app._idle_receive()
            assert len(app._idle_session.audit().chat.pending) == 2
            app._idle_advance()
            app._idle_preview()
            assert len(app._idle_session.audit().suggestions) == 1
            assert '채팅 처리 우선' in app._idle_status.get()
            app._idle_process()
            assert len(app._idle_session.audit().chat.replied) == 2
            app._idle_advance()
            app._idle_preview()
            assert len(app._idle_session.audit().suggestions) == 2
            app._idle_chat_input.delete('1.0', 'end')
            app._idle_chat_input.insert('1.0', 'malformed')
            app._idle_receive()
            assert '채팅 접수 실패' in app._idle_status.get()
            assert app._idle_session.audit().chat.accepted == 2
            app._idle_threshold.set('0')
            app._idle_configure()
            assert '설정 실패' in app._idle_status.get()
            assert app._idle_session.audit().enabled
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._idle_reset()
            assert app._idle_session is not None
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._idle_reset()
            assert app._idle_session is None and not app._idle_enabled.get()
            assert not setting_path.exists()
            print('GUI original roadmap 038 idle speech simulation: PASS')
        finally:
            app.destroy()
