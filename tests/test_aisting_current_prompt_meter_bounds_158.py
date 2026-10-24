# -*- coding: utf-8 -*-
"""158회차: 실제 입 움직임 범위 밖 OBS 미터의 WAV 상관 오염 방지 계약검사.

합성 시간과 가상 미터만 검사하며 실제 방송·Cubism·GPT-SoVITS 검증이 아니다.
"""
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.original_plan_full_pipeline import _current_prompt_pcm_meter_bounds
from ai_broadcaster.obs_consecutive_audio import collect_obs_input_meter_levels


def 범위(wav=100.1, 입시작=100.5, 입끝=101.5, 질문시작=100.0, 질문끝=102.0):
    return _current_prompt_pcm_meter_bounds(
        wav, 입시작, 입끝, 질문시작, 질문끝)


class 현재질문WAV_OBS미터범위검사(unittest.TestCase):
    def test_정상_입구간에_기존_근접허용_적용(self):
        self.assertEqual(범위(), (100.3, 101.7))

    def test_WAV수신전_미터는_제외(self):
        self.assertEqual(범위(wav=100.45), (100.45, 101.7))

    def test_질문종료_이후_미터는_제외(self):
        self.assertEqual(범위(질문끝=101.6), (100.3, 101.6))

    def test_질문시작_이전_WAV_거절(self):
        self.assertIsNone(범위(wav=99.9))

    def test_질문종료_이후_WAV_거절(self):
        self.assertIsNone(범위(wav=102.1))

    def test_입시각이_질문범위_밖이면_거절(self):
        self.assertIsNone(범위(입시작=99.9))
        self.assertIsNone(범위(입끝=102.1))

    def test_WAV가_입움직임_이후면_교집합_없음(self):
        self.assertIsNone(범위(wav=101.8))

    def test_입움직임_시각_역행_거절(self):
        self.assertIsNone(범위(입시작=101.6, 입끝=101.5))

    def test_불리언_NaN_무한대_거절(self):
        for value in (True, float("nan"), math.inf, -math.inf, "100.5"):
            with self.subTest(value=repr(value)):
                self.assertIsNone(범위(입시작=value))

    def test_채택된_같은_OBS창에서도_입범위_밖_레벨_제외(self):
        levels = tuple((100.1 + n * 0.1, float(n % 5)) for n in range(19))
        sample = SimpleNamespace(
            coherent_media_candidate=True,
            before_audio_route="입력A", after_audio_route="입력A",
            audio=SimpleNamespace(selected_all_meter_level_samples=levels),
        )
        obs = ((100.0, 102.0, sample),)
        since, until = 범위()
        result = collect_obs_input_meter_levels(
            obs, since=since, until=until, accepted_window_indices=(0,))
        self.assertTrue(result)
        self.assertTrue(all(since <= t <= until for t, _ in result))
        self.assertNotIn((100.1, 0.0), result)
        self.assertNotIn((101.9, 3.0), result)


if __name__ == "__main__":
    unittest.main()
