"""Linux virtual-display smoke for original roadmap 035; no real model or stream."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as temp:
    setting_path = Path(temp) / 'settings.json'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(setting_path)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, setting_path)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('기본 대화 반응 검사')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '기본 대화 반응 검사'
            assert not setting_path.exists()
            assert '미실행' in app._basic_reaction_status.get()
            app._run_basic_reaction_test()
            assert '통과 6/6건' in app._basic_reaction_status.get(), app._basic_reaction_status.get()
            assert '별: 안녕!' in app._basic_reaction_result.get('1.0', 'end')
            app._basic_reaction_input.delete('1.0', 'end')
            app._basic_reaction_input.insert('1.0', '가: ㅋㅋㅋ\n가: ㅋㅋㅋ\n나: 감사합니다')
            app._run_basic_reaction_test()
            assert '통과 3/3건' in app._basic_reaction_status.get()
            app._basic_reaction_input.delete('1.0', 'end')
            app._basic_reaction_input.insert('1.0', '잘못된 대본')
            app._run_basic_reaction_test()
            assert '검사 실패' in app._basic_reaction_status.get()
            app._reset_basic_reaction_test()
            assert '별: 안녕!' in app._basic_reaction_input.get('1.0', 'end')
            assert not setting_path.exists()
            print('GUI original stage035 basic reaction: PASS')
        finally:
            app.destroy()
