"""177절: 합성 단조시각으로 검사하는 파싱→AI 종결 계측 계약."""
import unittest
from ai_broadcaster.live_runtime_metrics import LiveParseReplyMetrics

class ParseReplyTests(unittest.TestCase):
    def test_정상_구간(self):
        m = LiveParseReplyMetrics()
        self.assertTrue(m.terminal(10, 10.2, 11, 12))
        self.assertEqual(m.snapshot()["종결"], 1)
        self.assertAlmostEqual(m.snapshot()["대기p95초"], 1)
        self.assertAlmostEqual(m.snapshot()["AIp95초"], 1)
    def test_실패와_초과_보존(self):
        m = LiveParseReplyMetrics()
        self.assertTrue(m.terminal(10, 11, 12, 15, True))
        self.assertEqual(m.snapshot()["실패"], 1)
        self.assertEqual(m.snapshot()["3초초과"], 1)
    def test_파싱시각_누락(self):
        m = LiveParseReplyMetrics()
        self.assertFalse(m.terminal(None, 10, 11, 12))
        self.assertEqual(m.snapshot()["파싱시각누락"], 1)
    def test_파싱시각_역행(self):
        m = LiveParseReplyMetrics()
        self.assertFalse(m.terminal(12, 11, 13, 14))
        self.assertEqual(m.snapshot()["시각오류"], 1)
    def test_모델시각_역행(self):
        m = LiveParseReplyMetrics()
        self.assertFalse(m.terminal(10, 12, 11, 13))
    def test_비정상_숫자(self):
        m = LiveParseReplyMetrics()
        self.assertFalse(m.terminal(float("nan"), 2, 3, 4))
        self.assertFalse(m.terminal(1, 2, 3, float("inf")))
        self.assertEqual(m.snapshot()["시각오류"], 2)
    def test_실패인자_형식(self):
        m = LiveParseReplyMetrics()
        self.assertFalse(m.terminal(1, 2, 3, 4, 1))
    def test_표본_상한(self):
        m = LiveParseReplyMetrics(capacity=2)
        for i in range(3):
            self.assertTrue(m.terminal(10+i, 10+i, 11+i, 12+i))
        self.assertEqual(m.snapshot()["최근표본"], 2)
        self.assertEqual(m.snapshot()["종결"], 3)
    def test_플랫폼별_독립(self):
        meters = {p: LiveParseReplyMetrics() for p in
                  ("twitch", "chzzk", "soop", "youtube")}
        for i, p in enumerate(meters):
            meters[p].terminal(10, 10.1, 11, 12+i)
        self.assertEqual([m.snapshot()["종결"] for m in meters.values()],
                         [1, 1, 1, 1])
    def test_빈_상태_미측정(self):
        self.assertIsNone(LiveParseReplyMetrics().snapshot()["최근p95초"])

if __name__ == "__main__":
    unittest.main()
