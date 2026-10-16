"""7단계: 100% 오프라인 목소리 선택 방식, 기본값과 동의 보호, 이전 설정 호환."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.offline_settings import (
    DEFAULTS, VOICES, load_settings, save_settings,
    validate_settings, validate_voice_profile,
)
from ai_broadcaster.offline_tts import KoreanVoice
from ai_broadcaster.voice_choices import describe_voice_source, preferred_installed_voice
from ai_broadcaster.requirements import load_json, validate, status


class TestVoiceSelection(unittest.TestCase):
    def test_all_runtime_choices_including_undecided(self):
        self.assertEqual(set(VOICES.values()), {
            "undecided", "windows_system", "own_recording",
            "consented_recording", "licensed_recording",
        })
        self.assertEqual(DEFAULTS["voice"], "undecided")
        for code in VOICES.values():
            settings = copy.deepcopy(DEFAULTS)
            settings["voice"] = code
            self.assertEqual(validate_settings(settings)["voice"], code)

    def test_user_does_not_need_to_choose_now(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "settings.json"
            self.assertEqual(load_settings(target), DEFAULTS)
            save_settings(DEFAULTS, target)
            self.assertEqual(load_settings(target)["voice"], "undecided")

    def test_all_voice_sources_described_as_planned_or_system(self):
        self.assertIn("Windows", describe_voice_source("windows_system"))
        for code in ("own_recording", "consented_recording", "licensed_recording"):
            self.assertIn("하지 않아", describe_voice_source(code))
        with self.assertRaises(ValueError):
            describe_voice_source("online_paid")

    def test_rate_volume_and_name_are_saved_locally(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            data = copy.deepcopy(DEFAULTS)
            data["voice"] = "windows_system"
            data["voice_profile"] = {
                "installed_voice_name": "Microsoft Heami Desktop",
                "rate": -2, "volume": 62,
            }
            save_settings(data, path)
            restored = load_settings(path)
            self.assertEqual(restored, data)
            self.assertNotIn("github", path.read_text(encoding="utf-8").lower())
            self.assertFalse(restored["streaming_enabled"])
            self.assertFalse(restored["scheduled_execution"])

    def test_default_voice_is_optional_even_if_windows_selected(self):
        settings = copy.deepcopy(DEFAULTS)
        settings["voice"] = "windows_system"
        self.assertEqual(validate_settings(settings)["voice_profile"]["installed_voice_name"], "")

    def test_validate_voice_profile_rejects_invalid_values(self):
        bad_profiles = [
            {}, None, [], {"installed_voice_name": "X", "rate": 0, "volume": 85, "extra": 0},
            {"installed_voice_name": "\x00", "rate": 0, "volume": 85},
            {"installed_voice_name": "x\n", "rate": 0, "volume": 85},
            {"installed_voice_name": "x" * 161, "rate": 0, "volume": 85},
            {"installed_voice_name": None, "rate": 0, "volume": 85},
            {"installed_voice_name": "A", "rate": -5, "volume": 85},
            {"installed_voice_name": "A", "rate": 5, "volume": 85},
            {"installed_voice_name": "A", "rate": 0, "volume": -1},
            {"installed_voice_name": "A", "rate": 0, "volume": 101},
            {"installed_voice_name": "A", "rate": True, "volume": 85},
            {"installed_voice_name": "A", "rate": 0, "volume": False},
        ]
        for bad in bad_profiles:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_voice_profile(bad)

    def test_profile_validation_is_pure(self):
        profile = {"installed_voice_name": "한국어 목소리", "rate": 4, "volume": 0}
        validated = validate_voice_profile(profile)
        validated["rate"] = -4
        self.assertEqual(profile["rate"], 4)

    def test_legacy_v07_and_v05_preserve_other_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            data = copy.deepcopy(DEFAULTS)
            data["platforms"] = ["chzzk", "youtube"]
            data["content"] = "both"
            data["persona"]["name"] = "내 방송인"
            data["persona_mode"] = "custom"
            data.pop("voice_profile")
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            upgraded = load_settings(path)
            self.assertEqual(upgraded["platforms"], ["chzzk", "youtube"])
            self.assertEqual(upgraded["content"], "both")
            self.assertEqual(upgraded["persona"]["name"], "내 방송인")
            self.assertEqual(upgraded["voice_profile"], DEFAULTS["voice_profile"])
            self.assertNotIn("voice_profile", json.loads(path.read_text()))  # 로드 자체는 파일 변경 없음
            data.pop("persona_mode")  # legacy v05: 둘 다 없는 파일
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            older = load_settings(path)
            self.assertEqual(older["persona_mode"], "custom")
            self.assertEqual(older["persona"]["name"], "내 방송인")
            self.assertEqual(older["voice_profile"], DEFAULTS["voice_profile"])

    def test_malformed_legacy_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            data = copy.deepcopy(DEFAULTS)
            data.pop("voice_profile")
            data["extra_unknown"] = True
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_settings(path)

    def test_saved_korean_voice_restores_exact_name_only(self):
        voices = [KoreanVoice("Heami"), KoreanVoice("새 목소리")]
        self.assertEqual(preferred_installed_voice("Heami", voices), voices[0])
        self.assertIsNone(preferred_installed_voice("No longer installed", voices))
        self.assertIsNone(preferred_installed_voice("", voices))
        with self.assertRaises(TypeError):
            preferred_installed_voice(None, voices)
        with self.assertRaises(TypeError):
            preferred_installed_voice("Heami", ["Heami"])

    def test_non_windows_sources_are_not_cloning_permission(self):
        for source in ("own_recording", "consented_recording", "licensed_recording"):
            value = copy.deepcopy(DEFAULTS)
            value["voice"] = source
            self.assertFalse(value["external_publish_enabled"])
            self.assertFalse(value["streaming_enabled"])
            self.assertFalse(value["scheduled_execution"])
            self.assertEqual(validate_settings(value)["voice"], source)

    def test_bad_voice_policy_rejected(self):
        value = copy.deepcopy(DEFAULTS)
        value["voice"] = "auto_clone_anyone"
        with self.assertRaises(ValueError):
            validate_settings(value)

    def test_roadmap_step_7_completed_without_preselection(self):
        config = load_json(ROOT / "config" / "requirements.json")
        roadmap = load_json(ROOT / "config" / "roadmap.json")
        self.assertEqual(validate(config, roadmap), [])
        self.assertEqual((status(roadmap)["completed"], status(roadmap)["current"]["number"]), (9, 10))
        self.assertEqual(config["operator_decisions"]["voice_source_and_consent"],
                         "runtime_optional_source_no_clone_without_permission")
        altered = copy.deepcopy(config)
        altered["operator_decisions"]["voice_source_and_consent"] = "clone_automatically"
        self.assertTrue(any("목소리" in item for item in validate(altered, roadmap)))
        road = copy.deepcopy(roadmap)
        road["steps"][6]["status"] = "pending"
        self.assertTrue(any("7단계" in item for item in validate(config, road)))

    def test_non_windows_voice_methods_cannot_automatically_clone_or_play_tts(self):
        gui = (ROOT / "src" / "ai_broadcaster" / "desktop.py").read_text(encoding="utf-8")
        self.assertIn('self._voice.get() != "Windows 무료 음성"', gui)
        self.assertIn('self._auto_read.set(False)', gui)
        self.assertIn('self._speech_pending.clear()', gui)

    def test_exe_gui_has_voice_choice_and_explicit_save(self):
        gui = (ROOT / "src" / "ai_broadcaster" / "desktop.py").read_text(encoding="utf-8")
        self.assertIn("self._voice_preferred_name", gui)
        self.assertIn("self._voice_rate", gui)
        self.assertIn("self._voice_volume", gui)
        self.assertIn("preferred_installed_voice", gui)
        self.assertIn("self._voice_source_changed", gui)
        self.assertIn("save_broadcast_without_persona(self.settings, data)", gui)
        self.assertIn("def _save_character_identity(self)", gui)
        self.assertIn("commit_character_identity(self.settings, mode, draft)", gui)
        self.assertNotIn("StartStream", gui)
        self.assertNotIn("auto_clone", gui)


if __name__ == "__main__":
    unittest.main()
