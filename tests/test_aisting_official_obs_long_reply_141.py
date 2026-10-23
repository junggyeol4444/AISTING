# -*- coding: utf-8 -*-
"""141회차: 긴 실제 공식 응답 동안 OBS 관찰창 조기 소진 방지 계약검사.

가상 OBS/가상 공식 응답만 사용한다. 실제 한국어 WAV·Cubism·OBS·시청자
출력의 성공 또는 Windows 실사용 검증으로 해석하지 않는다.
"""
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster import original_plan_full_pipeline as pipeline


class 가상읽기전용OBS:
    관찰횟수 = 0
    일곱창관찰 = threading.Event()

    def __init__(self, password, *, port=4455):
        self._client = self

    def connect(self):
        return SimpleNamespace(streaming=False, scene="기존장면")

    def status(self):
        return SimpleNamespace(streaming=False, scene="기존장면")

    def get_record_status(self):
        return SimpleNamespace(output_active=False)

    def read_program_audio_route(self, *, input_name, scene):
        return SimpleNamespace(confirmed=True)

    def inspect_program_media(self, *, operator_approved, input_name,
                              duration, observe_program_motion):
        self.__class__.관찰횟수 += 1
        if self.__class__.관찰횟수 >= 7:
            self.__class__.일곱창관찰.set()
        time.sleep(0.015)
        return SimpleNamespace(
            coherent_media_candidate=False,
            program_video_change_candidate=False,
            audio=SimpleNamespace(
                first_selected_signal_monotonic=None,
                last_selected_signal_monotonic=None),
        )


class 긴공식응답OBS관찰검사(unittest.TestCase):
    def setUp(self):
        가상읽기전용OBS.관찰횟수 = 0
        가상읽기전용OBS.일곱창관찰 = threading.Event()

    @staticmethod
    def 가상입결과():
        return SimpleNamespace(
            verified_signal=False,
            first_audio_mouth_monotonic=0.0,
            last_audio_mouth_monotonic=0.0,
        )

    def test_일곱번째창까지_응답전_OBS관찰을_유지한다(self):
        보낸질문 = []
        def 가상공식질문(text, *, operator_approved, duration):
            보낸질문.append(text)
            if not 가상읽기전용OBS.일곱창관찰.wait(timeout=2):
                raise RuntimeError("공식 응답보다 OBS 관찰창이 먼저 종료됨")
            return self.가상입결과()

        with patch.object(pipeline, "OfficialObsWebsocket", 가상읽기전용OBS), \\
             patch.object(pipeline, "send_to_native_live2d_session_with_observation",
                          가상공식질문):
            result = pipeline.verify_official_chat_live2d_obs(
                "한국어 질문", obs_password="가상암호",
                obs_input_name="기존오디오", duration=1,
                operator_approved=True, voice_rights_confirmed=True)
        self.assertEqual(보낸질문, ["한국어 질문"])
        self.assertGreaterEqual(가상읽기전용OBS.관찰횟수, 7)
        self.assertFalse(result.verified_observation)
        self.assertFalse(result.viewer_end_to_end_verified)

    def test_긴응답중_운영자취소를_성공으로_보고하지않는다(self):
        중지 = threading.Event()
        보낸질문 = []
        def 가상공식질문(text, *, operator_approved, duration):
            보낸질문.append(text)
            if not 가상읽기전용OBS.일곱창관찰.wait(timeout=2):
                raise RuntimeError("OBS 관찰 조기 종료")
            중지.set()
            return self.가상입결과()

        with patch.object(pipeline, "OfficialObsWebsocket", 가상읽기전용OBS), \\
             patch.object(pipeline, "send_to_native_live2d_session_with_observation",
                          가상공식질문):
            with self.assertRaises(InterruptedError):
                pipeline.verify_official_chat_live2d_obs(
                    "한국어 질문", obs_password="가상암호",
                    obs_input_name="기존오디오", duration=1,
                    operator_approved=True, voice_rights_confirmed=True,
                    cancel_event=중지)
        self.assertEqual(보낸질문, ["한국어 질문"])
        self.assertGreaterEqual(가상읽기전용OBS.관찰횟수, 7)


if __name__ == "__main__":
    unittest.main()
