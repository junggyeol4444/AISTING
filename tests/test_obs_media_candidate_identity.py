"""Regression for exact OBS audio input identity and final scene read.

This test uses value objects only; it is not a live OBS, audio or stream test.
"""
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.original_plan_obs import (
    ActualObsState, ActualObsFrame, ActualObsAudioMeters,
    ActualObsAudioRoute, ActualObsProgramMediaObservation,
)


class TestProgramMediaCandidateIdentity(unittest.TestCase):
    def setUp(self):
        self.state = ActualObsState('31.0', 'Current scene', False)
        self.frame = ActualObsFrame('Current scene', 1, 1, b'png')
        self.meter = ActualObsAudioMeters(
            event_count=2, input_peaks=(('Voice Output', 0.2),),
            selected_input='Voice Output', selected_muted=False,
            selected_volume=1.0, selected_meter_events=2,
        )
        self.route = ActualObsAudioRoute(
            'Current scene', 'Voice Output', 'enabled-scene-item',
            ('5:uuid-voice',), (1,),
        )
        self.observation = ActualObsProgramMediaObservation(
            before=self.state, after_frame=self.state, after_meter=self.state,
            frame=self.frame, audio=self.meter,
            before_audio_route=self.route, after_audio_route=self.route,
            after_route=self.state,
        )

    def test_matching_audio_input_and_final_scene_is_candidate_only(self):
        self.assertTrue(self.observation.coherent_media_candidate)

    def test_different_meter_input_cannot_confirm_another_route(self):
        mismatched = replace(
            self.observation,
            audio=replace(self.meter, input_peaks=(('Different Input', 0.5),),
                          selected_input='Different Input'),
        )
        self.assertTrue(mismatched.audio.usable_output_candidate)
        self.assertFalse(mismatched.coherent_media_candidate)

    def test_final_obs_scene_read_is_required(self):
        missing = replace(self.observation, after_route=None)
        self.assertFalse(missing.coherent_media_candidate)

    def test_changed_final_scene_cannot_be_confirmed(self):
        changed = replace(
            self.observation,
            after_route=ActualObsState('31.0', 'Other scene', False),
        )
        self.assertFalse(changed.coherent_media_candidate)


if __name__ == '__main__':
    unittest.main()
