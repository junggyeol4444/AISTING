# -*- coding: utf-8 -*-
"""149회차: OBS 관찰창의 시간 역행을 동일 발화 표본으로 결합하지 않는 가상 계약검사.

실제 OBS·권리 있는 GPT-SoVITS·공식 Cubism 출력 검증이 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.obs_consecutive_audio import (
    collect_obs_audio_times, collect_obs_input_meter_levels,
)


def 창(시작, 끝, 시각=(), 경로="장면A"):
    음성 = SimpleNamespace(
        first_selected_signal_monotonic=시각[0] if len(시각) > 1 else None,
        last_selected_signal_monotonic=시각[-1] if len(시각) > 1 else None,
        selected_signal_sample_times=시각,
        selected_all_meter_level_samples=tuple((t, 0.6) for t in 시각),
    )
    관찰 = SimpleNamespace(
        coherent_media_candidate=True,
        before_audio_route=경로, after_audio_route=경로, audio=음성,
    )
    return (시작, 끝, 관찰)


class OBS관찰창시간역행검사(unittest.TestCase):
    def setUp(self):
        self.첫 = 창(100.0, 101.0, (100.4, 100.5))
        self.뒤 = 창(101.0, 103.0, (101.4, 101.5))

    def 음성(self, windows):
        return collect_obs_audio_times(windows, 100.3, 102.0)

    def 미터(self, windows):
        return collect_obs_input_meter_levels(windows, since=100.3, until=102.0)

    def test_정상_순서의_겹치는_관찰창은_실측_새표본_보존(self):
        겹침 = 창(100.8, 102.0, (101.1, 101.2))
        self.assertEqual(self.음성((self.첫, 겹침, self.뒤)),
                         ((100.4, 100.5, 101.1, 101.2, 101.4, 101.5), 3))
        self.assertEqual(len(self.미터((self.첫, 겹침, self.뒤))), 6)

    def test_시작시각이_역행한_창은_뒤쪽_음성_증거_차단(self):
        역행 = 창(99.9, 102.0, (101.1, 101.2))
        self.assertEqual(self.음성((self.첫, 역행, self.뒤)),
                         ((100.4, 100.5), 1))

    def test_시작시각이_역행한_창은_뒤쪽_미터_증거_차단(self):
        역행 = 창(99.9, 102.0, (101.1, 101.2))
        self.assertEqual(self.미터((self.첫, 역행, self.뒤)),
                         ((100.4, 0.6), (100.5, 0.6)))

    def test_무음_창도_관찰창_시간순서_검사에_포함_음성(self):
        무음 = 창(101.0, 102.0)
        역행 = 창(100.9, 102.5, (101.8, 101.9))
        self.assertEqual(self.음성((self.첫, 무음, 역행, self.뒤)),
                         ((100.4, 100.5), 1))

    def test_무음_창도_관찰창_시간순서_검사에_포함_미터(self):
        무음 = 창(101.0, 102.0)
        역행 = 창(100.9, 102.5, (101.8, 101.9))
        self.assertEqual(self.미터((self.첫, 무음, 역행, self.뒤)),
                         ((100.4, 0.6), (100.5, 0.6)))

    def test_첫_유효_표본_전_역행_창은_정상_표본을_막지_않음(self):
        앞 = 창(101.0, 101.2)
        self.assertEqual(self.음성((앞, self.첫, self.뒤)),
                         ((100.4, 100.5, 101.4, 101.5), 2))
        self.assertEqual(len(self.미터((앞, self.첫, self.뒤))), 4)


if __name__ == "__main__":
    unittest.main()
