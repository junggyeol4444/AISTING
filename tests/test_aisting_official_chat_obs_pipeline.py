"""Existing GUI official Live2D -> OBS one-shot integration (offline contracts).

No real network, voice training, stream start, account access, OBS state changes.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster import original_plan_full_pipeline as pipeline


def make_obs(*, confirmed=True, stable=True):
    class Obs:
        def __init__(self):
            self.probe_count = 0
            self._client = SimpleNamespace(
                get_record_status=lambda: SimpleNamespace(output_active=False)
            )
        def connect(self):
            return SimpleNamespace(streaming=False, scene="Scene")
        def read_program_audio_route(self, **kwargs):
            return SimpleNamespace(confirmed=confirmed)
        def inspect_program_media(self, **kwargs):
            self.probe_count += 1
            return SimpleNamespace(coherent_media_candidate=stable)
        def status(self):
            return SimpleNamespace(streaming=False, scene="Scene")
    return Obs()


class FullPipelineContracts(unittest.TestCase):
    def test_explicit_rights_and_operator_gate_blocks_before_any_calls(self):
        with patch.object(pipeline, "OfficialObsWebsocket") as obs:
            with self.assertRaises(PermissionError):
                pipeline.verify_official_chat_live2d_obs(
                    "안녕하세요", obs_password="secret", obs_input_name="Mic")
            obs.assert_not_called()

    def test_existing_official_ai_turn_only_once_and_obs_read_only(self):
        obs = make_obs()
        lip = SimpleNamespace(verified_signal=True)
        send = Mock(return_value=lip)
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), (
            patch.object(pipeline, "send_to_native_live2d_session_with_observation", send)
        ):
            result = pipeline.verify_official_chat_live2d_obs(
                "한국어 테스트", obs_password="local", obs_input_name="Mic",
                operator_approved=True, voice_rights_confirmed=True)
        self.assertTrue(result.verified_observation)
        self.assertEqual(obs.probe_count, 1)
        send.assert_called_once_with(
            "한국어 테스트", operator_approved=True, duration=8.0)

    def test_active_obs_recording_denies_prompt_without_side_effect(self):
        obs = make_obs()
        obs._client.get_record_status = lambda: SimpleNamespace(output_active=True)
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), (
            patch.object(pipeline, "send_to_native_live2d_session_with_observation")
        ) as sender:
            with self.assertRaisesRegex(RuntimeError, "녹화 중"):
                pipeline.verify_official_chat_live2d_obs(
                    "테스트", obs_password="local", obs_input_name="Mic",
                    operator_approved=True, voice_rights_confirmed=True)
            sender.assert_not_called()
        self.assertEqual(obs.probe_count, 0)

    def test_recording_status_unavailable_fails_closed(self):
        obs = make_obs()
        obs._client.get_record_status = Mock(side_effect=OSError("OBS unreachable"))
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), (
            patch.object(pipeline, "send_to_native_live2d_session_with_observation")
        ) as sender:
            with self.assertRaisesRegex(RuntimeError, "녹화 상태"):
                pipeline.verify_official_chat_live2d_obs(
                    "테스트", obs_password="local", obs_input_name="Mic",
                    operator_approved=True, voice_rights_confirmed=True)
            sender.assert_not_called()

    def test_recording_starts_after_preflight_still_blocks_ai_turn(self):
        obs = make_obs()
        visits = iter((False, True, True))
        obs._client.get_record_status = lambda: SimpleNamespace(
            output_active=next(visits)
        )
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), (
            patch.object(pipeline, "send_to_native_live2d_session_with_observation")
        ) as sender:
            with self.assertRaisesRegex(RuntimeError, "녹화 중"):
                pipeline.verify_official_chat_live2d_obs(
                    "테스트", obs_password="local", obs_input_name="Mic",
                    operator_approved=True, voice_rights_confirmed=True)
            sender.assert_not_called()

    def test_unconfirmed_obs_route_does_not_send_ai_prompt(self):
        obs = make_obs(confirmed=False)
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), (
            patch.object(pipeline, "send_to_native_live2d_session_with_observation")
        ) as send:
            with self.assertRaises(RuntimeError):
                pipeline.verify_official_chat_live2d_obs(
                    "한국어", obs_password="local", obs_input_name="Mic",
                    operator_approved=True, voice_rights_confirmed=True)
            send.assert_not_called()

    def test_missing_mouth_motion_is_not_reported_as_success(self):
        obs = make_obs()
        lip = SimpleNamespace(verified_signal=False)
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), (
            patch.object(pipeline, "send_to_native_live2d_session_with_observation",
                         return_value=lip)
        ):
            result = pipeline.verify_official_chat_live2d_obs(
                "테스트", obs_password="local", obs_input_name="Mic",
                operator_approved=True, voice_rights_confirmed=True)
        self.assertFalse(result.verified_observation)

    def test_obs_unstable_does_not_report_success(self):
        obs = make_obs(stable=False)
        lip = SimpleNamespace(verified_signal=True)
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), (
            patch.object(pipeline, "send_to_native_live2d_session_with_observation",
                         return_value=lip)
        ):
            result = pipeline.verify_official_chat_live2d_obs(
                "테스트", obs_password="local", obs_input_name="Mic",
                operator_approved=True, voice_rights_confirmed=True)
        self.assertFalse(result.verified_observation)

    def test_send_error_does_not_repeat_prompt(self):
        obs = make_obs()
        send = Mock(side_effect=RuntimeError("unknown delivery"))
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), (
            patch.object(pipeline, "send_to_native_live2d_session_with_observation", send)
        ):
            with self.assertRaisesRegex(RuntimeError, "자동 재시도하지 않습니다"):
                pipeline.verify_official_chat_live2d_obs(
                    "안녕", obs_password="local", obs_input_name="Mic",
                    operator_approved=True, voice_rights_confirmed=True)
        self.assertEqual(send.call_count, 1)


if __name__ == "__main__":
    unittest.main()
