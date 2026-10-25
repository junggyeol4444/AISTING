"""184절: 실제 WAV→공식 Cubism→OBS 단일 음성 경로 개발 계약검사.

테스트용 PCM은 실제 권리 음성이 아니며 인과관계/실모델/실장비 성공
증명으로 사용하지 않는다. 본 파일은 전체 개발 완료 뒤 실행한다.
"""
import io
import math
import struct
import unittest
import wave
from unittest.mock import patch

from ai_broadcaster.same_wav_cubism_driver import (
    authorized_pcm_envelope, start_pcm_driver_script, finish_pcm_driver_script)
from ai_broadcaster.original_plan_voice_obs_bridge import (
    RealVoiceObsResult, verify_gpt_sovits_to_obs)
from ai_broadcaster import original_plan_frontend as frontend


def _wave_bytes(duration=1.0, silent=False):
    result = io.BytesIO()
    with wave.open(result, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        samples = []
        for index in range(round(duration * 16000)):
            amplitude = 0 if silent else 10000 * (1 + (index // 800) % 4) / 4
            value = round(amplitude * math.sin(index * math.pi / 12))
            samples.append(struct.pack("<h", value))
        audio.writeframes(b"".join(samples))
    return result.getvalue()


class TestSameWavOfficialCubismContract184(unittest.TestCase):
    def test_실제_pcm_윤곽만_50ms로_내보냄(self):
        levels = authorized_pcm_envelope(_wave_bytes())
        self.assertEqual(len(levels), 20)
        self.assertTrue(any(v > 0.01 for v in levels))
        self.assertTrue(all(0 <= v <= 1 for v in levels))

    def test_무음과_관찰창초과_음성은_합격시키지_않음(self):
        with self.assertRaises(ValueError):
            authorized_pcm_envelope(_wave_bytes(silent=True))
        with self.assertRaises(ValueError):
            authorized_pcm_envelope(_wave_bytes(duration=9))

    def test_공식_Cubism_JS는_실제_원본_핸들러를_복원(self):
        levels = authorized_pcm_envelope(_wave_bytes())
        token = "a" * 32
        script = start_pcm_driver_script(levels, token)
        self.assertIn("window.getLive2DManager", script)
        self.assertIn("wav.getRms=state.wrapper", script)
        self.assertIn("wav.getRms=original", script)
        self.assertIn("공식음성중첩", script)
        self.assertIn(token, script)
        self.assertNotIn("tts.wav", script)
        finish = finish_pcm_driver_script(token)
        self.assertIn("state.cleanup()", finish)
        self.assertIn("performance", script)
        self.assertIn("location.origin", finish)

    def test_권리와_승인_없이_실제_IPC_차단(self):
        with self.assertRaises(PermissionError):
            frontend.start_authorized_pcm_live2d_mouth((0.1,) * 20)
        with self.assertRaises(PermissionError):
            frontend.finish_authorized_pcm_live2d_mouth("a" * 32)
        with self.assertRaises(PermissionError):
            verify_gpt_sovits_to_obs(
                "참조.wav", "참조", "안녕하세요", obs_password="",
                couple_live2d=True)

    def test_잘못된_요청_ID와_RMS_검증(self):
        with self.assertRaises(ValueError):
            start_pcm_driver_script((0.1,) * 20, "잘못된토큰")
        with self.assertRaises(ValueError):
            start_pcm_driver_script((float("nan"),) * 20, "a" * 32)
        with self.assertRaises(ValueError):
            finish_pcm_driver_script("바르지않음")

    def test_기존_Live2D_브리지_연결_명령_계약(self):
        def fake_ipc(payload, expected):
            self.assertEqual(payload["type"], "authorized-pcm-start")
            self.assertEqual(expected, "authorized-pcm-start-result")
            return {"type": expected, "ok": True,
                    "token": payload["token"], "lipSyncIds": 2}
        with patch.object(frontend, "_authorized_pcm_ipc", side_effect=fake_ipc):
            token = frontend.start_authorized_pcm_live2d_mouth(
                (0.1,) * 20, operator_approved=True, rights_confirmed=True)
        self.assertEqual(len(token), 32)

    def test_실제_관찰_없으면_기존_결과_미확인(self):
        result = RealVoiceObsResult(
            sample_rate=16000, channels=1, frames=16000,
            obs_version="테스트", audio_input_events=0,
            actual_signal=False)
        self.assertFalse(result.cubism_wav_mouth_candidate)
        self.assertFalse(result.same_wav_cubism_obs_candidate)
        self.assertFalse(result.cubism_obs_time_overlap_candidate)


if __name__ == "__main__":
    unittest.main()
