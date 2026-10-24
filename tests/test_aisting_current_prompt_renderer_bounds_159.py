# -*- coding: utf-8 -*-
"""159회차: 공식 WAV·입·질문 범위 밖 렌더러 RMS 오염 방지 가상 계약검사.

이 검사는 실제 GPT-SoVITS·공식 Cubism·OBS 송출/시청자 수신 실증이 아니다.
"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.original_plan_full_pipeline import (
    _current_prompt_renderer_rms_levels,
)


def 수집(표본, 수신=100.0, 범위=(100.2, 101.0)):
    return _current_prompt_renderer_rms_levels(표본, 수신, 범위)


class 현재질문렌더러RMS범위검사(unittest.TestCase):
    def test_이번_질문_입구간_표본_채택(self):
        self.assertEqual(
            수집(((0.2, 0.1), (0.5, 0.7), (1.0, 0.3))),
            ((100.2, 0.1), (100.5, 0.7), (101.0, 0.3)),
        )

    def test_입_움직임_이전_표본_제외(self):
        self.assertEqual(수집(((0.1, 0.8), (0.3, 0.2))), ((100.3, 0.2),))

    def test_입_움직임_이후_표본_제외(self):
        self.assertEqual(수집(((0.5, 0.3), (1.1, 0.9))), ((100.5, 0.3),))

    def test_이번_질문_범위가_없으면_상관_후보_없음(self):
        self.assertEqual(수집(((0.3, 0.8),), 범위=None), ())

    def test_공식_WAV_수신_시각_없으면_후보_없음(self):
        self.assertEqual(수집(((0.3, 0.8),), 수신=None), ())

    def test_시간_범위_역행_및_WAV_전_범위_거절(self):
        self.assertEqual(수집(((0.3, 0.8),), 범위=(101.0, 100.2)), ())
        self.assertEqual(수집(((0.3, 0.8),), 범위=(99.0, 100.5)), ())

    def test_미래_12초_초과_범위_거절(self):
        self.assertEqual(수집(((0.3, 0.8),), 범위=(100.2, 112.1)), ())

    def test_불리언_비수치_비정상_오프셋_거절(self):
        for value in (True, "0.3", float("nan"), math.inf, -0.1, 12.1):
            with self.subTest(value=repr(value)):
                self.assertEqual(수집(((value, 0.5),)), ())

    def test_잘못된_RMS_레벨_거절(self):
        for value in (True, -0.1, 10.1, float("nan"), math.inf):
            with self.subTest(value=repr(value)):
                self.assertEqual(수집(((0.3, value),)), ())

    def test_중복_및_역행_시각_전체_거절(self):
        self.assertEqual(수집(((0.3, 0.5), (0.3, 0.6))), ())
        self.assertEqual(수집(((0.5, 0.5), (0.3, 0.6))), ())

    def test_형식이_손상된_표본_전체_거절(self):
        self.assertEqual(수집(((0.3, 0.5), (0.6,))), ())
        self.assertEqual(수집(((0.3, 0.5), [0.6, 0.4])), ())

    def test_비정상_시간_범위_거절(self):
        self.assertEqual(수집(((0.3, 0.5),), 범위=(100.2, math.inf)), ())
        self.assertEqual(수집(((0.3, 0.5),), 범위=(True, 101.0)), ())


if __name__ == "__main__":
    unittest.main()
