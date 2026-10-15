"""Original 053 local GUI: verify current rendered Canvas without external model/PC access."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import AVATARS, load_settings, save_settings

with tempfile.TemporaryDirectory() as dirname:
    base = Path(dirname)
    setting_path = base / 'settings.json'
    db_path = base / 'chat.sqlite3'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(setting_path)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda value: save_settings(value, setting_path)), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('sqlite3.connect', side_effect=AssertionError('DB forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('캐릭터 화면 표시 검사')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '캐릭터 화면 표시 검사'
            assert '미검사' in app._avatar_display_status.get()
            app._avatar_display_check()
            assert '검사 통과' in app._avatar_display_status.get()
            assert '본 창 캐릭터 이름' in app._avatar_display_result.get('1.0', 'end')
            two_d = next(k for k, v in AVATARS.items() if v == '2d')
            three_d = next(k for k, v in AVATARS.items() if v == '3d')
            app._avatar.set(two_d)
            app.update()
            assert '재검사 필요' in app._avatar_display_status.get()
            app._open_avatar_capture()
            app.update()
            assert app._avatar_capture_window is not None
            app._avatar_demo.set(True)
            app._avatar_frame = 1
            app._avatar_capture_background.set('초록색 배경')
            app._avatar_display_check()
            assert '검사 통과' in app._avatar_display_status.get()
            details = app._avatar_display_result.get('1.0', 'end')
            assert '별도 창 캐릭터 이름' in details and '별도 창 배경' in details
            app._close_avatar_capture()
            app._avatar_display_check()
            assert '별도 창 닫힘' in app._avatar_display_result.get('1.0', 'end')
            app._avatar.set(three_d)
            app.update()
            app._avatar_display_check()
            assert '검사 통과' in app._avatar_display_status.get()
            assert '2D 자동 대체 차단' in app._avatar_display_result.get('1.0', 'end')
            app._open_avatar_capture()
            assert app._avatar_capture_window is None
            # Detect actual canvas tampering without touching settings.
            app._canvas.delete('aisting_3d_unavailable')
            from ai_broadcaster.avatar_display_validation import audit_avatar_display
            result = audit_avatar_display(avatar='3d', name='아이스팅', speaking=False,
                                          frame=0, main_canvas=app._canvas)
            assert not result.passed
            assert not setting_path.exists() and not db_path.exists()
            print('GUI stage 053 existing avatar display: PASS')
        finally:
            app.destroy()
