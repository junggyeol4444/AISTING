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
            + " / 공식 동일 WS WAV 헤더 이벤트 "
            + str(getattr(self.lip, "official_wav_header_events", 0))
            + "건(헤더 후보) / RIFF 길이 일치 "
            + str(getattr(self.lip, "official_wav_riff_length_matched", 0))
            + "건 / 길이 불일치 "
            + str(getattr(self.lip, "official_wav_riff_length_mismatched", 0))
            + "건 / 첫 공식 WS WAV 후보 "
            + measured(getattr(self.lip, "first_official_wav_seconds", None))
            + " / PCM·float 헤더 구조 후보 "
            + str(getattr(self.lip, "official_pcm_header_candidates", 0))
            + "건 / 헤더 구조 미확인 "
            + str(getattr(self.lip, "official_pcm_header_unsupported", 0))
            + "건 / WAV 헤더상 합계 음성 길이 "
            + measured(getattr(self.lip, "official_pcm_header_total_seconds", None))
            + " / 최초 WAV 헤더 표본율 "
            + str(getattr(self.lip, "official_pcm_first_sample_rate", None) or "미측정")
            + "Hz / 채널 "
            + str(getattr(self.lip, "official_pcm_first_channels", None) or "미측정")
            + " / 공식 WAV 수신 예상 음성창 안 Cubism 입·RMS 표본 "
            + str(getattr(self.lip, "official_pcm_mouth_window_samples", 0))
            + "건 / 입·OBS 근접 표본 쌍 "
            + str(self.pcm_obs_near_pair_count)
            + "쌍 / 콜백시각 차이 절댓값 p95 "
            + (f"{self.pcm_obs_near_abs_p95_ms:.1f}ms"
               if self.pcm_obs_near_abs_p95_ms is not None else "미측정")
            + " / 시청자 E2E 별도 미검증"
        )

    @property
    def same_session_voice_candidate(self) -> bool:
        """한 질문과 같은 공식 WebSocket의 WAV 길이 후보+입+OBS 관측.

        RIFF 표본 길이가 맞더라도 실제 보이스 사용권이나 OBS 인코더에
        바로 그 WAV가 출력되었다고 단정할 수는 없다.
        """
        return bool(
            self.verified_observation
            and getattr(self.lip, "official_wav_riff_length_matched", 0) > 0
            and getattr(self.lip, "official_ws_audio_events", 0) > 0
        )

    @property
    def same_session_audio_video_candidate(self) -> bool:
        """동일 발화 시간 후보·공식 WAV 길이·실제 프로그램 영상 변화를 결합.

        화면 변화가 반드시 아바타 입이라는 증거는 아니며
        시청자 인코더/송출/수신 검증으로 보고하지 않는다.
        """
        return bool(
            self.same_session_voice_candidate
            and getattr(self.obs, "program_video_change_candidate", False)
        )

    @property
    def same_session_pcm_audio_video_candidate(self) -> bool:
        """공식 서버 PCM/float WAV 메타데이터와 실제 입·OBS 관측 결합.

        헤더만 확인하며 오디오 본문 파형/화자·인코더/시청자 송출은
        확인하지 않는다. 기존 단일 질문·관찰 경로만 사용한다.
        """
        return bool(
            self.same_session_audio_video_candidate
            and getattr(self.lip, "official_pcm_header_candidates", 0) > 0
        )

    @property
    def same_session_pcm_mouth_audio_video_candidate(self) -> bool:
        """공식 WAV 수신 예상 음성창 안 Cubism 입·RMS 표본과 OBS 후보.

        WAV 수신창은 실제 재생 시각/OBS 인코더/시청자 수신의 실증이 아니다.
        """
        if (not self.same_session_pcm_audio_video_candidate
                or getattr(self.lip, 'official_pcm_mouth_window_samples', 0) < 2):
            return False
        first = getattr(self.lip, 'official_pcm_mouth_first_monotonic', 0.0)
        last = getattr(self.lip, 'official_pcm_mouth_last_monotonic', 0.0)
        audio = getattr(self.obs, 'audio', None)
        audio_first = getattr(audio, 'first_selected_signal_monotonic', 0.0)
        audio_last = getattr(audio, 'last_selected_signal_monotonic', 0.0)
        return bool(
            all(type(v) in (int, float) and math.isfinite(v)
                for v in (first, last, audio_first, audio_last))
            and 0 < first < last and 0 < audio_first < audio_last
            and first < audio_last and last > audio_first
        )


    def _pcm_obs_near_deltas_seconds(self) -> tuple[float, ...]:
        """동일 검사에서 얻은 입·OBS 콜백시각 근접 쌍. 시청자 지연 아님."""
        if not self.same_session_pcm_mouth_audio_video_candidate:
            return ()
        mouth = getattr(self.lip, "official_pcm_mouth_sample_times", ())
        audio = getattr(getattr(self.obs, "audio", None), "selected_signal_sample_times", ())
        if (not isinstance(mouth, tuple) or not isinstance(audio, tuple)
                or len(mouth) < 2 or len(audio) < 2):
            return ()
        if (any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
                for v in mouth + audio)
                or any(x >= y for times in (mouth, audio)
                       for x, y in zip(times, times[1:]))):
            return ()
        i = j = 0
        deltas: list[float] = []
        while i < len(mouth) and j < len(audio):
            difference = mouth[i] - audio[j]
            if abs(difference) <= 0.2:
                deltas.append(audio[j] - mouth[i])
                i += 1
                j += 1
            elif difference < 0:
                i += 1
            else:
                j += 1
        return tuple(deltas)

    @property
    def pcm_obs_near_pair_count(self) -> int:
        """실제 근접 관측 표본의 중복 없는 쌍 개수."""
        return len(self._pcm_obs_near_deltas_seconds())

    @property
    def pcm_obs_near_abs_p95_ms(self) -> float | None:
        """콜백시각 차이 절댓값 p95(ms). 전송 지연으로 간주하지 않는다."""
        values = sorted(abs(v) * 1000 for v in self._pcm_obs_near_deltas_seconds())
        if len(values) < 2:
            return None
        return round(values[math.ceil(len(values) * 0.95) - 1], 3)

    @property
    def same_session_pcm_sample_pair_candidate(self) -> bool:
        """Cubism 입·OBS 미터의 서로 다른 근접 표본 2쌍 이상 후보."""
        return self.pcm_obs_near_pair_count >= 2

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
                    observe_program_motion=True,
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
                          and 0 < mouth_first < mouth_last
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
                or not (began <= first < last <= ended)):
            return False
        # The same monotonic clock is used by both native Windows OBS events
        # and official WebView2/Cubism evidence; NO broad window shortcut.
        # 경계점 하나에서만 맞닿은 소리/입 표본은 겹친 지속시간이
        # 0이다. 이전/다음 발화가 우연히 경계에 닿아도 동일 발화가 아니다.
        return first < mouth_last and last > mouth_first

    matching = [sample for began, ended, sample in observation
                if same_utterance_window(began, ended, sample)]
    # 연속 관찰 구간 중 실제 근접 표본이 가장 많은 후보를 선택한다.
    def candidate_quality(sample) -> tuple[int, int]:
        candidate = OfficialChatObsEvidence(
            lip=lip, obs=sample, temporal_overlap_candidate=True)
        return (candidate.pcm_obs_near_pair_count,
                int(bool(sample.program_video_change_candidate)))

    selected = max(matching, key=candidate_quality) if matching else next(
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
        getattr(selected, "audio", None), "first_selected_signal_monotonic", None
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
