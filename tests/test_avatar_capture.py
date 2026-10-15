"""독립 로컬 아바타 출력의 안전성/프레임 계산 테스트 (창 서버 없이 실행)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.avatar_renderer import AvatarFrame, BACKGROUND_COLORS, draw_avatar


class TestAvatarFrame(unittest.TestCase):
    def test_still_idle_with_closed_mouth(self):
        for i in range(50):
            self.assertEqual(AvatarFrame("아이스팅", False, i).mouth, 0)

    def test_speaking_changes_mouth_without_audio_samples(self):
        self.assertEqual([AvatarFrame("아이스팅", True, i).mouth for i in range(8)],
                         [1, 2, 3, 2] * 2)

    def test_blink_has_periodic_pattern(self):
        self.assertTrue(AvatarFrame("아이스팅", False, 0).blink)
        self.assertTrue(AvatarFrame("아이스팅", False, 1).blink)
        self.assertFalse(AvatarFrame("아이스팅", False, 2).blink)
        self.assertTrue(AvatarFrame("아이스팅", False, 45).blink)

    def test_long_name_only_visually_truncated(self):
        frame = AvatarFrame("가"*80, False, 0)
        self.assertEqual(frame.display_name, "가"*24)
        self.assertEqual(len(frame.name), 80)

    def test_blank_name_fallback(self):
        self.assertEqual(AvatarFrame(" ", False, 0).display_name, "아이스팅")

    def test_only_declared_local_backgrounds_allowed(self):
        self.assertIn("남색 스튜디오", BACKGROUND_COLORS)
        self.assertIn("초록색 배경", BACKGROUND_COLORS)
        with self.assertRaises(ValueError):
            AvatarFrame("아이스팅", False, 0, background="https://example.org")

    def test_invalid_frame_state_types(self):
        for args in (("a", "yes", 0), ("a", True, -1), ("a", True, True), (None, False, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                AvatarFrame(*args)

    def test_speaking_same_frame_for_both_windows(self):
        main = AvatarFrame("아이스팅", True, 12)
        detached = AvatarFrame("아이스팅", True, 12, background="초록색 배경")
        self.assertEqual(main.mouth, detached.mouth)
        self.assertEqual(main.blink, detached.blink)
        self.assertEqual(main.display_name, detached.display_name)

    def test_draw_does_not_use_network_or_save_files(self):
        canvas = Mock()
        draw_avatar(canvas, AvatarFrame("나의 캐릭터", True, 2, "초록색 배경"))
        canvas.configure.assert_called_once_with(bg=BACKGROUND_COLORS["초록색 배경"])
        canvas.delete.assert_called_once_with("all")
        self.assertGreater(canvas.create_oval.call_count, 5)
        self.assertEqual(canvas.create_text.call_args.kwargs["text"], "나의 캐릭터")

    def test_2d_sample_not_claimed_precise_lipsync(self):
        code = (ROOT / "src" / "ai_broadcaster" / "avatar_renderer.py").read_text(encoding="utf-8")
        self.assertIn("음소", code)
        self.assertNotIn("librosa", code)
        self.assertNotIn("sounddevice", code)

    def test_no_external_obs_automation_or_browser(self):
        code = (ROOT / "src" / "ai_broadcaster" / "desktop.py").read_text(encoding="utf-8")
        self.assertIn("tk.Toplevel(self)", code)
        self.assertIn("command=self._open_avatar_capture", code)
        self.assertIn('win.protocol("WM_DELETE_WINDOW", self._close_avatar_capture)', code)
        self.assertNotIn("webbrowser.open", code)
        self.assertNotIn("StartStream", code)

    def test_local_runtime_does_not_require_git_workflows(self):
        code = (ROOT / "src/ai_broadcaster/desktop.py").read_text(encoding="utf-8")
        self.assertFalse(any((ROOT / "src").rglob(".github")))
        self.assertNotIn("git push", code.lower())
        self.assertNotIn("subprocess.Popen(", code)


if __name__ == "__main__":
    unittest.main()
