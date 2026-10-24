"""167회차: 수신기 종료·통신 무응답의 동시 입장 관측 가상 계약검사.

네트워크·실제 24시간·실계정·방송·OBS·음성 모델을 실행하지 않는다.
아래 시각은 단조시계의 가상 값이며 실사용 증빙이 아니다.
"""
import unittest
from unittest.mock import patch

from ai_broadcaster import multi_platform_session as module


class 가상수신기:
    def __init__(self, *args, **kwargs):
        self.stopped = False

    def stop(self):
        self.stopped = True

    def run(self, *, max_seconds=None):
        return None


class 수신기종료동시입장관측검사(unittest.TestCase):
    def setUp(self):
        self.clock = [10.0]
        p = patch.object(
            module.time, "monotonic", side_effect=lambda: self.clock[0])
        p.start()
        self.addCleanup(p.stop)
        for name in ("TwitchReadOnlySession", "ChzzkReadOnlySession",
                     "SoopReadOnlySession", "YouTubeReadOnlySession"):
            p = patch.object(module, name, 가상수신기)
            p.start()
            self.addCleanup(p.stop)
        self.codes = ("twitch", "chzzk", "soop", "youtube")
        self.emitted = []
        self.session = module.MultiPlatformReadOnlySession(
            {code: "가상채널" for code in self.codes},
            lambda kind, item: self.emitted.append((kind, item)) or True,
        )
        self.session._session_started_at = self.clock[0]

    def notify(self, code, kind, at):
        self.clock[0] = at
        return self.session._callbacks[code](kind, None)

    def ready_all(self, at=20.0):
        for code in self.codes:
            self.notify(code, "ready", at)

    def stat(self, code, at):
        self.clock[0] = at
        return self.session.reconnect_snapshot()[code]

    def test_reader_stopped_immediately_ends_common_ready(self):
        self.ready_all()
        self.notify("soop", "stopped", 35.0)
        data = self.stat("twitch", 100.0)
        self.assertFalse(data["선택플랫폼동시입장현재"])
        self.assertEqual(data["선택플랫폼동시입장누적초"], 15.0)
        self.assertFalse(self.stat("soop", 100.0)["채팅방입장"])

    def test_duplicate_stopped_does_not_double_count(self):
        self.ready_all()
        self.notify("chzzk", "stopped", 35.0)
        self.notify("chzzk", "stopped", 75.0)
        self.assertEqual(
            self.stat("twitch", 100.0)["선택플랫폼동시입장누적초"],
            15.0)
        self.assertEqual(
            self.stat("chzzk", 100.0)["입장관측누적초"], 15.0)

    def test_stalled_ends_ready_before_exception_cleanup(self):
        self.ready_all()
        self.notify("twitch", "transport_stalled", 33.0)
        data = self.stat("twitch", 35.0)
        self.assertEqual(data["통신무응답재연결"], 1)
        self.assertTrue(data["현재공백"])
        self.assertFalse(data["채팅방입장"])
        self.assertEqual(data["선택플랫폼동시입장누적초"], 13.0)

    def test_stalled_gap_starts_at_first_notice_not_later_cleanup(self):
        self.ready_all()
        self.notify("youtube", "transport_stalled", 30.0)
        self.notify("youtube", "stopped", 34.0)
        self.notify("youtube", "ready", 50.0)
        data = self.stat("youtube", 60.0)
        self.assertEqual(data["재연결완료"], 1)
        self.assertEqual(data["관측공백초"], 20.0)
        self.assertEqual(data["선택플랫폼동시입장누적초"], 20.0)
        self.assertEqual(data["선택플랫폼동시입장최장초"], 10.0)

    def test_duplicate_stalled_keeps_earliest_gap(self):
        self.ready_all()
        self.notify("soop", "transport_stalled", 30.0)
        self.notify("soop", "transport_stalled", 34.0)
        self.notify("soop", "ready", 50.0)
        data = self.stat("soop", 55.0)
        self.assertEqual(data["통신무응답재연결"], 2)
        self.assertEqual(data["관측공백초"], 20.0)
        self.assertEqual(data["재연결완료"], 1)

    def test_stalled_before_24_hours_prevents_false_24h_streak(self):
        self.ready_all()
        self.notify("twitch", "transport_stalled", 86399.0)
        data = self.stat("twitch", 90000.0)
        self.assertEqual(data["선택플랫폼동시입장24시간관측구간"], 0)
        self.assertEqual(data["24시간연속입장관측완료구간"], 0)

    def test_one_stopped_reader_does_not_close_other_readers(self):
        self.ready_all()
        self.notify("chzzk", "stopped", 31.0)
        data = self.stat("twitch", 45.0)
        self.assertTrue(data["채팅방입장"])
        self.assertFalse(data["선택플랫폼동시입장현재"])
        self.assertEqual(data["입장관측누적초"], 25.0)

    def test_clean_stopped_does_not_invent_reconnect_gap(self):
        self.ready_all()
        self.notify("youtube", "stopped", 35.0)
        data = self.stat("youtube", 50.0)
        self.assertFalse(data["현재공백"])
        self.assertEqual(data["관측공백초"], 0.0)
        self.assertEqual(data["재연결완료"], 0)

    def test_stalled_callback_does_not_emit_chat_or_outbound_status(self):
        self.ready_all()
        previous = len(self.emitted)
        self.notify("twitch", "transport_stalled", 30.0)
        self.assertEqual(len(self.emitted), previous)
        self.assertEqual(
            self.stat("twitch", 31.0)["콜백수신"], 0)

    def test_operator_stop_does_not_extend_finished_interval(self):
        self.ready_all()
        self.notify("soop", "stopped", 30.0)
        self.clock[0] = 50.0
        self.session.stop()
        self.assertEqual(
            self.stat("twitch", 90000.0)["선택플랫폼동시입장누적초"],
            10.0)


if __name__ == "__main__":
    unittest.main()
