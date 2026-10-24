# -*- coding: utf-8 -*-
"""152회차: 실제 OBS 관찰창 사이의 무관측 공백을 동일 발화로 합치지 않는다.

이 검사는 가상 관찰 객체에 대한 계약검사다.
실제 GPT-SoVITS WAV·공식 Live2D Cubism·OBS 방송 출력의 성공 증거가 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.obs_consecutive_audio import (
    collect_obs_audio_times, collect_obs_input_meter_levels,
)


def 창(시작, 종료, 시각=(), *, 경로="장면A/입력A/트랙1"):
    음성 = SimpleNamespace(
        first_selected_signal_monotonic=시각[0] if 시각 else None,
        last_selected_signal_monotonic=시각[-1] if 시각 else None,
        selected_signal_sample_times=시각,
        selected_all_meter_level_samples=tuple((t, 0.5) for t in 시각),
    )
    return 시작, 종료, SimpleNamespace(
        coherent_media_candidate=True,
        before_audio_route=경로, after_audio_route=경로, audio=음성,
    )


class OBS무관측공백연속성검사(unittest.TestCase):
    def setUp(self):
        self.첫 = 창(100.0, 101.0, (100.4, 100.5))
        self.연속 = 창(101.0, 103.0, (101.4, 101.5))
        self.공백뒤 = 창(101.1, 103.0, (101.4, 101.5))

    def 음성(self, 창들, 시작=100.3, 종료=103.0):
        return collect_obs_audio_times(창들, 시작, 종료)

    def 미터(self, 창들, 시작=100.3, 종료=103.0):
        return collect_obs_input_meter_levels(창들, since=시작, until=종료)

    def test_음성_관찰창사이_무관측공백은_뒤쪽결합차단(self):
        self.assertEqual(self.음성((self.첫, self.공백뒤)),
                         ((100.4, 100.5), 1))

    def test_미터_관찰창사이_무관측공백은_뒤쪽결합차단(self):
        self.assertEqual(self.미터((self.첫, self.공백뒤)),
                         ((100.4, 0.5), (100.5, 0.5)))

    def test_무음창까지_연속관찰한뒤_공백발생하면_음성차단(self):
        중간무음 = 창(100.8, 101.5)
        뒤 = 창(101.6, 103.0, (102.0, 102.1))
        self.assertEqual(self.음성((self.첫, 중간무음, 뒤)),
                         ((100.4, 100.5), 1))

    def test_무음창까지_연속관찰한뒤_공백발생하면_미터차단(self):
        중간무음 = 창(100.8, 101.5)
        뒤 = 창(101.6, 103.0, (102.0, 102.1))
        self.assertEqual(self.미터((self.첫, 중간무음, 뒤)),
                         ((100.4, 0.5), (100.5, 0.5)))

    def test_겹친짧은창은_기존의_긴관찰범위를_축소하지않음(self):
        긴창 = 창(100.0, 103.0, (100.4, 100.5))
        짧은겹침 = 창(100.8, 101.1, (100.9, 101.0))
        뒤 = 창(102.5, 104.0, (102.6, 102.7))
        창들 = (긴창, 짧은겹침, 뒤)
        self.assertEqual(self.음성(창들, 종료=103.0),
                         ((100.4, 100.5, 100.9, 101.0, 102.6, 102.7), 3))
        self.assertEqual(len(self.미터(창들, 종료=103.0)), 6)

    def test_정확히_맞닿은_관찰창은_정상결합(self):
        self.assertEqual(self.음성((self.첫, self.연속)),
                         ((100.4, 100.5, 101.4, 101.5), 2))
        self.assertEqual(len(self.미터((self.첫, self.연속))), 4)

    def test_첫_실측증거_전의_무관측공백은_첫정상창을_막지않음(self):
        앞무음 = 창(98.0, 99.0)
        self.assertEqual(self.음성((앞무음, self.첫, self.연속)),
                         ((100.4, 100.5, 101.4, 101.5), 2))
        self.assertEqual(len(self.미터((앞무음, self.첫, self.연속))), 4)


if __name__ == "__main__":
    unittest.main()
