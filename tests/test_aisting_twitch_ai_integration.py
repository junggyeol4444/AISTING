"""Existing AISTING local AI consumer must process every Twitch chat in FIFO.

These regression tests exercise production message-queue code. They are not a
claim that an Ollama model, Live2D, or real viewers were available in the test.
"""
import queue
import threading
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
        current = SimpleNamespace(_stop=threading.Event())
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

    def test_stopped_connection_does_not_process_queued_ai(self):
        import threading
        from ai_broadcaster.multiplatform_readonly import PlatformChat
        for official in (False,True):
            with self.subTest(official=official):
                stop=threading.Event()
                stop.set()
                inbox,outbox=queue.SimpleQueue(),queue.SimpleQueue()
                for text in ("첫째","첫째","둘째"):
                    inbox.put(PlatformChat("room","viewer",text,"soop"))
                inbox.put(None)
                with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                           side_effect=AssertionError("AI called after Stop")), patch(
                    "ai_broadcaster.original_plan_frontend.send_to_native_live2d_session_with_observation",
                    side_effect=AssertionError("Live2D called after Stop")):
                    LocalChatTab._work_twitch_ai(
                        SimpleNamespace(_results=outbox),"model",inbox,official,
                        SimpleNamespace(_stop=stop))
                self.assertTrue(outbox.empty())

    def test_stop_during_first_reply_prevents_further_queued_ai(self):
        import threading
        from ai_broadcaster.multiplatform_readonly import PlatformChat
        stop=threading.Event()
        inbox,outbox=queue.SimpleQueue(),queue.SimpleQueue()
        for txt in ("첫째","둘째","둘째"):
            inbox.put(PlatformChat("room","viewer",txt,"chzzk"))
        inbox.put(None)
        calls=[]
        def response(model,text,**kwargs):
            calls.append(text)
            stop.set()
            return SimpleNamespace(reply="결과",remembered_count=1)
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                   side_effect=response):
            LocalChatTab._work_twitch_ai(
                SimpleNamespace(_results=outbox),"model",inbox,False,
                SimpleNamespace(_stop=stop))
        self.assertEqual(calls,["첫째"])
        self.assertTrue(outbox.empty())

    def test_stop_button_wakes_ai_queue(self):
        import threading
        stop=threading.Event()
        inbox=queue.SimpleQueue()
        receiver=SimpleNamespace(
            _twitch_session=SimpleNamespace(stop=stop.set),
            _twitch_ai_inbox=inbox)
        LocalChatTab._stop_twitch(receiver)
        self.assertTrue(stop.is_set())
        self.assertIsNone(inbox.get_nowait())

    def test_stop_before_reader_disconnect_restores_gui_and_ignores_late_events(self):
        from ai_broadcaster.multiplatform_readonly import PlatformChat
        stopped=threading.Event()
        session=SimpleNamespace(stop=stopped.set, _stop=stopped)
        inbox=queue.SimpleQueue()
        statuses=[]
        buttons=[]
        fake=SimpleNamespace(
            _closed=False, _twitch_session=session, _twitch_ai_inbox=inbox,
            _twitch_reader_finished=False,
            _twitch_start=SimpleNamespace(configure=lambda **kw:buttons.append(("start",kw))),
            _twitch_end=SimpleNamespace(configure=lambda **kw:buttons.append(("end",kw))),
            _twitch_status=SimpleNamespace(set=statuses.append),
            _results=queue.SimpleQueue(),_poll=lambda:None,after=lambda *args:None,
            _twitch_received=0,_twitch_replied=0,_twitch_ai_failures=0)
        LocalChatTab._stop_twitch(fake)
        self.assertTrue(stopped.is_set())
        self.assertIsNone(fake._twitch_session)
        self.assertIsNone(fake._twitch_ai_inbox)
        self.assertEqual(buttons,[("start",{"state":"normal"}),("end",{"state":"disabled"})])
        new_session=SimpleNamespace(_stop=threading.Event())
        fake._twitch_session=new_session
        fake._results.put(("twitch_scoped",(session,"twitch_chat",
             PlatformChat("room","viewer","늦은 채팅","soop"))))
        fake._results.put(("twitch_scoped",(session,"twitch_finished",session)))
        LocalChatTab._poll(fake)
        self.assertIs(fake._twitch_session,new_session)
        self.assertEqual(fake._twitch_received,0)
        self.assertEqual(fake._twitch_replied,0)

    def test_stop_discards_buffered_scoped_events_except_finish(self):
        import threading
        from ai_broadcaster.multiplatform_readonly import PlatformChat
        stop=threading.Event()
        stop.set()
        session=SimpleNamespace(_stop=stop)
        msg=PlatformChat("room","viewer","늦은 채팅","soop")
        result=queue.SimpleQueue()
        for kind,payload in [
            ("twitch_chat",msg),
            ("twitch_ai_ok",(msg,SimpleNamespace(reply="늦은 응답"))),
            ("twitch_finished",session),
        ]:
            result.put(("twitch_scoped",(session,kind,payload)))
        fake=SimpleNamespace(
            _closed=False,_results=result,_twitch_session=session,
            _twitch_ai_inbox=None,_twitch_received=0,_twitch_replied=0,
            _twitch_ai_failures=0,
            _append=lambda *args:self.fail("stale text displayed"),
            _twitch_start=SimpleNamespace(configure=lambda **kwargs:None),
            _twitch_end=SimpleNamespace(configure=lambda **kwargs:None),
            _poll=lambda:None,after=lambda *args:None)
        LocalChatTab._poll(fake)
        self.assertEqual(fake._twitch_received,0)
        self.assertEqual(fake._twitch_replied,0)
        self.assertIsNone(fake._twitch_session)

    def test_tk_poll_drains_512_events_in_bounded_fifo_slices(self):
        """A high-volume public chat cannot monopolize Tk's GUI thread."""
        records, scheduled=[],[]
        session=object()
        outbox=queue.SimpleQueue()
        for index in range(512):
            outbox.put(("twitch_scoped",(
                session,"twitch_connected","room-"+str(index))))
        stub=SimpleNamespace(
            _closed=False, _results=outbox, _twitch_session=session,
            _chat_platform=SimpleNamespace(get=lambda:"SOOP"),
            _twitch_status=SimpleNamespace(set=records.append),
            _poll=lambda:None,
            after=lambda delay, callback:scheduled.append((delay,callback)))
        LocalChatTab._poll(stub)
        self.assertEqual(len(records),128)
        self.assertEqual(scheduled.pop(0)[0],1)
        self.assertEqual(len(records),128)
        # The queue retains the exact next FIFO event until Tk runs again.
        for _ in range(3):
            LocalChatTab._poll(stub)
        self.assertEqual(len(records),512)
        self.assertEqual(
            [row.split(" ")[1] for row in records],
            ["room-"+str(i) for i in range(512)])
        self.assertTrue(outbox.empty())
        self.assertEqual(scheduled[-1][0],150)

    def test_gui_yields_when_129th_event_is_pending_not_discarded(self):
        updates,scheduling=[],[]
        out=queue.SimpleQueue()
        for i in range(129):
            out.put(("twitch_scoped",(object(),"twitch_ready","unused")))
        # All objects above are stale; they still count toward Tk work and
        # must not get lost from the FIFO solely because they are stale.
        receiver=SimpleNamespace(
            _closed=False,_results=out,_twitch_session=object(),
            _poll=lambda:None,
            after=lambda ms, cb:scheduling.append(ms))
        LocalChatTab._poll(receiver)
        self.assertEqual(scheduling,[1])
        self.assertFalse(out.empty())
        LocalChatTab._poll(receiver)
        self.assertTrue(out.empty())
        self.assertEqual(scheduling,[1,150])


    def test_reader_eof_preserves_pending_fifo_ai_replies_until_worker_finishes(self):
        """A real reader EOF must not silently discard already accepted chats."""
        from ai_broadcaster.multiplatform_readonly import PlatformChat
        session = SimpleNamespace(_stop=threading.Event())
        msgs = [PlatformChat("room", "viewer", txt, "soop")
                for txt in ("첫 채팅", "첫 채팅", "다음 채팅")]
        pending, events, display, buttons = queue.SimpleQueue(), queue.SimpleQueue(), [], []
        fake = SimpleNamespace(
            _results=events, _closed=False, _twitch_session=session,
            _twitch_ai_inbox=pending, _twitch_reader_finished=False,
            _twitch_received=0, _twitch_replied=0, _twitch_ai_failures=0,
            _chat_platform=SimpleNamespace(get=lambda: "SOOP"),
            _twitch_status=SimpleNamespace(set=display.append),
            _twitch_start=SimpleNamespace(configure=lambda **kw: buttons.append(("start", kw))),
            _twitch_end=SimpleNamespace(configure=lambda **kw: buttons.append(("end", kw))),
            _append=display.append, _refresh_voice_buttons=lambda: None,
            _tts_voices={}, _voice_name=SimpleNamespace(get=lambda: ""),
            _auto_voice=SimpleNamespace(get=lambda: False),
            _last_reply=None, _memory_count=SimpleNamespace(set=lambda *_: None),
            _poll=lambda:None, after=lambda *args:None)
        for msg in msgs:
            events.put(("twitch_scoped", (session, "twitch_chat", msg)))
        events.put(("twitch_scoped", (session, "twitch_finished", session)))
        LocalChatTab._poll(fake)
        self.assertIs(fake._twitch_session, session)
        self.assertTrue(fake._twitch_reader_finished)
        self.assertEqual([pending.get_nowait() for _ in range(4)], msgs + [None])
        for index, msg in enumerate(msgs):
            events.put(("twitch_scoped", (session, "twitch_ai_ok", (
                msg, SimpleNamespace(reply="AI 응답 "+str(index), remembered_count=index+1)))))
        events.put(("twitch_scoped", (session, "twitch_ai_finished", session)))
        LocalChatTab._poll(fake)
        self.assertEqual(fake._twitch_received, 3)
        self.assertEqual(fake._twitch_replied, 3)
        self.assertIsNone(fake._twitch_session)
        self.assertFalse(fake._twitch_reader_finished)
        self.assertEqual(fake._last_reply, "AI 응답 2")
        self.assertEqual(buttons[-2:], [
            ("start", {"state":"normal"}), ("end", {"state":"disabled"})])
        self.assertEqual(sum("AI →" in line for line in display), 3)

    def test_stop_during_reader_eof_drain_aborts_late_model_reply(self):
        stop = threading.Event()
        session = SimpleNamespace(_stop=stop, stop=stop.set)
        updates = []
        fake = SimpleNamespace(
            _twitch_session=session, _twitch_reader_finished=True,
            _twitch_ai_inbox=queue.SimpleQueue(),
            _twitch_start=SimpleNamespace(configure=lambda **kw:updates.append(kw)),
            _twitch_end=SimpleNamespace(configure=lambda **kw:updates.append(kw)),
            _twitch_status=SimpleNamespace(set=updates.append))
        LocalChatTab._stop_twitch(fake)
        self.assertTrue(stop.is_set())
        self.assertIsNone(fake._twitch_session)
        self.assertIsNone(fake._twitch_ai_inbox)
        self.assertEqual(updates[0], {"state":"normal"})

    def test_worker_emits_drain_completion_after_all_scoped_replies(self):
        inbox, outbox = queue.SimpleQueue(), queue.SimpleQueue()
        session = SimpleNamespace(_stop=threading.Event())
        for value in ("하나", "하나", "둘"):
            inbox.put(TwitchChatLine("room","user",value))
        inbox.put(None)
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                   side_effect=lambda model,text,**kwargs:
                       SimpleNamespace(reply=text,remembered_count=1)):
            LocalChatTab._work_twitch_ai(
                SimpleNamespace(_results=outbox), "model", inbox, False, session)
        events = [outbox.get_nowait()[1][1] for _ in range(4)]
        self.assertEqual(events, ["twitch_ai_ok"]*3 + ["twitch_ai_finished"])
        self.assertTrue(outbox.empty())


    def test_transport_error_remains_visible_after_ai_queue_finishes(self):
        session = SimpleNamespace(_stop=threading.Event())
        events = queue.SimpleQueue()
        statuses = []
        fake = SimpleNamespace(
            _results=events, _closed=False, _twitch_session=session,
            _twitch_ai_inbox=queue.SimpleQueue(), _twitch_reader_finished=False,
            _twitch_reader_error=None, _twitch_received=2, _twitch_replied=0,
            _twitch_ai_failures=0,
            _chat_platform=SimpleNamespace(get=lambda: "트위치"),
            _twitch_status=SimpleNamespace(set=statuses.append),
            _twitch_start=SimpleNamespace(configure=lambda **kw: None),
            _twitch_end=SimpleNamespace(configure=lambda **kw: None),
            _poll=lambda:None, after=lambda *args:None)
        events.put(("twitch_scoped", (session, "twitch_error", "서버 연결 끊김")))
        events.put(("twitch_scoped", (session, "twitch_finished", session)))
        LocalChatTab._poll(fake)
        self.assertIn("서버 연결 끊김", statuses[-1])
        self.assertIs(fake._twitch_session, session)
        events.put(("twitch_scoped", (session, "twitch_ai_finished", session)))
        LocalChatTab._poll(fake)
        self.assertIsNone(fake._twitch_session)
        self.assertIn("서버 연결 끊김", statuses[-1])
        self.assertIn("대기 AI 응답 처리 완료", statuses[-1])

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
