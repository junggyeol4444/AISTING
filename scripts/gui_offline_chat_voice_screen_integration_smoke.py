"""Stage 077 actual Tk local GUI smoke on Xvfb; no audio/OBS/network."""
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
    sentinel.write_text('PRESERVED', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda x: save_settings(x, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('방송 화면 구성 미리보기')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._chat_voice_screen_integration_check()
            assert app._scene_chat_voice_report is None
            assert '미통과' in app._scene_chat_voice_status.get()
            app._broadcast_scene_preview()
            app._chat_voice_screen_integration_check()
            assert app._scene_chat_voice_report is None
            assert '플랫폼' in app._scene_chat_voice_status.get()
            app._platforms['chzzk'].set(True)
            app._platforms['youtube'].set(True)
            app._voice.set('Windows 무료 음성')
            app._broadcast_scene_preview()
            before = tuple(app._scene_canvas.find_all())
            app._chat_voice_screen_integration_check()
            report = app._scene_chat_voice_report
            assert report is not None and report.passed, app._scene_chat_voice_status.get()
            assert (report.received, report.responded, report.displayed) == (3, 3, 3)
            assert tuple(app._scene_canvas.find_all()) == before  # independent canvas
            assert not app._scene_canvas.find_withtag('aisting_scene_voice')
            assert not report.actual_audio and not report.actual_streaming
            app._voice_volume.set('0')
            assert app._scene_chat_voice_report is None
            app._chat_voice_screen_integration_check()
            assert app._scene_chat_voice_report.passed
            app._avatar.set('3D')
            assert app._scene_chat_voice_report is None
            app._broadcast_scene_preview()
            app._chat_voice_screen_integration_check()
            assert app._scene_chat_voice_report.passed
            assert not app._scene_canvas.find_withtag('aisting_sample_2d')
            app._scene_canvas.delete('aisting_scene_watermark')
            app._chat_voice_screen_integration_check()
            assert app._scene_chat_voice_report is None
            assert '오류' in app._scene_chat_voice_status.get()
            app._broadcast_scene_preview()
            app._chat_voice_screen_integration_check()
            assert app._scene_chat_voice_report.passed
            assert not settings.exists() and sentinel.read_text(encoding='utf-8') == 'PRESERVED'
            print('Stage 077 GUI mock-chat -> mock-reply -> silent voice -> local Tk overlay, failures, stale, 3D, no IO: PASS')
        finally:
            app.destroy()
