"""169회차: 치지직·SOOP 실제 WebSocket 프레임 미수용 채팅 보존 계약.

가상 프레임·가상 콜백만 사용한다. 실제 서버/계정/AI/OBS/방송은 실행하지 않는다.
"""
import sys
import unittest
from collections import deque
from types import SimpleNamespace
from unittest.mock import patch

from ai_broadcaster.multiplatform_readonly import (
    PlatformChat, ReadOnlySession,
)
from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession


class 가상소켓:
    def __init__(self, frames):
        self.frames = deque(frames)
        self.timeouts = []

    def settimeout(self, value):
        self.timeouts.append(value)

    def recv(self):
        if not self.frames:
            raise RuntimeError("가상 프레임 종료")
        return self.frames.popleft()


class 수신프레임보류검사(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.reader = ReadOnlySession(
            "가상채널", lambda kind, item: self.events.append(item) or True)
        self.items = [
            PlatformChat("가상채널", "시청자", f"채팅 {i}", "chzzk", f"id{i}")
            for i in range(3)
        ]

    def test_join_before_chat_delivery(self):
        self.reader._queue_received_chats(self.items)
        self.reader._flush_pending_chats()
        self.assertEqual(self.events, [])
        self.assertEqual(list(self.reader._pending_chats), self.items)

    def test_fifo_delivery_after_join(self):
        self.reader._queue_received_chats(self.items)
        self.reader._chat_room_ready = True
        self.reader._flush_pending_chats()
        self.assertEqual(self.events, self.items)
        self.assertFalse(self.reader._pending_chats)

    def test_false_keeps_failed_item_and_rest_of_frame(self):
        delivered = []
        def emit(kind, item):
            if item is self.items[1]:
                return False
            delivered.append(item)
            return True
        self.reader.emit = emit
        self.reader._chat_room_ready = True
        self.reader._queue_received_chats(self.items)
        with self.assertRaises(RuntimeError):
            self.reader._flush_pending_chats()
        self.assertEqual(delivered, [self.items[0]])
        self.assertEqual(list(self.reader._pending_chats), self.items[1:])

    def test_callback_exception_keeps_unaccepted_tail(self):
        def emit(kind, item):
            raise ValueError("가상 AI FIFO 오류")
        self.reader.emit = emit
        self.reader._chat_room_ready = True
        self.reader._queue_received_chats(self.items)
        with self.assertRaises(ValueError):
            self.reader._flush_pending_chats()
        self.assertEqual(list(self.reader._pending_chats), self.items)

    def test_new_reader_can_continue_same_pending_deque(self):
        self.reader._queue_received_chats(self.items)
        replacement = ReadOnlySession("가상채널", lambda kind, item: (
            self.events.append(item) or True))
        replacement._pending_chats = self.reader._pending_chats
        replacement._chat_room_ready = True
        replacement._flush_pending_chats()
        self.assertEqual(self.events, self.items)
        self.assertFalse(self.reader._pending_chats)

    def test_full_socket_frame_is_saved_before_first_failed_callback(self):
        self.reader._chat_room_ready = True
        self.reader.emit = lambda kind, item: False if kind == "chat" else True
        sock = 가상소켓(["프레임"])
        with patch.dict(sys.modules, {
            "websocket": SimpleNamespace(WebSocketTimeoutException=TimeoutError)
        }):
            with self.assertRaises(RuntimeError):
                self.reader._receive_socket(
                    sock, lambda data, channel: list(self.items))
        self.assertEqual(list(self.reader._pending_chats), self.items)

    def test_pending_frame_drains_before_next_socket_frame(self):
        self.reader._chat_room_ready = True
        self.reader._queue_received_chats(self.items[:2])
        sock = 가상소켓(["새프레임", ""])
        with patch.dict(sys.modules, {
            "websocket": SimpleNamespace(WebSocketTimeoutException=TimeoutError)
        }):
            with self.assertRaises(RuntimeError):
                self.reader._receive_socket(
                    sock, lambda data, channel: self.items[2:])
        self.assertEqual(self.events, self.items)
        self.assertFalse(self.reader._pending_chats)

    def test_stop_prevents_pending_chat_forward(self):
        self.reader._chat_room_ready = True
        self.reader._queue_received_chats(self.items)
        self.reader.stop()
        self.reader._flush_pending_chats()
        self.assertEqual(self.events, [])
        self.assertEqual(len(self.reader._pending_chats), 3)

    def test_coordinator_shares_memory_pending_with_websocket_reader(self):
        session = MultiPlatformReadOnlySession(
            {"chzzk": "a" * 32, "soop": "abc/1"},
            lambda kind, item: True)
        for code in ("chzzk", "soop"):
            self.assertIs(
                session._readers[code]._pending_chats,
                session._pending_websocket_chats[code])

    def test_snapshot_counts_pending_without_claiming_delivery(self):
        session = MultiPlatformReadOnlySession(
            {"chzzk": "a" * 32, "soop": "abc/1"},
            lambda kind, item: True)
        session._pending_websocket_chats["chzzk"].extend(self.items)
        snap = session.reconnect_snapshot()
        self.assertEqual(snap["chzzk"]["수신프레임미수용보류"], 3)
        self.assertEqual(snap["soop"]["수신프레임미수용보류"], 0)
        self.assertEqual(snap["chzzk"]["콜백전달완료"], 0)


if __name__ == "__main__":
    unittest.main()
