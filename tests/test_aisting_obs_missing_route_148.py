# -*- coding: utf-8 -*-
"""148회차: OBS 경로 속성이 존재하나 값이 누락된 관찰창은 불확정으로 처리.

모든 검사는 가상 객체 계약검사이며 실제 WAV·Cubism·OBS 출력 증거가 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.obs_consecutive_audio import (
    collect_obs_audio_times, collect_obs_input_meter_levels,
)


def 관찰(시작, 끝, 시각, *, 경로="A", 상태="정상"):
    오디오 = SimpleNamespace(
        first_selected_signal_monotonic=시각[0] if 시각 else None,
        last_selected_signal_monotonic=시각[-1] if 시각 else None,
        selected_signal_sample_times=시각,
        selected_all_meter_level_samples=tuple((t, 0.5) for t in 시각),
    )
    결과 = SimpleNamespace(coherent_media_candidate=True, audio=오디오)
    if 상태 == "정상":
        결과.before_audio_route = 경로
        결과.after_audio_route = 경로
    elif 상태 == "양쪽값없음":
        결과.before_audio_route = None
        결과.after_audio_route = None
    elif 상태 == "뒤속성없음":
        결과.before_audio_route = 경로
    elif 상태 == "앞속성없음":
        결과.after_audio_route = 경로
    elif 상태 == "뒤값없음":
        결과.before_audio_route = 경로
        결과.after_audio_route = None
    elif 상태 != "과거가상":
        raise ValueError("알 수 없는 가상 경로 상태")
    return (시작, 끝, 결과)


class OBS경로누락차단(unittest.TestCase):
    def setUp(self):
        self.첫 = 관찰(100.0, 101.0, (100.4, 100.5))
        self.뒤 = 관찰(101.0, 103.0, (101.4, 101.5))

    def 검사(self, 중간):
        창 = (self.첫, 중간, self.뒤)
        self.assertEqual(
            collect_obs_audio_times(창, 100.3, 102.0),
            ((100.4, 100.5), 1),
        )
        self.assertEqual(
            collect_obs_input_meter_levels(창, since=100.3, until=102.0),
            ((100.4, 0.5), (100.5, 0.5)),
        )

    def test_경로속성_둘다_있지만_값없으면_중간에서_중단(self):
        self.검사(관찰(100.8, 101.6, (), 상태="양쪽값없음"))

    def test_뒤경로속성이_없으면_중간에서_중단(self):
        self.검사(관찰(100.8, 101.6, (), 상태="뒤속성없음"))

    def test_앞경로속성이_없으면_중간에서_중단(self):
        self.검사(관찰(100.8, 101.6, (), 상태="앞속성없음"))

    def test_뒤경로값이_없으면_중간에서_중단(self):
        self.검사(관찰(100.8, 101.6, (), 상태="뒤값없음"))

    def test_처음_불명확한_경로는_이후_정상창을_막지않음(self):
        앞 = 관찰(99.0, 99.8, (), 상태="양쪽값없음")
        창 = (앞, self.첫, self.뒤)
        self.assertEqual(
            collect_obs_audio_times(창, 100.3, 102.0),
            ((100.4, 100.5, 101.4, 101.5), 2),
        )

    def test_과거_가상객체_양쪽_속성없는_경로_호환(self):
        창 = (
            관찰(100.0, 101.0, (100.4, 100.5), 상태="과거가상"),
            관찰(101.0, 103.0, (101.4, 101.5), 상태="과거가상"),
        )
        self.assertEqual(
            collect_obs_audio_times(창, 100.3, 102.0),
            ((100.4, 100.5, 101.4, 101.5), 2),
        )


if __name__ == "__main__":
    unittest.main()
