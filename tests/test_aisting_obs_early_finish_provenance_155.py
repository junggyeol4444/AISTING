# -*- coding: utf-8 -*-
"""155회차: 실제 OBS 선택 오디오 출처 확인 전 조기 종료 금지 계약검사.

SimpleNamespace는 계약검사 입력일 뿐 실제 OBS/공식 Cubism 실증이 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.original_plan_full_pipeline import (
    _confirmed_mouth_obs_audio_provenance,
)


def 관찰창(시작, 종료, 시각, *, 이전경로="입력A/장면A/트랙1",
       이후경로="입력A/장면A/트랙1", 후보=True):
    음성 = SimpleNamespace(
        first_selected_signal_monotonic=시각[0] if 시각 else None,
        last_selected_signal_monotonic=시각[-1] if 시각 else None,
        selected_signal_sample_times=tuple(시각),
    )
    return (시작, 종료, SimpleNamespace(
        audio=음성, coherent_media_candidate=후보,
        before_audio_route=이전경로, after_audio_route=이후경로,
    ))


def 입(시작=100.4, 종료=101.2):
    return SimpleNamespace(
        first_audio_mouth_monotonic=시작,
        last_audio_mouth_monotonic=종료,
    )


class 조기종료출처검사(unittest.TestCase):
    def test_같은_경로의_실측_두_표본만_조기종료(self):
        관찰 = (관찰창(100, 101.5, (100.5, 100.9)),)
        self.assertTrue(_confirmed_mouth_obs_audio_provenance(
            관찰, 입(), 100, 102))

    def test_양성_미터_구간만_있고_선택표본이_없으면_대기(self):
        창 = 관찰창(100, 101.5, ())
        창[2].audio.first_selected_signal_monotonic = 100.5
        창[2].audio.last_selected_signal_monotonic = 100.9
        self.assertFalse(_confirmed_mouth_obs_audio_provenance(
            (창,), 입(), 100, 102))

    def test_입력_장면_트랙_변경시_조기종료_금지(self):
        관찰 = (관찰창(100, 101.5, (100.5, 100.9),
                      이후경로="입력B/장면B/트랙1"),)
        self.assertFalse(_confirmed_mouth_obs_audio_provenance(
            관찰, 입(), 100, 102))

    def test_한_표본만_있으면_조기종료_금지(self):
        관찰 = (관찰창(100, 101.5, (100.7,)),)
        self.assertFalse(_confirmed_mouth_obs_audio_provenance(
            관찰, 입(), 100, 102))

    def test_현재_질문_밖의_과거_입_시각_거절(self):
        관찰 = (관찰창(100, 101.5, (100.5, 100.9)),)
        self.assertFalse(_confirmed_mouth_obs_audio_provenance(
            관찰, 입(99.5, 100.8), 100, 102))

    def test_미확정_프로그램_영상_후보는_거절(self):
        관찰 = (관찰창(100, 101.5, (100.5, 100.9), 후보=False),)
        self.assertFalse(_confirmed_mouth_obs_audio_provenance(
            관찰, 입(), 100, 102))

    def test_겹친_실측_창의_중복_제거_후_두_표본이면_허용(self):
        관찰 = (
            관찰창(100, 101, (100.5, 100.7)),
            관찰창(100.9, 101.5, (100.7, 101.1)),
        )
        self.assertTrue(_confirmed_mouth_obs_audio_provenance(
            관찰, 입(), 100, 102))


if __name__ == "__main__":
    unittest.main()
