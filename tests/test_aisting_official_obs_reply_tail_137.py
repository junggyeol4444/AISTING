# -*- coding: utf-8 -*-
"""137회차: 공식 응답 직후 OBS 표본 관찰을 조기 종료하지 않는 경계 검사.

단위 모의 시각만 사용한다. 실제 GPT-SoVITS/OBS/Live2D·방송 실증이 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.original_plan_full_pipeline import (
    _coherent_mouth_obs_window, _observed_mouth_obs_overlap,
)


def 관찰(시작, 끝, 소리시작, 소리끝, *, 정상=True):
    표본 = SimpleNamespace(
        coherent_media_candidate=정상,
        audio=SimpleNamespace(
            first_selected_signal_monotonic=소리시작,
            last_selected_signal_monotonic=소리끝))
    return (시작, 끝, 표본)


class 공식응답후실제입오디오관찰검사(unittest.TestCase):
    def test_첫창무음_둘째창에서_실제입과_obs겹침(self):
        입 = SimpleNamespace(first_audio_mouth_monotonic=103.1,
                              last_audio_mouth_monotonic=103.8)
        창 = [관찰(100, 102, 100.5, 101, 정상=False),
              관찰(102, 105, 103.2, 103.7)]
        self.assertTrue(_observed_mouth_obs_overlap(창, 입, 100, 106))

    def test_빠른응답_첫창무음이면_성공후보아님(self):
        입 = SimpleNamespace(first_audio_mouth_monotonic=103.1,
                              last_audio_mouth_monotonic=103.8)
        self.assertFalse(_observed_mouth_obs_overlap(
            [관찰(100, 102, 100.5, 101, 정상=False)], 입, 100, 106))

    def test_이전발화입움직임을_동일질문으로_인정하지않음(self):
        입 = SimpleNamespace(first_audio_mouth_monotonic=99.5,
                              last_audio_mouth_monotonic=100.5)
        self.assertFalse(_observed_mouth_obs_overlap(
            [관찰(100, 102, 100.1, 100.4)], 입, 100, 106))

    def test_시간경계접촉만으로_겹침인정하지않음(self):
        self.assertFalse(_coherent_mouth_obs_window(
            *관찰(102, 105, 103.8, 104.2), 103.1, 103.8))
        self.assertFalse(_coherent_mouth_obs_window(
            *관찰(102, 105, 102.7, 103.1), 103.1, 103.8))

    def test_입증없는_영상및_잘못된시각은_거절(self):
        self.assertFalse(_coherent_mouth_obs_window(
            *관찰(102, 105, 103.2, 103.7, 정상=False), 103.1, 103.8))
        self.assertFalse(_coherent_mouth_obs_window(
            *관찰(102, 105, float("nan"), 103.7), 103.1, 103.8))
        self.assertFalse(_observed_mouth_obs_overlap(
            [관찰(102, 105, 103.2, 103.7)], None, 100, 106))


if __name__ == "__main__":
    unittest.main()
