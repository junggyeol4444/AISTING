"""Real Tk stage 059 interaction, Linux Xvfb compatible. No external services."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import AVATARS, load_settings, save_settings

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    settings = base/'settings.json'
    memory = base/'memory.sqlite3'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda obj: save_settings(obj, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('아바타 장시간 모의 시험')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '아바타 장시간 모의 시험'
            two = next(k for k,v in AVATARS.items() if v == '2d')
            three = next(k for k,v in AVATARS.items() if v == '3d')
            app._avatar.set(two)
            app._endurance_hours.set('24')
            app._avatar_expression.set('미소')
            app._endurance_run()
            app.update()
            result = app._endurance_result
            assert result is not None and result.inspected_frames == 86400
            assert len(result.checkpoints) == 12
            assert '240회' in app._endurance_status.get()
            assert app._endurance_canvas.find_withtag('aisting_sample_2d')
            assert len(app._endurance_canvas.find_all()) <= 40
            app._avatar_expression.set('놀람')
            app.update()
            assert app._endurance_result is None
            assert '무효' in app._endurance_status.get()
            app._endurance_hours.set('1')
            app._endurance_run()
            assert app._endurance_result.inspected_frames == 3600
            app._avatar.set(three)
            app.update()
            assert app._endurance_result is None
            assert app._endurance_canvas.find_withtag('aisting_3d_unavailable')
            assert not app._endurance_canvas.find_withtag('aisting_sample_2d')
            app._endurance_run()
            assert app._endurance_result is None
            assert '차단' in app._endurance_status.get()
            assert not settings.exists() and not memory.exists()
            print('GUI stage 059 virtual 24h, bounded canvas, invalidation, 3D refusal: PASS')
        finally:
            app.destroy()
