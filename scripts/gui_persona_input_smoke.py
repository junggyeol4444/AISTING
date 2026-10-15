import sys, tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings,save_settings
with tempfile.TemporaryDirectory() as temp:
    path=Path(temp)/'settings.json'
    with patch('ai_broadcaster.desktop.load_settings',side_effect=lambda:load_settings(path)),patch('ai_broadcaster.desktop.save_settings',side_effect=lambda data:save_settings(data,path)),patch('socket.socket.connect',side_effect=AssertionError('network')):
        app=AistingApp()
        try:
            app.update()
            app._tab_nav.set('캐릭터 입력 확인')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(),'text')=='캐릭터 입력 확인'
            assert '미실행' in app._persona_input_status.get()
            app._run_persona_input_review()
            assert '통과' in app._persona_input_status.get()
            assert '9/100' in app._persona_input_text.get('1.0','end')
            assert not path.exists()
            print('GUI persona input smoke: PASS')
        finally:
            app.destroy()
