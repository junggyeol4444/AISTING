"""175회차 채팅 파싱→AI FIFO 수용 지연의 가상 계약검사.

전부 로컬 시각/가상 사건으로 구성하며 실수백 명·실방송·실모델 검사가 아니다.
네트워크 접속, 채팅 발신, 방송/녹화, OAuth 동의, 모델 학습을 실행하지 않는다.
"""
import time
import unittest
from collections import deque

from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession
from ai_broadcaster.multiplatform_readonly import (
    PlatformChat, parse_youtube_page,
)
from ai_broadcaster.twitch_readonly import (
    TwitchChatLine, parse_irc_chat_line,
)


class ParseToFifoLatencyTests(unittest.TestCase):
    def setUp(self):
        self.accepted = []
        self.session = MultiPlatformReadOnlySession(
            {"twitch": "tester", "chzzk": "a" * 32,
             "soop": "caster/1", "youtube": "LCabc"},
            lambda kind, item: self.accepted.append((kind, item)) or True,
            youtube_api_key="x" * 24)

    def test_twitch_irc_parser_records_local_parse_time(self):
        before = time.monotonic()
        chat = parse_irc_chat_line(
            "@id=evt1 :alice!x@y PRIVMSG #tester :안녕", "tester")
        after = time.monotonic()
        self.assertIsNotNone(chat)
        self.assertTrue(before <= chat.parsed_at_monotonic <= after)

    def test_youtube_parser_records_local_parse_time(self):
        before = time.monotonic()
        chats = parse_youtube_page({
            "items": [{"id": "evt1", "snippet": {
                "type": "textMessageEvent", "displayMessage": "안녕"},
                "authorDetails": {"displayName": "시청자"}}]}, "LCabc")
        after = time.monotonic()
        self.assertEqual(len(chats), 1)
        self.assertTrue(before <= chats[0].parsed_at_monotonic <= after)

    def test_four_platforms_measure_accepted_events_without_merging_text(self):
        now = time.monotonic()
        for code in ("twitch", "chzzk", "soop", "youtube"):
            chat = (TwitchChatLine("tester", "시청자", "같은 내용", None, now - 0.2)
                    if code == "twitch" else
                    PlatformChat("채널", "시청자", "같은 내용", code,
                                 None, now - 0.2))
            self.assertTrue(self.session._callbacks[code]("chat", chat))
        snapshot = self.session.reconnect_snapshot()
        self.assertEqual(len(self.accepted), 4)
        for code in ("twitch", "chzzk", "soop", "youtube"):
            self.assertEqual(snapshot[code]["파싱후수용최근표본"], 1)
            self.assertGreaterEqual(snapshot[code]["파싱후수용최근p95초"], 0.2)
            self.assertEqual(snapshot[code]["파싱시각미확인수용"], 0)

    def test_reconnect_delay_over_three_seconds_is_counted(self):
        now = time.monotonic()
        self.session._callbacks["twitch"](
            "chat", TwitchChatLine("tester", "a", "지연", None, now - 4))
        result = self.session.reconnect_snapshot()["twitch"]
        self.assertEqual(result["파싱후수용3초초과"], 1)
        self.assertGreaterEqual(result["파싱후수용최장초"], 4)

    def test_duplicate_server_id_is_not_new_accepted_latency_sample(self):
        now = time.monotonic()
        callback = self.session._callbacks["youtube"]
        callback("chat", PlatformChat("LCabc", "a", "첫 채팅", "youtube",
                                       "same-id", now - 1))
        callback("chat", PlatformChat("LCabc", "a", "재전송", "youtube",
                                       "same-id", now - 9))
        result = self.session.reconnect_snapshot()["youtube"]
        self.assertEqual(result["파싱후수용최근표본"], 1)
        self.assertEqual(result["콜백내부중복ID"], 1)
        self.assertEqual(len(self.accepted), 1)

    def test_unknown_parse_time_not_reported_as_measured(self):
        self.session._callbacks["soop"](
            "chat", PlatformChat("caster/1", "a", "시각없음", "soop"))
        result = self.session.reconnect_snapshot()["soop"]
        self.assertEqual(result["파싱후수용최근표본"], 0)
        self.assertEqual(result["파싱시각미확인수용"], 1)
        self.assertIsNone(result["파싱후수용최근p95초"])

    def test_future_parse_time_not_reported_as_measured(self):
        self.session._callbacks["soop"](
            "chat", PlatformChat("caster/1", "a", "미래", "soop",
                                 None, time.monotonic() + 60))
        result = self.session.reconnect_snapshot()["soop"]
        self.assertEqual(result["파싱후수용최근표본"], 0)
        self.assertEqual(result["파싱시각미확인수용"], 1)

    def test_pending_oldest_age_from_websocket_reconnect(self):
        self.session._pending_websocket_chats["twitch"].extend([
            TwitchChatLine("tester", "a", "오래된 것", None, time.monotonic() - 5),
            TwitchChatLine("tester", "b", "새로운 것", None, time.monotonic() - 1)])
        result = self.session.reconnect_snapshot()["twitch"]
        self.assertGreaterEqual(result["파싱후미수용최장경과초"], 5)
        self.assertEqual(result["파싱후수용최근표본"], 0)

    def test_pending_prejoin_age(self):
        self.session._prejoin_resume_states["chzzk"].pending.append(
            PlatformChat("채널", "a", "JOIN 전", "chzzk",
                         None, time.monotonic() - 3))
        result = self.session.reconnect_snapshot()["chzzk"]
        self.assertGreaterEqual(result["파싱후미수용최장경과초"], 3)

    def test_pending_youtube_page_age(self):
        self.session._youtube_resume.pending_page_chats.append(
            PlatformChat("LCabc", "a", "페이지", "youtube",
                         None, time.monotonic() - 2))
        result = self.session.reconnect_snapshot()["youtube"]
        self.assertGreaterEqual(result["파싱후미수용최장경과초"], 2)

    def test_missing_pending_timestamp_is_not_guessed(self):
        self.session._pending_websocket_chats["twitch"].append(
            TwitchChatLine("tester", "a", "시각없음"))
        result = self.session.reconnect_snapshot()["twitch"]
        self.assertIsNone(result["파싱후미수용최장경과초"])

    def test_stopping_does_not_generate_fake_latency_samples(self):
        self.session.stop()
        self.assertFalse(self.session._callbacks["youtube"](
            "chat", PlatformChat("LCabc", "a", "중지 뒤", "youtube",
                                 None, time.monotonic())))
        result = self.session.reconnect_snapshot()["youtube"]
        self.assertEqual(result["파싱후수용최근표본"], 0)
        self.assertEqual(result["중지후채팅거절"], 1)


if __name__ == "__main__":
    unittest.main()
