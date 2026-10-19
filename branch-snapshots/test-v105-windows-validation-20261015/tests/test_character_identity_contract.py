"""Character creation is one-time, durable, and distinct from avatar selection.

No cloud, Windows account, external platforms or real-person data required.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.offline_settings import (
    DEFAULTS, active_persona, load_settings, save_settings,
)


class CharacterIdentityContract(unittest.TestCase):
    def test_created_character_survives_relaunch_and_unrelated_avatar_changes(self):
        with tempfile.TemporaryDirectory(prefix="aisting-character-once-") as folder:
            path = Path(folder) / "settings.json"
            settings = deepcopy(DEFAULTS)
            settings["persona_mode"] = "custom"
            settings["persona"] = {
                "name": "한번만만든방송인",
                "style": "차분하게 말해요",
                "character": "친절하고 기억력이 좋은 AI",
            }
            save_settings(settings, path)
            created = active_persona(load_settings(path))
            self.assertEqual(created["name"], "한번만만든방송인")
            for avatar in ("2d", "3d", "undecided", "2d"):
                reloaded = load_settings(path)
                reloaded["avatar"] = avatar
                save_settings(reloaded, path)
                self.assertEqual(active_persona(load_settings(path)), created)

    def test_unsaved_draft_cannot_change_active_character(self):
        with tempfile.TemporaryDirectory(prefix="aisting-character-draft-") as folder:
            path = Path(folder) / "settings.json"
            identity = deepcopy(DEFAULTS)
            identity["persona_mode"] = "custom"
            identity["persona"] = {
                "name": "고정캐릭터", "style": "고정말투", "character": "고정성격"
            }
            save_settings(identity, path)
            draft = deepcopy(load_settings(path))
            draft["persona"]["name"] = "아직저장안한초안"
            self.assertEqual(active_persona(load_settings(path))["name"], "고정캐릭터")

    def test_desktop_never_uses_unsaved_entry_as_active_character(self):
        source = (ROOT / "src/ai_broadcaster/desktop.py").read_text(encoding="utf-8")
        start = source.index("    def _current_persona(self)")
        end = source.index("    def _persona_changed", start)
        active = source[start:end]
        self.assertIn("return active_persona(self.settings)", active)
        self.assertIn("def _save_character_identity", active)
        general = source[source.index("    def _save(self)"):source.index("    def _build_rehearsal", source.index("    def _save(self)"))]
        self.assertIn('data["persona_mode"] = self.settings["persona_mode"]', general)
        self.assertIn('data["persona"] = deepcopy(self.settings["persona"])', general)
        self.assertNotIn('PERSONA_MODES[self._persona_mode.get()]', general)

    def test_3d_avatar_is_not_the_personality(self):
        identity = deepcopy(DEFAULTS)
        identity["persona_mode"] = "custom"
        identity["persona"] = {
            "name": "고정캐릭터", "style": "반말", "character": "유쾌한 성격"
        }
        first = active_persona(identity)
        identity["avatar"] = "3d"
        self.assertEqual(active_persona(identity), first)
        self.assertEqual(identity["avatar"], "3d")


if __name__ == "__main__":
    unittest.main()
