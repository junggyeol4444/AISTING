# -*- coding: utf-8 -*-
"""147회차: 연속 OBS 창 사이의 미확인/무음 경로를 건너뛰지 않는 계약검사.

가상 관찰 객체 검사다. 실제 한국어 WAV·공식 Cubism·OBS 출력 실증이 아니다.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.obs_consecutive_audio import (
    collect_obs_audio_times, collect_obs_input_meter_levels,
)


def 관찰(시작, 끝, 시각=(100.4, 100.5), *, 입력="A", 종료입력=None,
       정상=True, 경로누락=False):
    def 경로(이름):
        return SimpleNamespace(
            scene="장면1", input_name=이름, origin="scene",
            identity=("장면1", 이름), enabled_tracks=(1,))
    오디오 = SimpleNamespace(
        first_selected_signal_monotonic=시각[0] if len(시각) >= 2 else None,
        last_selected_signal_monotonic=시각[-1] if len(시각) >= 2 else None,
        selected_signal_sample_times=시각,
        selected_all_meter_level_samples=tuple((t, 0.5) for t in 시각),
    )
    결과 = SimpleNamespace(coherent_media_candidate=정상, audio=오디오)
    if not 경로누락:
        결과.before_audio_route = 경로(입력)
        결과.after_audio_route = 경로(종료입력 if 종료입력 is not None else 입력)
    return (시작, 끝, 결과)


class OBS중간경로검사(unittest.TestCase):
    def setUp(self):
        self.첫 = 관찰(100.0, 101.0)
        self.끝 = 관찰(101.0, 103.0, (101.4, 101.5))

    def 음성(self, 창):
        return collect_obs_audio_times(창, 100.3, 102.0)

    def 미터(self, 창):
        return collect_obs_input_meter_levels(창, since=100.3, until=102.0)

    def test_경로전후불일치_중간창_뒤쪽_음성을_합치지않음(self):
        중간 = 관찰(100.8, 101.6, (101.1, 101.2), 종료입력="B")
        self.assertEqual(self.음성((self.첫, 중간, self.끝)),
                         ((100.4, 100.5), 1))
        self.assertEqual(self.미터((self.첫, 중간, self.끝)),
                         ((100.4, 0.5), (100.5, 0.5)))

    def test_미확인_중간창_뒤의_복귀경로도_분리(self):
        중간 = 관찰(100.8, 101.6, (101.1, 101.2), 정상=False)
        self.assertEqual(self.음성((self.첫, 중간, self.끝)),
                         ((100.4, 100.5), 1))
        self.assertEqual(len(self.미터((self.첫, 중간, self.끝))), 2)

    def test_무음_중간창에서_입력이_바뀌었다_복귀해도_분리(self):
        중간 = 관찰(100.8, 101.6, (), 입력="B")
        self.assertEqual(self.음성((self.첫, 중간, self.끝)),
                         ((100.4, 100.5), 1))
        self.assertEqual(len(self.미터((self.첫, 중간, self.끝))), 2)

    def test_경로가_같은_무음창은_뒤의_새표본_허용(self):
        중간 = 관찰(100.8, 101.6, ())
        self.assertEqual(self.음성((self.첫, 중간, self.끝)),
                         ((100.4, 100.5, 101.4, 101.5), 2))
        self.assertEqual(len(self.미터((self.첫, 중간, self.끝))), 4)

    def test_처음의_불명확한_창은_정상창_시작을_막지않음(self):
        앞 = 관찰(99.0, 99.9, (99.4, 99.5), 정상=False)
        self.assertEqual(self.음성((앞, self.첫, self.끝)),
                         ((100.4, 100.5, 101.4, 101.5), 2))

    def test_시각이_잘못된_중간창_뒤_음성은_불연속(self):
        중간 = 관찰(100.8, 100.8, (100.8, 100.9))
        self.assertEqual(self.음성((self.첫, 중간, self.끝)),
                         ((100.4, 100.5), 1))
        self.assertEqual(len(self.미터((self.첫, 중간, self.끝))), 2)

    def test_경로없는_기존_가상관찰_호환(self):
        첫 = 관찰(100.0, 101.0, 경로누락=True)
        끝 = 관찰(101.0, 103.0, (101.4, 101.5), 경로누락=True)
        self.assertEqual(self.음성((첫, 끝)),
                         ((100.4, 100.5, 101.4, 101.5), 2))


if __name__ == "__main__":
    unittest.main()
