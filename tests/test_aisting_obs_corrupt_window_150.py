# -*- coding: utf-8 -*-
"""150회차: OBS 손상된 오디오 관찰창을 무음으로 오인해 결합하지 않는 가상 계약검사.

실제 OBS·권리 있는 한국어 GPT-SoVITS·공식 Cubism 통합 성공 증거가 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.obs_consecutive_audio import (
    collect_obs_audio_times, collect_obs_input_meter_levels,
)


def 창(시작, 끝, 시각=(), *, 레벨=None, 첫=None, 마지막=None, 오디오있음=True):
    if 레벨 is None:
        레벨 = tuple((t, 0.5) for t in 시각)
    오디오 = SimpleNamespace(
        first_selected_signal_monotonic=(시각[0] if 시각 else None) if 첫 is None else 첫,
        last_selected_signal_monotonic=(시각[-1] if 시각 else None) if 마지막 is None else 마지막,
        selected_signal_sample_times=시각,
        selected_all_meter_level_samples=레벨,
    ) if 오디오있음 else None
    return (시작, 끝, SimpleNamespace(
        coherent_media_candidate=True,
        before_audio_route="장면A/입력A/트랙1",
        after_audio_route="장면A/입력A/트랙1",
        audio=오디오,
    ))


class OBS손상관찰창연속성검사(unittest.TestCase):
    def setUp(self):
        self.첫 = 창(100.0, 101.0, (100.4, 100.5))
        self.뒤 = 창(101.0, 103.0, (101.4, 101.5))

    def 음성(self, windows):
        return collect_obs_audio_times(windows, 100.3, 102.0)

    def 미터(self, windows):
        return collect_obs_input_meter_levels(windows, since=100.3, until=102.0)

    def test_오디오_시각역행_중간창은_뒤쪽_실측증거_차단(self):
        중간 = 창(100.8, 101.8, (101.2, 101.1))
        self.assertEqual(self.음성((self.첫, 중간, self.뒤)), ((100.4, 100.5), 1))

    def test_오디오_일부_메타데이터만_있는_중간창은_뒤쪽_차단(self):
        중간 = 창(100.8, 101.8, (), 첫=101.1)
        self.assertEqual(self.음성((self.첫, 중간, self.뒤)), ((100.4, 100.5), 1))

    def test_오디오_객체누락은_정상무음으로_취급하지_않음(self):
        중간 = 창(100.8, 101.8, 오디오있음=False)
        self.assertEqual(self.음성((self.첫, 중간, self.뒤)), ((100.4, 100.5), 1))
        self.assertEqual(self.미터((self.첫, 중간, self.뒤)),
                         ((100.4, 0.5), (100.5, 0.5)))

    def test_미터_형식오류_중간창은_뒤쪽_실측증거_차단(self):
        중간 = 창(100.8, 101.8, 레벨=((101.1, -1.0),))
        self.assertEqual(self.미터((self.첫, 중간, self.뒤)),
                         ((100.4, 0.5), (100.5, 0.5)))

    def test_미터_시각역행_중간창은_뒤쪽_실측증거_차단(self):
        중간 = 창(100.8, 101.8, 레벨=((101.2, 0.5), (101.1, 0.5)))
        self.assertEqual(self.미터((self.첫, 중간, self.뒤)),
                         ((100.4, 0.5), (100.5, 0.5)))

    def test_정상무음_중간창은_뒤쪽_실측표본_보존(self):
        중간 = 창(100.8, 101.8)
        self.assertEqual(self.음성((self.첫, 중간, self.뒤)),
                         ((100.4, 100.5, 101.4, 101.5), 2))
        self.assertEqual(len(self.미터((self.첫, 중간, self.뒤))), 4)

    def test_입움직임_밖의_정상_오디오는_손상으로_간주하지_않음(self):
        중간 = 창(100.8, 101.8, (101.1, 101.2))
        self.assertEqual(collect_obs_audio_times(
            (self.첫, 중간, self.뒤), 100.3, 100.7),
            ((100.4, 100.5), 1))

    def test_첫_실측표본_전_손상창은_이후_정상창_시작을_막지않음(self):
        앞 = 창(99.0, 99.8, (99.7, 99.6))
        self.assertEqual(self.음성((앞, self.첫, self.뒤)),
                         ((100.4, 100.5, 101.4, 101.5), 2))


if __name__ == "__main__":
    unittest.main()
