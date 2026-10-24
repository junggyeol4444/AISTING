"""166회차: 선택된 모든 플랫폼의 동시 ready 관측 구간 가상 계약검사.

가상 단조시계만 사용한다. 실제 24시간, 실제 채팅 무누락, 방송 송출,
시청자 수신을 검사하거나 입증하지 않는다.
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


class 선택플랫폼동시입장관측검사(unittest.TestCase):
    def setUp(self):
        self.clock = [10.0]
        self.clock_patch = patch.object(
            module.time, "monotonic", side_effect=lambda: self.clock[0])
        self.clock_patch.start()
        self.addCleanup(self.clock_patch.stop)
        patches = [
            patch.object(module, name, 가상수신기)
            for name in ("TwitchReadOnlySession", "ChzzkReadOnlySession",
                         "SoopReadOnlySession", "YouTubeReadOnlySession")
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.events = []
        self.codes = ("twitch", "chzzk", "soop", "youtube")
        self.session = module.MultiPlatformReadOnlySession(
            {code: "가상채널" for code in self.codes},
            lambda kind, item: self.events.append((kind, item)) or True,
        )
        self.session._session_started_at = self.clock[0]

    def ready(self, code, at):
        self.clock[0] = at
        self.session._callbacks[code]("ready", None)

    def leave(self, code, at):
        self.clock[0] = at
        with self.session._emit_lock:
            self.session._end_ready_interval_locked(code, at)

    def stat(self, at):
        self.clock[0] = at
        return self.session.reconnect_snapshot()["twitch"]

    def test_three_of_four_are_not_all_ready(self):
        for code in self.codes[:3]:
            self.ready(code, 20.0)
        data = self.stat(50.0)
        self.assertFalse(data["선택플랫폼동시입장현재"])
        self.assertEqual(data["선택플랫폼동시입장누적초"], 0.0)

    def test_fourth_ready_starts_common_interval_only_from_fourth(self):
        for code in self.codes[:3]:
            self.ready(code, 20.0)
        self.ready(self.codes[3], 25.0)
        data = self.stat(35.0)
        self.assertTrue(data["선택플랫폼동시입장현재"])
        self.assertEqual(data["선택플랫폼동시입장누적초"], 10.0)
        self.assertEqual(data["선택플랫폼동시입장최장초"], 10.0)

    def test_any_disconnect_ends_common_interval_without_erasing_history(self):
        for code in self.codes:
            self.ready(code, 20.0)
        self.leave("soop", 40.0)
        data = self.stat(100.0)
        self.assertFalse(data["선택플랫폼동시입장현재"])
        self.assertEqual(data["선택플랫폼동시입장누적초"], 20.0)
        self.assertEqual(data["선택플랫폼동시입장최장초"], 20.0)
        self.ready("soop", 100.0)
        data = self.stat(115.0)
        self.assertTrue(data["선택플랫폼동시입장현재"])
        self.assertEqual(data["선택플랫폼동시입장누적초"], 35.0)
        self.assertEqual(data["선택플랫폼동시입장최장초"], 20.0)

    def test_24_hour_boundary_counts_only_actual_common_streak(self):
        for code in self.codes:
            self.ready(code, 20.0)
        data = self.stat(86420.0)
        self.assertEqual(data["선택플랫폼동시입장24시간관측구간"], 1)
        self.leave("youtube", 86430.0)
        data = self.stat(86431.0)
        self.assertEqual(data["선택플랫폼동시입장24시간관측구간"], 1)
        self.assertFalse(data["선택플랫폼동시입장현재"])

    def test_disjoint_individual_ready_intervals_are_not_common_24h(self):
        for code in self.codes[:3]:
            self.ready(code, 20.0)
        self.leave("twitch", 90020.0)
        self.ready("youtube", 90021.0)
        data = self.stat(90025.0)
        self.assertEqual(data["선택플랫폼동시입장24시간관측구간"], 0)
        self.assertEqual(data["선택플랫폼동시입장누적초"], 0.0)

    def test_repeated_ready_does_not_restart_common_interval(self):
        for code in self.codes:
            self.ready(code, 20.0)
        self.ready("chzzk", 30.0)
        self.assertEqual(self.stat(40.0)["선택플랫폼동시입장누적초"], 20.0)

    def test_operator_stop_closes_common_interval_once(self):
        for code in self.codes:
            self.ready(code, 20.0)
        self.clock[0] = 40.0
        self.session.stop()
        data = self.stat(100.0)
        self.assertEqual(data["선택플랫폼동시입장누적초"], 20.0)
        self.assertFalse(data["선택플랫폼동시입장현재"])
        self.session.stop()
        self.assertEqual(self.stat(200.0)["선택플랫폼동시입장누적초"], 20.0)

    def test_same_common_metrics_exposed_per_selected_platform(self):
        for code in self.codes:
            self.ready(code, 20.0)
        self.clock[0] = 24.0
        snapshots = self.session.reconnect_snapshot()
        self.assertEqual(
            {item["선택플랫폼동시입장누적초"] for item in snapshots.values()},
            {4.0},
        )


if __name__ == "__main__":
    unittest.main()
