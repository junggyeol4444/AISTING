"""AISTING existing Tk chat tab's read-only multi-platform connection safeguards."""
import queue
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop_chat_tab import LocalChatTab


class Value:
    def __init__(self, value=""):
        self.value = value
    def get(self):
        return self.value


class NativeChatRouting(unittest.TestCase):
    def fake(self):
        return SimpleNamespace(
            _closed=False, _twitch_session=None, _pipeline_busy=False,
            _busy=False, _twitch_active_workers=set(),
            _model_name=Value("local-model"),
            _official_live2d=Value(False),
            _chat_platform=Value("전체"),
            _multi_channels={key: Value()
                             for key in ("twitch", "chzzk", "soop", "youtube")},
            _twitch_channel=Value(), _youtube_api_key=Value("secret-test-api-key"),
            _results=queue.SimpleQueue(),
        )

    def test_voice_playback_failure_does_not_disclose_raw_exception(self):
        received = queue.SimpleQueue()
        obj = SimpleNamespace(_results=received,
              _voice_player=SimpleNamespace(read=lambda *args: (_ for _ in ()).throw(
                  RuntimeError("PRIVATE_VOICE_REFERENCE_PATH"))))
        LocalChatTab._read_worker(obj, "text", object())
        self.assertEqual(received.get_nowait(),
                         ("speech_error", "RuntimeError"))

    def test_memory_delete_failure_does_not_expose_local_path(self):
        shown = []
        fake = SimpleNamespace(_busy=False, _pipeline_busy=False,
                               _twitch_session=None, _twitch_active_workers=set())
        with patch("ai_broadcaster.desktop_chat_tab.messagebox.askyesno",
                   return_value=True), patch(
                   "ai_broadcaster.desktop_chat_tab.ConversationMemory.clear",
                   side_effect=OSError("PRIVATE_SQLITE_FILE_PATH")), patch(
                   "ai_broadcaster.desktop_chat_tab.messagebox.showerror",
                   side_effect=lambda *args, **kwargs: shown.append(args)):
            LocalChatTab._clear_memory(fake)
        self.assertEqual(len(shown), 1)
        self.assertNotIn("PRIVATE_SQLITE_FILE_PATH", repr(shown))

    def test_missing_channel_refuses_connect_before_any_reader(self):
        tab = self.fake()
        with patch("ai_broadcaster.desktop_chat_tab.load_settings",
                   return_value={"platforms": ["twitch", "chzzk"]}), patch(
                   "ai_broadcaster.desktop_chat_tab.MultiPlatformReadOnlySession") as reader, patch(
                   "ai_broadcaster.desktop_chat_tab.messagebox.showinfo") as notice:
            LocalChatTab._start_twitch(tab)
        reader.assert_not_called()
        notice.assert_called_once()
        self.assertIsNone(tab._twitch_session)

    def test_bad_saved_settings_refuses_network(self):
        for saved in ("twitch", ["twitch", "twitch"], [None], [[]],
                      ["chzzk", "other"], []):
            with self.subTest(saved=saved):
                tab = self.fake()
                with patch("ai_broadcaster.desktop_chat_tab.load_settings",
                           return_value={"platforms": saved}), patch(
                           "ai_broadcaster.desktop_chat_tab.MultiPlatformReadOnlySession") as reader, patch(
                           "ai_broadcaster.desktop_chat_tab.messagebox.showinfo") as notice:
                    LocalChatTab._start_twitch(tab)
                reader.assert_not_called()
                notice.assert_called_once()

    def test_four_channels_forwarded_without_leaking_key_on_constructor_error(self):
        tab = self.fake()
        for key, value in (("twitch","tester"), ("chzzk","a"*32),
                           ("soop","tester/123"), ("youtube","existingChatId")):
            tab._multi_channels[key] = Value(value)
        with patch("ai_broadcaster.desktop_chat_tab.load_settings",
                   return_value={"platforms": ["twitch","chzzk","soop","youtube"]}), patch(
                   "ai_broadcaster.desktop_chat_tab.MultiPlatformReadOnlySession",
                   side_effect=RuntimeError("secret-test-api-key")) as reader, patch(
                   "ai_broadcaster.desktop_chat_tab.messagebox.showinfo") as notice:
            LocalChatTab._start_twitch(tab)
        reader.assert_called_once()
        self.assertEqual(reader.call_args.args[0], {
            "twitch":"tester", "chzzk":"a"*32,
            "soop":"tester/123", "youtube":"existingChatId"})
        self.assertEqual(reader.call_args.kwargs["youtube_api_key"], "secret-test-api-key")
        self.assertNotIn("secret-test-api-key", str(notice.call_args))
        self.assertIsNone(tab._twitch_session)

    def test_transport_and_local_ai_errors_hide_credentials(self):
        secret = "never-output-this-secret"
        rows = queue.SimpleQueue()
        class BrokenReader:
            def run(self):
                raise RuntimeError(secret)
        LocalChatTab._work_twitch(SimpleNamespace(_results=rows), BrokenReader())
        self.assertNotIn(secret, str(rows.get_nowait()))
        self.assertEqual(rows.get_nowait()[1][1], "twitch_finished")
        out = queue.SimpleQueue()
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                   side_effect=RuntimeError(secret)):
            LocalChatTab._work(SimpleNamespace(_results=out), "local", "hello")
        self.assertEqual(out.get_nowait(), ("error", "RuntimeError"))


if __name__ == "__main__":
    unittest.main()
