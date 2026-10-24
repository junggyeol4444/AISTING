"""AISTING 165회차: 같은 질문의 WAV/입/OBS 관찰 경계 가상 계약검사.

아래 시각과 음량은 전부 가상 값이며 실모델·실송출 증거가 아니다.
네트워크, 계정, OBS, TTS, 브라우저를 실행하지 않는다.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ai_broadcaster.original_plan_full_pipeline import (
    OfficialChatObsEvidence,
    _confirmed_current_prompt_wav_obs_provenance,
)


class CurrentPromptWavProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.lip = SimpleNamespace(
            first_audio_mouth_monotonic=12.0,
            last_audio_mouth_monotonic=14.0,
            official_pcm_first_wav_received_monotonic=11.5,
            official_wav_riff_length_matched=1,
            official_ws_audio_events=1,
            verified_signal=True,
        )

    def _check(self, *, times=(12.2, 13.3), matching=True):
        with patch(
            "ai_broadcaster.original_plan_full_pipeline._confirmed_mouth_obs_audio_provenance",
            return_value=True,
        ), patch(
            "ai_broadcaster.original_plan_full_pipeline._matched_obs_audio_evidence",
            return_value=(times, 1 if matching else 0, [object()] if matching else [], (0,)),
        ):
            return _confirmed_current_prompt_wav_obs_provenance(
                [object()], self.lip, 10.0, 15.0)

    def test_current_real_wav_and_two_simultaneous_obs_samples_allow_early_finish_candidate(self):
        self.assertTrue(self._check())

    def test_past_wav_receive_time_cannot_finish_current_observation(self):
        self.lip.official_pcm_first_wav_received_monotonic = 9.9
        self.assertFalse(self._check())

    def test_wav_without_received_timestamp_cannot_finish(self):
        self.lip.official_pcm_first_wav_received_monotonic = None
        self.assertFalse(self._check())

    def test_late_wav_cannot_explain_earlier_mouth(self):
        self.lip.official_pcm_first_wav_received_monotonic = 12.5
        self.assertFalse(self._check())

    def test_one_audio_sample_does_not_cut_short_observation(self):
        self.assertFalse(self._check(times=(12.3,)))

    def test_mouth_near_only_audio_does_not_count_as_simultaneous(self):
        self.assertFalse(self._check(times=(11.9, 14.1)))

    def test_unverified_riff_or_missing_server_audio_does_not_cut_short_observation(self):
        self.lip.official_wav_riff_length_matched = 0
        self.assertFalse(self._check())
        self.lip.official_wav_riff_length_matched = 1
        self.lip.official_ws_audio_events = 0
        self.assertFalse(self._check())

    def test_unmatched_obs_route_does_not_cut_short_observation(self):
        self.assertFalse(self._check(matching=False))

    def test_voice_candidate_requires_current_prompt_wav_timestamp(self):
        obs = SimpleNamespace(coherent_media_candidate=True)
        stale = OfficialChatObsEvidence(
            lip=self.lip, obs=obs, temporal_overlap_candidate=True)
        self.assertFalse(stale.same_session_voice_candidate)
        recent = OfficialChatObsEvidence(
            lip=self.lip, obs=obs, temporal_overlap_candidate=True,
            current_prompt_wav_received=True)
        self.assertTrue(recent.same_session_voice_candidate)


if __name__ == "__main__":
    unittest.main()
