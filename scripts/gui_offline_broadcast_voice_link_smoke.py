"""Stage 073 GUI regression: only fake speech segments and Canvas markers."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / 'settings.json'
    sentinel = Path(tmp) / 'keep.txt'
    sentinel.write_text('UNCHANGED', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(path)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda obj: save_settings(obj, path)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')), \
         patch('sqlite3.connect', side_effect=AssertionError('db')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('방송 화면 구성 미리보기')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._broadcast_voice_prepare()
            assert app._scene_voice_link is None, 'undecided source must not auto-fallback'
            assert '미연결' in app._scene_voice_status.get()
            app._voice.set('Windows 무료 음성')
            app._avatar.set('2D')
            app._broadcast_voice_prepare()
            assert app._scene_voice_link is not None
            assert app._scene_voice_link.cursor == 0
            assert not app._scene_canvas.find_withtag('aisting_scene_voice')
            app._broadcast_voice_interrupt()
            assert app._scene_voice_link.cursor == 0
            app._broadcast_voice_next()
            assert app._scene_voice_link.cursor == 1
            assert app._scene_canvas.find_withtag('aisting_scene_voice')
            assert '실제 음성/OBS 송출 0건' in app._scene_voice_status.get()
            app._scene_voice_text.set('다른 가상 문장')
            assert app._scene_voice_link is None
            assert not app._scene_canvas.find_withtag('aisting_scene_voice')
            app._broadcast_voice_prepare()
            assert app._scene_voice_link is not None
            app._content.set('게임')
            assert app._scene_voice_link is None
            app._voice.set('미정')
            app._broadcast_voice_prepare()
            assert app._scene_voice_link is None
            assert not path.exists() and sentinel.read_text(encoding='utf-8') == 'UNCHANGED'
            print('Stage 073 Tk voice/scene mock route, manual retry, invalidation, no fallback: PASS')
        finally:
            app.destroy()
