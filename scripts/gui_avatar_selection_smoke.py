"""가상 화면/Xvfb 또는 Windows GUI에서 8단계 아바타 형태 저장·동작 검증."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings,save_settings


def main():
    with tempfile.TemporaryDirectory() as temp, patch('socket.create_connection') as network:
        path=Path(temp)/'settings.json'
        with patch('ai_broadcaster.desktop.load_settings',side_effect=lambda: load_settings(path)), \
             patch('ai_broadcaster.desktop.save_settings',side_effect=lambda x: save_settings(x,path)):
            app=AistingApp()
            try:
                app.update()
                assert app._avatar.get()=='미정'
                assert '선택과 무관한' in app._avatar_tab_info.get()
                app._open_avatar_capture()
                app.update()
                assert app._avatar_capture_window is not None
                app._avatar.set('3D')
                app.update()
                assert app._avatar_capture_window is None,'3D로 바꾼 뒤 기존 2D 캡처 창은 닫아야 함'
                assert str(app._avatar_open_button.cget('state'))=='disabled'
                assert 'VRM' in app._avatar_tab_info.get()
                assert '미설치' in app._avatar_tab_info.get()
                app._open_avatar_capture()
                assert app._avatar_capture_window is None
                app._save()
                assert load_settings(path)['avatar']=='3d'
                app._avatar.set('2D')
                app.update()
                assert str(app._avatar_open_button.cget('state'))=='normal'
                app._open_avatar_capture()
                app.update()
                assert app._avatar_capture_window is not None
                app._save()
                assert load_settings(path)['avatar']=='2d'
                app._close_avatar_capture()
                app._avatar.set('미정')
                app._save()
                assert load_settings(path)['avatar']=='undecided'
                network.assert_not_called()
            finally:
                app._shutdown()
            app=AistingApp()
            try:
                app.update()
                assert app._avatar.get()=='미정'
                app._avatar.set('3D')
                app._save()
                network.assert_not_called()
            finally:
                app._shutdown()
            app=AistingApp()
            try:
                app.update()
                assert app._avatar.get()=='3D'
                assert str(app._avatar_open_button.cget('state'))=='disabled'
                network.assert_not_called()
            finally:
                app._shutdown()
    print('GUI 아바타 미정/2D/3D 전환, 샘플 차단, 별도 창 종료, 저장 및 복원: 통과')


if __name__=='__main__':
    main()
