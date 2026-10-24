"""168회차: 무기한 실제 읽기 종료시각 기반 공백 관측 가상 계약검사.

네트워크·OBS·계정·방송·실제 24시간은 실행하지 않는다.
가상 단조시각과 가상 수신기로만 기존 계약을 확인하도록 작성했다.
"""
import unittest
from unittest.mock import patch

from ai_broadcaster import multi_platform_session as module


class 가상수신기:
    def __init__(self, *args, **kwargs):
        self._terminal_chat_end = False
        self.stopped = False

    def stop(self):
        self.stopped = True

    def run(self, *, max_seconds=None):
        return None


class 예기치않은수신종료공백검사(unittest.TestCase):
    def setUp(self):
        self.clock = [10.0]
        time_patch = patch.object(
            module.time, "monotonic", side_effect=lambda: self.clock[0])
        time_patch.start()
        self.addCleanup(time_patch.stop)
        for name in ("TwitchReadOnlySession", "ChzzkReadOnlySession",
                     "SoopReadOnlySession", "YouTubeReadOnlySession"):
            reader_patch = patch.object(module, name, 가상수신기)
            reader_patch.start()
            self.addCleanup(reader_patch.stop)
        self.codes = ("twitch", "chzzk", "soop", "youtube")
        self.events = []
        self.session = module.MultiPlatformReadOnlySession(
            {code: "가상채널" for code in self.codes},
            lambda kind, item: self.events.append((kind, item)) or True)
        self.session._session_started_at = 10.0
        self.session._running = True
        self.session._run_max_seconds = None

    def notify(self, code, kind, at):
        self.clock[0] = at
        return self.session._callbacks[code](kind, None)

    def snapshot(self, code, at):
        self.clock[0] = at
        return self.session.reconnect_snapshot()[code]

    def ready_all(self, at=20.0):
        for code in self.codes:
            self.notify(code, "ready", at)

    def test_unexpected_stopped_starts_gap_before_read_loop_exception(self):
        self.ready_all()
        self.notify("chzzk", "stopped", 31.0)
        data = self.snapshot("chzzk", 35.0)
        self.assertTrue(data["현재공백"])
        self.assertEqual(data["관측공백초"], 4.0)
        self.assertEqual(data["예기치않은수신기종료"], 1)
        self.assertFalse(data["채팅방입장"])

    def test_reconnect_gap_preserves_first_stopped_timestamp(self):
        self.ready_all()
        self.notify("twitch", "stopped", 30.0)
        self.clock[0] = 38.0
        with self.session._emit_lock:
            self.session._disconnect_started.setdefault("twitch", 38.0)
        self.notify("twitch", "ready", 50.0)
        data = self.snapshot("twitch", 55.0)
        self.assertEqual(data["관측공백초"], 20.0)
        self.assertEqual(data["재연결완료"], 1)
        self.assertEqual(data["예기치않은수신기종료"], 1)

    def test_duplicate_stopped_does_not_double_count_gap(self):
        self.ready_all()
        self.notify("soop", "stopped", 30.0)
        self.notify("soop", "stopped", 35.0)
        data = self.snapshot("soop", 40.0)
        self.assertEqual(data["관측공백초"], 10.0)
        self.assertEqual(data["예기치않은수신기종료"], 1)

    def test_stalled_then_stopped_keeps_original_gap(self):
        self.ready_all()
        self.notify("youtube", "transport_stalled", 30.0)
        self.notify("youtube", "stopped", 35.0)
        data = self.snapshot("youtube", 45.0)
        self.assertEqual(data["관측공백초"], 15.0)
        self.assertEqual(data["통신무응답재연결"], 1)
        self.assertEqual(data["예기치않은수신기종료"], 0)

    def test_finite_inspection_stopped_does_not_invent_gap(self):
        self.session._run_max_seconds = 60.0
        self.ready_all()
        self.notify("chzzk", "stopped", 30.0)
        data = self.snapshot("chzzk", 40.0)
        self.assertFalse(data["현재공백"])
        self.assertEqual(data["관측공백초"], 0.0)
        self.assertEqual(data["예기치않은수신기종료"], 0)

    def test_operator_stop_then_stopped_does_not_invent_gap(self):
        self.ready_all()
        self.clock[0] = 30.0
        self.session.stop()
        self.notify("twitch", "stopped", 35.0)
        data = self.snapshot("twitch", 40.0)
        self.assertFalse(data["현재공백"])
        self.assertEqual(data["예기치않은수신기종료"], 0)

    def test_youtube_terminal_chat_end_is_not_network_outage(self):
        self.ready_all()
        self.session._readers["youtube"]._terminal_chat_end = True
        self.notify("youtube", "stopped", 30.0)
        data = self.snapshot("youtube", 40.0)
        self.assertFalse(data["현재공백"])
        self.assertEqual(data["예기치않은수신기종료"], 0)

    def test_stopped_without_started_run_does_not_invent_gap(self):
        self.session._running = False
        self.ready_all()
        self.notify("soop", "stopped", 30.0)
        data = self.snapshot("soop", 40.0)
        self.assertFalse(data["현재공백"])
        self.assertEqual(data["예기치않은수신기종료"], 0)

    def test_other_three_platforms_stay_ready_after_one_stopped(self):
        self.ready_all()
        self.notify("soop", "stopped", 30.0)
        data = self.snapshot("twitch", 45.0)
        self.assertTrue(data["채팅방입장"])
        self.assertFalse(data["선택플랫폼동시입장현재"])
        self.assertEqual(data["선택플랫폼동시입장누적초"], 10.0)

    def test_gap_does_not_create_chat_or_outbound_event(self):
        self.ready_all()
        old = len(self.events)
        self.notify("chzzk", "stopped", 30.0)
        self.assertEqual(len(self.events), old)
        self.assertEqual(self.snapshot("chzzk", 31.0)["콜백수신"], 0)


if __name__ == "__main__":
    unittest.main()
