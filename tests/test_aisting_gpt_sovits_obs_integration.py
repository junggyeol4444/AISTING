"""Operator-approved real GPT-SoVITS -> official OBS media meter path contract.

Unit tests intentionally substitute dependencies. They cannot certify the
presence of a downloaded GPT-SoVITS model or a real OBS process.
"""
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from ai_broadcaster.original_plan_obs import OfficialObsWebsocket

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.original_plan_voice_obs_bridge import verify_gpt_sovits_to_obs

class VerifyRealVoiceObsTests(unittest.TestCase):
    def test_obs_meter_subscribes_before_authorized_temporary_source_restart(self):
        steps = []
        class Client:
            def get_input_list(self):
                return SimpleNamespace(inputs=[{
                    "inputName":"AISTING-new-temp", "inputUuid":"unique-test-uuid"}])
            def get_input_mute(self, name):
                return SimpleNamespace(input_muted=False)
            def get_input_volume(self, name):
                return SimpleNamespace(input_volume_mul=1.0)
        class Events:
            def __init__(self, **kwargs):
                self.callback = SimpleNamespace(register=self.register)
            def register(self, fn):
                steps.append("registered")
                self.fn = fn
            def disconnect(self):
                steps.append("disconnected")
        event = Events()
        fake_obsws = SimpleNamespace(
            Subs=SimpleNamespace(INPUTVOLUMEMETERS=128),
            EventClient=lambda **kwargs:event)
        real_obs = OfficialObsWebsocket("test-only", port=4455)
        real_obs._client = Client()
        def start():
            self.assertEqual(steps, ["registered"])
            steps.append("restart")
            event.fn(SimpleNamespace(inputs=[{
                "inputName":"AISTING-new-temp",
                "inputLevelsMul":[[0.15,0.08]]}]))
        with patch.dict(sys.modules, {"obsws_python":fake_obsws}):
            obs_meter = real_obs.read_actual_audio_meters(
                operator_approved=True,
                input_name="AISTING-new-temp",
                duration=1, start_action=start)
        self.assertEqual(steps, ["registered","restart","disconnected"])
        self.assertEqual(obs_meter.selected_meter_events,1)
        self.assertTrue(obs_meter.selected_signal)
        self.assertGreater(obs_meter.first_selected_signal_monotonic,0)
        self.assertLessEqual(
            obs_meter.first_selected_signal_monotonic,
            obs_meter.last_selected_signal_monotonic)

    def test_obs_meter_will_not_accept_any_unbound_restart_action(self):
        real_obs = OfficialObsWebsocket("test-only", port=4455)
        real_obs._client = object()
        with self.assertRaises(ValueError):
            real_obs.read_actual_audio_meters(
                operator_approved=True, input_name=None,
                duration=1, start_action=lambda:None)
        with self.assertRaises(PermissionError):
            real_obs.read_actual_audio_meters(
                operator_approved=False, input_name="AISTING-new-temp",
                duration=1, start_action=lambda:None)

    def test_permission_rejection_does_not_contact_obs_or_voice(self):
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   side_effect=AssertionError("unexpected obs")):
            with self.assertRaises(PermissionError):
                verify_gpt_sovits_to_obs(Path("ref.wav"), "한글", "반가워요",
                    obs_password="test", rights_confirmed=True)
            with self.assertRaises(PermissionError):
                verify_gpt_sovits_to_obs(Path("ref.wav"), "한글", "반가워요",
                    obs_password="test", operator_approved=True)

    def test_existing_live_stream_is_never_modified(self):
        obs=SimpleNamespace(connect=lambda:SimpleNamespace(streaming=True))
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                side_effect=AssertionError("unapproved voice call")):
            with self.assertRaisesRegex(RuntimeError,"방송 중"):
                verify_gpt_sovits_to_obs(Path("ref.wav"),"한글","안녕",
                    obs_password="test",operator_approved=True,rights_confirmed=True)

    def test_wave_is_temporary_only_and_own_obs_input_is_removed(self):
        created=[]
        deleted=[]
        class FakeClient:
            def get_record_status(self):
                return SimpleNamespace(output_active=False)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])
            def create_input(self, scene, name, kind, settings, enabled):
                data=Path(settings["local_file"]).read_bytes()
                self_len=len(data)
                self.assertEqual(kind,"ffmpeg_source")
                self.assertEqual(scene,"Scene")
                self.assertEqual(self_len,64)
                self.assertEqual(settings["looping"],False)
                self.assertEqual(settings["restart_on_activate"],False)
                created.append((name,settings["local_file"]))
            def remove_input(self,name):
                deleted.append(name)
        client=FakeClient()
        # Bind the test's assertion without introducing an actual OBS process.
        test=self
        client.assertEqual=test.assertEqual
        obs=SimpleNamespace(
            _client=client,
            connect=lambda:SimpleNamespace(version="32.2.2",scene="Scene",streaming=False),
            status=lambda:SimpleNamespace(scene="Scene",streaming=False),
            read_actual_audio_meters=lambda **kwargs:
                SimpleNamespace(selected_meter_events=12, selected_signal=True))
        voice=SimpleNamespace(sample_rate=24000,channels=1,frame_count=80,
                              wav_data=b"RIFF"+b"x"*60)
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
               "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                return_value=voice) as synth, patch("time.sleep"):
            result=verify_gpt_sovits_to_obs(Path("owned_ref.wav"),"녹음 문장",
                "안녕하세요",obs_password="test",operator_approved=True,
                rights_confirmed=True)
        self.assertTrue(result.actual_signal)
        self.assertEqual(result.audio_input_events,12)
        self.assertEqual(len(created),1)
        self.assertEqual(deleted,[created[0][0]])
        self.assertFalse(Path(created[0][1]).exists())
        self.assertEqual(synth.call_args.kwargs["play_to_speaker"],False)
        self.assertEqual(synth.call_args.kwargs["return_audio_bytes"],True)


    def test_stream_started_during_real_synthesis_does_not_create_obs_input(self):
        class Client:
            def get_record_status(self):
                return SimpleNamespace(output_active=False)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])

            def create_input(self, *args):
                self.fail("OBS source created while broadcasting")

        client=Client()
        client.fail=self.fail
        obs=SimpleNamespace(
            _client=client,
            connect=lambda:SimpleNamespace(version="32.2.2",scene="Scene",streaming=False),
            status=lambda:SimpleNamespace(scene="Scene",streaming=True))
        voice=SimpleNamespace(wav_data=b"RIFF"+b"x"*60)
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                return_value=voice) as synth:
            with self.assertRaisesRegex(RuntimeError,"방송이 시작"):
                verify_gpt_sovits_to_obs(Path("owned.wav"),"기록된 문장","시험 음성",
                    obs_password="test",operator_approved=True,rights_confirmed=True)
        synth.assert_called_once()

    def test_scene_change_during_real_synthesis_does_not_touch_obs(self):
        class Client:
            def get_record_status(self):
                return SimpleNamespace(output_active=False)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])

            def create_input(self, *args):
                raise AssertionError("Created input in a different scene")

        obs=SimpleNamespace(
            _client=Client(),
            connect=lambda:SimpleNamespace(version="32.2.2",scene="Scene A",streaming=False),
            status=lambda:SimpleNamespace(scene="Scene B",streaming=False))
        voice=SimpleNamespace(wav_data=b"RIFF"+b"x"*60)
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                return_value=voice):
            with self.assertRaisesRegex(RuntimeError,"장면이 변경"):
                verify_gpt_sovits_to_obs(Path("owned.wav"),"기록된 문장","시험 음성",
                    obs_password="test",operator_approved=True,rights_confirmed=True)

    def test_stream_started_after_input_creation_always_cleans_up(self):
        created,removed,read_meter=[],[],[]
        states=iter([
            SimpleNamespace(scene="Scene",streaming=False),
            SimpleNamespace(scene="Scene",streaming=True),
        ])
        class Client:
            def get_record_status(self):
                return SimpleNamespace(output_active=False)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])

            def create_input(self, scene,name,kind,settings,enabled):
                self.assertEqual(scene,"Scene")
                created.append(name)

            def remove_input(self,name):
                removed.append(name)

        client=Client()
        client.assertEqual=self.assertEqual
        obs=SimpleNamespace(
            _client=client,
            connect=lambda:SimpleNamespace(version="32.2.2",scene="Scene",streaming=False),
            status=lambda:next(states),
            read_actual_audio_meters=lambda **kwargs:read_meter.append(kwargs))
        voice=SimpleNamespace(wav_data=b"RIFF"+b"x"*60)
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                return_value=voice):
            with self.assertRaisesRegex(RuntimeError,"송출 또는 장면"):
                verify_gpt_sovits_to_obs(Path("owned.wav"),"기록된 문장","시험 음성",
                    obs_password="test",operator_approved=True,rights_confirmed=True)
        self.assertEqual(removed,created)
        self.assertEqual(len(created),1)
        self.assertEqual(read_meter,[])

    def test_scene_change_during_meter_observation_prevents_success(self):
        created,removed=[],[]
        states=iter([
            SimpleNamespace(scene="Scene",streaming=False),
            SimpleNamespace(scene="Scene",streaming=False),
            SimpleNamespace(scene="New scene",streaming=False),
        ])
        class Client:
            def get_record_status(self):
                return SimpleNamespace(output_active=False)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])

            def create_input(self,scene,name,kind,settings,enabled):
                created.append(name)

            def remove_input(self,name):
                removed.append(name)

        obs=SimpleNamespace(
            _client=Client(),
            connect=lambda:SimpleNamespace(version="32.2.2",scene="Scene",streaming=False),
            status=lambda:next(states),
            read_actual_audio_meters=lambda **kwargs:SimpleNamespace(
                selected_meter_events=2,selected_signal=True))
        voice=SimpleNamespace(sample_rate=24000,channels=1,frame_count=100,
                              wav_data=b"RIFF"+b"x"*60)
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                return_value=voice), patch("time.sleep"):
            with self.assertRaisesRegex(RuntimeError,"송출 또는 장면"):
                verify_gpt_sovits_to_obs(Path("owned.wav"),"기록된 문장","시험 음성",
                    obs_password="test",operator_approved=True,rights_confirmed=True)
        self.assertEqual(removed,created)
        self.assertEqual(len(created),1)

    def test_created_obs_media_uuid_remains_owned_until_restart_and_cleanup(self):
        """임시 OBS 소스의 UUID가 일치하면 재생과 정리 작업을 수행한다."""
        actions, removed, listed = [], [], []
        class Client:
            def get_record_status(self):
                return SimpleNamespace(output_active=False)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])
            def create_input(self, scene, name, kind, settings, enabled):
                listed.append(name)
                return SimpleNamespace(input_uuid="probe-uuid-1")
            def get_input_list(self):
                return SimpleNamespace(inputs=[{
                    "inputName":listed[0], "inputUuid":"probe-uuid-1",
                    "inputKind":"ffmpeg_source"}])
            def trigger_media_input_action(self, name, action):
                actions.append((name, action))
            def remove_input(self, name):
                removed.append(name)
        def meter(**kwargs):
            kwargs["start_action"]()
            return SimpleNamespace(selected_meter_events=2, selected_signal=True)
        obs = SimpleNamespace(
            _client=Client(),
            connect=lambda:SimpleNamespace(
                version="32.2",scene="Scene",streaming=False),
            status=lambda:SimpleNamespace(scene="Scene",streaming=False),
            read_actual_audio_meters=meter)
        voice = SimpleNamespace(sample_rate=24000,channels=1,frame_count=80,
                                wav_data=b"RIFF"+b"x"*60)
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                return_value=voice):
            result = verify_gpt_sovits_to_obs(
                Path("licensed.wav"),"권리 확인","안녕하세요",
                obs_password="test",operator_approved=True,rights_confirmed=True)
        self.assertTrue(result.actual_signal)
        self.assertEqual(removed,listed)
        self.assertEqual(actions,[(
            listed[0],"OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART")])

    def test_replaced_obs_media_uuid_is_never_restarted_or_deleted(self):
        """재생 전 임시 소스 이름이 재사용되면 해당 소스를 건드리지 않는다."""
        listed, restarted, removed = [], [], []
        lookups = [0]
        class Client:
            def get_record_status(self):
                return SimpleNamespace(output_active=False)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])
            def create_input(self, scene, name, kind, settings, enabled):
                listed.append(name)
                return SimpleNamespace(input_uuid="original-uuid")
            def get_input_list(self):
                lookups[0] += 1
                uid = "original-uuid" if lookups[0] == 1 else "other-uuid"
                return SimpleNamespace(inputs=[{
                    "inputName":listed[0], "inputUuid":uid,
                    "inputKind":"ffmpeg_source"}])
            def trigger_media_input_action(self, name, action):
                restarted.append(name)
            def remove_input(self, name):
                removed.append(name)
        def meter(**kwargs):
            kwargs["start_action"]()
            return SimpleNamespace(selected_meter_events=1, selected_signal=True)
        obs = SimpleNamespace(
            _client=Client(),
            connect=lambda:SimpleNamespace(
                version="32.2",scene="Scene",streaming=False),
            status=lambda:SimpleNamespace(scene="Scene",streaming=False),
            read_actual_audio_meters=meter)
        voice = SimpleNamespace(sample_rate=24000,channels=1,frame_count=80,
                                wav_data=b"RIFF"+b"x"*60)
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                return_value=voice):
            with self.assertRaisesRegex(RuntimeError,"정리에 실패"):
                verify_gpt_sovits_to_obs(
                    Path("licensed.wav"),"권리 확인","안녕하세요",
                    obs_password="test",operator_approved=True,rights_confirmed=True)
        self.assertEqual(restarted,[])
        self.assertEqual(removed,[])
        self.assertGreaterEqual(lookups[0],3)

    def test_obs_media_uuid_changed_only_after_playback_still_protects_cleanup(self):
        """재생 후 소스가 교체됐을 때 타인의 소스를 삭제하지 않는다."""
        listed, restarted, removed, lookups = [], [], [], [0]
        class Client:
            def get_record_status(self):
                return SimpleNamespace(output_active=False)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])
            def create_input(self, scene, name, kind, settings, enabled):
                listed.append(name)
                return SimpleNamespace(input_uuid="original-uuid")
            def get_input_list(self):
                lookups[0] += 1
                return SimpleNamespace(inputs=[{
                    "inputName":listed[0],
                    "inputUuid":("original-uuid" if lookups[0] <= 2 else "replacement-uuid"),
                    "inputKind":"ffmpeg_source"}])
            def trigger_media_input_action(self, name, action):
                restarted.append(name)
            def remove_input(self, name):
                removed.append(name)
        def meter(**kwargs):
            kwargs["start_action"]()
            return SimpleNamespace(selected_meter_events=2, selected_signal=True)
        obs = SimpleNamespace(
            _client=Client(),
            connect=lambda:SimpleNamespace(version="32", scene="Scene", streaming=False),
            status=lambda:SimpleNamespace(scene="Scene", streaming=False),
            read_actual_audio_meters=meter)
        voice = SimpleNamespace(sample_rate=24000, channels=1, frame_count=80,
                                wav_data=b"RIFF"+b"x"*60)
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                return_value=voice):
            with self.assertRaisesRegex(RuntimeError, "정리에 실패"):
                verify_gpt_sovits_to_obs(Path("licensed.wav"),"권리 확인","안녕하세요",
                                         obs_password="test",operator_approved=True,
                                         rights_confirmed=True)
        self.assertEqual(len(restarted), 1)
        self.assertEqual(removed, [])
        self.assertEqual(lookups[0], 3)

    def test_gpt_obs_gui_worker_uses_captured_tk_inputs(self):
        """Tk StringVar.get belongs on the GUI thread, not the synthesis worker."""
        import ast
        import inspect
        import textwrap
        from ai_broadcaster.original_plan_studio import OriginalPlanStudio
        source=textwrap.dedent(inspect.getsource(
            OriginalPlanStudio._open_gpt_sovits_panel))
        body=ast.parse(source)
        workers=[node for node in ast.walk(body)
                 if isinstance(node,ast.FunctionDef) and node.name=="worker"]
        self.assertEqual(len(workers),1)
        worker=ast.unparse(workers[0])
        self.assertNotIn("prompt_var.get()",worker)
        self.assertNotIn("obs_password_var.get()",worker)
        self.assertIn("obs_password=obs_password",worker)
        self.assertIn("reference_text",worker)

    def test_rpc_error_after_obs_creates_source_removes_only_own_source(self):
        """A lost CreateInput reply cannot leave the temporary audio looping."""
        recorded,removed=[],[]
        class Client:
            def get_record_status(self):
                return SimpleNamespace(output_active=False)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])
            def create_input(self, scene, name, kind, settings, enabled):
                self.assertEqual(kind, "ffmpeg_source")
                recorded.append((name, kind))
                raise OSError("RPC response lost after OBS accepted CreateInput")
            def get_input_list(self):
                return SimpleNamespace(inputs=[
                    {"inputName":name, "inputKind":kind}
                    for name,kind in recorded
                ] + [{"inputName":"User Original", "inputKind":"ffmpeg_source"}])
            def remove_input(self,name):
                removed.append(name)
        client=Client()
        client.assertEqual=self.assertEqual
        obs=SimpleNamespace(
            _client=client,
            connect=lambda:SimpleNamespace(version="32.0",scene="Scene",streaming=False),
            status=lambda:SimpleNamespace(scene="Scene",streaming=False))
        voice=SimpleNamespace(wav_data=b"RIFF"+b"x"*60)
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                return_value=voice):
            with self.assertRaisesRegex(OSError,"RPC response lost"):
                verify_gpt_sovits_to_obs(Path("owned.wav"),"참조 발화","안녕하세요",
                    obs_password="secret",operator_approved=True,rights_confirmed=True)
        self.assertEqual(removed,[recorded[0][0]])
        self.assertNotIn("User Original",removed)

    def test_rpc_error_without_created_source_does_not_remove_any_input(self):
        removed=[]
        class Client:
            def get_record_status(self):
                return SimpleNamespace(output_active=False)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])
            def create_input(self, *args):
                raise ConnectionError("Rejected before creating")
            def get_input_list(self):
                return SimpleNamespace(inputs=[
                    {"inputName":"User Original","inputKind":"ffmpeg_source"}])
            def remove_input(self,name):
                removed.append(name)
        obs=SimpleNamespace(
            _client=Client(),
            connect=lambda:SimpleNamespace(version="32.0",scene="Scene",streaming=False),
            status=lambda:SimpleNamespace(scene="Scene",streaming=False))
        voice=SimpleNamespace(wav_data=b"RIFF"+b"x"*60)
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                return_value=voice):
            with self.assertRaisesRegex(ConnectionError,"Rejected before creating"):
                verify_gpt_sovits_to_obs(Path("owned.wav"),"참조 발화","안녕하세요",
                    obs_password="secret",operator_approved=True,rights_confirmed=True)
        self.assertEqual(removed,[])

    def test_cleanup_verification_failure_never_claims_success(self):
        class Client:
            def get_record_status(self):
                return SimpleNamespace(output_active=False)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])
            def create_input(self, *args):
                raise OSError("Create result unknown")
            def get_input_list(self):
                raise OSError("OBS input inventory offline")
        obs=SimpleNamespace(
            _client=Client(),
            connect=lambda:SimpleNamespace(version="32.0",scene="Scene",streaming=False),
            status=lambda:SimpleNamespace(scene="Scene",streaming=False))
        voice=SimpleNamespace(wav_data=b"RIFF"+b"x"*60)
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                return_value=voice):
            with self.assertRaisesRegex(RuntimeError,"정리 상태를 확인하지 못"):
                verify_gpt_sovits_to_obs(Path("owned.wav"),"참조 발화","안녕하세요",
                    obs_password="secret",operator_approved=True,rights_confirmed=True)


    def test_active_obs_recording_rejected_before_synthesizing(self):
        class Client:
            def get_record_status(self):
                return SimpleNamespace(output_active=True)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])
        obs=SimpleNamespace(
            _client=Client(),
            connect=lambda:SimpleNamespace(version="32",scene="Scene",streaming=False))
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                side_effect=AssertionError("Synthesized during recording")):
            with self.assertRaisesRegex(RuntimeError,"녹화 중"):
                verify_gpt_sovits_to_obs(Path("owned.wav"),"참조","합성",
                    obs_password="secret",operator_approved=True,rights_confirmed=True)

    def test_recording_started_during_synthesis_never_creates_audio_source(self):
        observed=[]
        class Client:
            def get_record_status(self):
                observed.append("check")
                return SimpleNamespace(output_active=len(observed)>1)
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])
            def create_input(self,*args):
                raise AssertionError("Source created during existing recording")
        obs=SimpleNamespace(
            _client=Client(),
            connect=lambda:SimpleNamespace(version="32",scene="Scene",streaming=False),
            status=lambda:SimpleNamespace(scene="Scene",streaming=False))
        voice=SimpleNamespace(wav_data=b"RIFF"+b"x"*60)
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                return_value=voice):
            with self.assertRaisesRegex(RuntimeError,"녹화 중"):
                verify_gpt_sovits_to_obs(Path("owned.wav"),"참조","합성",
                    obs_password="secret",operator_approved=True,rights_confirmed=True)
        self.assertEqual(len(observed),2)

    def test_missing_recording_status_fails_closed(self):
        class Client:
            def get_record_status(self):
                raise OSError("OBS record endpoint unavailable")
        obs=SimpleNamespace(
            _client=Client(),
            connect=lambda:SimpleNamespace(version="32",scene="Scene",streaming=False))
        with patch("ai_broadcaster.original_plan_voice_obs_bridge.OfficialObsWebsocket",
                   return_value=obs), patch(
                "ai_broadcaster.original_plan_voice_obs_bridge.synthesize_local_gpt_sovits",
                side_effect=AssertionError("Unexpected audio")):
            with self.assertRaisesRegex(RuntimeError,"녹화 상태를 확인하지 못"):
                verify_gpt_sovits_to_obs(Path("owned.wav"),"참조","합성",
                    obs_password="secret",operator_approved=True,rights_confirmed=True)

if __name__=="__main__":
    unittest.main()
