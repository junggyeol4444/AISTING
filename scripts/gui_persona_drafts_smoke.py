"""Tkinter 창에서 예시 초안 적용/수정/저장/기본 복귀와 미리보기 무통신 확인."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import DEFAULTS, load_settings, save_settings
from ai_broadcaster.persona_drafts import EXAMPLE_DRAFTS


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'settings.json'
        with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(path)), \
             patch('ai_broadcaster.desktop.save_settings', side_effect=lambda value: save_settings(value, path)), \
             patch('socket.create_connection') as network:
            app = AistingApp()
            try:
                app.update()
                assert app._persona_mode.get() == '기본 캐릭터'
                initial = {key: field.get() for key, field in app._persona.items()}
                assert initial == DEFAULTS['persona']
                assert '아이스팅' in app._persona_preview.get()
                assert '내 캐릭터' not in app._persona_preview.get()
                app._persona_draft_example.set(list(EXAMPLE_DRAFTS)[0])
                app._apply_persona_example()
                app.update()
                assert app._persona_mode.get() == '직접 만들기'
                assert app._persona['name'].get() == '아이스팅'
                assert app._persona['style'].get() == EXAMPLE_DRAFTS[list(EXAMPLE_DRAFTS)[0]].speech_style
                app._persona['name'].delete(0,'end')
                app._persona['name'].insert(0,'나만의 캐릭터')
                app._persona['character'].delete(0,'end')
                app._persona['character'].insert(0,'내가 정한 성격')
                app._persona_changed()
                assert '내가 정한 성격' in app._persona_preview.get()
                app._save()
                saved = load_settings(path)
                assert saved['persona_mode'] == 'custom'
                assert saved['persona']['name'] == '나만의 캐릭터'
                assert saved['persona']['character'] == '내가 정한 성격'
                # Default mode must not overwrite user draft.
                app._persona_mode.set('기본 캐릭터')
                app.update()
                assert app._current_persona()['name'] == '아이스팅'
                assert app._persona['name'].get() == '나만의 캐릭터'
                app._save()
                assert load_settings(path)['persona']['name'] == '나만의 캐릭터'
                assert load_settings(path)['persona_mode'] == 'default'
                # 화면 높이보다 설정 항목이 커져도 저장 버튼을 스크롤로 찾을 수 있어야 한다.
                app._settings_canvas.yview_moveto(1.0)
                app.update()
                from tkinter import ttk
                save_buttons = []
                def visit(widget):
                    if isinstance(widget, ttk.Button) and widget.cget('text') == '설정 PC에 저장':
                        save_buttons.append(widget)
                    for child in widget.winfo_children():
                        visit(child)
                visit(app)
                assert len(save_buttons) == 1
                save_button = save_buttons[0]
                assert save_button.winfo_width() > 50
                assert 0 <= save_button.winfo_rooty() < app.winfo_rooty() + app.winfo_height()
                network.assert_not_called()
                print('GUI 성격·말투 예시/수정/저장/기본 전환/스크롤/무통신: 통과')
            finally:
                app._shutdown()


if __name__ == '__main__':
    main()
