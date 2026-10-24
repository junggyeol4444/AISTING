"""172회차 치지직·SOOP JOIN 이전 수신 프레임 재연결 보존 계약검사.

실제 플랫폼·사용자 계정·시청자·24시간 방송에 접속하지 않는 가상 검사.
원본 서버가 보내지 않은 채팅과 프로세스 종료 뒤 복구를 보장하지 않는다.
"""
import json
import unittest
from collections import deque
from types import SimpleNamespace
from unittest.mock import patch

from ai_broadcaster.multiplatform_readonly import (
    ChzzkReadOnlySession, PlatformChat, PreJoinChatResumeState,
)
from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession


def 채팅(번호, *, 서버ID=True, 내용=None):
    return PlatformChat(
        "가상채널", "가상시청자", 내용 or f"가상채팅{번호}", "chzzk",
        f"서버-{번호}" if 서버ID else None)


class 가상소켓:
    def __init__(self, frames):
        self.frames = deque(frames)
        self.sent = []
        self.closed = False

    def settimeout(self, value):
        pass

    def recv(self):
        if not self.frames:
            raise OSError("가상 연결 종료")
        return self.frames.popleft()

    def send(self, value):
        self.sent.append(value)

    def close(self):
        self.closed = True


class 입장전보류검사(unittest.TestCase):
    def setUp(self):
        self.state = PreJoinChatResumeState()
        self.state.bind_room("가상서버방1")

    def test_같은방_재연결후_원래순서로_해제(self):
        self.state.stage([채팅(1), 채팅(2)])
        self.state.bind_room("가상서버방1")
        self.state.stage([채팅(3)])
        target = deque([채팅(0)])
        self.state.release_to(target)
        self.assertEqual([c.text for c in target],
                         [f"가상채팅{i}" for i in range(4)])
        self.assertEqual(len(self.state.pending), 0)

    def test_서버ID있는_재전송만_중복차단(self):
        self.state.stage([채팅(1), 채팅(2)])
        self.state.stage([채팅(2), 채팅(3)])
        self.assertEqual([x.event_id for x in self.state.pending],
                         ["서버-1", "서버-2", "서버-3"])
        self.assertEqual(self.state.duplicate_server_ids, 1)

    def test_서버ID없는_같은본문_다른사건_보존(self):
        self.state.stage([채팅(i, 서버ID=False, 내용="같은말")
                          for i in range(3)])
        self.assertEqual(len(self.state.pending), 3)

    def test_같은배치의_중복ID도_한번만_보관(self):
        self.state.stage([채팅(1), 채팅(1), 채팅(2)])
        self.assertEqual(len(self.state.pending), 2)
        self.assertEqual(self.state.duplicate_server_ids, 1)

    def test_다른서버방_미수용사건_이동금지(self):
        self.state.stage([채팅(1)])
        with self.assertRaises(RuntimeError):
            self.state.bind_room("다른서버방")
        self.assertEqual(self.state.room_id, "가상서버방1")
        self.assertEqual(len(self.state.pending), 1)

    def test_이미승인된_미수용FIFO도_다른서버방으로_전달금지(self):
        with self.assertRaises(RuntimeError):
            self.state.bind_room("다른서버방", accepted_pending=True)
        self.assertEqual(self.state.room_id, "가상서버방1")

    def test_모든사건_수용후_다른서버방_바인딩_가능(self):
        self.state.stage([채팅(1)])
        self.state.release_to(deque())
        self.state.bind_room("다른서버방")
        self.assertEqual(self.state.room_id, "다른서버방")

    def test_4096개_한도_초과시_기존사건_그대로_보존(self):
        self.state.stage([채팅(i, 서버ID=False) for i in range(4096)])
        with self.assertRaises(RuntimeError):
            self.state.stage([채팅(4096, 서버ID=False)])
        self.assertEqual(len(self.state.pending), 4096)

    def test_잘못된항목은_큐를_변경하지_않음(self):
        with self.assertRaises(ValueError):
            self.state.stage([채팅(1), object()])
        self.assertEqual(len(self.state.pending), 0)

    def test_4플랫폼조정기_기존큐_공유와_JOIN전보류_진단(self):
        channels = {"chzzk": "a" * 32, "soop": "testuser/123",
                    "youtube": "가상채팅방"}
        coordinator = MultiPlatformReadOnlySession(
            channels, lambda *args: True, youtube_api_key="가상키" * 8)
        state = coordinator._prejoin_resume_states["chzzk"]
        state.bind_room("서버방")
        state.stage([채팅(1), 채팅(2)])
        snapshot = coordinator.reconnect_snapshot()
        self.assertEqual(snapshot["chzzk"]["JOIN전미수용보류"], 2)
        self.assertEqual(snapshot["soop"]["JOIN전미수용보류"], 0)
        self.assertEqual(snapshot["youtube"]["JOIN전미수용보류"], 0)
        self.assertIs(coordinator._readers["chzzk"]._prejoin_resume, state)
        self.assertIs(
            coordinator._readers["soop"]._prejoin_resume,
            coordinator._prejoin_resume_states["soop"])

    def test_치지직_JOIN전_연결끊김후_동일방_승인_보류채팅전달(self):
        channel = "a" * 32
        frames_first = [json.dumps({
            "cmd": 93101,
            "bdy": [{"msg": "먼저 도착한 가상 채팅", "uid": "가상", "msgId": "id1"}]
        })]
        frames_second = [json.dumps({"cmd": 10100, "bdy": {"sid": "승인"}})]
        sockets = [가상소켓(frames_first), 가상소켓(frames_second)]
        delivered = []
        def cb(kind, item):
            if kind == "chat":
                delivered.append(item.text)
            return True
        state = PreJoinChatResumeState()
        first = ChzzkReadOnlySession(channel, cb)
        first._prejoin_resume = state
        second = ChzzkReadOnlySession(channel, cb)
        second._prejoin_resume = state
        second._pending_chats = first._pending_chats
        def fake_json_get(url):
            if url.endswith("live-status"):
                return {"content": {"chatChannelId": "같은서버방"}}
            return {"content": {"accessToken": "가상읽기토큰"}}
        fake_websocket = SimpleNamespace(
            create_connection=lambda *a, **kw: sockets.pop(0),
            WebSocketTimeoutException=TimeoutError)
        with patch.dict("sys.modules", {"websocket": fake_websocket}), patch(
                "ai_broadcaster.multiplatform_readonly._json_get",
                side_effect=fake_json_get), patch.object(
                    ChzzkReadOnlySession, "_receive_socket", return_value=None):
            # 첫 연결은 승인 전 프레임 수신 뒤 가상 연결이 끊긴다.
            with self.assertRaises(OSError):
                first.run()
            self.assertEqual(len(state.pending), 1)
            self.assertEqual(delivered, [])
            second.run()
        self.assertEqual(delivered, ["먼저 도착한 가상 채팅"])
        self.assertEqual(len(state.pending), 0)


    def test_SOOP_JOIN전_가상프레임_연결끊김후_같은방_승인_전달(self):
        from ai_broadcaster.multiplatform_readonly import SoopReadOnlySession
        import urllib.request

        class 가상응답:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, size):
                return json.dumps({"CHANNEL": {
                    "CHDOMAIN": "example.test", "CHATNO": "55", "CHPT": "1234"
                }}).encode("utf-8")

        # 0005는 서버 채팅 프레임, 0001/0002는 가상 CONNECT/JOIN 승인.
        first_sock = 가상소켓(["\\x1b\\t000500000000\\x0c먼저온말\\x0c가상\\x0c"])
        second_sock = 가상소켓([
            "\\x1b\\t000100000000\\x0c",
            "\\x1b\\t000200000000\\x0c",
        ])
        sockets = [first_sock, second_sock]
        received = []
        def cb(kind, item):
            if kind == "chat":
                received.append(item.text)
            return True
        shared = PreJoinChatResumeState()
        first = SoopReadOnlySession("testuser/123", cb)
        first._prejoin_resume = shared
        second = SoopReadOnlySession("testuser/123", cb)
        second._prejoin_resume = shared
        second._pending_chats = first._pending_chats
        fake_websocket = SimpleNamespace(
            create_connection=lambda *a, **kw: sockets.pop(0),
            WebSocketTimeoutException=TimeoutError)
        with patch.dict("sys.modules", {"websocket": fake_websocket}), patch(
                "urllib.request.urlopen", return_value=가상응답()):
            with self.assertRaises(OSError):
                first.run()
            self.assertEqual(len(shared.pending), 1)
            self.assertEqual(received, [])
            with self.assertRaises(OSError):
                second.run()
        self.assertEqual(received, ["먼저온말"])
        self.assertEqual(len(shared.pending), 0)


if __name__ == "__main__":
    unittest.main()
