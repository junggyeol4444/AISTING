"""Test original 056 stage Tk UI in isolation; virtual display, no hardware."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import AVATARS, VOICES, load_settings, save_settings

with tempfile.TemporaryDirectory() as d:
    home = Path(d)
    settings = home/'settings.json'
    db = home/'memory.sqlite3'
    sentinel = home/'old_data'
    sentinel.write_bytes(b'unchanged')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda v: save_settings(v, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('sqlite3.connect', side_effect=AssertionError('db forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('음성·입 동기화 모의')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '음성·입 동기화 모의'
            two = next(k for k,v in AVATARS.items() if v == '2d')
            three = next(k for k,v in AVATARS.items() if v == '3d')
            windows = next(k for k,v in VOICES.items() if v == 'windows_system')
            app._avatar.set(two); app._voice.set(windows)
            app._sync_start()
            assert app._sync_session is not None
            assert app._sync_session.duration_ms == 0
            app._sync_step()
            assert len(app._sync_session.windows) == 1
            app._sync_seek(0)
            assert app._sync_canvas.find_withtag('aisting_mouth_open')
            end = app._sync_session.duration_ms
            app._sync_seek(end-1)
            assert app._sync_canvas.find_withtag('aisting_mouth_closed')
            app._sync_seek(end)
            assert app._sync_canvas.find_withtag('aisting_mouth_closed')
            app._sync_clock.set('-1'); app._sync_seek_entry()
            assert '범위' in app._sync_status.get()
            app._sync_seek(0)
            app._sync_advance(); assert app._sync_session.clock_ms == 100
            assert len(app._sync_session.rehearsal.status().pending) == 2
            app._sync_char_ms.set('110')
            assert app._sync_session is None
            app._sync_start()
            app._sync_step()
            app._sync_step()
            assert len(app._sync_session.windows) == 2
            app._sync_fail_second.set(True)
            assert app._sync_session is None
            app._sync_start(); app._sync_step(); app._sync_step()
            assert len(app._sync_session.windows) == 1
            assert 'simulated_interrupted' in app._sync_status.get()
            app._sync_step()
            assert len(app._sync_session.windows) == 2
            assert app._sync_session.audit()[0]
            app._avatar.set(three); app.update()
            assert app._sync_session is None
            assert app._sync_canvas.find_withtag('aisting_3d_unavailable')
            app._sync_start(); assert app._sync_session is None
            app._avatar.set(two)
            app._voice.set(next(k for k,v in VOICES.items() if v == 'own_recording'))
            app._sync_start(); assert app._sync_session is None
            app._voice.set(windows)
            app._sync_start(); assert app._sync_session is not None
            app._sync_script.insert('end', '\n새 채팅: 새로운 메세지')
            app.update(); assert app._sync_session is None
            assert not settings.exists() and not db.exists()
            assert sentinel.read_bytes() == b'unchanged'
            print('GUI 056 virtual voice/mouth timing timeline: PASS')
        finally:
            app.destroy()
