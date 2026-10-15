"""Stage 060 real Tk GUI smoke under Xvfb; no account, network or audio."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import AVATARS, VOICES, load_settings, save_settings
from ai_broadcaster.avatar_motion_review import inspect_motion_canvas
from ai_broadcaster.avatar_renderer import AvatarFrame

with tempfile.TemporaryDirectory() as tmp:
    data = Path(tmp)
    settings = data / 'settings.json'
    sentinel = data / 'existing_data.txt'
    sentinel.write_text('KEEP', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda obj: save_settings(obj, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('캐릭터 통합 작동 시험')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '캐릭터 통합 작동 시험'
            app._integration_run()
            assert app._integration_report is None  # 2D/voice not chosen
            two = next(k for k, v in AVATARS.items() if v == '2d')
            three = next(k for k, v in AVATARS.items() if v == '3d')
            voice = next(k for k, v in VOICES.items() if v == 'windows_system')
            app._avatar.set(two)
            app._voice.set(voice)
            app._avatar_expression.set('미소')
            app._layout_background.set('초록색 배경')
            app._layout_horizontal.set(35)
            app._layout_vertical.set(85)
            app._layout_size.set(80)
            app._integration_run()
            report = app._integration_report
            assert report is not None and report.passed
            assert report.virtual_frames == 3600 and report.canvas_cycles == 60
            assert '통과' in app._integration_status.get()
            assert '운영자 승인 대기' in app._integration_log.get('1.0', 'end')
            expected = AvatarFrame(app._current_persona()['name'], False, 4,
                                   background='초록색 배경', expression='smile')
            assert not inspect_motion_canvas(app._integration_canvas, expected)
            app._layout_size.set(81)
            assert app._integration_report is None
            assert '무효' in app._integration_status.get()
            app._integration_run()
            assert app._integration_report is not None
            app._voice_rate.set('1')
            assert app._integration_report is None
            app._integration_run()
            assert app._integration_report is not None
            app._avatar.set(three)
            assert app._integration_report is None
            assert app._integration_canvas.find_withtag('aisting_3d_unavailable')
            assert not app._integration_canvas.find_withtag('aisting_sample_2d')
            app._integration_run()
            assert app._integration_report is None and '차단' in app._integration_status.get()
            assert not settings.exists() and sentinel.read_text(encoding='utf-8') == 'KEEP'
            print('GUI stage 060 2D integration, voice interruption, invalidation, 3D refusal: PASS')
        finally:
            app.destroy()
