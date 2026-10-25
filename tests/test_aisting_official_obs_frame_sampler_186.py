"""186절: OBS 공식 Live2D 창의 실제 경로 관측 코드 계약검사(실장비 아님).

이 검사는 실제 OBS·권리 음성·방송/인코더·시청자 응답의 실증을 대신하지
않는다. 전체 기능 개발 완료 후 회귀 단계에서 실행하기 위해 작성한다.
"""
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ai_broadcaster.obs_live2d_frame_link import (
    OfficialProgramFrameSampler, active_official_window_capture,
    program_motion_near_audio,
)


OFFICIAL = (
    "AISTING 얼굴창 (window_capture, 활성)"
    " / 선택된 창 AISTING | 공식 Live2D 및 AI 대화:WebView2"
)


class TestOfficialObsProgramMotionContract186(unittest.TestCase):
    def test_공식_Live2D_창_제목과_활성_창_캡처만_인정(self):
        self.assertTrue(active_official_window_capture((OFFICIAL,)))
        self.assertFalse(active_official_window_capture((
            "화면 (monitor_capture, 활성)",)))
        self.assertFalse(active_official_window_capture((
            "다른 윈도우 (window_capture, 활성)"
            " / 선택된 창 다른 방송:WebView2",)))
        self.assertFalse(active_official_window_capture((
            "공식 창: 비활성 (window_capture, 활성)"
            " / 선택된 창 AISTING | 공식 Live2D 및 AI 대화",)))

    def test_실제관찰시각_없는_영상은_결합후보_금지(self):
        self.assertFalse(program_motion_near_audio((), (), restart_at=1.0,
                                                   wav_seconds=3.0))
        self.assertFalse(program_motion_near_audio((
            (0.1, "장면", "0" * 64),
            (0.7, "장면", "1" * 64),
            (1.0, "다른장면", "1" * 64),
        ), (0.8,), restart_at=0.5, wav_seconds=1.5))

    def test_관찰중_마지막프레임_변화도_WAV_근접후보(self):
        frames = (
            (1.0, "장면", "0" * 64),
            (1.4, "장면", "0" * 64),
            (1.8, "장면", "1" * 64),
        )
        self.assertTrue(program_motion_near_audio(
            frames, (1.77,), restart_at=1.2, wav_seconds=1.0))

    def test_실제_관찰작업자는_메모리_해시만_기록하고_종료(self):
        seen = {"frames": 0}

        class FakeObs:
            def __init__(self, _password, *, port):
                self._client = SimpleNamespace(get_record_status=lambda:
                                               SimpleNamespace(output_active=False))

            def connect(self):
                return SimpleNamespace(streaming=False, scene="공식장면")

            def status(self):
                return SimpleNamespace(streaming=False, scene="공식장면")

            def read_scene_media_path(self):
                return SimpleNamespace(capture_sources=(OFFICIAL,))

            def read_current_scene_frame(self, *, operator_approved):
                seen["frames"] += 1
                return SimpleNamespace(
                    scene="공식장면",
                    png_data=("가상프레임-" + str(seen["frames"])).encode("utf-8"))

        with patch("ai_broadcaster.original_plan_obs.OfficialObsWebsocket", FakeObs):
            sampler = OfficialProgramFrameSampler(
                "테스트전용", port=4455, scene="공식장면",
                interval_seconds=0.2)
            sampler.start()
            sampler.begin()
            time.sleep(0.5)
            frames = sampler.finish()
        self.assertGreaterEqual(len(frames), 3)
        self.assertTrue(all(len(record[2]) == 64 for record in frames))
        self.assertTrue(all(record[1] == "공식장면" for record in frames))
        self.assertTrue(all(frames[i][0] < frames[i + 1][0]
                            for i in range(len(frames) - 1)))

    def test_실제_공식_창_미확인시_관찰_시작도_금지(self):
        class WrongWindowObs:
            def __init__(self, _password, *, port):
                self._client = SimpleNamespace(get_record_status=lambda:
                                               SimpleNamespace(output_active=False))
            def connect(self):
                return SimpleNamespace(streaming=False, scene="장면")
            def status(self):
                return self.connect()
            def read_scene_media_path(self):
                return SimpleNamespace(capture_sources=(
                    "다른창 (window_capture, 활성)",))
        with patch("ai_broadcaster.original_plan_obs.OfficialObsWebsocket",
                   WrongWindowObs):
            sampler = OfficialProgramFrameSampler(
                "테스트", port=4455, scene="장면")
            with self.assertRaises(RuntimeError):
                sampler.start()


if __name__ == "__main__":
    unittest.main()
