# -*- coding: utf-8 -*-
"""144회차: 실제 OBS 구독 뒤 최종 안전 확인 동안 첫 미터 관찰시간 보존.

가상 OBS·가상 공식 응답 계약검사이며 실제 WAV·Cubism·OBS 실증은 아니다.
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


class 미터예산가상OBS:
    구독완료 = threading.Event()
    관찰시작 = threading.Event()
    최종안전확인동안대기 = threading.Event()
    최종확인실패 = False
    최종확인취소 = None

    def __init__(self, password, *, port=4455):
        self._client = self

    def connect(self):
        return SimpleNamespace(streaming=False, scene="기존장면")

    def status(self):
        if (threading.current_thread().name != "aisting-official-obs-program-observer"
                and type(self).구독완료.is_set()):
            if not type(self).관찰시작.is_set():
                type(self).최종안전확인동안대기.set()
            # 첫 미터 구독 이후 메인 스레드의 실제 최종 안전 확인을 모의한다.
            time.sleep(0.03)
            if type(self).최종확인취소 is not None:
                type(self).최종확인취소.set()
            if type(self).최종확인실패:
                raise RuntimeError("가상 OBS 최종 안전 확인 실패")
        return SimpleNamespace(streaming=False, scene="기존장면")

    def get_record_status(self):
        return SimpleNamespace(output_active=False)

    def read_program_audio_route(self, *, input_name, scene):
        return SimpleNamespace(confirmed=True)

    def inspect_program_media_with_meter_ready(
        self, *, ready_action, operator_approved, input_name,
        duration, observe_program_motion,
    ):
        type(self).구독완료.set()
        ready_action()  # 실제 OBS의 이벤트 등록 후 콜백과 동일한 순서
        type(self).관찰시작.set()
        time.sleep(0.01)
        return SimpleNamespace(
            coherent_media_candidate=False,
            program_video_change_candidate=False,
            audio=SimpleNamespace(
                first_selected_signal_monotonic=None,
                last_selected_signal_monotonic=None),
        )


class 공식미터예산검사(unittest.TestCase):
    def setUp(self):
        for event in (미터예산가상OBS.구독완료, 미터예산가상OBS.관찰시작,
                      미터예산가상OBS.최종안전확인동안대기):
            event.clear()
        미터예산가상OBS.최종확인실패 = False
        미터예산가상OBS.최종확인취소 = None

    def test_최종안전확인중에는_미터관찰시간을_소진하지_않는다(self):
        sent = []
        def send(text, *, operator_approved, duration):
            self.assertTrue(미터예산가상OBS.구독완료.is_set())
            self.assertTrue(미터예산가상OBS.최종안전확인동안대기.is_set())
            self.assertTrue(미터예산가상OBS.관찰시작.wait(0.5))
            sent.append(text)
            return SimpleNamespace(verified_signal=False,
                                   first_audio_mouth_monotonic=0.0,
                                   last_audio_mouth_monotonic=0.0)
        with patch.object(pipeline, "OfficialObsWebsocket", 미터예산가상OBS), \
             patch.object(pipeline, "send_to_native_live2d_session_with_observation", send):
            result = pipeline.verify_official_chat_live2d_obs(
                "승인된 한국어 가상 질문", obs_password="가상암호",
                obs_input_name="기존입력", duration=1,
                operator_approved=True, voice_rights_confirmed=True)
        self.assertEqual(sent, ["승인된 한국어 가상 질문"])
        self.assertFalse(result.verified_observation)

    def test_최종안전확인실패면_미터대기를_해제하고_질문은_미전송(self):
        미터예산가상OBS.최종확인실패 = True
        sent = []
        with patch.object(pipeline, "OfficialObsWebsocket", 미터예산가상OBS), \
             patch.object(pipeline, "send_to_native_live2d_session_with_observation",
                          lambda *a, **k: sent.append(a)):
            with self.assertRaisesRegex(RuntimeError, "가상 OBS 최종 안전 확인 실패"):
                pipeline.verify_official_chat_live2d_obs(
                    "승인된 가상 질문", obs_password="가상암호",
                    obs_input_name="기존입력", duration=1,
                    operator_approved=True, voice_rights_confirmed=True)
        self.assertEqual(sent, [])

    def test_최종안전확인중_운영자취소면_질문은_미전송(self):
        stop = threading.Event()
        미터예산가상OBS.최종확인취소 = stop
        sent = []
        with patch.object(pipeline, "OfficialObsWebsocket", 미터예산가상OBS), \
             patch.object(pipeline, "send_to_native_live2d_session_with_observation",
                          lambda *a, **k: sent.append(a)):
            with self.assertRaisesRegex(InterruptedError, "중지 요청"):
                pipeline.verify_official_chat_live2d_obs(
                    "승인된 가상 질문", obs_password="가상암호",
                    obs_input_name="기존입력", duration=1,
                    operator_approved=True, voice_rights_confirmed=True,
                    cancel_event=stop)
        self.assertEqual(sent, [])


if __name__ == "__main__":
    unittest.main()
