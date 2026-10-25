"""184회차 개발 계약검사 — 전체 기능 개발 후 회귀 단계에서 실행.

본 파일 작성만으로 실제 OBS/공식 Live2D/시청자 송출 성공을 주장하지 않는다.
"""
from __future__ import annotations

import unittest

from ai_broadcaster.obs_live2d_frame_link import (
    active_official_window_capture,
    program_motion_near_audio,
)


class OfficialWindowCaptureContracts(unittest.TestCase):
    def test_exact_official_window_capture_is_candidate(self):
        self.assertTrue(active_official_window_capture((
            "AISTING 창 (window_capture, 활성) / 선택된 창 "
            "AISTING | 공식 Live2D 및 AI 대화:Chrome_WidgetWin_1:pid",)))

    def test_unrelated_or_inactive_capture_is_not_official(self):
        for captures in (
            ("다른 방송 창 (window_capture, 활성) / 선택된 창 다른 창",),
            ("모니터 (monitor_capture, 활성)",),
            ("AISTING (window_capture, 활성) / 선택된 창 다른 창",),
            ("AISTING: 비활성",),
            (),
        ):
            self.assertFalse(active_official_window_capture(captures))


class ActualProgramFrameTimingContracts(unittest.TestCase):
    def setUp(self):
        self.samples = (
            (9.0, "원래 장면", "a" * 64),
            (10.8, "원래 장면", "b" * 64),
            (11.9, "원래 장면", "a" * 64),
            (13.1, "원래 장면", "a" * 64),
        )

    def check(self, frames=None, audio=(10.85,), restart=10.0, wav=3.0):
        return program_motion_near_audio(
            self.samples if frames is None else frames,
            audio, restart_at=restart, wav_seconds=wav)

    def test_real_audio_near_changed_program_frame_is_candidate_only(self):
        self.assertTrue(self.check())

    def test_silent_meter_never_claims_program_audio(self):
        self.assertFalse(self.check(audio=()))

    def test_unrelated_program_scene_change_is_not_same_path(self):
        frames = list(self.samples)
        frames[2] = (11.9, "다른 장면", "a" * 64)
        self.assertFalse(self.check(frames=tuple(frames)))

    def test_changed_frame_outside_wav_is_not_candidate(self):
        self.assertFalse(self.check(audio=(12.95,), wav=0.4))

    def test_no_video_change_does_not_count_as_motion(self):
        frames = tuple((t, scene, "a" * 64)
                       for t, scene, _ in self.samples)
        self.assertFalse(self.check(frames=frames))

    def test_future_audio_outside_real_wav_is_rejected(self):
        self.assertFalse(self.check(audio=(15.0,)))

    def test_nonmonotonic_or_missing_baseline_is_rejected(self):
        frames = list(self.samples)
        frames[1] = (8.0, "원래 장면", "b" * 64)
        self.assertFalse(self.check(frames=tuple(frames)))
        self.assertFalse(self.check(frames=self.samples[1:]))

    def test_invalid_time_and_hash_are_rejected(self):
        self.assertFalse(self.check(restart=float("nan")))
        frames = list(self.samples)
        frames[1] = (10.8, "원래 장면", "bad")
        self.assertFalse(self.check(frames=tuple(frames)))


if __name__ == "__main__":
    unittest.main()
