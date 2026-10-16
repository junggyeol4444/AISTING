"""Regression checks for operator settings save safety (offline only)."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.offline_settings import DEFAULTS, load_settings, save_settings
from ai_broadcaster.original_plan_persona_store import commit_character_identity


class SettingsAtomicityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "config" / "settings.json"
        self.config = copy.deepcopy(DEFAULTS)

    def test_existing_legacy_tmp_not_overwritten(self):
        self.path.parent.mkdir(parents=True)
        legacy = self.path.with_suffix(".tmp")
        legacy.write_text("operator's previous temporary data", encoding="utf-8")
        save_settings(self.config, self.path)
        self.assertEqual(legacy.read_text(encoding="utf-8"), "operator's previous temporary data")
        self.assertEqual(load_settings(self.path), self.config)

    def test_failed_replace_preserves_previous_settings_and_removes_new_temp(self):
        save_settings(self.config, self.path)
        before = self.path.read_bytes()
        new = copy.deepcopy(self.config)
        new["content"] = "game"
        with patch("ai_broadcaster.offline_settings.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaisesRegex(OSError, "disk failure"):
                save_settings(new, self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(load_settings(self.path), self.config)
        self.assertFalse(list(self.path.parent.glob("*.tmp")))
        self.assertTrue((self.path.parent / ".settings.json.aisting-write.lock").is_file())
        backups = list(self.path.parent.glob("settings.json.before-broadcast-*.bak"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before)

    def test_existing_legacy_tmp_symlink_target_untouched(self):
        self.path.parent.mkdir(parents=True)
        important = Path(self.temp.name) / "important.txt"
        important.write_text("preserve me", encoding="utf-8")
        legacy = self.path.with_suffix(".tmp")
        try:
            legacy.symlink_to(important)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        save_settings(self.config, self.path)
        self.assertTrue(legacy.is_symlink())
        self.assertEqual(important.read_text(encoding="utf-8"), "preserve me")
        self.assertEqual(load_settings(self.path), self.config)

    def test_successful_atomic_save_preserves_selection_and_no_leftover(self):
        self.config["platforms"] = ["youtube", "chzzk"]
        self.config["persona_mode"] = "custom"
        self.config["persona"]["name"] = "테스트"
        save_settings(self.config, self.path)
        draft_safe = load_settings(self.path)
        self.assertEqual(draft_safe["persona"], DEFAULTS["persona"])
        commit_character_identity(draft_safe, self.config["persona_mode"],
                                  self.config["persona"], path=self.path)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), self.config)
        self.assertEqual(load_settings(self.path), self.config)
        self.assertFalse(list(self.path.parent.glob("*.tmp")))
        self.assertTrue((self.path.parent / ".settings.json.aisting-write.lock").is_file())
        self.assertEqual(len(list(self.path.parent.glob("settings.json.before-character-*.bak"))), 1)
