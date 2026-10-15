"""Original 071: Tk scene composition smoke on Linux virtual display, no OBS."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as tmp:
    settings = Path(tmp) / 'settings.json'
    sentinel = Path(tmp) / 'untouched.txt'
    sentinel.write_text('KEEP', encoding='utf8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda obj: save_settings(obj, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('방송 화면 구성 미리보기')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '방송 화면 구성 미리보기'
            app._broadcast_scene_preview()
            assert app._scene_snapshot is not None
            assert app._scene_snapshot.avatar == 'undecided'
            assert 'aisting_scene_avatar_placeholder' in app._scene_canvas.gettags('aisting_scene_avatar_placeholder')
            assert '2D 자동 대체 없음' in app._scene_status.get()
            app._avatar.set('2D')
            assert app._scene_snapshot is None
            assert 'aisting_scene_stale' in app._scene_canvas.gettags('aisting_scene_stale')
            app._content.set('수다 + 게임')
            app._platforms['chzzk'].set(True)
            app._platforms['youtube'].set(True)
            app._broadcast_scene_preview()
            assert app._scene_snapshot is not None
            assert app._scene_snapshot.platforms == ('chzzk', 'youtube')
            assert app._scene_snapshot.content == 'both'
            assert 'aisting_sample_2d' in app._scene_canvas.gettags('aisting_sample_2d')
            assert 'aisting_scene_content' in app._scene_canvas.gettags('aisting_scene_content')
            assert 'aisting_scene_watermark' in app._scene_canvas.gettags('aisting_scene_watermark')
            app._scene_show_title.set(False)
            assert app._scene_snapshot is None
            app._broadcast_scene_preview()
            assert not app._scene_canvas.find_withtag('aisting_scene_title')
            app._avatar.set('3D')
            app._broadcast_scene_preview()
            assert app._scene_snapshot.avatar == '3d'
            assert not app._scene_canvas.find_withtag('aisting_sample_2d')
            assert app._scene_canvas.find_withtag('aisting_scene_avatar_placeholder')
            assert not settings.exists() and sentinel.read_text(encoding='utf8') == 'KEEP'
            print('GUI original 071 offline broadcast scene preview + stale/2D/3D: PASS')
        finally:
            app.destroy()
