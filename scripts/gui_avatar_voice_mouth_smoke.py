"""Original 055: exercise actual Tk GUI; no audio, account, network or file I/O."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import AVATARS, VOICES, load_settings, save_settings

with tempfile.TemporaryDirectory() as d:
    home = Path(d)
    settings = home/'settings.json'
    db = home/'memory.sqlite3'
    sentinel = home/'old_project_data.json'
    sentinel.write_bytes(b'unchanged-original-data')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda v: save_settings(v, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('sqlite3.connect', side_effect=AssertionError('DB forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('음성·입 움직임 모의')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '음성·입 움직임 모의'
            assert app._mouth_session is None
            two = next(k for k, v in AVATARS.items() if v == '2d')
            three = next(k for k, v in AVATARS.items() if v == '3d')
            windows_voice = next(k for k, v in VOICES.items() if v == 'windows_system')
            app._avatar.set(two)
            app._voice.set(windows_voice)
            app._mouth_start()
            assert app._mouth_session is not None
            assert len(app._mouth_session.cues) == 0
            app._mouth_step()
            assert len(app._mouth_session.cues) == 3
            app._mouth_next_frame()
            assert app._mouth_canvas.find_withtag('aisting_mouth_open')
            app._mouth_next_frame()
            assert app._mouth_canvas.find_withtag('aisting_mouth_open')
            app._mouth_next_frame()
            assert app._mouth_canvas.find_withtag('aisting_mouth_closed')
            # Never automatically move to another dialogue or audio frame.
            assert len(app._mouth_session.status().completed) == 1
            app._mouth_next_frame()
            assert app._mouth_canvas.find_withtag('aisting_mouth_closed')
            # On second chat, one failure only; no skipped head and no new mouth cue.
            app._mouth_fail_second.set(True)
            assert app._mouth_session is None
            app._mouth_start()
            app._mouth_step()
            app._mouth_step()
            assert len(app._mouth_session.status().pending) == 2
            assert len(app._mouth_session.cues) == 3
            assert 'simulated_interrupted' in app._mouth_status.get()
            app._mouth_step()
            assert len(app._mouth_session.status().completed) == 2
            assert len(app._mouth_session.cues) == 6
            # Changing the voice/selected avatar invalidates; no old cues reused.
            app._avatar.set(three)
            app.update()
            assert app._mouth_session is None
            assert app._mouth_canvas.find_withtag('aisting_3d_unavailable')
            app._mouth_start()
            assert app._mouth_session is None
            assert '준비 불가' in app._mouth_status.get()
            app._avatar.set(two)
            app._voice.set(next(k for k, v in VOICES.items() if v == 'own_recording'))
            app._mouth_start()
            assert app._mouth_session is None
            app._voice.set(windows_voice)
            app._mouth_start()
            assert app._mouth_session is not None
            app._mouth_script.insert('end', '\n새 시청자: 추가 댓글')
            app.update()
            assert app._mouth_session is None
            assert not settings.exists() and not db.exists()
            assert sentinel.read_bytes() == b'unchanged-original-data'
            print('GUI 055 voice-to-mouth simulated routing and manual preview: PASS')
        finally:
            app.destroy()
