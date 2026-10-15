"""Stage 074 real Tk GUI smoke: no speaker, device/OBS, Internet or user settings."""
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
         patch('sqlite3.connect', side_effect=AssertionError('database')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('방송 화면 구성 미리보기')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._broadcast_output_check()
            assert app._scene_output_report is None
            assert '먼저' in app._scene_output_status.get()
            app._broadcast_scene_preview()
            app._broadcast_output_check()
            assert app._scene_output_report is not None
            assert app._scene_output_report.screen_ok
            assert '실제 소리 크기' in app._scene_output_status.get()
            app._voice_volume.set('0')
            assert app._scene_output_report is None
            app._broadcast_output_check()
            assert app._scene_output_report.silent_by_setting
            app._voice_volume.set('invalid')
            app._broadcast_output_check()
            assert app._scene_output_report is None
            assert '실패' in app._scene_output_status.get()
            app._voice_volume.set('85')
            app._avatar.set('2D')
            assert app._scene_output_report is None
            app._broadcast_scene_preview()
            app._voice.set('Windows 무료 음성')
            app._broadcast_voice_prepare()
            app._broadcast_voice_next()
            app._broadcast_output_check()
            assert app._scene_output_report.screen_ok
            app._scene_canvas.delete('aisting_scene_watermark')
            app._broadcast_output_check()
            assert not app._scene_output_report.screen_ok
            assert '불일치' in app._scene_output_status.get()
            app._avatar.set('3D')
            assert app._scene_output_report is None
            app._broadcast_scene_preview()
            app._broadcast_output_check()
            assert app._scene_output_report.screen_ok
            assert app._scene_output_report.cautions
            assert not app._scene_canvas.find_withtag('aisting_sample_2d')
            assert not path.exists() and sentinel.read_text(encoding='utf-8') == 'UNCHANGED'
            print('Stage 074 Tk nominal volume 0/85/invalid, scene tags, voice marker, 2D/3D, no IO: PASS')
        finally:
            app.destroy()
