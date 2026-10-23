# -*- coding: utf-8 -*-
"""136회차: 공식 로컬 시각차와 Stop 후 수신 공백 동결의 단위 회귀.

이 검사는 모의 시각/로컬 객체를 사용하며 실제 한국어 WAV·OBS·방송
또는 실제 수백 명·24시간 운영·시청자 종단간 3초 달성 증거가 아니다.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_broadcaster.official_media_stage_timing import measure_official_media_stages
from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession


class 공식로컬관측지연검사(unittest.TestCase):
    def test_로컬첫오디오와입_병렬지연_실측구간으로계산(self):
        result = measure_official_media_stages(
            prompt_started_at=100.0, prompt_finished_at=104.0,
            wav_received_at=101.2, mouth_first_at=101.6,
            obs_first_at=101.9, obs_observation_ended_at=104.0,
            same_utterance_overlap=True,
        )
        self.assertAlmostEqual(result.first_local_audio_seconds, 1.9)
        self.assertAlmostEqual(result.first_local_mouth_seconds, 1.6)
        self.assertAlmostEqual(result.first_local_audio_video_seconds, 1.9)
        self.assertIs(result.local_audio_video_over_three_seconds, False)
        self.assertEqual(result.longest_observed_stage_ko, "질문→공식 WAV")
        self.assertIn("시청자 전달 미검증", result.describe_ko())

    def test_로컬삼초초과와_후반관측구간_구분(self):
        result = measure_official_media_stages(
            prompt_started_at=100, prompt_finished_at=107,
            wav_received_at=100.2, mouth_first_at=103.4,
            obs_first_at=102.5, obs_observation_ended_at=105,
            same_utterance_overlap=True,
        )
        self.assertAlmostEqual(result.first_local_audio_video_seconds, 3.4)
        self.assertIs(result.local_audio_video_over_three_seconds, True)
        self.assertEqual(result.longest_observed_stage_ko, "WAV→Cubism 첫 입")

    def test_동일발화_오디오_미확인시_성공값을만들지않음(self):
        result = measure_official_media_stages(
            prompt_started_at=100, prompt_finished_at=107,
            wav_received_at=101, mouth_first_at=102,
            obs_first_at=102.3, obs_observation_ended_at=105,
            same_utterance_overlap=False,
        )
        self.assertIsNone(result.first_local_audio_video_seconds)
        self.assertIsNone(result.local_audio_video_over_three_seconds)
        self.assertEqual(result.longest_observed_stage_ko, "미측정")
        self.assertIn("로컬 3초 초과 미측정", result.describe_ko())


class 실제수신세션중지후공백검사(unittest.TestCase):
    def test_연결공백은_중지시각에서동결되고_현재공백은종료(self):
        session = MultiPlatformReadOnlySession(
            {"twitch": "aisting_test_channel"}, lambda kind, item: True
        )
        session._session_started_at = 100.0
        session._disconnect_started["twitch"] = 105.0
        with patch("ai_broadcaster.multi_platform_session.time.monotonic", return_value=108.0):
            before = session.reconnect_snapshot()["twitch"]
        self.assertEqual(before["관측공백초"], 3.0)
        self.assertTrue(before["현재공백"])
        with patch("ai_broadcaster.multi_platform_session.time.monotonic", return_value=110.0):
            session.stop()
        with patch("ai_broadcaster.multi_platform_session.time.monotonic", return_value=900.0):
            after = session.reconnect_snapshot()["twitch"]
        self.assertEqual(after["관측공백초"], 5.0)
        self.assertFalse(after["현재공백"])
        self.assertFalse(after["채팅방입장"])


if __name__ == "__main__":
    unittest.main()
