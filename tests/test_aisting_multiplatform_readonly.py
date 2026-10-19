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
        one = ("\x1b\\t000500002000\x0c첫째\x0ctester"
               "\x0c닉네임\x0c0\x0c0\x0c시청자\x0c")
        second = one.replace("첫째", "둘째")
        self.assertEqual(
            [x.text for x in parse_soop_frame(one + second, "bj/1")],
            ["첫째", "둘째"])
        self.assertEqual(
            [x.text for x in parse_soop_frame(one + one, "bj/1")],
            ["첫째", "첫째"])

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
