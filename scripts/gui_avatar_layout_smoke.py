"""Stage 058 real Tk interaction on Linux virtual display, fully offline."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.avatar_layout import load_layout, PREVIEW_WIDTH, PREVIEW_HEIGHT
from ai_broadcaster.offline_settings import AVATARS, load_settings, save_settings

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    target = root/'layout.json'
    setting = root/'settings.json'
    memory = root/'memory.sqlite3'
    other = root/'unrelated.json'
    other.write_bytes(b'unchanged')
    with patch('ai_broadcaster.desktop.layout_path', return_value=target), \
         patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(setting)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda v: save_settings(v, setting)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')), \
         patch('subprocess.Popen', side_effect=AssertionError('external program')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('캐릭터 화면 배치')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '캐릭터 화면 배치'
            assert not target.exists()
            two = next(k for k,v in AVATARS.items() if v == '2d')
            three = next(k for k,v in AVATARS.items() if v == '3d')
            app._avatar.set(two)
            app.update()
            assert app._layout_canvas.find_withtag('aisting_sample_2d')
            app._avatar_expression.set('미소')
            app._layout_horizontal.set(0)
            app._layout_vertical.set(0)
            app._layout_size.set(100)
            app._layout_background.set('초록색 배경')
            app.update()
            assert app._layout_canvas.cget('bg') == '#00db53'
            assert app._layout_canvas.find_withtag('aisting_expression_smile')
            x1,y1,x2,y2 = app._layout_canvas.bbox('all')
            assert x1 >= -2 and y1 >= -2 and x2 <= PREVIEW_WIDTH+2 and y2 <= PREVIEW_HEIGHT+2, (x1,y1,x2,y2)
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._layout_save()
            assert not target.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._layout_save()
            saved = load_layout(target, selected_avatar='2d')
            assert saved.horizontal == 0 and saved.vertical == 0 and saved.size == 100
            assert saved.background == '초록색 배경'
            app._layout_reset()
            assert app._layout_horizontal.get() == 75
            app._layout_load()
            assert app._layout_horizontal.get() == 0
            assert app._layout_canvas.find_withtag('aisting_sample_2d')
            # 3D selection must not show the 2D sample or reuse the old layout.
            app._avatar.set(three)
            app.update()
            assert app._layout_canvas.find_withtag('aisting_layout_unavailable')
            assert not app._layout_canvas.find_withtag('aisting_sample_2d')
            app._layout_save()
            assert '불가' in app._layout_status.get()
            app._layout_load()
            assert '차단' in app._layout_status.get()
            app._avatar.set(two)
            app.update()
            # 2-level deletion never touches other files.
            with patch('ai_broadcaster.desktop.messagebox.askyesno', side_effect=[True, False]):
                app._layout_delete()
            assert target.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._layout_delete()
            assert not target.exists()
            assert other.read_bytes() == b'unchanged'
            assert not setting.exists() and not memory.exists()
            print('GUI original 058 layout preview/save/load/refusal/delete: PASS')
        finally:
            app.destroy()
