# -*- coding: utf-8 -*-
"""154회차: WAV-OBS 미터 대조를 실제 채택된 오디오 관찰창으로 제한.

이 검사는 가상 관찰 객체의 계약검사이며 실모델·실OBS 실증이 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_broadcaster.obs_consecutive_audio import collect_obs_input_meter_levels
from ai_broadcaster.original_plan_full_pipeline import (
    _matched_obs_audio_candidates, _matched_obs_audio_evidence,
)


def 관찰창(시작, 끝, 오디오시각, 레벨시각, 경로="입력A/장면A/트랙1"):
    오디오 = SimpleNamespace(
        first_selected_signal_monotonic=오디오시각[0] if 오디오시각 else None,
        last_selected_signal_monotonic=오디오시각[-1] if 오디오시각 else None,
        selected_signal_sample_times=tuple(오디오시각),
        selected_all_meter_level_samples=tuple((t, 0.4) for t in 레벨시각),
    )
    표본 = SimpleNamespace(
        audio=오디오, coherent_media_candidate=True,
        before_audio_route=경로, after_audio_route=경로,
        program_video_change_candidate=True,
    )
    return (시작, 끝, 표본)


class 동일발화미터출처검사(unittest.TestCase):
    def test_기존_미터_호출은_동작_유지(self):
        창 = 관찰창(100, 101, (100.4, 100.6), (100.2, 100.5))
        self.assertEqual(
            collect_obs_input_meter_levels((창,), since=100, until=102),
            ((100.2, 0.4), (100.5, 0.4)))

    def test_첫_채택_이전_다른_경로_미터는_제외(self):
        다른창 = 관찰창(100, 101, (100.1, 100.3),
                       (100.2, 100.4), "입력B/장면B/트랙1")
        채택창 = 관찰창(100.9, 102, (101.2, 101.6), (101.3, 101.5))
        관찰 = (다른창, 채택창)
        _, _, _, 순번 = _matched_obs_audio_evidence(관찰, 101.1, 101.8)
        self.assertEqual(순번, (1,))
        self.assertEqual(
            collect_obs_input_meter_levels(
                관찰, since=100, until=102, accepted_window_indices=순번),
            ((101.3, 0.4), (101.5, 0.4)))

    def test_경로_변경_후_복귀한_창의_미터도_제외(self):
        첫창 = 관찰창(100, 101, (100.4, 100.6), (100.5,))
        다른창 = 관찰창(100.9, 102, (101.2, 101.4),
                       (101.3,), "입력B/장면B/트랙1")
        복귀창 = 관찰창(101.9, 103, (102.2, 102.4), (102.3,))
        관찰 = (첫창, 다른창, 복귀창)
        _, _, _, 순번 = _matched_obs_audio_evidence(관찰, 100.2, 103)
        self.assertEqual(순번, (0,))
        self.assertEqual(
            collect_obs_input_meter_levels(
                관찰, since=100, until=103, accepted_window_indices=순번),
            ((100.5, 0.4),))

    def test_동일경로_겹친_두_창의_실측_레벨_유지(self):
        첫창 = 관찰창(100, 101, (100.4, 100.6), (100.5,))
        둘째창 = 관찰창(100.9, 102, (101.2, 101.4), (101.3,))
        관찰 = (첫창, 둘째창)
        _, _, _, 순번 = _matched_obs_audio_evidence(관찰, 100.2, 102)
        self.assertEqual(순번, (0, 1))
        self.assertEqual(
            collect_obs_input_meter_levels(
                관찰, since=100, until=102, accepted_window_indices=순번),
            ((100.5, 0.4), (101.3, 0.4)))

    def test_채택_창이_없으면_다른_미터로_대체하지_않음(self):
        창 = 관찰창(100, 101, (), (100.5,))
        self.assertEqual(
            collect_obs_input_meter_levels(
                (창,), since=100, until=102, accepted_window_indices=()),
            ())

    def test_잘못된_창_순번_입력은_거절(self):
        창 = 관찰창(100, 101, (100.4, 100.6), (100.5,))
        for 잘못된순번 in ((0, 0), (True,), (-1,), [0], (1, 0)):
            with self.subTest(순번=잘못된순번):
                self.assertEqual(
                    collect_obs_input_meter_levels(
                        (창,), since=100, until=102,
                        accepted_window_indices=잘못된순번), ())

    def test_기존_동일발화_세값_반환_계약_유지(self):
        창 = 관찰창(100, 101, (100.4, 100.6), (100.5,))
        시각, 개수, 후보 = _matched_obs_audio_candidates((창,), 100.2, 100.8)
        self.assertEqual((시각, 개수, 후보), ((100.4, 100.6), 1, [창[2]]))


if __name__ == "__main__":
    unittest.main()
