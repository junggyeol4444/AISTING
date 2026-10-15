"""Xvfb/Windows 화면에서 캐릭터 2가지 전환·로컬 저장·아바타 이름 확인."""
from __future__ import annotations

import tempfile
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import DEFAULTS, load_settings, save_settings


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'settings.json'
        with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(path)), \
             patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, path)), \
             patch('socket.create_connection') as remote:
            app = AistingApp()
            try:
                app.update()
                assert app._persona_mode.get() == '기본 캐릭터'
                assert app._current_persona()['name'] == '아이스팅'
                assert str(app._persona['name'].cget('state')) == 'disabled'

                app._persona_mode.set('직접 만들기')
                app.update()
                assert str(app._persona['name'].cget('state')) == 'normal'
                app._persona['name'].delete(0,'end')
                app._persona['name'].insert(0,'은별')
                app._persona['style'].delete(0,'end')
                app._persona['style'].insert(0,'친절한 한국어')
                app._persona['character'].delete(0,'end')
                app._persona['character'].insert(0,'별을 좋아하는 AI')
                assert app._current_persona()['name'] == '아이스팅'
                app._save_character_identity()
                app._save()
                saved = load_settings(path)
                assert saved['persona_mode'] == 'custom'
                assert saved['persona']['name'] == '은별'
                assert app._current_persona()['name'] == '은별'

                app._draw_avatar_canvases()
                text_nodes = [app._canvas.itemcget(i, 'text') for i in app._canvas.find_all()
                              if app._canvas.type(i) == 'text']
                assert '은별' in ' '.join(text_nodes), text_nodes

                app._persona_mode.set('기본 캐릭터')
                app.update()
                assert app._current_persona()['name'] == '은별', 'Uncommitted default-mode draft must not switch identity'
                assert app._persona['name'].get() == '은별'
                app._save_character_identity()
                assert app._current_persona()['name'] == '아이스팅'
                app._save()
                assert load_settings(path)['persona_mode'] == 'default'
                assert load_settings(path)['persona']['name'] == '은별'
                app._persona_mode.set('직접 만들기')
                app.update()
                assert app._persona['name'].get() == '은별'
                assert app._current_persona()['name'] == '아이스팅'
                app._save_character_identity()
                assert app._current_persona()['name'] == '은별'
                assert not load_settings(path)['streaming_enabled']
                assert not load_settings(path)['scheduled_execution']
                remote.assert_not_called()
                print('GUI 캐릭터 기본값/직접 만들기/아바타 이름/저장/초안 보존: 통과')
            finally:
                app._shutdown()


if __name__ == '__main__':
    main()
