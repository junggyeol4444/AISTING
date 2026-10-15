"""Headless Xvfb Tk smoke for the operator-triggered mock speed tab."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as tmp:
    settings_file = Path(tmp) / 'settings.json'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings_file)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, settings_file)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('응답 속도 관찰')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '응답 속도 관찰'
            assert '미실행' in app._speed_status.get()
            assert not settings_file.exists()
            app._run_response_speed_test()
            assert '완료 6/6건' in app._speed_status.get(), app._speed_status.get()
            report = app._speed_result.get('1.0', 'end')
            assert '중앙값' in report and 'P95' in report and '미판정' not in report
            assert '자연스러움' in report
            app._speed_input.delete('1.0', 'end')
            app._speed_input.insert('1.0', '가: ㅋㅋㅋ\n가: ㅋㅋㅋ')
            app._run_response_speed_test()
            assert '완료 2/2건' in app._speed_status.get()
            app._speed_input.delete('1.0', 'end')
            app._speed_input.insert('1.0', '형식 오류')
            app._run_response_speed_test()
            assert '검증 실패' in app._speed_status.get()
            app._reset_response_speed_test()
            assert '별: 안녕!' in app._speed_input.get('1.0', 'end')
            assert not settings_file.exists()
            print('GUI roadmap 036 mock reply time observation: PASS')
        finally:
            app.destroy()
