"""Existing official AI/Live2D session + OBS program media proof in one native flow.

This *observes* the real existing upstream components. It never launches OBS,
trains/clones voices, posts chat, records, starts a stream or creates an OBS
source. A stable OBS media candidate does not prove encoder/audience delivery.
"""
from __future__ import annotations

import math
import threading
import time
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
    # Positive signals observed at unrelated times cannot prove one turn.
    temporal_overlap_candidate: bool = False
    # 운영자가 승인한 실제 공식 세션에서 측정한 시간만 표시한다.
    # AI 요청 왕복에는 실제 로컬 모델·음성·Cubism 검사 시간이 함께 포함된다.
    local_roundtrip_seconds: float | None = None
    first_cubism_audio_seconds: float | None = None
    first_obs_audio_seconds: float | None = None
    # 녹화·송출을 시작하지 않았으므로 시청자 측 출력 지연은 별도 실증이다.
    viewer_end_to_end_verified: bool = False

    @property
    def latency_summary_ko(self) -> str:
        """실측값만 표시하며 시청자 지연을 추정해 넣지 않는다."""
        def measured(value: float | None) -> str:
            if (type(value) in (int, float) and math.isfinite(value)
                    and value >= 0):
                return f"{value:.3f}초"
            return "미측정"
        return (
            "공식 AI·음성·Cubism 요청 왕복 " + measured(self.local_roundtrip_seconds)
            + " / 첫 Cubism 입·음성 표본 " + measured(self.first_cubism_audio_seconds)
            + " / OBS 첫 오디오 표본 " + measured(self.first_obs_audio_seconds)
            + " / 시청자 E2E 별도 미검증"
        )

    @property
    def verified_observation(self) -> bool:
        """Two real concurrent observations; NOT proof of encoded stream."""
        return bool(self.lip.verified_signal and self.obs.coherent_media_candidate
                    and self.temporal_overlap_candidate)


def verify_official_chat_live2d_obs(
    text: str,
    *,
    obs_password: str,
    obs_input_name: str,
    obs_port: int = 4455,
    duration: float = 8.0,
    operator_approved: bool = False,
    voice_rights_confirmed: bool = False,
    cancel_event: threading.Event | None = None,
) -> OfficialChatObsEvidence:
    """One operator-approved real AI turn with concurrent OBS read-only monitor.

    The official Live2D child performs the existing GPT-SoVITS-configured
    conversation; AISTING never submits a second LLM/TTS prompt. An OBS frame,
    the exact named audio input route and actual Cubism RMS/mouth evidence are
    examined together. No automatic retries after possibly sending a prompt.
    """
    if operator_approved is not True or voice_rights_confirmed is not True:
        raise PermissionError("실제 질문·음성 사용 권리·OBS 동시 관찰 승인이 필요합니다.")
    if cancel_event is not None and not isinstance(cancel_event, threading.Event):
        raise TypeError("검사 중지 이벤트 형식 오류")

    def check_cancelled() -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("검사 중지 요청됨 · 이미 보낸 질문을 자동 재전송하지 않습니다.")

    check_cancelled()
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

    check_cancelled()
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
    observation: list[tuple[float, float, object]] = []
    errors: list[Exception] = []
    started = threading.Event()
    # The official server may take seconds to synthesize Korean audio. Keep
    # sampling real OBS meters while the single official prompt is pending.
    # No additional prompt is issued for subsequent meter observations.
    send_finished = threading.Event()
    prompt_started = threading.Event()
    cancel_observation = threading.Event()
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

            def monitor_still_offline() -> None:
                # 본 연결과 별도인 관찰 연결에서도 녹화·송출·장면 변경을
                # 매 표본의 앞뒤에서 감지한다. 마지막에 원상 복구돼도
                # 중간 방송/녹화 노출을 '정상 증거'로 기록하지 않는다.
                status = observer.status()
                if status.streaming or status.scene != before.scene:
                    raise RuntimeError("OBS 동시 관찰 중 송출 또는 장면 변경 감지")
                try:
                    recording = observer._client.get_record_status().output_active
                except Exception as exc:
                    raise RuntimeError("OBS 동시 관찰 중 녹화 상태 확인 실패") from exc
                if type(recording) is not bool or recording:
                    raise RuntimeError("OBS 동시 관찰 중 녹화 시작 또는 상태 불명")

            monitor_still_offline()
            # No approved AI prompt is sent until the separate OBS monitor
            # has actually connected to the correct stopped scene.
            started.set()
            # Do not let fast callbacks (or a slow OBS safety preflight) use
            # up the audio observation budget BEFORE the actual user turn.
            if not prompt_started.wait(timeout=8) or cancel_observation.is_set():
                return
            # A single 8-second OBS probe can finish before the official
            # GPT-SoVITS speech starts. Observe bounded consecutive windows
            # (up to 6 x 3 seconds) through the actual question response.
            for _ in range(6):
                if cancel_observation.is_set() or (cancel_event is not None and cancel_event.is_set()):
                    break
                if send_finished.is_set() and observation:
                    break
                monitor_still_offline()
                capture_started = time.monotonic()
                sample = observer.inspect_program_media(
                    operator_approved=True, input_name=obs_input_name,
                    duration=min(float(duration), 3.0),
                )
                capture_ended = time.monotonic()
                # 검사 도중 사용자가 녹화 또는 방송을 잠시 시작한
                # 경우에도 정상 관측으로 채택하지 않는다.
                monitor_still_offline()
                observation.append((capture_started, capture_ended, sample))
                if send_finished.is_set():
                    break
            if not send_finished.is_set() and not cancel_observation.is_set() and not (
                    cancel_event is not None and cancel_event.is_set()):
                monitor_ended_before_reply.append(True)
        except Exception as exc:
            errors.append(exc)
            started.set()

    monitor = threading.Thread(target=obs_worker, daemon=True,
                               name="aisting-official-obs-program-observer")
    monitor.start()
    if not started.wait(timeout=3):
        # No prompt is sent. A late connected read-only worker must not sit
        # waiting for a request that this session has already rejected.
        cancel_observation.set()
        prompt_started.set()
        monitor.join(timeout=1)
        raise RuntimeError("OBS 영상·음성 관찰을 시작하지 못했습니다.")
    if errors:
        cancel_observation.set()
        prompt_started.set()
        monitor.join(timeout=1)
        raise RuntimeError("OBS 관찰 연결 준비 실패 · AI 질문을 보내지 않았습니다.") from errors[0]
    # No text is handed to the official upstream session if OBS began
    # broadcasting/recording during the read-only monitor setup.
    try:
        ensure_offline()
        check_cancelled()
    except Exception:
        cancel_observation.set()
        prompt_started.set()
        monitor.join(timeout=2)
        raise
    lip = None
    send_failure = None
    prompt_started_at = time.monotonic()
    prompt_finished_at = prompt_started_at
    try:
        prompt_started.set()
        check_cancelled()
        lip = send_to_native_live2d_session_with_observation(
            text, operator_approved=True, duration=duration
        )
    except Exception as exc:
        # Sending may have succeeded before a lost IPC response. NO retry.
        send_failure = exc
    finally:
        prompt_finished_at = time.monotonic()
        send_finished.set()
    monitor.join(timeout=duration + 20)
    if monitor.is_alive():
        raise RuntimeError("OBS 읽기 검사 제한 시간을 초과했습니다. 질문을 자동 재전송하지 않습니다.")
    # A delivered upstream request cannot be undone; never report its late
    # output as successful after an operator cancelled the observation.
    check_cancelled()
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
    # A Stop click may arrive during the final OBS read-only status query.
    # Check it once more before any success-shaped evidence is returned.
    check_cancelled()
    # Prefer an actually observed, coherent media route; never treat an
    # earlier silent frame as proof that speech did not reach the OBS input.
    # Compare an OBS positive meter window with the *real measured*
    # overlap of RMS and Cubism mouth changes, not the entire AI request.
    # Lack of the official real sample times must fail closed.
    mouth_first = getattr(lip, 'first_audio_mouth_monotonic', 0.0)
    mouth_last = getattr(lip, 'last_audio_mouth_monotonic', 0.0)
    valid_mouth_window = (type(mouth_first) in (int, float)
                          and type(mouth_last) in (int, float)
                          and math.isfinite(mouth_first)
                          and math.isfinite(mouth_last)
                          and 0 < mouth_first <= mouth_last
                          # 과거 발화의 입 움직임 시간이 이번 요청 시점을
                          # 가로질러도 동일 발화로 잘못 인정하지 않는다.
                          and prompt_started_at <= mouth_first
                          and mouth_last <= prompt_finished_at)
    # Match the actual NON-SILENT OBS meter timestamps, not a broad
    # 3-second video+audio inspection window that could include unrelated
    # noise before/after the Cubism mouth change.
    def same_utterance_window(began, ended, sample):
        if not valid_mouth_window or not sample.coherent_media_candidate:
            return False
        audio = getattr(sample, "audio", None)
        first = getattr(audio, "first_selected_signal_monotonic", 0.0)
        last = getattr(audio, "last_selected_signal_monotonic", 0.0)
        if (type(first) not in (int, float) or type(last) not in (int, float)
                or not math.isfinite(first) or not math.isfinite(last)
                or not (began <= first <= last <= ended)):
            return False
        # The same monotonic clock is used by both native Windows OBS events
        # and official WebView2/Cubism evidence; NO broad window shortcut.
        return first <= mouth_last and last >= mouth_first

    matching = [sample for began, ended, sample in observation
                if same_utterance_window(began, ended, sample)]
    selected = matching[0] if matching else next(
        (sample for _, _, sample in observation if sample.coherent_media_candidate),
        observation[-1][2],
    )
    # 원래 같은 발화 검증에 사용했던 실제 monotonic 표본을 시간 지표로
    # 재사용한다. 시간 자료가 없거나 일치하지 않는 구간은 추정하지 않는다.
    first_cubism_latency = (
        round(mouth_first - prompt_started_at, 6)
        if valid_mouth_window and prompt_started_at <= mouth_first <= prompt_finished_at
        else None
    )
    matched_first_audio = getattr(
        getattr(matching[0], "audio", None), "first_selected_signal_monotonic", None
    ) if matching else None
    first_obs_latency = (
        round(matched_first_audio - prompt_started_at, 6)
        if (type(matched_first_audio) in (float, int)
            and math.isfinite(matched_first_audio)
            and prompt_started_at <= matched_first_audio <= time.monotonic())
        else None
    )
    return OfficialChatObsEvidence(
        lip=lip, obs=selected, temporal_overlap_candidate=bool(matching),
        local_roundtrip_seconds=round(prompt_finished_at - prompt_started_at, 6),
        first_cubism_audio_seconds=first_cubism_latency,
        first_obs_audio_seconds=first_obs_latency)
