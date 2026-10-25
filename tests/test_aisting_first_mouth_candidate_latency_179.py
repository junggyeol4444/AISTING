"""179회차: 기존 공식 Cubism 첫 입·WAV 시각 후보의 로컬 계약검사.

전부 가상 단조 시각이며 실제 Windows, GPT-SoVITS, 공식 Live2D,
OBS·시청자 전송 확인이 아니다. 로그인·방송·녹화·채팅 발신 없음.
"""
import unittest

from ai_broadcaster.live_runtime_metrics import LiveFirstMouthLatencyMetrics


class FirstMouthCandidateLatencyTests(unittest.TestCase):
    def test_파싱부터입_구간과_wav입_후보(self):
        m = LiveFirstMouthLatencyMetrics()
        self.assertTrue(m.observe(10, 11, 12, 16, 14, True, 13))
        state = m.snapshot()
        self.assertEqual(state["입표본후보"], 1)
        self.assertEqual(state["WAV입시각후보"], 1)
        self.assertAlmostEqual(state["파싱부터전송대기p95초"], 2)
        self.assertAlmostEqual(state["전송부터입후보p95초"], 2)
        self.assertAlmostEqual(state["파싱부터입후보p95초"], 4)
        self.assertAlmostEqual(state["WAV부터입후보p95초"], 1)

    def test_정확히_3초는_초과로_세지_않음(self):
        m = LiveFirstMouthLatencyMetrics()
        self.assertTrue(m.observe(10, 11, 12, 15, 13, True))
        self.assertEqual(m.snapshot()["3초초과후보"], 0)

    def test_3초_초과_후보는_별도_계측(self):
        m = LiveFirstMouthLatencyMetrics()
        m.observe(10, 11, 12, 18, 16, True)
        self.assertEqual(m.snapshot()["3초초과후보"], 1)

    def test_입움직임_검증실패는_성공이_아님(self):
        m = LiveFirstMouthLatencyMetrics()
        self.assertFalse(m.observe(10, 11, 12, 18, None, False))
        self.assertEqual(m.snapshot()["입미관측"], 1)
        self.assertEqual(m.snapshot()["입표본후보"], 0)

    def test_관찰예외는_미관측과_구별(self):
        m = LiveFirstMouthLatencyMetrics()
        m.error()
        state = m.snapshot()
        self.assertEqual(state["관찰시도"], 1)
        self.assertEqual(state["공식관찰오류"], 1)
        self.assertEqual(state["입미관측"], 0)

    def test_파싱시각누락_표본제외(self):
        m = LiveFirstMouthLatencyMetrics()
        self.assertFalse(m.observe(None, 11, 12, 15, 13, True))
        self.assertEqual(m.snapshot()["파싱시각누락"], 1)
        self.assertIsNone(m.snapshot()["파싱부터입후보p95초"])

    def test_파싱과_전송시각_역행_거부(self):
        m = LiveFirstMouthLatencyMetrics()
        self.assertFalse(m.observe(12, 11, 13, 15, 14, True))
        self.assertFalse(m.observe(10, 12, 11, 15, 14, True))
        self.assertEqual(m.snapshot()["시각오류"], 2)

    def test_과거_입움직임과_관찰종료후_입움직임_거부(self):
        m = LiveFirstMouthLatencyMetrics()
        self.assertFalse(m.observe(10, 11, 12, 15, 11.9, True))
        self.assertFalse(m.observe(10, 11, 12, 15, 15.1, True))
        self.assertEqual(m.snapshot()["시각오류"], 2)

    def test_nan_inf_bool시각_거부(self):
        m = LiveFirstMouthLatencyMetrics()
        for value in (float("nan"), float("inf"), True):
            self.assertFalse(m.observe(10, 11, 12, 15, value, True))
        self.assertEqual(m.snapshot()["시각오류"], 3)

    def test_wav없는입후보는_wav상관근거아님(self):
        m = LiveFirstMouthLatencyMetrics()
        self.assertTrue(m.observe(10, 11, 12, 16, 14, True))
        self.assertEqual(m.snapshot()["WAV시각누락"], 1)
        self.assertIsNone(m.snapshot()["WAV부터입후보p95초"])

    def test_입보다_늦은_wav는_동일후보_근거아님(self):
        m = LiveFirstMouthLatencyMetrics()
        self.assertTrue(m.observe(10, 11, 12, 16, 14, True, 14.1))
        self.assertEqual(m.snapshot()["입표본후보"], 1)
        self.assertEqual(m.snapshot()["WAV시각오류"], 1)
        self.assertEqual(m.snapshot()["WAV입시각후보"], 0)

    def test_전송이전의_옛_wav는_제외(self):
        m = LiveFirstMouthLatencyMetrics()
        self.assertTrue(m.observe(10, 11, 12, 16, 14, True, 11.9))
        self.assertEqual(m.snapshot()["WAV시각오류"], 1)

    def test_플랫폼별_최근표본_한도_및_통계_독립(self):
        codes = ("twitch", "chzzk", "soop", "youtube")
        meters = {code: LiveFirstMouthLatencyMetrics(capacity=2) for code in codes}
        for index, meter in enumerate(meters.values()):
            for i in range(3):
                self.assertTrue(meter.observe(
                    10+i, 11+i, 12+i, 16+i+index, 14+i+index, True,
                    13+i+index))
        self.assertEqual(
            [meters[k].snapshot()["입표본후보"] for k in codes], [3] * 4)
        self.assertEqual(
            [meters[k].snapshot()["최근표본"] for k in codes], [2] * 4)

    def test_잘못된_검증플래그_거부(self):
        m = LiveFirstMouthLatencyMetrics()
        self.assertFalse(m.observe(10, 11, 12, 16, 14, 1))
        self.assertEqual(m.snapshot()["시각오류"], 1)

    def test_비정상_표본_한도(self):
        with self.assertRaises(ValueError):
            LiveFirstMouthLatencyMetrics(capacity=0)


if __name__ == "__main__":
    unittest.main()
