# -*- coding: utf-8 -*-
"""156회차: 실제 입 움직임과 동시에 관측한 OBS 오디오 표본 계약검사.

가상 SimpleNamespace 관찰창이며 실제 OBS·GPT-SoVITS·Cubism 검증이 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.original_plan_full_pipeline import (
    _confirmed_mouth_obs_audio_provenance,
)


def 관찰창(시작, 종료, 표본):
    음성 = SimpleNamespace(
        first_selected_signal_monotonic=표본[0],
        last_selected_signal_monotonic=표본[-1],
        selected_signal_sample_times=tuple(표본),
    )
    return (시작, 종료, SimpleNamespace(
        audio=음성,
        coherent_media_candidate=True,
        before_audio_route="입력A/장면A/트랙1",
        after_audio_route="입력A/장면A/트랙1",
    ))


def 조기종료(관찰):
    입 = SimpleNamespace(
        first_audio_mouth_monotonic=100.4,
        last_audio_mouth_monotonic=101.2,
    )
    return _confirmed_mouth_obs_audio_provenance(
        관찰, 입, 100.0, 102.0)


class 실제입음성동시표본검사(unittest.TestCase):
    def test_입_이전_근접_표본_두개와_입중_한개는_부족(self):
        self.assertFalse(조기종료((
            관찰창(100.0, 101.5, (100.21, 100.22, 100.41)),
        )))

    def test_입_이후_근접_표본_두개와_입중_한개는_부족(self):
        self.assertFalse(조기종료((
            관찰창(100.0, 101.5, (101.19, 101.31, 101.32)),
        )))

    def test_입_양쪽의_근접_표본만_있으면_거절(self):
        self.assertFalse(조기종료((
            관찰창(100.0, 101.5, (100.21, 100.22, 101.31, 101.32)),
        )))

    def test_입중_두_실측_표본은_허용(self):
        self.assertTrue(조기종료((
            관찰창(100.0, 101.5, (100.5, 100.9)),
        )))

    def test_입중_한개와_입밖_두개는_거절(self):
        self.assertFalse(조기종료((
            관찰창(100.0, 101.5, (100.22, 100.8, 101.31)),
        )))

    def test_연속된_겹침_관찰창의_입중_표본은_보존(self):
        self.assertTrue(조기종료((
            관찰창(100.0, 101.0, (100.3, 100.55)),
            관찰창(100.9, 101.5, (100.95, 101.3)),
        )))


if __name__ == "__main__":
    unittest.main()
