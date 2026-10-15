import sys, tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings,save_settings
with tempfile.TemporaryDirectory() as temp:
    path=Path(temp)/'settings.json'
    with patch('ai_broadcaster.desktop.load_settings',side_effect=lambda:load_settings(path)),patch('ai_broadcaster.desktop.save_settings',side_effect=lambda data:save_settings(data,path)),patch('socket.socket.connect',side_effect=AssertionError('network')):
        app=AistingApp()
        try:
            app.update();app._tab_nav.set('반응 방향 설정');app._tab_nav_widget.event_generate('<<ComboboxSelected>>');app.update()
            assert app._tabs.tab(app._tabs.select(),'text')=='반응 방향 설정'
            app._reaction_inputs['일반 채팅'].insert(0,'반갑게 인사')
            app._run_reaction_directions();assert '통과' in app._reaction_status.get()
            assert '반갑게 인사' in app._reaction_result.get('1.0','end')
            app._reaction_inputs['일반 채팅'].insert('end','x'*501)
            app._run_reaction_directions();assert '실패' in app._reaction_status.get()
            assert not path.exists()
            print('GUI stage34 smoke: PASS')
        finally:app.destroy()
