"""Real protocol parsers + no-login read-only adapter regressions.

These prove parsing and fail-closed behavior; they are NOT claims of
live CHZZK, SOOP, or YouTube chat connectivity on the CI runner.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.multiplatform_readonly import (
    PlatformChat, parse_chzzk_frame, parse_soop_frame,
    parse_youtube_page, ChzzkReadOnlySession, SoopReadOnlySession,
    YouTubeReadOnlySession,
)
from ai_broadcaster.offline_settings import DEFAULTS, validate_settings


class MultiplePlatformChatTests(unittest.TestCase):
    def test_chzzk_live_and_recent_preserve_korean_duplicates(self):
        rows = [{"profile": '{"nickname":"시청자"}', "msg": "안녕 😀"},
                {"profile": '{"nickname":"시청자"}', "msg": "안녕 😀"}]
        for cmd, bdy in ((93101, rows),(15101,{"messageList":rows})):
            parsed = parse_chzzk_frame(json.dumps({"cmd":cmd,"bdy":bdy}), "room")
            self.assertEqual(len(parsed), 2)
            self.assertEqual(parsed[0], PlatformChat("room", "시청자", "안녕 😀", "chzzk"))
            self.assertEqual(parsed[0], parsed[1])

    def test_chzzk_skips_system_frames_and_fails_on_bad_chat_shape(self):
        self.assertEqual(parse_chzzk_frame('{"cmd":0,"bdy":[]}', "room"), [])
        with self.assertRaises(ValueError):
            parse_chzzk_frame('{"cmd":93101,"bdy":"bad"}', "room")

    def test_soop_parses_real_protocol_chat_and_ignores_nonchat(self):
        message = ("\x1b\t000500002000\x0c안녕하세요😀\x0ctester"
                   "\x0c닉네임\x0c0\x0c0\x0c시청자이름\x0c")
        self.assertEqual(parse_soop_frame(message,"id/123"),
                         [PlatformChat("id/123","시청자이름","안녕하세요😀","soop")])
        self.assertEqual(parse_soop_frame(message.replace("0005","0001",1),"id/123"), [])

    def test_soop_batched_protocol_frames_preserve_every_message(self):
        one = ("\x1b\t000500002000\x0c첫째\x0ctester"
               "\x0c닉네임\x0c0\x0c0\x0c시청자\x0c")
        second = one.replace("첫째", "둘째")
        self.assertEqual(
            [x.text for x in parse_soop_frame(one + second, "bj/1")],
            ["첫째", "둘째"])
        self.assertEqual(
            [x.text for x in parse_soop_frame(one + one, "bj/1")],
            ["첫째", "첫째"])

    def test_soop_real_chat_content_is_never_silently_selected(self):
        """Every 0005 text, including numeric/control-like words, is chat."""
        texts = ("1", "-1", "fw=something", " ", "", "안녕", "안녕")
        frames = [
            "\x1b\t000500002000\x0c" + text +
            "\x0cuser\x0c닉네임\x0c0\x0c0\x0c시청자\x0c"
            for text in texts
        ]
        frames.insert(3, "\x1b\t000100000600\x0c\x0c\x0c16\x0c")
        results = parse_soop_frame("".join(frames), "bj/123")
        self.assertEqual([item.text for item in results], list(texts))
        self.assertEqual([item.sender for item in results],
                         ["시청자"] * len(texts))

    def test_soop_waits_for_connect_ack_then_joins_and_reads_chat(self):
        """A socket handshake alone must never be mistaken for chat-room entry."""
        from io import BytesIO
        from types import SimpleNamespace

        sent = []
        events = []
        replies = [
            "\x1b\t000100000600\x0c\x0c\x0c16\x0c",
            "\x1b\t000200000600\x0c\x0c\x0cjoined\x0c",
            ("\x1b\t000500002000\x0c안녕😀\x0ctester"
             "\x0c닉네임\x0c0\x0c0\x0c시청자\x0c") * 2,
        ]
        session = SoopReadOnlySession(
            "streamer/123", lambda kind, value: events.append((kind, value)))
        test_case = self

        class Socket:
            def send(self, packet):
                sent.append(packet)

            def recv(self):
                if len(replies) == 3:
                    test_case.assertEqual(len(sent), 1, "JOIN before CONNECT ack")
                if len(replies) == 2:
                    test_case.assertEqual(len(sent), 2, "JOIN not sent on ack")
                if replies:
                    return replies.pop(0)
                session.stop()
                return "\x1b\t000000000100\x0c"

            def settimeout(self, timeout):
                pass

            def close(self):
                pass

        socket = Socket()
        fake_websocket = SimpleNamespace(
            create_connection=lambda *args, **kwargs: socket,
            WebSocketTimeoutException=TimeoutError,
        )
        metadata = BytesIO(json.dumps({
            "CHANNEL": {"CHDOMAIN": "chat.example.test",
                        "CHATNO": "123456", "CHPT": "12345"}
        }).encode("utf-8"))
        with patch.dict(sys.modules, {"websocket": fake_websocket}), \
                patch("urllib.request.urlopen", return_value=metadata):
            session.run(max_seconds=3)

        self.assertEqual(len(sent), 2)
        self.assertTrue(sent[0].startswith("\x1b\t0001"))
        self.assertTrue(sent[1].startswith("\x1b\t0002"))
        self.assertEqual(sum(k == "ready" for k, _ in events), 1)
        self.assertEqual(
            [value.text for k, value in events if k == "chat"],
            ["안녕😀", "안녕😀"])
        self.assertEqual(
            next(value for kind, value in events if kind == "packet_commands"),
            {"0001": 1, "0002": 1, "0005": 2})

    def test_soop_ping_only_after_enter_while_receiving_long_term(self):
        """No early keepalive and no dropped chat, even across idle periods."""
        from io import BytesIO
        from types import SimpleNamespace
        clock = [0.0]
        events, sent = [], []
        session = SoopReadOnlySession(
            "streamer/123", lambda kind, value: events.append((kind, value)))

        class SocketTimeout(Exception):
            pass

        class Socket:
            def __init__(self):
                self.reads = 0

            def settimeout(self, timeout):
                pass

            def send(self, packet):
                sent.append(packet)

            def close(self):
                pass

            def recv(self):
                self.reads += 1
                if self.reads == 1:
                    # Before CONNECT acknowledgement: no JOIN, no PING.
                    clock[0] = 80.0
                    return "\x1b\t000100000600\x0c\x0c\x0c16\x0c"
                if self.reads == 2:
                    self_test.assertEqual(len(sent), 2)
                    clock[0] = 100.0
                    return "\x1b\t000200000600\x0c\x0c\x0cjoined\x0c"
                if self.reads == 3:
                    clock[0] = 161.0
                    raise SocketTimeout()
                if self.reads == 4:
                    return ("\x1b\t000500002000\x0c첫째\x0ctester"
                            "\x0c닉네임\x0c0\x0c0\x0c시청자\x0c") * 2
                session.stop()
                return "\x1b\t000000000100\x0c"

        self_test = self
        metadata = BytesIO(json.dumps({
            "CHANNEL": {"CHDOMAIN": "chat.example.test",
                        "CHATNO": "123456", "CHPT": "12345"}
        }).encode())
        fake_socket = Socket()
        fake_websocket = SimpleNamespace(
            create_connection=lambda *args, **kwargs: fake_socket,
            WebSocketTimeoutException=SocketTimeout)
        with patch.dict(sys.modules, {"websocket": fake_websocket}), \
                patch("urllib.request.urlopen", return_value=metadata), \
                patch("ai_broadcaster.multiplatform_readonly.time.monotonic",
                      side_effect=lambda: clock[0]):
            session.run(max_seconds=240)
        self.assertEqual([packet[2:6] for packet in sent],
                         ["0001", "0002", "0000"])
        self.assertEqual(sum(kind == "ready" for kind, _ in events), 1)
        self.assertEqual([item.text for kind, item in events if kind == "chat"],
                         ["첫째", "첫째"])

    def test_readonly_socket_stop_during_blocking_receive_is_normal(self):
        """A stopped socket must not deliver stale chat or show an error."""
        from types import SimpleNamespace
        for failure_mode in ("empty", "closed"):
            with self.subTest(failure_mode=failure_mode):
                events = []
                session = SoopReadOnlySession(
                    "streamer/123", lambda kind, item: events.append((kind, item)))

                class Socket:
                    def settimeout(self, timeout):
                        pass

                    def recv(self):
                        session.stop()
                        if failure_mode == "closed":
                            raise OSError("Socket closed by the Stop button")
                        return ""

                    def close(self):
                        pass

                transport = SimpleNamespace(
                    WebSocketTimeoutException=TimeoutError)
                with patch.dict(sys.modules, {"websocket": transport}):
                    session._receive_socket(
                        Socket(),
                        lambda raw, channel: self.fail("Parsed after Stop"))
                self.assertEqual(events, [])

    def test_youtube_page_chat_and_superchat(self):
        items = [
            {"snippet":{"type":"textMessageEvent","displayMessage":"안녕"},
             "authorDetails":{"displayName":"첫사람"}},
            {"snippet":{"type":"superChatEvent","displayMessage":"응원합니다"},
             "authorDetails":{"displayName":"둘째"}},
            {"snippet":{"type":"messageDeletedEvent","displayMessage":"x"},
             "authorDetails":{"displayName":"운영자"}}]
        parsed = parse_youtube_page({"items":items},"liveId")
        self.assertEqual([(m.sender,m.text) for m in parsed],
                         [("첫사람","안녕"),("둘째","응원합니다")])
        self.assertTrue(all(x.platform=="youtube" for x in parsed))

    def test_youtube_video_address_resolves_actual_chat_id_and_preserves_messages(self):
        from urllib.parse import parse_qs, urlsplit
        calls, observed = [], []
        video = "AbCdEfGhI12"
        url = "https://www.youtube.com/watch?v=" + video
        def api(address, *, timeout=10):
            params = parse_qs(urlsplit(address).query)
            calls.append((urlsplit(address).path, params))
            if address.startswith("https://www.googleapis.com/youtube/v3/videos?"):
                self.assertEqual(params["part"], ["liveStreamingDetails"])
                self.assertEqual(params["id"], [video])
                return {"items":[{"liveStreamingDetails":{
                    "activeLiveChatId":"ACTUAL_LIVE_CHAT"}}]}
            self.assertEqual(params["liveChatId"], ["ACTUAL_LIVE_CHAT"])
            return {"nextPageToken":"cursor_2", "pollingIntervalMillis":1000,
                    "offlineAt":"2026-10-19T12:00:00Z",
                    "items":[
                        {"id":"A","snippet":{"type":"textMessageEvent",
                                            "displayMessage":"안녕"},
                         "authorDetails":{"displayName":"시청자"}},
                        {"id":"B","snippet":{"type":"textMessageEvent",
                                            "displayMessage":"안녕"},
                         "authorDetails":{"displayName":"시청자"}},
                    ]}
        session=YouTubeReadOnlySession(url,lambda k,v:observed.append((k,v)),"x"*39)
        with patch("ai_broadcaster.multiplatform_readonly._json_get",side_effect=api):
            session.run(max_seconds=3)
        self.assertEqual(len(calls),2)
        self.assertEqual([kind for kind,_ in observed], ["chat","chat","ready","stopped"])
        self.assertEqual([m.text for k,m in observed if k=="chat"],["안녕","안녕"])

    def test_youtube_live_url_short_url_and_raw_livechat_id(self):
        from ai_broadcaster.multiplatform_readonly import _youtube_video_id_or_none
        video = "AbCdEfGhI12"
        for url in (video, "https://youtu.be/"+video,
                    "https://youtube.com/live/"+video,
                    "https://m.youtube.com/watch?v="+video+"&t=1"):
            self.assertEqual(_youtube_video_id_or_none(url),video)
        self.assertIsNone(_youtube_video_id_or_none("Cg0KCLongChatID"))

    def test_youtube_rejects_non_youtube_urls_before_any_network(self):
        for bad in ("http://youtube.com/watch?v=AbCdEfGhI12",
                    "https://youtube.com.evil.com/watch?v=AbCdEfGhI12",
                    "https://youtube.com/watch?v=bad",
                    "https://www.youtube.com/live/AbCdEfGhI12#fragment"):
            with self.subTest(bad=bad),self.assertRaises(ValueError),patch(
                "ai_broadcaster.multiplatform_readonly._json_get",
                side_effect=AssertionError("Network must not be used")):
                YouTubeReadOnlySession(bad,lambda *args:None,"x"*39)

    def test_youtube_live_video_without_active_chat_reports_not_available(self):
        events=[]
        session=YouTubeReadOnlySession("AbCdEfGhI12",
                                      lambda *args:events.append(args),"x"*39)
        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   return_value={"items":[{"liveStreamingDetails":{}}]}) as api:
            with self.assertRaisesRegex(RuntimeError,"활성화된 유튜브 채팅방"):
                session.run(max_seconds=2)
        self.assertEqual(api.call_count,1)
        self.assertEqual(events,[])

    def test_youtube_stop_while_resolving_video_never_polls_or_emits(self):
        events=[]
        session=YouTubeReadOnlySession("AbCdEfGhI12",
                                      lambda *args:events.append(args),"x"*39)
        def stopped_api(url, *, timeout=10):
            session.stop()
            return {"items":[{"liveStreamingDetails":{
                "activeLiveChatId":"ACTUAL_LIVE_CHAT"}}]}
        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   side_effect=stopped_api) as api:
            session.run(max_seconds=3)
        self.assertEqual(api.call_count,1)
        self.assertEqual(events,[])

    def test_youtube_api_errors_never_show_key_to_operator(self):
        secret="private_api_key_"+"x"*34
        session=YouTubeReadOnlySession("AbCdEfGhI12",lambda *args:None,secret)
        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   side_effect=RuntimeError("HTTP 403 URL key="+secret)):
            with self.assertRaises(RuntimeError) as cm:
                session.run(max_seconds=2)
        self.assertNotIn(secret,str(cm.exception))

    def test_stop_in_middle_of_batched_socket_data_stops_delivery(self):
        from types import SimpleNamespace
        observed=[]
        session=SoopReadOnlySession("streamer/1",lambda kind, item:(
            observed.append(item), session.stop()))
        messages=[
            PlatformChat("streamer/1","viewer","첫째","soop"),
            PlatformChat("streamer/1","viewer","둘째","soop"),
            PlatformChat("streamer/1","viewer","셋째","soop")]
        class Sock:
            def settimeout(self, timeout):
                pass
            def recv(self):
                return "one-frame"
            def close(self):
                pass
        with patch.dict(sys.modules,{"websocket":SimpleNamespace(
            WebSocketTimeoutException=TimeoutError)}):
            session._receive_socket(Sock(),lambda data, channel:messages)
        self.assertEqual(observed,[messages[0]])

    def test_youtube_live_empty_cursor_does_not_repeat_first_page(self):
        events=[]
        chat=YouTubeReadOnlySession(
            "existingChatId",lambda kind,obj:events.append((kind,obj)),"k"*39)
        page={"nextPageToken":"","items":[
            {"snippet":{"type":"textMessageEvent","displayMessage":"안녕"},
             "authorDetails":{"displayName":"시청자"}}]}
        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   return_value=page) as api:
            with self.assertRaisesRegex(RuntimeError,"페이지 응답 토큰"):
                chat.run(max_seconds=2)
        self.assertEqual(api.call_count,1)
        self.assertEqual(events,[])

    def test_youtube_final_page_without_cursor_is_not_failure(self):
        from urllib.parse import urlsplit
        events=[]
        session=YouTubeReadOnlySession("existingChatID",
             lambda kind, payload: events.append((kind,payload)), "k"*39)
        page={"offlineAt":"2026-10-19T08:00:00Z",
              "items":[{"id":"one","snippet":{"type":"textMessageEvent",
                          "displayMessage":"마지막 채팅"},
                        "authorDetails":{"displayName":"시청자"}}]}
        with patch("ai_broadcaster.multiplatform_readonly._json_get",
                   return_value=page) as api:
            session.run(max_seconds=3)
        self.assertEqual(api.call_count,1)
        self.assertEqual([kind for kind,_ in events],["chat","ready","stopped"])
        self.assertEqual(events[0][1].text,"마지막 채팅")

    def test_whitespace_only_real_chat_is_preserved(self):
        data={"cmd":93101,"bdy":[
            {"profile":{"nickname":"시청자"},"msg":"  "},
            {"profile":{"nickname":"시청자"},"msg":""}]}
        self.assertEqual(
            [x.text for x in parse_chzzk_frame(json.dumps(data),"room")],["  "])
        page={"items":[
            {"snippet":{"type":"textMessageEvent","displayMessage":"  "},
             "authorDetails":{"displayName":"시청자"}},
            {"snippet":{"type":"textMessageEvent","displayMessage":""},
             "authorDetails":{"displayName":"시청자"}}]}
        self.assertEqual(
            [x.text for x in parse_youtube_page(page,"chat")],["  "])

    def test_no_auth_or_platform_send_on_initialization(self):
        cb=lambda *x: None
        self.assertEqual(ChzzkReadOnlySession("a"*32,cb).channel,"a"*32)
        self.assertEqual(SoopReadOnlySession("bjid/123",cb).channel,"bjid/123")
        self.assertEqual(YouTubeReadOnlySession("chatId",cb,"x"*39).channel,"chatId")
        with self.assertRaises(ValueError):
            ChzzkReadOnlySession("bad",cb)
        with self.assertRaises(ValueError):
            SoopReadOnlySession("https://evil/1",cb)
        with self.assertRaises(ValueError):
            YouTubeReadOnlySession("chatId",cb,"")

    def test_operator_settings_preserve_all_four_platform_choices(self):
        value=dict(DEFAULTS)
        value["platforms"]=["chzzk","soop","youtube","twitch"]
        self.assertEqual(validate_settings(value)["platforms"],
                         ["chzzk","soop","youtube","twitch"])

    def test_stop_before_socket_start_prevents_external_connect(self):
        for cls, target, credential in ((ChzzkReadOnlySession, "a"*32, None),
                                        (SoopReadOnlySession, "bjid/123", None),
                                        (YouTubeReadOnlySession, "livechat", "x"*39)):
            with self.subTest(cls=cls), patch(
                "ai_broadcaster.multiplatform_readonly._json_get",
                side_effect=AssertionError("Unexpected network request")):
                obj=(cls(target, lambda *x: None) if credential is None else
                     cls(target, lambda *x: None, credential))
                obj.stop()
                obj.run(max_seconds=1)


if __name__=="__main__":
    unittest.main()
