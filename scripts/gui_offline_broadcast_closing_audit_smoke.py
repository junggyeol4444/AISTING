"""080: actual Tk smoke on a disposable Linux virtual display; no OBS/network."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as scratch:
    local = Path(scratch)
    settings = local / 'settings.json'
    sentinel = local / 'keep.txt'
    sentinel.write_text('ORIGINAL', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda x: save_settings(x, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('subprocess.Popen', side_effect=AssertionError('external process')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')), \
         patch('time.sleep', side_effect=AssertionError('delay')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('방송 화면 구성 미리보기')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._broadcast_closing_audit()
            assert app._closing_audit_report is None
            assert '미통과' in app._closing_audit_status.get()
            app._broadcast_scene_preview()
            app._broadcast_closing_audit()
            r = app._closing_audit_report
            assert r and r.passed and r.total == 12
            assert '실제 음성·OBS·방송 자동 종료 미검증' in app._closing_audit_status.get()
            # Audit should not alter an actual local closing rehearsal session.
            app._duration_elapsed.set('180')
            app._broadcast_duration_check()
            app._broadcast_closing_prepare()
            session = app._closing_session
            assert session is not None
            before = session.snapshot()
            app._broadcast_closing_audit()
            assert app._closing_session is session and session.snapshot() == before
            # Tampering with invalid duration must fail closed without overwriting closing state.
            app._duration_maximum.set('2')
            app._broadcast_closing_audit()
            assert app._closing_audit_report is None
            assert '미통과' in app._closing_audit_status.get()
            # Modifying the avatar selection invalidates audit state without overriding user choice.
            app._duration_maximum.set('180')
            app._broadcast_closing_audit()
            assert app._closing_audit_report and app._closing_audit_report.passed
            app._avatar.set('3D')
            assert app._closing_audit_report is None
            assert app._avatar.get() == '3D'
            assert not settings.exists()
            assert sentinel.read_text(encoding='utf-8') == 'ORIGINAL'
            print('Stage 080 GUI isolated offline audit/invalid inputs/selection change/no IO PASS')
        finally:
            app.destroy()
