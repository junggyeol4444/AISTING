"""Operator-approved real GPT-SoVITS -> official OBS media meter path contract.

Unit tests intentionally substitute dependencies. They cannot certify the
presence of a downloaded GPT-SoVITS model or a real OBS process.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.original_plan_voice_obs_bridge import verify_gpt_sovits_to_obs

class VerifyRealVoiceObsTests(unittest.TestCase):
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
            def get_input_kind_list(self, ignored):
                return SimpleNamespace(input_kinds=["ffmpeg_source"])
            def create_input(self, scene, name, kind, settings, enabled):
                data=Path(settings["local_file"]).read_bytes()
                self_len=len(data)
                self.assertEqual(kind,"ffmpeg_source")
                self.assertEqual(scene,"Scene")
                self.assertEqual(self_len,64)
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
            status=lambda:SimpleNamespace(streaming=False),
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

if __name__=="__main__":
    unittest.main()
