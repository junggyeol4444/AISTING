"""Original 057 isolated Tk GUI smoke, with I/O disabled."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import AVATARS, load_settings, save_settings
from ai_broadcaster.avatar_motion_review import inspect_motion_canvas

with tempfile.TemporaryDirectory() as td:
    data = Path(td)
    settings = data/'settings.json'
    memory = data/'memory.sqlite3'
    sentinel = data/'original.txt'
    sentinel.write_text('keep', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda v: save_settings(v, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('sqlite3.connect', side_effect=AssertionError('DB forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('표정·움직임 시험')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '표정·움직임 시험'
            assert app._motion_session is None
            assert '미시험' in app._motion_status.get()
            app._motion_audit()
            assert '먼저' in app._motion_status.get()
            two = next(k for k,v in AVATARS.items() if v == '2d')
            three = next(k for k,v in AVATARS.items() if v == '3d')
            app._avatar.set(two)
            app._avatar_expression.set('미소')
            app._motion_background.set('초록색 배경')
            app._motion_start()
            assert app._motion_session is not None
            assert app._motion_session.count == 9
            app._motion_next()
            assert app._motion_session.index == 1
            label, pose = app._motion_session.current
            assert not inspect_motion_canvas(app._motion_canvas, pose)
            assert app._motion_canvas.find_withtag('aisting_mouth_open')
            app._motion_audit()
            assert '검사 통과' in app._motion_status.get()
            assert '운영자 평가 대기' in app._motion_log.get('1.0', 'end')
            assert app._motion_session.index == 1
            app._motion_previous()
            assert app._motion_session.index == 0
            assert app._motion_canvas.find_withtag('aisting_eyes_blink')
            app._avatar_expression.set('걱정')
            assert app._motion_session is None
            assert '무효' in app._motion_status.get()
            app._motion_start()
            assert app._motion_session is not None
            app._avatar.set(three)
            assert app._motion_session is None
            assert app._motion_canvas.find_withtag('aisting_3d_unavailable')
            app._motion_start()
            assert app._motion_session is None
            assert '준비 불가' in app._motion_status.get()
            app._avatar.set(two)
            app._motion_start()
            assert app._motion_session is not None
            # Selected state is not persisted by the rehearsal.
            assert not settings.exists() and not memory.exists()
            assert sentinel.read_text(encoding='utf-8') == 'keep'
            print('GUI stage 057 avatar expression/motion preview: PASS')
        finally:
            app.destroy()
