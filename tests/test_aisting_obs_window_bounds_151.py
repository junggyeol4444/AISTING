# -*- coding: utf-8 -*-
"""151회차: OBS 오디오 미터의 관찰창 밖 콜백과 빈 경로를 같은 발화로 결합하지 않는다.

모든 검사는 가상 OBS 관찰 계약검사이며 실제 WAV/Live2D/OBS 성공 증거가 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.obs_consecutive_audio import (
    collect_obs_audio_times, collect_obs_input_meter_levels,
)


def 창(시작, 종료, 시각=(), *, 경로="장면A/마이크A/트랙1", 미터=None):
    오디오 = SimpleNamespace(
        first_selected_signal_monotonic=시각[0] if 시각 else None,
        last_selected_signal_monotonic=시각[-1] if 시각 else None,
        selected_signal_sample_times=시각,
        selected_all_meter_level_samples=(
            tuple((t, 0.5) for t in 시각) if 미터 is None else 미터),
    )
    관찰 = SimpleNamespace(
        coherent_media_candidate=True,
        before_audio_route=경로, after_audio_route=경로, audio=오디오,
    )
    return 시작, 종료, 관찰


class OBS관찰창경계검사(unittest.TestCase):
    def setUp(self):
        self.첫 = 창(100.0, 101.0, (100.4, 100.5))
        self.끝 = 창(101.0, 103.0, (101.4, 101.5))

    def 미터(self, *창들):
        return collect_obs_input_meter_levels(
            창들, since=100.3, until=102.0)

    def 음성(self, *창들):
        return collect_obs_audio_times(창들, 100.3, 102.0)

    def test_중간창_시작이전_미터콜백은_뒤쪽_결합차단(self):
        중간 = 창(100.8, 101.8, 미터=((100.7, 0.5),))
        self.assertEqual(self.미터(self.첫, 중간, self.끝),
                         ((100.4, 0.5), (100.5, 0.5)))

    def test_중간창_종료이후_미터콜백은_뒤쪽_결합차단(self):
        중간 = 창(100.8, 101.8, 미터=((101.9, 0.5),))
        self.assertEqual(self.미터(self.첫, 중간, self.끝),
                         ((100.4, 0.5), (100.5, 0.5)))

    def test_중간창_경계안과_경계밖_혼합은_뒤쪽_결합차단(self):
        중간 = 창(100.8, 101.8, 미터=((101.0, 0.5), (101.9, 0.5)))
        self.assertEqual(self.미터(self.첫, 중간, self.끝),
                         ((100.4, 0.5), (100.5, 0.5)))

    def test_첫증거_이전의_손상창은_다음_정상관찰_허용(self):
        앞 = 창(99.0, 99.8, 미터=((100.1, 0.5),))
        self.assertEqual(self.미터(앞, self.첫, self.끝),
                         ((100.4, 0.5), (100.5, 0.5),
                          (101.4, 0.5), (101.5, 0.5)))

    def test_창경계_정확한_시각은_유효(self):
        중간 = 창(100.8, 101.8, 미터=((100.8, 0.5), (101.8, 0.5)))
        self.assertEqual(self.미터(self.첫, 중간, self.끝),
                         ((100.4, 0.5), (100.5, 0.5),
                          (100.8, 0.5), (101.8, 0.5)))

    def test_조회구간_밖이지만_관찰창_안인_정상콜백은_손상아님(self):
        중간 = 창(100.8, 101.8, 미터=((101.7, 0.5),))
        실제 = collect_obs_input_meter_levels(
            (self.첫, 중간, self.끝), since=100.3, until=101.6)
        self.assertEqual(실제, ((100.4, 0.5), (100.5, 0.5),
                              (101.4, 0.5), (101.5, 0.5)))

    def test_공백_오디오경로_중간창은_음성_미터_모두_차단(self):
        중간 = 창(100.8, 101.8, 경로="   ")
        self.assertEqual(self.음성(self.첫, 중간, self.끝),
                         ((100.4, 100.5), 1))
        self.assertEqual(self.미터(self.첫, 중간, self.끝),
                         ((100.4, 0.5), (100.5, 0.5)))

    def test_첫창_공백경로는_다음_정상창을_막지않음(self):
        앞 = 창(99.0, 99.8, 경로=" ")
        self.assertEqual(self.음성(앞, self.첫, self.끝),
                         ((100.4, 100.5, 101.4, 101.5), 2))

    def test_기존_정상_중복창_새실측표본_보존(self):
        중간 = 창(100.8, 102.0, (101.1, 101.2))
        self.assertEqual(self.음성(self.첫, 중간, self.끝),
                         ((100.4, 100.5, 101.1, 101.2, 101.4, 101.5), 3))


if __name__ == "__main__":
    unittest.main()
