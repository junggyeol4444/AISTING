# -*- coding: utf-8 -*-
"""153회차: 실제 채택 OBS 미터 표본의 출처와 동일 발화 후보 일치.

가상 객체 계약검사다. 실제 GPT-SoVITS·Cubism·OBS 실증이 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.obs_consecutive_audio import (
    collect_obs_audio_evidence, collect_obs_audio_times,
)
from ai_broadcaster.original_plan_full_pipeline import _matched_obs_audio_candidates


def 관찰창(시작, 끝, 시각=(), 경로="입력A/장면A/트랙1", 정상=True):
    audio = SimpleNamespace(
        first_selected_signal_monotonic=시각[0] if 시각 else None,
        last_selected_signal_monotonic=시각[-1] if 시각 else None,
        selected_signal_sample_times=tuple(시각),
    )
    sample = SimpleNamespace(
        audio=audio, coherent_media_candidate=정상,
        before_audio_route=경로, after_audio_route=경로,
        program_video_change_candidate=True,
    )
    return 시작, 끝, sample


class OBS채택창출처검사(unittest.TestCase):
    def setUp(self):
        self.첫 = 관찰창(100.0, 101.0, (100.4, 100.6))
        self.둘 = 관찰창(100.9, 102.0, (101.2, 101.4))
        self.셋 = 관찰창(101.9, 103.0, (102.2, 102.4))

    def test_기존_두값_반환_계약_보존(self):
        self.assertEqual(
            collect_obs_audio_times((self.첫, self.둘), 100.2, 103.0),
            ((100.4, 100.6, 101.2, 101.4), 2))

    def test_연속_동일경로_창의_실제_출처_순번(self):
        result = collect_obs_audio_evidence(
            (self.첫, self.둘, self.셋), 100.2, 103.0)
        self.assertEqual(result[1:], (3, (0, 1, 2)))

    def test_경로_바뀌었다_복귀해도_후속_후보_제외(self):
        중간 = 관찰창(100.9, 102.0, (101.2, 101.4), "입력B/장면B/트랙1")
        times, count, matching = _matched_obs_audio_candidates(
            (self.첫, 중간, self.셋), 100.2, 103.0)
        self.assertEqual((times, count), ((100.4, 100.6), 1))
        self.assertEqual(matching, [self.첫[2]])

    def test_무관측_공백_뒤의_후보_제외(self):
        늦은창 = 관찰창(101.1, 102.0, (101.3, 101.5))
        times, count, matching = _matched_obs_audio_candidates(
            (self.첫, 늦은창), 100.2, 103.0)
        self.assertEqual((times, count), ((100.4, 100.6), 1))
        self.assertEqual(matching, [self.첫[2]])

    def test_후속_손상_관찰창을_후보로_선택하지_않음(self):
        손상 = 관찰창(100.9, 102.0, (101.2, 101.4), 정상=False)
        _, count, matching = _matched_obs_audio_candidates(
            (self.첫, 손상, self.셋), 100.2, 103.0)
        self.assertEqual(count, 1)
        self.assertEqual(matching, [self.첫[2]])

    def test_중복_표본만_있는_창은_새_출처가_아님(self):
        중복 = 관찰창(100.3, 101.5, (100.4, 100.6))
        times, count, indices = collect_obs_audio_evidence(
            (self.첫, 중복), 100.2, 103.0)
        self.assertEqual((times, count, indices), ((100.4, 100.6), 1, (0,)))

    def test_실측_표본_없으면_동일발화_후보도_없음(self):
        _, count, matching = _matched_obs_audio_candidates(
            (관찰창(100.0, 101.0),), 100.2, 103.0)
        self.assertEqual(count, 0)
        self.assertEqual(matching, [])


if __name__ == "__main__":
    unittest.main()
