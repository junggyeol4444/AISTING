"""공식 첫 WAV 수신 *후보*의 로컬 지연 계약검사.

모의 시각만 사용한다. 실제 GPT-SoVITS 합성·Cubism·OBS·시청자 실증 아님.
"""
import unittest

from ai_broadcaster.live_runtime_metrics import LiveFirstWavLatencyMetrics


class FirstWavCandidateLatencyTests(unittest.TestCase):
    def test_파싱부터첫_wav후보_구간(self):
        m = LiveFirstWavLatencyMetrics()
        self.assertTrue(m.observe(10, 11, 12, 0.5, True))
        state = m.snapshot()
        self.assertEqual(state["WAV수신후보"], 1)
        self.assertAlmostEqual(state["파싱부터전송대기p95초"], 2)
        self.assertAlmostEqual(state["전송부터WAV후보p95초"], 0.5)
        self.assertAlmostEqual(state["파싱부터후보p95초"], 2.5)

    def test_3초_초과_후보(self):
        m = LiveFirstWavLatencyMetrics()
        self.assertTrue(m.observe(10, 11, 12, 1.5, True))
        self.assertEqual(m.snapshot()["3초초과후보"], 1)

    def test_정확히_3초_초과_아님(self):
        m = LiveFirstWavLatencyMetrics()
        self.assertTrue(m.observe(10, 11, 12, 1, True))
        self.assertEqual(m.snapshot()["3초초과후보"], 0)

    def test_wav_미관측은_성공_아님(self):
        m = LiveFirstWavLatencyMetrics()
        self.assertFalse(m.observe(10, 11, 12, None, False))
        self.assertEqual(m.snapshot()["WAV미관측"], 1)
        self.assertIsNone(m.snapshot()["파싱부터후보p95초"])

    def test_관찰_오류는_미관측과_분리(self):
        m = LiveFirstWavLatencyMetrics()
        m.error()
        self.assertEqual(m.snapshot()["전송관찰오류"], 1)
        self.assertEqual(m.snapshot()["관찰시도"], 1)
        self.assertEqual(m.snapshot()["WAV미관측"], 0)

    def test_파싱시각_없는_경우_성공표본_제외(self):
        m = LiveFirstWavLatencyMetrics()
        self.assertFalse(m.observe(None, 11, 12, 1, True))
        self.assertEqual(m.snapshot()["파싱시각누락"], 1)
        self.assertEqual(m.snapshot()["WAV수신후보"], 0)

    def test_파싱시각_역행_거부(self):
        m = LiveFirstWavLatencyMetrics()
        self.assertFalse(m.observe(12, 11, 13, 1, True))
        self.assertEqual(m.snapshot()["시각오류"], 1)

    def test_전송시각_역행_거부(self):
        m = LiveFirstWavLatencyMetrics()
        self.assertFalse(m.observe(10, 12, 11, 1, True))

    def test_비정상_시간_거부(self):
        m = LiveFirstWavLatencyMetrics()
        self.assertFalse(m.observe(10, 11, 12, float("nan"), True))
        self.assertFalse(m.observe(10, 11, 12, float("inf"), True))
        self.assertFalse(m.observe(10, 11, 12, -1, True))
        self.assertEqual(m.snapshot()["시각오류"], 3)

    def test_미관측인데_시간이_있으면_오류(self):
        m = LiveFirstWavLatencyMetrics()
        self.assertFalse(m.observe(10, 11, 12, 1, False))
        self.assertEqual(m.snapshot()["시각오류"], 1)

    def test_잘못된_관찰_플래그(self):
        m = LiveFirstWavLatencyMetrics()
        self.assertFalse(m.observe(10, 11, 12, 1, 1))
        self.assertEqual(m.snapshot()["시각오류"], 1)

    def test_표본_상한_및_누적건수(self):
        m = LiveFirstWavLatencyMetrics(capacity=2)
        for i in range(3):
            self.assertTrue(m.observe(10+i, 11+i, 12+i, 1, True))
        self.assertEqual(m.snapshot()["최근표본"], 2)
        self.assertEqual(m.snapshot()["WAV수신후보"], 3)

    def test_플랫폼별_독립(self):
        meters = {code: LiveFirstWavLatencyMetrics() for code in
                  ("twitch", "chzzk", "soop", "youtube")}
        for i, meter in enumerate(meters.values()):
            meter.observe(10, 11, 12, 0.1+i, True)
        self.assertEqual([meter.snapshot()["WAV수신후보"]
                          for meter in meters.values()], [1, 1, 1, 1])

    def test_비정상_표본_한도(self):
        with self.assertRaises(ValueError):
            LiveFirstWavLatencyMetrics(capacity=0)


if __name__ == "__main__":
    unittest.main()
