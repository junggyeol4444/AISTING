# -*- coding: utf-8 -*-
"""142회차: 공식 질문 전 OBS 첫 관찰 준비 및 취소 계약검사.

가상 OBS/가상 응답만 사용한다. 실제 WAV·Cubism·OBS 출력 또는
시청자 종단간 전달을 검증한 것으로 해석하지 않는다.
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


class 관찰준비OBS:
    def __init__(self, password, *, port=4455):
        self._client = self
        self._worker_status_count = 0

    def connect(self):
        return SimpleNamespace(streaming=False, scene="기존장면")

    def status(self):
        if threading.current_thread().name == "aisting-official-obs-program-observer":
            self._worker_status_count += 1
        return SimpleNamespace(streaming=False, scene="기존장면")

    def get_record_status(self):
        return SimpleNamespace(output_active=False)

    def read_program_audio_route(self, *, input_name, scene):
        return SimpleNamespace(confirmed=True)

    def inspect_program_media(self, *, operator_approved, input_name,
                              duration, observe_program_motion):
        time.sleep(0.01)
        return SimpleNamespace(
            coherent_media_candidate=False,
            program_video_change_candidate=False,
            audio=SimpleNamespace(
                first_selected_signal_monotonic=None,
                last_selected_signal_monotonic=None),
        )


class 두번째안전확인차단OBS(관찰준비OBS):
    def status(self):
        state = super().status()
        if (threading.current_thread().name == "aisting-official-obs-program-observer"
                and self._worker_status_count >= 2):
            raise RuntimeError("관찰 시작 직전 안전 확인 실패")
        return state


class 공식OBS질문준비검사(unittest.TestCase):
    def test_준비대기_한차례_시간초과뒤에도_질문신호를_받는다(self):
        class 한차례미수신:
            def __init__(self):
                self.calls = 0
            def wait(self, timeout):
                self.calls += 1
                return self.calls >= 2
        fake = 한차례미수신()
        self.assertTrue(pipeline._await_official_prompt_start(
            fake, threading.Event(), None))
        self.assertEqual(fake.calls, 2)

    def test_준비대기중_운영자취소를_반영한다(self):
        stop = threading.Event()
        stop.set()
        self.assertFalse(pipeline._await_official_prompt_start(
            threading.Event(), threading.Event(), stop))

    def test_첫OBS관찰_안전확인_실패면_질문을_보내지_않는다(self):
        sent = []
        def fake_send(text, *, operator_approved, duration):
            sent.append(text)
            raise AssertionError("안전 확인 실패 후 질문 전송 금지")
        with patch.object(pipeline, "OfficialObsWebsocket", 두번째안전확인차단OBS), \
             patch.object(pipeline, "send_to_native_live2d_session_with_observation",
                          fake_send):
            with self.assertRaisesRegex(RuntimeError, "질문 미전송"):
                pipeline.verify_official_chat_live2d_obs(
                    "한국어 질문", obs_password="가상암호",
                    obs_input_name="기존오디오", duration=1,
                    operator_approved=True, voice_rights_confirmed=True)
        self.assertEqual(sent, [])

    def test_관찰_준비후_승인질문_한번만_전송한다(self):
        sent = []
        def fake_send(text, *, operator_approved, duration):
            sent.append(text)
            return SimpleNamespace(
                verified_signal=False,
                first_audio_mouth_monotonic=0.0,
                last_audio_mouth_monotonic=0.0)
        with patch.object(pipeline, "OfficialObsWebsocket", 관찰준비OBS), \
             patch.object(pipeline, "send_to_native_live2d_session_with_observation",
                          fake_send):
            evidence = pipeline.verify_official_chat_live2d_obs(
                "한국어 질문", obs_password="가상암호",
                obs_input_name="기존오디오", duration=1,
                operator_approved=True, voice_rights_confirmed=True)
        self.assertEqual(sent, ["한국어 질문"])
        self.assertFalse(evidence.verified_observation)


if __name__ == "__main__":
    unittest.main()
