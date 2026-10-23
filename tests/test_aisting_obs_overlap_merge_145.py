# -*- coding: utf-8 -*-
"""145회차 연속 OBS 관찰창 실측 시각 병합 계약검사.

가상 표본으로 검사하며 실제 한국어 WAV·공식 Cubism·OBS 실증은 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.obs_consecutive_audio import collect_obs_audio_times


def 관찰창(시작, 끝, 표본, *, 경로확인=True):
    오디오 = SimpleNamespace(
        first_selected_signal_monotonic=표본[0],
        last_selected_signal_monotonic=표본[-1],
        selected_signal_sample_times=표본,
    )
    결과 = SimpleNamespace(coherent_media_candidate=경로확인, audio=오디오)
    return (시작, 끝, 결과)


class 연속OBS관찰창병합검사(unittest.TestCase):
    def test_겹친창에서_기존시각을_제외하고_새표본을_보존(self):
        창 = (
            관찰창(100.0, 101.0, (100.40, 100.50, 100.60)),
            관찰창(100.3, 101.2, (100.55, 100.65, 100.75)),
        )
        시각, 창수 = collect_obs_audio_times(창, 100.35, 100.80)
        self.assertEqual(시각, (100.40, 100.50, 100.60, 100.65, 100.75))
        self.assertEqual(창수, 2)

    def test_중복뿐인_두번째창은_집계하지_않음(self):
        창 = (
            관찰창(100.0, 101.0, (100.40, 100.50, 100.60)),
            관찰창(100.1, 101.1, (100.40, 100.50, 100.60)),
        )
        시각, 창수 = collect_obs_audio_times(창, 100.35, 100.80)
        self.assertEqual(시각, (100.40, 100.50, 100.60))
        self.assertEqual(창수, 1)

    def test_새로운_실측_간격을_보간하지_않음(self):
        창 = (
            관찰창(100.0, 100.8, (100.40, 100.50)),
            관찰창(100.7, 101.3, (100.90, 101.00)),
        )
        시각, 창수 = collect_obs_audio_times(창, 100.35, 101.05)
        self.assertEqual(시각, (100.40, 100.50, 100.90, 101.00))
        self.assertEqual(창수, 2)

    def test_확인되지_않은_장면경로_표본은_병합하지_않음(self):
        창 = (
            관찰창(100.0, 101.0, (100.40, 100.50)),
            관찰창(100.2, 101.2, (100.55, 100.70), 경로확인=False),
        )
        시각, 창수 = collect_obs_audio_times(창, 100.35, 100.80)
        self.assertEqual(시각, (100.40, 100.50))
        self.assertEqual(창수, 1)

    def test_역행_표본은_전체창_거절(self):
        창 = (
            관찰창(100.0, 101.0, (100.40, 100.50)),
            관찰창(100.1, 101.2, (100.70, 100.60)),
        )
        시각, 창수 = collect_obs_audio_times(창, 100.35, 100.80)
        self.assertEqual(시각, (100.40, 100.50))
        self.assertEqual(창수, 1)


if __name__ == "__main__":
    unittest.main()
