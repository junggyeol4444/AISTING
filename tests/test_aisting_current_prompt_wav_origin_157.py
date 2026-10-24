# -*- coding: utf-8 -*-
"""157회차: 공식 WAV 수신 시각의 단일 질문 출처 계약검사.

모의 시각만 사용하며 실제 GPT-SoVITS·Live2D·OBS 검증이 아니다.
"""
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.original_plan_full_pipeline import (
    _validated_current_prompt_wav_received_at,
)


def 검증(수신시각, 시작=100.0, 종료=103.0):
    입 = SimpleNamespace(
        official_pcm_first_wav_received_monotonic=수신시각)
    return _validated_current_prompt_wav_received_at(입, 시작, 종료)


class 현재질문공식WAV출처검사(unittest.TestCase):
    def test_이번_질문_내_수신시각_채택(self):
        self.assertEqual(검증(101.25), 101.25)

    def test_질문_시작_경계_수신_허용(self):
        self.assertEqual(검증(100.0), 100.0)

    def test_질문_종료_경계_수신_허용(self):
        self.assertEqual(검증(103.0), 103.0)

    def test_이전_발화의_수신시각_차단(self):
        self.assertIsNone(검증(99.99))

    def test_다음_발화의_수신시각_차단(self):
        self.assertIsNone(검증(103.01))

    def test_공식_WAV_수신_속성_누락_차단(self):
        self.assertIsNone(_validated_current_prompt_wav_received_at(
            SimpleNamespace(), 100.0, 103.0))

    def test_숫자가_아닌_수신시각_차단(self):
        for value in (None, True, "101.0", float("nan"), math.inf, -math.inf):
            with self.subTest(value=repr(value)):
                self.assertIsNone(검증(value))

    def test_질문_시각_형식_오류_차단(self):
        for 시작, 종료 in ((True, 103.0), (100.0, False),
                           (float("nan"), 103.0), (100.0, math.inf)):
            with self.subTest(시작=시작, 종료=종료):
                self.assertIsNone(검증(101.0, 시작, 종료))

    def test_질문_시각_역행_차단(self):
        self.assertIsNone(검증(101.0, 103.0, 100.0))

    def test_질문_시작이_양수가_아니면_차단(self):
        self.assertIsNone(검증(1.0, 0.0, 103.0))


if __name__ == "__main__":
    unittest.main()
