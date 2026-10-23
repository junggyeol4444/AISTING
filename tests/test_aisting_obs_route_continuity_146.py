# -*- coding: utf-8 -*-
"""146회차 OBS 연속 관찰창 경로 변경 방지 계약검사.

가상 OBS 객체 검사이며 실제 WAV/Live2D/OBS 또는 시청자 실증이 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.obs_consecutive_audio import (
    collect_obs_audio_times, collect_obs_input_meter_levels,
)


def 관찰(시작, 끝, 표본, 입력="마이크A", 장면="장면1", 트랙=(1,), 경로포함=True):
    route = SimpleNamespace(scene=장면, input_name=입력, origin="scene",
                            identity=(장면, 입력), enabled_tracks=트랙)
    audio = SimpleNamespace(
        first_selected_signal_monotonic=표본[0],
        last_selected_signal_monotonic=표본[-1],
        selected_signal_sample_times=표본,
        selected_all_meter_level_samples=tuple((t, 0.5) for t in 표본),
    )
    result = SimpleNamespace(coherent_media_candidate=True, audio=audio)
    if 경로포함:
        result.before_audio_route = route
        result.after_audio_route = route
    return (시작, 끝, result)


class 연속OBS경로일치검사(unittest.TestCase):
    def test_동일입력_연속창의_새실측시각은_보존(self):
        창 = (관찰(100, 101, (100.4, 100.5)),
              관찰(100.8, 102, (100.9, 101.0)))
        self.assertEqual(collect_obs_audio_times(창, 100.3, 101.1),
                         ((100.4, 100.5, 100.9, 101.0), 2))
        self.assertEqual(len(collect_obs_input_meter_levels(
            창, since=100.3, until=101.1)), 4)

    def test_입력변경후_뒤쪽_관찰창을_섞지_않음(self):
        창 = (관찰(100, 101, (100.4, 100.5)),
              관찰(100.8, 102, (100.9, 101.0), 입력="마이크B"),
              관찰(101, 103, (101.4, 101.5)))
        self.assertEqual(collect_obs_audio_times(창, 100.3, 102),
                         ((100.4, 100.5), 1))
        self.assertEqual(len(collect_obs_input_meter_levels(
            창, since=100.3, until=102)), 2)

    def test_장면변경시_누적을_중지(self):
        창 = (관찰(100, 101, (100.4, 100.5)),
              관찰(100.8, 102, (100.9, 101.0), 장면="장면2"))
        self.assertEqual(collect_obs_audio_times(창, 100.3, 101.2),
                         ((100.4, 100.5), 1))

    def test_오디오트랙변경시_누적을_중지(self):
        창 = (관찰(100, 101, (100.4, 100.5)),
              관찰(100.8, 102, (100.9, 101.0), 트랙=(2,)))
        self.assertEqual(len(collect_obs_input_meter_levels(
            창, since=100.3, until=101.2)), 2)

    def test_중간창의_경로정보가_불완전하면_그창을_제외(self):
        첫째 = 관찰(100, 101, (100.4, 100.5))
        둘째 = 관찰(100.8, 102, (100.9, 101.0))
        둘째[2].after_audio_route = None
        self.assertEqual(collect_obs_audio_times((첫째, 둘째), 100.3, 101.2),
                         ((100.4, 100.5), 1))


if __name__ == "__main__":
    unittest.main()
