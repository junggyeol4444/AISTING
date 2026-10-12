import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.session import ChatMessage, SessionController, SessionPolicy, SessionState


class TestSession(unittest.TestCase):
    def test_initial_state_offline(self):
        self.assertEqual(SessionController().state, SessionState.OFFLINE)

    def test_start_is_simulation_only(self):
        ctrl = SessionController()
        self.assertEqual(ctrl.start(100).name, "simulated_session_started")
        self.assertEqual(ctrl.state, SessionState.LIVE)

    def test_no_automatic_end_without_operator_rule(self):
        ctrl = SessionController()
        ctrl.start(0)
        self.assertIsNone(ctrl.tick(10 ** 9))
        self.assertEqual(ctrl.state, SessionState.LIVE)

    def test_maximum_duration_close(self):
        ctrl = SessionController(SessionPolicy(minimum_seconds=60, maximum_seconds=120))
        ctrl.start(100)
        self.assertIsNone(ctrl.tick(219.9))
        self.assertEqual(ctrl.tick(220).name, "farewell_requested")
        self.assertEqual(ctrl.state, SessionState.CLOSING)

    def test_closing_event_is_not_repeated(self):
        ctrl = SessionController(SessionPolicy(maximum_seconds=5))
        ctrl.start(0)
        self.assertEqual(ctrl.tick(5).name, "farewell_requested")
        self.assertIsNone(ctrl.tick(6))
        self.assertIsNone(ctrl.request_close())

    def test_farewell_must_complete_before_offline(self):
        ctrl = SessionController()
        ctrl.start(0)
        with self.assertRaises(RuntimeError):
            ctrl.farewell_finished()
        self.assertEqual(ctrl.request_close().name, "farewell_requested")
        self.assertEqual(ctrl.farewell_finished().name, "simulated_session_ended")
        self.assertEqual(ctrl.state, SessionState.OFFLINE)

    def test_cannot_start_twice(self):
        ctrl = SessionController()
        ctrl.start(0)
        with self.assertRaises(RuntimeError):
            ctrl.start(1)

    def test_chat_fifo_every_message(self):
        ctrl = SessionController()
        messages = [ChatMessage(str(i), "viewer", f"채팅 {i}") for i in range(100)]
        for msg in messages:
            ctrl.receive_chat(msg)
        self.assertEqual(ctrl.pending_chats, 100)
        self.assertEqual([ctrl.next_chat() for _ in messages], messages)
        self.assertIsNone(ctrl.next_chat())
        self.assertEqual(ctrl.pending_chats, 0)
        self.assertEqual(ctrl.processed_chats, 100)

    def test_identical_texts_not_suppressed(self):
        ctrl = SessionController()
        ctrl.receive_chat(ChatMessage("1", "A", "ㅋㅋㅋ"))
        ctrl.receive_chat(ChatMessage("2", "B", "ㅋㅋㅋ"))
        self.assertEqual([ctrl.next_chat().message_id, ctrl.next_chat().message_id], ["1", "2"])

    def test_queue_does_not_discard_when_no_session(self):
        ctrl = SessionController()
        ctrl.receive_chat(ChatMessage("1", "A", "안녕"))
        self.assertEqual(ctrl.next_chat().text, "안녕")

    def test_early_manual_close_allowed(self):
        ctrl = SessionController(SessionPolicy(minimum_seconds=60, maximum_seconds=120))
        ctrl.start(0)
        self.assertEqual(ctrl.request_close().name, "farewell_requested")

    def test_invalid_policy_rejected(self):
        for kwargs in ({"minimum_seconds": -1}, {"maximum_seconds": 0}, {"minimum_seconds": 5, "maximum_seconds": 3}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                SessionPolicy(**kwargs)

    def test_time_must_not_move_backwards(self):
        ctrl = SessionController()
        ctrl.start(10)
        with self.assertRaises(ValueError):
            ctrl.tick(9)

    def test_chat_input_type_checked(self):
        with self.assertRaises(TypeError):
            SessionController().receive_chat("hello")
        with self.assertRaises(ValueError):
            ChatMessage("", "user", "hello")


if __name__ == "__main__":
    unittest.main()
