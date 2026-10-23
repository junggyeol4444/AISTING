# -*- coding: utf-8 -*-
"""135회차 단위검사: 모의 시각은 실제 WAV/OBS/시청자 실증이 아니다."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.official_media_stage_timing import measure_official_media_stages


class 공식동일질문단계지연검사(unittest.TestCase):
    def test_동일질문_세구간_측정(self):
        value = measure_official_media_stages(
            prompt_started_at=100, prompt_finished_at=106,
            wav_received_at=102, mouth_first_at=102.25,
            obs_first_at=102.45, obs_observation_ended_at=105,
            same_utterance_overlap=True)
        self.assertEqual((value.wav_after_prompt_seconds,
                          value.mouth_after_wav_seconds,
                          value.obs_after_wav_seconds,
                          value.obs_minus_mouth_seconds), (2.0, 0.25, 0.45, 0.2))
        self.assertIn("시청자 전달 미검증", value.describe_ko())

    def test_겹치지않는_obs는_미측정(self):
        value = measure_official_media_stages(
            prompt_started_at=100, prompt_finished_at=106,
            wav_received_at=102, mouth_first_at=102.25,
            obs_first_at=102.45, obs_observation_ended_at=105,
            same_utterance_overlap=False)
        self.assertIsNone(value.obs_after_wav_seconds)
        self.assertEqual(value.mouth_after_wav_seconds, 0.25)

    def test_이전_질문_wav는_모두_미측정(self):
        value = measure_official_media_stages(
            prompt_started_at=100, prompt_finished_at=106,
            wav_received_at=99, mouth_first_at=100.1,
            obs_first_at=104, obs_observation_ended_at=105,
            same_utterance_overlap=True)
        self.assertIsNone(value.wav_after_prompt_seconds)
        self.assertIsNone(value.obs_after_wav_seconds)

    def test_obs가_입보다_앞서면_음수_보존(self):
        value = measure_official_media_stages(
            prompt_started_at=100, prompt_finished_at=106,
            wav_received_at=102, mouth_first_at=103,
            obs_first_at=102.6, obs_observation_ended_at=105,
            same_utterance_overlap=True)
        self.assertAlmostEqual(value.obs_minus_mouth_seconds, -0.4)

    def test_관찰종료후_obs와_역행시간_거절(self):
        kwargs = dict(prompt_started_at=100, prompt_finished_at=106,
                      wav_received_at=102, mouth_first_at=103,
                      obs_first_at=106, obs_observation_ended_at=105,
                      same_utterance_overlap=True)
        self.assertIsNone(measure_official_media_stages(**kwargs).obs_after_wav_seconds)
        kwargs["prompt_started_at"] = 107
        self.assertIsNone(measure_official_media_stages(**kwargs).wav_after_prompt_seconds)


if __name__ == "__main__":
    unittest.main()
