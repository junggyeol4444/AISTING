"""054: exercise real Tk widgets in Xvfb, without PC probing or streaming."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.avatar_expressions import load_expression, expression_matches
from ai_broadcaster.offline_settings import AVATARS, load_settings, save_settings

with tempfile.TemporaryDirectory() as dirname:
    folder = Path(dirname)
    file = folder / 'expression.json'
    settings = folder / 'settings.json'
    db = folder / 'chat.sqlite3'
    prior = folder / 'avatar_preparation_draft.json'
    prior.write_bytes(b'previous-unchanged')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda v: save_settings(v, settings)), \
         patch('ai_broadcaster.desktop.expression_path', return_value=file), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('sqlite3.connect', side_effect=AssertionError('DB forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
        app = AistingApp()
        try:
            app.update()
            assert not file.exists()
            app._tab_nav.set('기본 표정 설정')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '기본 표정 설정'
            assert expression_matches(app._canvas, 'neutral')
            assert '실제 모델 미검증' in app._expression_status.get()
            two = next(k for k,v in AVATARS.items() if v == '2d')
            three = next(k for k,v in AVATARS.items() if v == '3d')
            app._avatar.set(two)
            app._avatar_expression.set('미소')
            app.update()
            assert expression_matches(app._canvas, 'smile')
            app._open_avatar_capture()
            app.update()
            assert expression_matches(app._avatar_capture_canvas, 'smile')
            app._avatar_expression.set('놀람')
            app.update()
            assert expression_matches(app._canvas, 'surprised')
            assert expression_matches(app._avatar_capture_canvas, 'surprised')
            app._avatar_capture_background.set('초록색 배경')
            app._avatar_expression.set('걱정')
            app.update()
            assert expression_matches(app._canvas, 'concerned')
            assert expression_matches(app._avatar_capture_canvas, 'concerned')
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._expression_save()
            assert not file.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._expression_save()
            assert load_expression(file, selected_avatar='2d').expression == 'concerned'
            app._expression_reset()
            assert expression_matches(app._canvas, 'neutral')
            app._expression_load()
            assert app._avatar_expression.get() == '걱정'
            app._avatar.set(three)
            app.update()
            assert app._avatar_expression.get() == '기본'
            assert app._avatar_capture_window is None
            assert app._canvas.find_withtag('aisting_3d_unavailable')
            assert not app._canvas.find_withtag('aisting_expression_neutral')
            app._avatar_expression.set('미소')
            app._expression_save()
            assert '내장 2D' in app._expression_status.get()
            app._avatar.set('미정')
            app.update()
            app._expression_load()
            assert '불러오기 차단' in app._expression_status.get()
            app._avatar.set(two)
            with patch('ai_broadcaster.desktop.messagebox.askyesno', side_effect=[True, False]):
                app._expression_delete()
            assert file.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._expression_delete()
            assert not file.exists()
            assert prior.read_bytes() == b'previous-unchanged'
            assert not settings.exists() and not db.exists()
            print('GUI 054 expressions selection/render/save/load/delete: PASS')
        finally:
            app.destroy()
