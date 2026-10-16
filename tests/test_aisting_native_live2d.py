"""Tests for the existing Windows EXE's native Live2D window path (no real launch)."""
import sys
from pathlib import Path
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster import original_plan_frontend as viewer


class NativeLive2DTests(unittest.TestCase):
    def setUp(self):
        self.good = viewer.OfficialFrontendReadiness(
            viewer.OFFICIAL_URL, Path("C:/Open-LLM-VTuber/frontend/index.html"),
            200, "text/html")

    def test_explicit_consent_required(self):
        with self.assertRaises(PermissionError):
            viewer.open_prechecked_frontend(self.good)

    def test_remote_web_page_refused(self):
        other = viewer.OfficialFrontendReadiness(
            "https://example.org/", Path("x"), 200, "text/html")
        with self.assertRaises(viewer.FrontendUnavailable):
            viewer.open_prechecked_frontend(other, operator_approved=True)

    def test_redirect_refused(self):
        other = viewer.OfficialFrontendReadiness(
            viewer.OFFICIAL_URL, Path("x"), 301, "text/html")
        with self.assertRaises(viewer.FrontendUnavailable):
            viewer.open_prechecked_frontend(other, operator_approved=True)

    def test_windows_only(self):
        with patch.object(viewer.sys, "platform", "linux"):
            with self.assertRaises(viewer.FrontendUnavailable):
                viewer.open_prechecked_frontend(self.good, operator_approved=True)

    def test_missing_viewer_not_installed_automatically(self):
        with patch.object(viewer.sys, "platform", "win32"), patch.object(
            viewer.importlib.util, "find_spec", return_value=None
        ):
            with self.assertRaises(viewer.FrontendUnavailable):
                viewer.open_prechecked_frontend(self.good, operator_approved=True)

    def test_same_application_child_not_external_browser(self):
        with patch.object(viewer.sys, "platform", "win32"), patch.object(
            viewer.importlib.util, "find_spec", return_value=object()
        ), patch.object(
            viewer, "native_viewer_command",
            return_value=["AISTING.exe", "--aisting-live2d-viewer"]
        ), patch.object(
            viewer.subprocess, "Popen", return_value=types.SimpleNamespace(pid=21)
        ) as popen:
            self.assertTrue(viewer.open_prechecked_frontend(self.good, operator_approved=True))
            popen.assert_called_once_with(
                ["AISTING.exe", "--aisting-live2d-viewer"], close_fds=True)

    def test_child_requires_approval(self):
        with self.assertRaises(PermissionError):
            viewer.run_native_live2d_window()

    def test_child_uses_native_edge_webview2(self):
        fake = types.SimpleNamespace(create_window=lambda *a, **k: None,
                                     start=lambda **k: None)
        with patch.object(viewer, "_check_windows_native_dependencies"), patch.dict(
            sys.modules, {"webview": fake}
        ), patch.object(fake, "create_window") as create, patch.object(
            fake, "start"
        ) as start:
            viewer.run_native_live2d_window(operator_approved=True)
            self.assertEqual(create.call_args.args[1], viewer.OFFICIAL_URL)
            start.assert_called_once_with(
                gui="edgechromium", debug=False, private_mode=True)


if __name__ == "__main__":
    unittest.main()
