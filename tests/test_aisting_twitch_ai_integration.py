"""Existing AISTING local AI consumer must process every Twitch chat in FIFO.

These regression tests exercise production message-queue code. They are not a
claim that an Ollama model, Live2D, or real viewers were available in the test.
"""
import queue
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_broadcaster.desktop_chat_tab import LocalChatTab
from ai_broadcaster.twitch_readonly import TwitchChatLine, TwitchReadOnlySession
from ai_broadcaster.desktop_chat import run_local_chat


class LiveChatReplyOrderTests(unittest.TestCase):
    def test_every_message_generates_reply_in_order_including_duplicates(self):
        messages = [
            TwitchChatLine("mychannel", "alice", "안녕"),
            TwitchChatLine("mychannel", "bob", "하이 😀"),
            TwitchChatLine("mychannel", "alice", "안녕"),
        ]
        inbox = queue.SimpleQueue()
        outbox = queue.SimpleQueue()
        for msg in messages:
            inbox.put(msg)
        inbox.put(None)
        recorder = SimpleNamespace(_results=outbox)
        calls = []
        def local_reply(model, text, *, sender, use_committed_gui_character):
            calls.append((model, text, sender, use_committed_gui_character))
            return SimpleNamespace(reply="한국어 답변 " + text, remembered_count=len(calls))
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                   side_effect=local_reply):
            LocalChatTab._work_twitch_ai(recorder, "local-model", inbox)
        self.assertEqual(calls, [
            ("local-model", "안녕", "[트위치] alice", True),
            ("local-model", "하이 😀", "[트위치] bob", True),
            ("local-model", "안녕", "[트위치] alice", True),
        ])
        results = [outbox.get_nowait() for _ in range(3)]
        self.assertTrue(all(kind == "twitch_ai_ok" for kind, _ in results))
        self.assertEqual([payload[0] for _, payload in results], messages)
        self.assertEqual([payload[1].reply for _, payload in results],
                         ["한국어 답변 안녕", "한국어 답변 하이 😀", "한국어 답변 안녕"])

    def test_one_ai_error_is_visible_and_next_message_is_not_filtered(self):
        inbox, outbox = queue.SimpleQueue(), queue.SimpleQueue()
        first = TwitchChatLine("mychannel", "viewer1", "첫 채팅")
        second = TwitchChatLine("mychannel", "viewer2", "둘째 채팅")
        for x in (first, second, None):
            inbox.put(x)
        stub = SimpleNamespace(_results=outbox)
        seen = []
        def local_reply(model, text, *, sender, use_committed_gui_character):
            self.assertTrue(use_committed_gui_character)
            seen.append(text)
            if text == "첫 채팅":
                raise ConnectionError("실제 로컬 AI 서버 없음")
            return SimpleNamespace(reply="두 번째 응답", remembered_count=1)
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                   side_effect=local_reply):
            LocalChatTab._work_twitch_ai(stub, "model", inbox)
        err, done = outbox.get_nowait(), outbox.get_nowait()
        self.assertEqual(seen, ["첫 채팅", "둘째 채팅"])
        self.assertEqual(err[0], "twitch_ai_error")
        self.assertEqual(err[1][0], first)
        self.assertEqual(done[0], "twitch_ai_ok")
        self.assertEqual(done[1][0], second)

    def test_old_connection_results_cannot_enter_new_session(self):
        from ai_broadcaster.multiplatform_readonly import PlatformChat
        old_session, new_session = object(), object()
        out = queue.SimpleQueue()
        shown, appended = [], []
        old_chat = PlatformChat("old", "old-viewer", "늦은 메시지", "soop")
        out.put(("twitch_scoped", (old_session, "twitch_chat", old_chat)))
        out.put(("twitch_scoped", (old_session, "twitch_ai_ok",
                                  (old_chat, SimpleNamespace(reply="늦은 답변")))))
        out.put(("twitch_scoped", (old_session, "twitch_ai_error",
                                  (old_chat, "예전 오류"))))
        out.put(("twitch_scoped", (old_session, "twitch_finished", old_session)))
        out.put(("twitch_scoped", (new_session, "twitch_connected", "new-room")))
        fake = SimpleNamespace(
            _results=out, _closed=False, _twitch_session=new_session,
            _twitch_received=0, _twitch_replied=0, _twitch_ai_failures=0,
            _chat_platform=SimpleNamespace(get=lambda:"SOOP"),
            _twitch_status=SimpleNamespace(set=shown.append),
            _append=appended.append,
            _poll=lambda:None,
            after=lambda *args:None)
        LocalChatTab._poll(fake)
        self.assertEqual(fake._twitch_received, 0)
        self.assertEqual(fake._twitch_replied, 0)
        self.assertEqual(fake._twitch_ai_failures, 0)
        self.assertEqual(appended, [])
        self.assertEqual(len(shown),1)
        self.assertIn("new-room",shown[0])

    def test_real_ui_ai_worker_attaches_originating_session(self):
        inbox, outbox = queue.SimpleQueue(), queue.SimpleQueue()
        current = object()
        chat = TwitchChatLine("room", "viewer", "안녕")
        inbox.put(chat)
        inbox.put(None)
        fake = SimpleNamespace(_results=outbox)
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                   return_value=SimpleNamespace(reply="답변",remembered_count=1)):
            LocalChatTab._work_twitch_ai(fake,"model",inbox,False,current)
        label, (session, event, value) = outbox.get_nowait()
        self.assertEqual(label,"twitch_scoped")
        self.assertIs(session,current)
        self.assertEqual(event,"twitch_ai_ok")
        self.assertEqual(value[0],chat)

    def test_stopping_before_thread_start_never_reopens_websocket(self):
        events = []
        receiver = TwitchReadOnlySession("streamer", lambda k, v: events.append((k, v)))
        receiver.stop()
        with patch.dict(sys.modules, {"websocket": SimpleNamespace(
                create_connection=lambda *args, **kw: self.fail("unexpected websocket open"))}):
            receiver.run(max_seconds=1)
        self.assertEqual(events, [("stopped", 0)])

    def test_soop_gui_distinguishes_socket_from_room_entry(self):
        inbox = queue.SimpleQueue()
        shown = []
        fake_tab = SimpleNamespace(
            _closed=False, _results=inbox,
            _twitch_status=SimpleNamespace(set=shown.append),
            _chat_platform=SimpleNamespace(get=lambda: "SOOP"),
            _poll=lambda: None,
            after=lambda *args: None,
        )
        inbox.put(("twitch_connected", "streamer/123"))
        LocalChatTab._poll(fake_tab)
        self.assertIn("서버 소켓 연결", shown[-1])
        self.assertIn("채팅방 입장 미확인", shown[-1])
        inbox.put(("twitch_ready", "streamer/123"))
        LocalChatTab._poll(fake_tab)
        self.assertIn("채팅방 입장 확인", shown[-1])
        inbox.put(("twitch_error", "연결 종료"))
        LocalChatTab._poll(fake_tab)
        self.assertIn("SOOP 읽기 오류", shown[-1])
        self.assertNotIn("트위치 읽기 오류", shown[-1])

    def test_sender_identity_validation(self):
        with self.assertRaises(ValueError):
            run_local_chat("any", "question", sender="")
        with self.assertRaises(ValueError):
            run_local_chat("any", "question", sender="x" * 161)


if __name__ == "__main__":
    unittest.main()
