# -*- coding: utf-8 -*-
"""로컬 수신 큐 관측기 검증. 실플랫폼·Windows/OBS/모델 통합검사 아님."""
import unittest

from ai_broadcaster.live_queue_wait_observation import LiveQueueWaitTracker


class LiveQueueWaitTrackerTests(unittest.TestCase):
    def setUp(self):
        self.now = [100.0]
        self.tracker = LiveQueueWaitTracker(lambda: self.now[0])

    def test_동시_플랫폼_대기_구분(self):
        a = self.tracker.begin("twitch")
        self.now[0] += 1
        b = self.tracker.begin("twitch")
        c = self.tracker.begin("soop")
        self.now[0] += 2
        snapshot = self.tracker.snapshot()
        self.assertEqual(snapshot["twitch"]["진행중"], 2)
        self.assertEqual(snapshot["twitch"]["진행최장초"], 3.0)
        self.assertEqual(snapshot["soop"]["진행중"], 1)
        self.tracker.finish(a, accepted=True)
        self.tracker.finish(b, accepted=False)
        self.tracker.finish(c, accepted=False)
        snapshot = self.tracker.snapshot()
        self.assertEqual(snapshot["twitch"]["중단"], 1)
        self.assertEqual(snapshot["twitch"]["중단누적초"], 2.0)
        self.assertEqual(snapshot["soop"]["중단"], 1)
        self.assertEqual(snapshot["soop"]["중단누적초"], 2.0)

    def test_수용은_중단으로_계산하지_않음(self):
        token = self.tracker.begin("youtube")
        self.now[0] += 4
        self.tracker.finish(token, accepted=True)
        self.assertIsNone(self.tracker.snapshot().get("youtube"))

    def test_중복_종료는_두번_계산하지_않음(self):
        token = self.tracker.begin("chzzk")
        self.now[0] += 2
        self.tracker.finish(token, accepted=False)
        self.tracker.finish(token, accepted=False)
        self.assertEqual(self.tracker.snapshot()["chzzk"]["중단"], 1)

    def test_미분류_대기와_시간_역행(self):
        token = self.tracker.begin("")
        self.now[0] -= 3
        self.assertEqual(self.tracker.snapshot()["미분류"]["진행최장초"], 0.0)
        self.tracker.finish(token, accepted=False)
        self.assertEqual(self.tracker.snapshot()["미분류"]["중단누적초"], 0.0)


if __name__ == "__main__":
    unittest.main()
