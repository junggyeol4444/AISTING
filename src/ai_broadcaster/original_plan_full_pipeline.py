"""Existing official AI/Live2D session + OBS program media proof in one native flow.

This *observes* the real existing upstream components. It never launches OBS,
trains/clones voices, posts chat, records, starts a stream or creates an OBS
source. A stable OBS media candidate does not prove encoder/audience delivery.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .original_plan_frontend import send_to_native_live2d_session_with_observation
from .original_plan_obs import OfficialObsWebsocket

if TYPE_CHECKING:
    from .original_plan_frontend import OfficialLipSyncEvidence
    from .original_plan_obs import ActualObsProgramMediaObservation


@dataclass(frozen=True)
class OfficialChatObsEvidence:
    lip: "OfficialLipSyncEvidence"
    obs: "ActualObsProgramMediaObservation"

    @property
    def verified_observation(self) -> bool:
        """Two real concurrent observations; NOT proof of encoded stream."""
        return bool(self.lip.verified_signal and self.obs.coherent_media_candidate)


def verify_official_chat_live2d_obs(
    text: str,
    *,
    obs_password: str,
    obs_input_name: str,
    obs_port: int = 4455,
    duration: float = 8.0,
    operator_approved: bool = False,
    voice_rights_confirmed: bool = False,
) -> OfficialChatObsEvidence:
    """One operator-approved real AI turn with concurrent OBS read-only monitor.

    The official Live2D child performs the existing GPT-SoVITS-configured
    conversation; AISTING never submits a second LLM/TTS prompt. An OBS frame,
    the exact named audio input route and actual Cubism RMS/mouth evidence are
    examined together. No automatic retries after possibly sending a prompt.
    """
    if operator_approved is not True or voice_rights_confirmed is not True:
        raise PermissionError("실제 질문·음성 사용 권리·OBS 동시 관찰 승인이 필요합니다.")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000:
        raise ValueError("공식 AI 질문은 1~4000글자여야 합니다.")
    if not isinstance(obs_password, str) or not obs_password:
        raise ValueError("OBS WebSocket 비밀번호가 필요합니다.")
    if (not isinstance(obs_input_name, str)
            or not 1 <= len(obs_input_name) <= 128
            or obs_input_name != obs_input_name.strip()
            or any(ord(ch) < 32 for ch in obs_input_name)):
        raise ValueError("OBS에 연결된 실제 음성 입력 이름을 지정하세요.")
    if type(obs_port) is not int or not 1 <= obs_port <= 65535:
        raise ValueError("OBS 포트 형식이 잘못되었습니다.")
    if type(duration) not in (int, float) or not 1 <= duration <= 8:
        raise ValueError("관찰 시간은 1~8초여야 합니다.")

    obs = OfficialObsWebsocket(obs_password, port=obs_port)
    before = obs.connect()
    # Do not conduct an unproven source/voice experiment on a live stream.
    if before.streaming:
        raise RuntimeError("OBS가 송출 중일 때 전체 경로 검증을 시작하지 않습니다.")

    def ensure_offline() -> None:
        # The existing OBS scene can capture official voice even if AISTING
        # never starts a recording. Refuse when the user's OBS is recording.
        now = obs.status()
        if now.streaming or now.scene != before.scene:
            raise RuntimeError("OBS 방송 또는 프로그램 장면이 변경되어 음성 요청을 중단합니다.")
        try:
            active = obs._client.get_record_status().output_active
        except Exception as exc:
            raise RuntimeError("OBS 녹화 상태를 확인하지 못했습니다.") from exc
        if type(active) is not bool:
            raise RuntimeError("OBS 녹화 상태 응답이 유효하지 않습니다.")
        if active:
            raise RuntimeError("OBS 녹화 중에는 공식 AI·음성 동시 검사를 실행하지 않습니다.")

    ensure_offline()
    route = obs.read_program_audio_route(
        input_name=obs_input_name, scene=before.scene
    )
    if not route.confirmed:
        raise RuntimeError("OBS 현재 프로그램 장면의 실제 음성 입력 경로가 확인되지 않았습니다.")
    ensure_offline()

    # The monitor runs at the same time as the official real conversation.
    # It only reads the current scene image and exact input's volume meters.
    observation: list = []
    errors: list[Exception] = []
    started = threading.Event()
    # The official server may take seconds to synthesize Korean audio. Keep
    # sampling real OBS meters while the single official prompt is pending.
    # No additional prompt is issued for subsequent meter observations.
    send_finished = threading.Event()
    monitor_ended_before_reply = []

    def obs_worker() -> None:
        # OBS WebSocket request/reply clients are not assumed thread-safe.
        # The monitor owns a different read-only localhost connection from
        # the main-thread stream/recording safety preflight.
        try:
            observer = OfficialObsWebsocket(obs_password, port=obs_port)
            state = observer.connect()
            if state.streaming or state.scene != before.scene:
                raise RuntimeError("OBS 관찰 연결 중 프로그램 장면·송출이 변경됐습니다.")
            # No approved AI prompt is sent until the separate OBS monitor
            # has actually connected to the correct stopped scene.
            started.set()
            # A single 8-second OBS probe can finish before the official
            # GPT-SoVITS speech starts. Observe bounded consecutive windows
            # (up to 6 x 3 seconds) through the actual question response.
            for _ in range(6):
                if send_finished.is_set() and observation:
                    break
                observation.append(observer.inspect_program_media(
                    operator_approved=True, input_name=obs_input_name,
                    duration=min(float(duration), 3.0),
                ))
                if send_finished.is_set():
                    break
            if not send_finished.is_set():
                monitor_ended_before_reply.append(True)
        except Exception as exc:
            errors.append(exc)
            started.set()

    monitor = threading.Thread(target=obs_worker, daemon=True,
                               name="aisting-official-obs-program-observer")
    monitor.start()
    if not started.wait(timeout=3):
        raise RuntimeError("OBS 영상·음성 관찰을 시작하지 못했습니다.")
    if errors:
        raise RuntimeError("OBS 관찰 연결 준비 실패 · AI 질문을 보내지 않았습니다.") from errors[0]
    # No text is handed to the official upstream session if OBS began
    # broadcasting/recording during the read-only monitor setup.
    ensure_offline()
    lip = None
    send_failure = None
    try:
        lip = send_to_native_live2d_session_with_observation(
            text, operator_approved=True, duration=duration
        )
    except Exception as exc:
        # Sending may have succeeded before a lost IPC response. NO retry.
        send_failure = exc
    finally:
        send_finished.set()
    monitor.join(timeout=duration + 20)
    if monitor.is_alive():
        raise RuntimeError("OBS 읽기 검사 제한 시간을 초과했습니다. 질문을 자동 재전송하지 않습니다.")
    if send_failure is not None:
        raise RuntimeError(
            "공식 Live2D 질문·립싱크 확인 실패. 중복 전송 방지를 위해 자동 재시도하지 않습니다."
        ) from send_failure
    if errors:
        raise RuntimeError("OBS 화면·음성 동시 관찰 실패") from errors[0]
    if not observation or lip is None:
        raise RuntimeError("공식 Live2D 또는 OBS 관찰 결과가 없습니다.")
    if monitor_ended_before_reply:
        raise RuntimeError(
            "OBS 관찰 시간이 실제 AI 응답보다 먼저 끝났습니다. "
            "음성·OBS의 동시 검증을 완료하지 못했습니다."
        )
    ensure_offline()
    # Prefer an actually observed, coherent media route; never treat an
    # earlier silent frame as proof that speech did not reach the OBS input.
    selected = next(
        (sample for sample in observation if sample.coherent_media_candidate),
        observation[-1],
    )
    return OfficialChatObsEvidence(lip=lip, obs=selected)
