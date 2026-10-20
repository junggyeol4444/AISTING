"""Bound the visible native Tk transcript without altering FIFO or SQLite."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop_chat_tab import LocalChatTab


class FakeText:
    def __init__(self, lines=1):
        self.lines = lines
        self.written = []
        self.states = []
        self.trimmed = []
        self.scrolled = []
    def configure(self, **options):
        self.states.append(options)
    def insert(self, location, data):
        self.written.append((location, data))
        self.lines += data.count("\n")
    def index(self, location):
        assert location == "end-1c"
        return f"{self.lines}.0"
    def delete(self, start, stop):
        self.trimmed.append((start, stop))
        self.lines -= 4000
    def see(self, location):
        self.scrolled.append(location)


class NativeTranscriptWindowTests(unittest.TestCase):
    def test_under_limit_keeps_every_korean_duplicate_and_input_order(self):
        view = FakeText(lines=1)
        tab = type("FakeTab", (), {"_dialog": view})()
        for text in ("안녕", "안녕", "다른 플랫폼: 🙂"):
            LocalChatTab._append(tab, text)
        self.assertEqual([item[1] for item in view.written],
                         ["안녕\n\n", "안녕\n\n", "다른 플랫폼: 🙂\n\n"])
        self.assertFalse(view.trimmed)
        self.assertEqual(view.states[-1], {"state":"disabled"})

    def test_long_window_trims_only_tk_display_not_any_fifo_item(self):
        view = FakeText(lines=11999)
        tab = type("FakeTab", (), {"_dialog": view})()
        LocalChatTab._append(tab, "새 채팅")
        self.assertEqual(view.trimmed, [("1.0", "4001.0")])
        self.assertEqual(view.written[-1], ("end", "새 채팅\n\n"))
        self.assertLessEqual(view.lines, 12000)
        self.assertEqual(view.scrolled[-1], "end")
        self.assertEqual(view.states[-1], {"state":"disabled"})

    def test_display_is_disabled_even_on_widget_error(self):
        class Broken(FakeText):
            def insert(self, location, data):
                raise RuntimeError("Tk widget vanished")
        view = Broken()
        tab = type("FakeTab", (), {"_dialog": view})()
        with self.assertRaisesRegex(RuntimeError, "widget vanished"):
            LocalChatTab._append(tab, "보호")
        self.assertEqual(view.states[-1], {"state":"disabled"})


if __name__ == "__main__":
    unittest.main()
