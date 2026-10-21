"""Existing GUI official Live2D -> OBS one-shot integration (offline contracts).

No real network, voice training, stream start, account access, OBS state changes.
"""
import sys
import time
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
            # The real meter API blocks for 1-3 seconds; the mock must yield
            # enough for the official-turn thread to finish (not instant-loop).
            import time
            began = time.monotonic()
            time.sleep(0.015)
            self.probe_count += 1
            ended = time.monotonic()
            return SimpleNamespace(
                coherent_media_candidate=stable,
                audio=SimpleNamespace(
                    first_selected_signal_monotonic=began if stable else 0.0,
                    last_selected_signal_monotonic=ended if stable else 0.0))
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
        def sampled_lip(*args, **kwargs):
            time.sleep(0.01)
            moment = time.monotonic()
            return SimpleNamespace(verified_signal=True,
                first_audio_mouth_monotonic=moment, last_audio_mouth_monotonic=moment)
        send = Mock(side_effect=sampled_lip)
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), (
            patch.object(pipeline, "send_to_native_live2d_session_with_observation", send)
        ):
            result = pipeline.verify_official_chat_live2d_obs(
                "한국어 테스트", obs_password="local", obs_input_name="Mic",
                operator_approved=True, voice_rights_confirmed=True)
        self.assertTrue(result.verified_observation)
        self.assertGreaterEqual(obs.probe_count, 1)
        self.assertLessEqual(obs.probe_count, 6)
        send.assert_called_once_with(
            "한국어 테스트", operator_approved=True, duration=8.0)

    def test_separate_positive_signals_without_time_overlap_are_not_verified(self):
        evidence = pipeline.OfficialChatObsEvidence(
            lip=SimpleNamespace(verified_signal=True),
            obs=SimpleNamespace(coherent_media_candidate=True),
            temporal_overlap_candidate=False,
        )
        self.assertFalse(evidence.verified_observation)

    def test_observation_overlap_without_real_audio_is_not_verified(self):
        evidence = pipeline.OfficialChatObsEvidence(
            lip=SimpleNamespace(verified_signal=True),
            obs=SimpleNamespace(coherent_media_candidate=False),
            temporal_overlap_candidate=True,
        )
        self.assertFalse(evidence.verified_observation)

    def test_lip_and_obs_positive_but_without_real_sample_times_is_unverified(self):
        obs = make_obs()
        lip = SimpleNamespace(verified_signal=True)
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), (
            patch.object(pipeline, "send_to_native_live2d_session_with_observation",
                         return_value=lip)
        ):
            outcome = pipeline.verify_official_chat_live2d_obs(
                "관찰 시각 없음", obs_password="local", obs_input_name="Mic",
                operator_approved=True, voice_rights_confirmed=True)
        self.assertFalse(outcome.verified_observation)
        self.assertFalse(outcome.temporal_overlap_candidate)

    def test_pre_cancel_denies_obs_and_ai_before_any_connection(self):
        import threading
        e = threading.Event()
        e.set()
        with patch.object(pipeline, "OfficialObsWebsocket") as obs, patch.object(
            pipeline, "send_to_native_live2d_session_with_observation") as ai:
            with self.assertRaises(InterruptedError):
                pipeline.verify_official_chat_live2d_obs("취소", obs_password="local",
                    obs_input_name="Mic", operator_approved=True,
                    voice_rights_confirmed=True, cancel_event=e)
        obs.assert_not_called()
        ai.assert_not_called()

    def test_cancel_after_ai_dispatch_never_reports_success_or_resends(self):
        import threading
        e = threading.Event()
        obs = make_obs()
        def sent(*a, **kwargs):
            e.set()
            return SimpleNamespace(verified_signal=True)
        ai = Mock(side_effect=sent)
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), patch.object(
            pipeline, "send_to_native_live2d_session_with_observation", ai):
            with self.assertRaises(InterruptedError):
                pipeline.verify_official_chat_live2d_obs("질문", obs_password="local",
                    obs_input_name="Mic", operator_approved=True,
                    voice_rights_confirmed=True, cancel_event=e)
        self.assertEqual(ai.call_count, 1)

    def test_stop_during_final_obs_safety_check_cannot_report_success(self):
        import threading
        stopped = threading.Event()
        obs = make_obs()
        visits = [0]
        original_status = obs.status
        def last_status():
            visits[0] += 1
            # Two early checks, one just before the request, then final.
            if visits[0] >= 4:
                stopped.set()
            return original_status()
        obs.status = last_status
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), (
            patch.object(pipeline, "send_to_native_live2d_session_with_observation",
                         return_value=SimpleNamespace(verified_signal=True))
        ) as send:
            with self.assertRaises(InterruptedError):
                pipeline.verify_official_chat_live2d_obs(
                    "마지막 OBS 검사 중단", obs_password="local",
                    obs_input_name="Mic", operator_approved=True,
                    voice_rights_confirmed=True, cancel_event=stopped)
        self.assertEqual(send.call_count, 1)

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

    def test_obs_monitor_owns_separate_connection(self):
        safety, monitor = make_obs(), make_obs()
        def sampled_lip(*args, **kwargs):
            time.sleep(0.01)
            moment = time.monotonic()
            return SimpleNamespace(verified_signal=True,
                first_audio_mouth_monotonic=moment, last_audio_mouth_monotonic=moment)
        with patch.object(
            pipeline, "OfficialObsWebsocket", side_effect=[safety, monitor]
        ) as factory, patch.object(
            pipeline, "send_to_native_live2d_session_with_observation",
            side_effect=sampled_lip,
        ):
            result = pipeline.verify_official_chat_live2d_obs(
                "테스트", obs_password="local", obs_input_name="Mic",
                operator_approved=True, voice_rights_confirmed=True)
        self.assertTrue(result.verified_observation)
        self.assertEqual(factory.call_count, 2)
        self.assertEqual(safety.probe_count, 0)
        self.assertGreaterEqual(monitor.probe_count, 1)
        self.assertLessEqual(monitor.probe_count, 6)

    def test_slow_korean_voice_uses_later_obs_meter_window(self):
        import threading

        safety, monitor = make_obs(), make_obs(stable=False)
        second_window = threading.Event()
        prompt_started = threading.Event()
        send = Mock()

        def monitor_window(**kwargs):
            self.assertTrue(prompt_started.wait(2))
            monitor.probe_count += 1
            if monitor.probe_count == 1:
                return SimpleNamespace(coherent_media_candidate=False)
            began = time.monotonic()
            second_window.set()
            import time
            time.sleep(0.01)
            return SimpleNamespace(
                coherent_media_candidate=True,
                audio=SimpleNamespace(
                    first_selected_signal_monotonic=began,
                    last_selected_signal_monotonic=time.monotonic()))

        def slow_official_turn(*args, **kwargs):
            prompt_started.set()
            self.assertTrue(
                second_window.wait(2),
                "The OBS monitor stopped before delayed Korean TTS started",
            )
            moment = time.monotonic()
            return SimpleNamespace(verified_signal=True,
                first_audio_mouth_monotonic=moment, last_audio_mouth_monotonic=moment)

        monitor.inspect_program_media = monitor_window
        send.side_effect = slow_official_turn
        with patch.object(
            pipeline, "OfficialObsWebsocket", side_effect=[safety, monitor]
        ), patch.object(
            pipeline, "send_to_native_live2d_session_with_observation", send
        ):
            result = pipeline.verify_official_chat_live2d_obs(
                "늦게 시작한 한국어 음성", obs_password="local",
                obs_input_name="Mic", operator_approved=True,
                voice_rights_confirmed=True,
            )
        self.assertTrue(result.verified_observation)
        self.assertGreaterEqual(monitor.probe_count, 2)
        self.assertEqual(send.call_count, 1)

    def test_obs_window_exhausted_before_ai_reply_is_not_success(self):
        import time

        safety, monitor = make_obs(), make_obs(stable=True)
        send = Mock(side_effect=lambda *a, **kw: (
            time.sleep(0.15), SimpleNamespace(verified_signal=True)
        )[1])
        with patch.object(
            pipeline, "OfficialObsWebsocket", side_effect=[safety, monitor]
        ), patch.object(
            pipeline, "send_to_native_live2d_session_with_observation", send
        ):
            with self.assertRaisesRegex(RuntimeError, "먼저 끝났습니다"):
                pipeline.verify_official_chat_live2d_obs(
                    "합성 지연 확인", obs_password="local",
                    obs_input_name="Mic", operator_approved=True,
                    voice_rights_confirmed=True,
                )
        self.assertEqual(monitor.probe_count, 6)
        self.assertEqual(send.call_count, 1)

    def test_outdated_lipsync_clock_will_not_certify_current_obs_sound(self):
        obs = make_obs()
        lip = SimpleNamespace(verified_signal=True,
                              first_audio_mouth_monotonic=0.001,
                              last_audio_mouth_monotonic=0.002)
        with patch.object(pipeline, "OfficialObsWebsocket", return_value=obs), (
            patch.object(pipeline, "send_to_native_live2d_session_with_observation",
                         return_value=lip)
        ):
            result = pipeline.verify_official_chat_live2d_obs(
                "과거 입 움직임", obs_password="local", obs_input_name="Mic",
                operator_approved=True, voice_rights_confirmed=True)
        self.assertFalse(result.temporal_overlap_candidate)
        self.assertFalse(result.verified_observation)

    def test_broad_three_second_window_does_not_certify_unrelated_meter_event(self):
        safety, monitor = make_obs(), make_obs()
        obs_signal = []
        def disjoint_media(**kwargs):
            began = time.monotonic()
            # A real 3-second OBS observation could be coherent even though
            # its only non-silent meter tick happened BEFORE mouth motion.
            time.sleep(0.08)
            ended = time.monotonic()
            obs_signal.append((began, ended))
            return SimpleNamespace(
                coherent_media_candidate=True,
                audio=SimpleNamespace(
                    first_selected_signal_monotonic=began,
                    last_selected_signal_monotonic=ended))
        monitor.inspect_program_media = disjoint_media
        def unrelated_lip(*args, **kwargs):
            time.sleep(0.035)
            tm = time.monotonic()
            return SimpleNamespace(
                verified_signal=True,
                first_audio_mouth_monotonic=tm,
                last_audio_mouth_monotonic=tm)
        with patch.object(pipeline, "OfficialObsWebsocket",
                          side_effect=[safety, monitor]), patch.object(
                          pipeline, "send_to_native_live2d_session_with_observation",
                          side_effect=unrelated_lip):
            result = pipeline.verify_official_chat_live2d_obs(
                "OBS 먼저 짧은 소리, Live2D 나중에 다른 발화",
                obs_password="local", obs_input_name="Mic",
                operator_approved=True, voice_rights_confirmed=True)
        self.assertFalse(result.verified_observation)
        self.assertFalse(result.temporal_overlap_candidate)

    def test_missing_obs_event_monotonic_times_cannot_certify_same_utterance(self):
        safety, monitor = make_obs(), make_obs()
        def no_timestamps(**kwargs):
            time.sleep(0.015)
            return SimpleNamespace(
                coherent_media_candidate=True,
                audio=SimpleNamespace(first_selected_signal_monotonic=0.0,
                                      last_selected_signal_monotonic=0.0))
        monitor.inspect_program_media = no_timestamps
        def live2d(*args, **kwargs):
            time.sleep(0.005)
            now = time.monotonic()
            return SimpleNamespace(
                verified_signal=True,
                first_audio_mouth_monotonic=now,
                last_audio_mouth_monotonic=now)
        with patch.object(pipeline, "OfficialObsWebsocket",
                          side_effect=[safety, monitor]), patch.object(
                          pipeline, "send_to_native_live2d_session_with_observation",
                          side_effect=live2d):
            result = pipeline.verify_official_chat_live2d_obs(
                "OBS time missing", obs_password="local", obs_input_name="Mic",
                operator_approved=True, voice_rights_confirmed=True)
        self.assertFalse(result.verified_observation)

    def test_failed_obs_observer_setup_prevents_ai_prompt(self):
        safety, monitor = make_obs(), make_obs()
        monitor.connect = Mock(side_effect=OSError("OBS disconnected"))
        with patch.object(
            pipeline, "OfficialObsWebsocket", side_effect=[safety, monitor]
        ), patch.object(
            pipeline, "send_to_native_live2d_session_with_observation"
        ) as sender:
            with self.assertRaisesRegex(RuntimeError, "질문을 보내지 않았습니다"):
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
