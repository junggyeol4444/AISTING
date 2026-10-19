"""Verify the existing Windows GUI's confirmed character reaches local AI.

No model request, user file mutation or speech occurs in this regression test.
"""
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster import desktop_chat, offline_settings


class ConfirmedPersonaLocalChatTests(unittest.TestCase):
    def test_saved_gui_character_used_in_real_ollama_prompt_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            stored = deepcopy(offline_settings.DEFAULTS)
            stored["persona_mode"] = "custom"
            stored["persona"] = {
                "name": "확정된시청자방송인", "style": "차분한 한국어 존댓말",
                "character": "호기심과 배려를 가진 인물",
            }
            path.write_text(json.dumps(stored, ensure_ascii=False), encoding="utf-8")
            # Draft edits that have not been saved must not change AI identity.
            unsaved_draft = {"name": "미확정 새이름", "style": "초안", "character": "초안"}
            observed = []
            class NoNetworkModel:
                def generate(self, message):
                    observed.append(message.sender)
                    return "한국어 응답"
                def on_delivered(self, message, reply):
                    pass
            def model_factory(cfg, user_settings, memory):
                observed.append(deepcopy(user_settings["persona"]))
                return NoNetworkModel()
            class NoDiskMemory:
                def count(self):
                    return 1
            with patch.object(desktop_chat, "load_gui_settings",
                              side_effect=lambda: offline_settings.load_settings(path)), \
                 patch.object(desktop_chat, "LocalOllamaReplyGenerator",
                              side_effect=model_factory), \
                 patch.object(desktop_chat, "ConversationMemory",
                              return_value=NoDiskMemory()):
                result = desktop_chat.run_local_chat(
                    "local-model", "안녕", sender="[트위치] viewer123",
                    use_committed_gui_character=True)
            self.assertEqual(result.reply, "한국어 응답")
            self.assertEqual(observed[0]["name"], stored["persona"]["name"])
            self.assertEqual(observed[0]["traits"], stored["persona"]["character"])
            self.assertEqual(observed[0]["speech_style"], stored["persona"]["style"])
            self.assertNotEqual(observed[0]["name"], unsaved_draft["name"])
            self.assertEqual(observed[1], "[트위치] viewer123")

    def test_existing_non_gui_local_chat_does_not_override_legacy_persona(self):
        observed = []
        class NoNetworkModel:
            def generate(self, message):
                return "대답"
            def on_delivered(self, message, reply):
                pass
        def model_factory(cfg, setting, memory):
            observed.append(setting["persona"]["name"])
            return NoNetworkModel()
        class FakeMemory:
            def count(self):
                return 1
        with patch.object(desktop_chat, "load_gui_settings",
                          side_effect=AssertionError("unexpected GUI setting access")), \
             patch.object(desktop_chat, "LocalOllamaReplyGenerator",
                          side_effect=model_factory), \
             patch.object(desktop_chat, "ConversationMemory",
                          return_value=FakeMemory()):
            self.assertEqual(desktop_chat.run_local_chat(
                "local-model", "hello").reply, "대답")
        self.assertEqual(observed, ["아이스팅"])


if __name__ == "__main__":
    unittest.main()
