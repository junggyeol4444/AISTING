"""Operator-facing Tk UI contract: no giant tab strip, persistent character editor.

Runs on an isolated local profile. Never uses live accounts, streaming or models.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import DEFAULTS, load_settings, save_settings


def descendants(widget):
    yield widget
    for child in widget.winfo_children():
        yield from descendants(child)


def run():
    with tempfile.TemporaryDirectory(prefix="aisting-operator-ui-") as temp:
        path = Path(temp) / "settings.json"
        with patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(path)), \
             patch("ai_broadcaster.desktop.save_settings", side_effect=lambda value: save_settings(value, path)), \
             patch("socket.create_connection", side_effect=AssertionError("network not allowed")):
            app = AistingApp()
            try:
                app.update()
                assert app._tabs.cget("style") == "Operator.TNotebook"
                from tkinter import ttk
                assert not ttk.Style(app).layout("Operator.TNotebook.Tab"), \
                    "100+ development tabs are still visible in the operator window"
                labels = [app._tabs.tab(t, "text") for t in app._tabs.tabs()]
                for required in ("방송 설정", "내 캐릭터", "시청자 채팅 연습",
                                 "무료 한국어 음성", "아바타 미리보기", "최종 기능 검수·승인 대기"):
                    assert required in labels
                setting_tab = app.nametowidget(app._tabs.tabs()[labels.index("방송 설정")])
                character_tab = app.nametowidget(app._tabs.tabs()[labels.index("내 캐릭터")])
                entry_ids = {str(e) for e in app._persona.values()}
                assert entry_ids <= {str(child) for child in descendants(character_tab)}
                assert not entry_ids.intersection({str(child) for child in descendants(setting_tab)})
                assert app._current_persona()["name"] == DEFAULTS["persona"]["name"]
                app._navigate_to("내 캐릭터")
                assert app._tab_nav.get() == "내 캐릭터"
                app._persona_mode.set("직접 만들기")
                identity = {
                    "name": "최초만든AI",
                    "style": "부드러운 한국어",
                    "character": "신중하고 따뜻한 성격",
                }
                for k, value in identity.items():
                    app._persona[k].delete(0, "end")
                    app._persona[k].insert(0, value)
                assert app._current_persona()["name"] == DEFAULTS["persona"]["name"]
                app._save_character_identity()
                assert app._current_persona() == identity
                app._navigate_to("방송 설정")
                app._content.set("수다 + 게임")
                app._save()
                assert load_settings(path)["persona"] == identity
                print("OPERATOR UI: uncluttered navigation + separate character editor PASS")
            finally:
                app._shutdown()
            app = AistingApp()
            try:
                app.update()
                assert app._current_persona() == identity
                assert "최초만든AI" in app._saved_character_status.get()
                app._navigate_to("시청자 채팅 연습")
                assert app._tab_nav.get() == "시청자 채팅 연습"
                app._navigate_to("방송 설정")
                assert app._current_persona() == identity
                print("OPERATOR UI: character restored without re-entering any field PASS")
            finally:
                app._shutdown()


if __name__ == "__main__":
    run()
