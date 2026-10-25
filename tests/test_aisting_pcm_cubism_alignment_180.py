"""180회차 기존 공식 WAV PCM↔Cubism 렌더러 RMS 정렬 후보 계약검사.

합성된 테스트 숫자만 사용한다. 실제 GPT-SoVITS·Live2D·OBS·시청자
출력 실증은 아니며 동일 발화 인과성은 이 검사로 증명되지 않는다.
"""
import unittest

from ai_broadcaster.live_pcm_cubism_alignment import (
    analyze_pcm_cubism_alignment, LivePcmCubismAlignmentMetrics,
)


class PcmCubismAlignmentCandidateTests(unittest.TestCase):
    def setUp(self):
        self.pcm = tuple(((i * 7) % 19) / 20 for i in range(80))
        self.renderer = tuple(
            (round(i * .05 + .2, 3), self.pcm[i] * 2)
            for i in range(12, 56))

    def test_기존_wav_pcm과_렌더러_정렬_후보(self):
        result = analyze_pcm_cubism_alignment(
            self.pcm, self.renderer, mouth_observed=True)
        self.assertEqual(result.status, "입·음량동시후보")
        self.assertTrue(result.cubism_mouth_observed)
        self.assertGreaterEqual(result.sample_count, 8)
        self.assertGreater(result.correlation, 0.99)

    def test_입표본이_없으면_입동시후보로_표시하지_않음(self):
        result = analyze_pcm_cubism_alignment(
            self.pcm, self.renderer, mouth_observed=False)
        self.assertEqual(result.status, "렌더러음량후보")
        self.assertFalse(result.cubism_mouth_observed)

    def test_양측_표본부족(self):
        result = analyze_pcm_cubism_alignment(
            self.pcm[:7], self.renderer, mouth_observed=True)
        self.assertEqual(result.status, "표본부족")
        self.assertIsNone(result.correlation)

    def test_렌더러_표본부족(self):
        result = analyze_pcm_cubism_alignment(
            self.pcm, self.renderer[:7], mouth_observed=True)
        self.assertEqual(result.status, "표본부족")

    def test_무음은_정렬근거가_아님(self):
        result = analyze_pcm_cubism_alignment(
            [0.0] * 80, self.renderer, mouth_observed=True)
        self.assertEqual(result.status, "변화·중첩표본부족")

    def test_변화없는_렌더러는_정렬근거가_아님(self):
        result = analyze_pcm_cubism_alignment(
            self.pcm, [(t, 0.2) for t, _ in self.renderer],
            mouth_observed=True)
        self.assertIsNone(result.correlation)

    def test_nan_inf_음량_거부(self):
        for value in (float("nan"), float("inf"), -0.1, 1.1, True):
            pcm = list(self.pcm)
            pcm[2] = value
            result = analyze_pcm_cubism_alignment(
                pcm, self.renderer, mouth_observed=True)
            self.assertEqual(result.status, "관찰값오류")

    def test_시각역행_거부(self):
        renderer = list(self.renderer)
        renderer[5] = renderer[4]
        result = analyze_pcm_cubism_alignment(
            self.pcm, renderer, mouth_observed=True)
        self.assertEqual(result.status, "관찰값오류")

    def test_렌더러_음량_범위_거부(self):
        renderer = list(self.renderer)
        renderer[3] = (renderer[3][0], 11)
        result = analyze_pcm_cubism_alignment(
            self.pcm, renderer, mouth_observed=True)
        self.assertEqual(result.status, "관찰값오류")

    def test_잘못된_입관찰_플래그_거부(self):
        result = analyze_pcm_cubism_alignment(
            self.pcm, self.renderer, mouth_observed=1)
        self.assertEqual(result.status, "관찰값오류")

    def test_원본_배열_변경하지_않음(self):
        pcm = list(self.pcm)
        renderer = list(self.renderer)
        analyze_pcm_cubism_alignment(pcm, renderer, mouth_observed=True)
        self.assertEqual(pcm, list(self.pcm))
        self.assertEqual(renderer, list(self.renderer))

    def test_4플랫폼별_독립_누적(self):
        meters = {k: LivePcmCubismAlignmentMetrics(capacity=2) for k in
                  ("twitch", "chzzk", "soop", "youtube")}
        result = analyze_pcm_cubism_alignment(
            self.pcm, self.renderer, mouth_observed=True)
        for meter in meters.values():
            for _ in range(3):
                meter.observe(result)
        for meter in meters.values():
            self.assertEqual(meter.snapshot()["관찰시도"], 3)
            self.assertEqual(meter.snapshot()["최근후보"], 2)
            self.assertEqual(meter.snapshot()["Cubism입동시후보"], 3)

    def test_미측정_결과는_상관후보_아님(self):
        meter = LivePcmCubismAlignmentMetrics()
        meter.observe(analyze_pcm_cubism_alignment(
            [], [], mouth_observed=False))
        self.assertEqual(meter.snapshot()["후보미충족"], 1)
        self.assertEqual(meter.snapshot()["상관후보"], 0)

    def test_보관한도_검사(self):
        with self.assertRaises(ValueError):
            LivePcmCubismAlignmentMetrics(capacity=0)


if __name__ == "__main__":
    unittest.main()
