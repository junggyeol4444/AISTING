import sys,tempfile
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
            app.update();app._tab_nav.set('말투 일관성 점검');app._tab_nav_widget.event_generate('<<ComboboxSelected>>');app.update()
            assert app._tabs.tab(app._tabs.select(),'text')=='말투 일관성 점검'
            app._style_samples.insert('1.0','안녕하세요\n안녕하세요')
            app._run_style_consistency();assert '통과' in app._style_status.get()
            app._style_samples.insert('end','\n ');app._run_style_consistency();assert '실패' in app._style_status.get()
            assert not path.exists()
            print('GUI stage33 smoke: PASS')
        finally:app.destroy()
