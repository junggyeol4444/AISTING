import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.platform_config import PlatformConfig

ROOT = Path(__file__).resolve().parents[1]


class TestPlatformConfig(unittest.TestCase):
    def test_unselected_platform_is_default(self):
        with (ROOT / "config/platform.json").open(encoding="utf-8") as f:
            p = PlatformConfig.from_dict(json.load(f))
        self.assertIsNone(p.selected_platform)
        self.assertFalse(p.external_broadcast_enabled)
        with self.assertRaises(PermissionError):
            p.assert_can_broadcast()

    def test_broadcast_requires_operator_permission(self):
        with self.assertRaises(PermissionError):
            PlatformConfig.from_dict({"selected_platform": "youtube", "external_broadcast_enabled": True})

    def test_broadcast_requires_platform(self):
        with self.assertRaises(PermissionError):
            PlatformConfig.from_dict({"operator_approved": True, "external_broadcast_enabled": True})

    def test_platform_without_approval_is_saved_not_activated(self):
        c = PlatformConfig.from_dict({"selected_platform": "chzzk"})
        self.assertEqual(c.selected_platform, "chzzk")
        with self.assertRaises(PermissionError):
            c.assert_can_broadcast()

    def test_unknown_platform_rejected(self):
        with self.assertRaises(ValueError):
            PlatformConfig.from_dict({"selected_platform": "unknown"})

    def test_explicit_approval_still_no_live_adapter(self):
        c = PlatformConfig.from_dict({"selected_platform": "twitch", "operator_approved": True, "external_broadcast_enabled": True})
        with self.assertRaises(NotImplementedError):
            c.assert_can_broadcast()

    def test_boolean_types_rejected(self):
        with self.assertRaises(ValueError):
            PlatformConfig.from_dict({"operator_approved": "yes"})


if __name__ == "__main__":
    unittest.main()
