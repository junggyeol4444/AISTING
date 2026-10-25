"""176회차: 실제 수용 채팅의 파싱→콜백 진입→FIFO 수용 지연 분해 계약검사.

가상 사건/로컬 단조시각만 사용. 실제 플랫폼·수백 명·Windows/OBS·
모델 지연이나 시청자 1~3초 달성 증거가 아니다.
"""
import time
import unittest

from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession
from ai_broadcaster.multiplatform_readonly import PlatformChat
from ai_broadcaster.twitch_readonly import TwitchChatLine


class ParseCallbackAcceptStagesTests(unittest.TestCase):
    def session(self, emit=None):
        return MultiPlatformReadOnlySession(
            {"twitch": "tester", "chzzk": "a" * 32,
             "soop": "caster/1", "youtube": "LCabc"},
            emit if emit is not None else (lambda kind, item: True),
            youtube_api_key="x" * 24)

    def test_four_platforms_have_separate_accepted_stage_samples(self):
        session = self.session()
        now = time.monotonic()
        for code in ("twitch", "chzzk", "soop", "youtube"):
            item = (TwitchChatLine("tester", "a", "같은 본문", None, now - 0.3)
                    if code == "twitch" else
                    PlatformChat("채널", "a", "같은 본문", code,
                                 None, now - 0.3))
            self.assertTrue(session._callbacks[code]("chat", item))
        for code, row in session.reconnect_snapshot().items():
            self.assertEqual(row["파싱후콜백최근표본"], 1, code)
            self.assertEqual(row["콜백진입후수용최근표본"], 1, code)
            self.assertEqual(row["파싱후수용최근표본"], 1, code)
            self.assertGreaterEqual(row["파싱후콜백최근p95초"], 0.3)
            self.assertGreaterEqual(row["콜백진입후수용최근p95초"], 0)

    def test_parse_to_callback_over_three_is_not_callback_delay(self):
        session = self.session()
        session._callbacks["twitch"]("chat", TwitchChatLine(
            "tester", "a", "지연", None, time.monotonic() - 4))
        row = session.reconnect_snapshot()["twitch"]
        self.assertEqual(row["파싱후콜백3초초과"], 1)
        self.assertEqual(row["파싱후수용3초초과"], 1)
        self.assertEqual(row["콜백진입후수용3초초과"], 0)

    def test_callback_processing_time_is_measured(self):
        def slow_emit(kind, item):
            time.sleep(0.025)
            return True
        session = self.session(slow_emit)
        session._callbacks["youtube"]("chat", PlatformChat(
            "LCabc", "a", "처리", "youtube",
            None, time.monotonic() - 0.1))
        row = session.reconnect_snapshot()["youtube"]
        self.assertGreaterEqual(row["콜백진입후수용최근p95초"], 0.02)
        self.assertGreaterEqual(row["파싱후수용최근p95초"],
                                row["파싱후콜백최근p95초"])

    def test_missing_timestamp_never_fabricates_stage_samples(self):
        session = self.session()
        session._callbacks["soop"]("chat", PlatformChat(
            "caster/1", "a", "시각없음", "soop"))
        row = session.reconnect_snapshot()["soop"]
        self.assertEqual(row["파싱후콜백최근표본"], 0)
        self.assertEqual(row["콜백진입후수용최근표본"], 0)
        self.assertEqual(row["파싱시각미확인수용"], 1)

    def test_future_timestamp_never_fabricates_stage_samples(self):
        session = self.session()
        session._callbacks["soop"]("chat", PlatformChat(
            "caster/1", "a", "미래", "soop",
            None, time.monotonic() + 100))
        row = session.reconnect_snapshot()["soop"]
        self.assertEqual(row["파싱후콜백최근표본"], 0)
        self.assertEqual(row["콜백진입후수용최근표본"], 0)

    def test_callback_rejection_never_counts_as_accepted(self):
        session = self.session(lambda kind, item: False)
        self.assertFalse(session._callbacks["youtube"]("chat", PlatformChat(
            "LCabc", "a", "거절", "youtube",
            None, time.monotonic() - 1)))
        row = session.reconnect_snapshot()["youtube"]
        self.assertEqual(row["콜백전달중단"], 1)
        self.assertEqual(row["파싱후콜백최근표본"], 0)
        self.assertEqual(row["콜백진입후수용최근표본"], 0)

    def test_callback_exception_never_counts_as_accepted(self):
        def broken(kind, item):
            raise RuntimeError("모의 FIFO 실패")
        session = self.session(broken)
        with self.assertRaises(RuntimeError):
            session._callbacks["chzzk"]("chat", PlatformChat(
                "채널", "a", "예외", "chzzk",
                None, time.monotonic() - 1))
        row = session.reconnect_snapshot()["chzzk"]
        self.assertEqual(row["콜백전달오류"], 1)
        self.assertEqual(row["파싱후콜백최근표본"], 0)
        self.assertEqual(row["콜백진입후수용최근표본"], 0)

    def test_duplicate_id_is_not_another_latency_sample(self):
        session = self.session()
        for i in range(2):
            session._callbacks["youtube"]("chat", PlatformChat(
                "LCabc", "a", "같은 사건", "youtube",
                "evt-1", time.monotonic() - (i + 1)))
        row = session.reconnect_snapshot()["youtube"]
        self.assertEqual(row["콜백내부중복ID"], 1)
        self.assertEqual(row["파싱후콜백최근표본"], 1)
        self.assertEqual(row["콜백진입후수용최근표본"], 1)

    def test_stop_never_creates_accepted_latency(self):
        session = self.session()
        session.stop()
        self.assertFalse(session._callbacks["twitch"]("chat", TwitchChatLine(
            "tester", "a", "중지", None, time.monotonic() - 1)))
        row = session.reconnect_snapshot()["twitch"]
        self.assertEqual(row["파싱후콜백최근표본"], 0)
        self.assertEqual(row["콜백진입후수용최근표본"], 0)
        self.assertEqual(row["중지후채팅거절"], 1)


if __name__ == "__main__":
    unittest.main()
