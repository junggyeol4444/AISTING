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
from .obs_consecutive_audio import collect_obs_audio_times, collect_obs_input_meter_levels
from .official_ws_wav_obs_match import compare_official_pcm_obs_levels
from .official_media_stage_timing import (
    OfficialMediaStageTiming, measure_official_media_stages,
)

if TYPE_CHECKING:
    from .original_plan_frontend import OfficialLipSyncEvidence
    from .original_plan_obs import ActualObsProgramMediaObservation


def _coherent_mouth_obs_window(began, ended, sample, mouth_first, mouth_last) -> bool:
    """실제 단조시계 입 움직임과 OBS 유효 입력 표본의 양수 길이 교집합."""
    audio = getattr(sample, "audio", None)
    first = getattr(audio, "first_selected_signal_monotonic", None)
    last = getattr(audio, "last_selected_signal_monotonic", None)
    values = (began, ended, mouth_first, mouth_last, first, last)
    return bool(
        getattr(sample, "coherent_media_candidate", False)
        and all(type(value) in (int, float) and math.isfinite(value)
                for value in values)
        and 0 < began < ended
        and 0 < mouth_first < mouth_last
        and began <= first < last <= ended
        and first < mouth_last and last > mouth_first
    )


def _observed_mouth_obs_overlap(observation, lip, prompt_started_at, prompt_finished_at) -> bool:
    """한 질문의 공식 입 움직임과 실제 OBS 미터가 겹쳤을 때만 참.

    다른 발화·시청자 출력의 증명은 아니다. 테스트에서는 모의 표본만 사용.
    """
    if lip is None:
        return False
    mouth_first = getattr(lip, "first_audio_mouth_monotonic", None)
    mouth_last = getattr(lip, "last_audio_mouth_monotonic", None)
    values = (prompt_started_at, prompt_finished_at, mouth_first, mouth_last)
    if (not all(type(value) in (int, float) and math.isfinite(value)
                for value in values)
            or not (0 < prompt_started_at <= mouth_first < mouth_last
                    <= prompt_finished_at)):
        return False
    return any(_coherent_mouth_obs_window(began, ended, sample, mouth_first, mouth_last)
               for began, ended, sample in observation)


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
    obs_audio_sample_times: tuple[float, ...] | None = None
    obs_audio_window_count: int = 0
    # 공식 동일 WS에서 받은 WAV PCM16 윤곽과 OBS 실제 미터 레벨 비교.
    official_wav_obs_score: float | None = None
    official_wav_obs_sample_count: int = 0
    official_wav_obs_lag_seconds: float | None = None
    official_wav_live2d_rms_score: float | None = None
    official_wav_live2d_rms_samples: int = 0
    official_wav_live2d_rms_lag_seconds: float | None = None
    media_stage_timing: OfficialMediaStageTiming | None = None

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
            + " / 실제 OBS 일치 관찰 구간 " + str(self.obs_audio_window_count)
            + "개 / 누적 유효 오디오 표본 " + str(len(self.obs_audio_sample_times or ()))
            + "건 / 공식 WS WAV·OBS 실제 음량 상관 "
            + (f"{self.official_wav_obs_score:.3f}"
               if self.official_wav_obs_score is not None else "미측정")
            + " / 실제 레벨 대응 표본 " + str(self.official_wav_obs_sample_count)
            + "건 / WS WAV 수신 후 후보 지연 "
            + (f"{self.official_wav_obs_lag_seconds:.3f}초"
               if self.official_wav_obs_lag_seconds is not None else "미측정")
            + " / 공식 WAV·Live2D 렌더러 RMS 상관 "
            + (f"{self.official_wav_live2d_rms_score:.3f}"
               if self.official_wav_live2d_rms_score is not None else "미측정")
            + " / 렌더러 RMS 비교 표본 " + str(self.official_wav_live2d_rms_samples)
            + "건 / " + (self.media_stage_timing.describe_ko()
                           if self.media_stage_timing is not None
                           else "단계별 지연 미측정")
            + " / 시청자 E2E 별도 미검증"
        )

    @property
    def same_session_official_wav_renderer_rms_candidate(self) -> bool:
        """서버 WAV 음량 윤곽과 동일 공식 Cubism 렌더러 RMS 유사 후보.

        실제 입 모델 인과성 또는 OBS 송출/시청자 수신 증거가 아니다.
        """
        return bool(
            self.lip.verified_signal
            and self.official_wav_live2d_rms_score is not None
            and self.official_wav_live2d_rms_score >= 0.85
            and self.official_wav_live2d_rms_samples >= 12
        )

    @property
    def same_session_official_wav_obs_level_candidate(self) -> bool:
        """동일 WS의 PCM 음량 윤곽 vs 동일 검사 OBS 입력 레벨 유사성.

        WAV 재생/화자 동일성, Cubism 파라미터 구동 원인,
        OBS 최종 인코딩이나 시청자 전달은 이 상관으로 증명할 수 없다.
        """
        return bool(
            self.same_session_pcm_sample_pair_candidate
            and self.official_wav_obs_score is not None
            and self.official_wav_obs_score >= 0.85
            and self.official_wav_obs_sample_count >= 12
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
    def same_session_observed_video_audio_timing_candidate(self) -> bool:
        """실제 OBS 영상 획득 두 시점 사이와 음성·입 근접 표본을 결합.

        프레임 자체의 내부 촬영 시간이나 방송 인코더·시청자 측
        출력 시각은 재지 않았으므로 이 값도 관측 후보에 그친다.
        """
        return bool(
            self.same_session_pcm_sample_pair_candidate
            and getattr(self.obs, 'observed_video_brackets_audio_candidate', False)
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
        audio = (self.obs_audio_sample_times if self.obs_audio_sample_times is not None
                 else getattr(getattr(self.obs, "audio", None), "selected_signal_sample_times", ()))
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


def _await_official_prompt_start(
    prompt_started: threading.Event,
    cancel_observation: threading.Event,
    cancel_event: threading.Event | None,
) -> bool:
    """OBS 관찰 준비 뒤 실제 질문 신호까지 대기하되 취소는 즉시 확인한다.

    고정 8초 대기 만료로 관찰자가 먼저 종료된 채 질문이 발송되는 상황을
    막는다. 주기적인 확인은 인위적인 AI 응답 지연을 추가하지 않는다.
    """
    while True:
        if cancel_observation.is_set() or (cancel_event is not None and cancel_event.is_set()):
            return False
        if prompt_started.wait(timeout=0.1):
            return not (cancel_observation.is_set() or
                        (cancel_event is not None and cancel_event.is_set()))


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
    first_capture_ready = threading.Event()
    # OBS 미터 구독 후의 최종 안전 확인이 길어져도 실제 질문 전
    # 관찰 예산이 먼저 소진되지 않도록 첫 관찰 시작을 질문에 맞춘다.
    meter_capture_release = threading.Event()
    monitor_ended_before_reply = []
    lip = None
    send_failure = None

    def observation_ready_to_finish() -> bool:
        # 빠른 공식 응답 직후에도 실제 OBS 입·오디오 교집합을 확인할 때까지
        # 기존 관찰 시간 범위 안에서 읽는다. 실패 시 추가 대기는 하지 않는다.
        if not send_finished.is_set():
            return False
        if send_failure is not None:
            return True
        if _observed_mouth_obs_overlap(
                observation, lip, prompt_started_at, prompt_finished_at):
            return True
        # 운영자가 기존에 지정한 관찰 시간만 사용하며 새 지연 옵션은 없다.
        return time.monotonic() >= prompt_finished_at + float(duration)

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
            def wait_for_prompt_after_meter_subscription() -> None:
                # 실제 미터 이벤트 구독 완료를 메인 스레드에 알리되,
                # 최종 송출·녹화·장면 확인이 끝나기 전에는 첫 관찰창의
                # duration 카운트다운을 시작하지 않는다.
                first_capture_ready.set()
                if not _await_official_prompt_start(
                        meter_capture_release, cancel_observation, cancel_event):
                    raise InterruptedError("OBS 미터 관찰 시작 전 검사 중지")

            # No approved AI prompt is sent until the separate OBS monitor
            # has actually connected to the correct stopped scene.
            started.set()
            # Do not let fast callbacks (or a slow OBS safety preflight) use
            # up the audio observation budget BEFORE the actual user turn.
            if not _await_official_prompt_start(
                    prompt_started, cancel_observation, cancel_event):
                return
            # 실제 한국어 GPT-SoVITS 응답이 느릴 때 고정 6개 창(최대 18초)이
            # 먼저 소진되어 공식 입·음성 실측을 놓치지 않도록 한다.
            # 이미 승인된 단일 질문이 끝날 때까지 OBS를 읽기 전용으로 관찰하고,
            # 응답 종료 후에는 기존 운영자 지정 duration 범위까지만 관찰한다.
            # 추가 질문·방송·녹화·음성 재생을 시작하지 않는다.
            while True:
                if cancel_observation.is_set() or (cancel_event is not None and cancel_event.is_set()):
                    break
                if observation_ready_to_finish():
                    break
                monitor_still_offline()
                # 공식 OBS 구현에서는 실제 오디오 미터 구독 등록 완료
                # 신호를 받은 후에만 질문 전송을 허용한다.
                capture_started = time.monotonic()
                ready_capture = getattr(
                    observer, "inspect_program_media_with_meter_ready", None)
                if callable(ready_capture):
                    sample = ready_capture(
                        ready_action=wait_for_prompt_after_meter_subscription,
                        operator_approved=True, input_name=obs_input_name,
                        duration=min(float(duration), 3.0),
                        observe_program_motion=True,
                    )
                else:
                    # 이전 가상 OBS 계약검사 대역은 미터 구독 기능이 없다.
                    first_capture_ready.set()
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
                if observation_ready_to_finish():
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
        meter_capture_release.set()
        prompt_started.set()
        monitor.join(timeout=1)
        raise RuntimeError("OBS 영상·음성 관찰을 시작하지 못했습니다.")
    if errors:
        cancel_observation.set()
        meter_capture_release.set()
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
        meter_capture_release.set()
        prompt_started.set()
        monitor.join(timeout=2)
        raise
    # 관찰자가 실제 첫 OBS 표본을 읽을 준비가 되기 전에는
    # 승인된 질문조차 발송하지 않는다. 실패·취소는 미전송으로 분류한다.
    prompt_started.set()
    try:
        deadline = time.monotonic() + 3.0
        while not first_capture_ready.is_set() and not errors:
            check_cancelled()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            first_capture_ready.wait(timeout=min(0.05, remaining))
        if errors:
            raise RuntimeError("OBS 첫 표본 준비 중 안전 검사 실패 · 질문 미전송") from errors[0]
        if not first_capture_ready.is_set():
            raise RuntimeError("OBS 첫 표본 준비 시간 초과 · 질문 미전송")
        ensure_offline()
        check_cancelled()
    except Exception:
        cancel_observation.set()
        meter_capture_release.set()
        monitor.join(timeout=2)
        raise
    prompt_started_at = time.monotonic()
    prompt_finished_at = prompt_started_at
    # 이 시점에만 실제 OBS 첫 미터 관찰창의 대기를 해제한다.
    # 이미 승인된 질문은 아래에서 단 한 번 전송하며 재전송하지 않는다.
    meter_capture_release.set()
    try:
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
        return bool(valid_mouth_window and _coherent_mouth_obs_window(
            began, ended, sample, mouth_first, mouth_last))

    matching = [sample for began, ended, sample in observation
                if same_utterance_window(began, ended, sample)]
    # 연속 OBS 관찰창 경계에 걸친 실제 오디오 표본 누적
    combined_audio_times, matched_window_count = collect_obs_audio_times(
        observation, mouth_first, mouth_last) if valid_mouth_window else ((), 0)
    # 동일 공식 WebSocket이 실제 전달한 PCM16 WAV 첫 음량 정보와
    # OBS의 같은 승인 검사 중 실제 선택 입력 미터 콜백을 결합한다.
    pcm_first_received_at = getattr(
        lip, "official_pcm_first_wav_received_monotonic", 0.0)
    pcm_first_envelope = getattr(
        lip, "official_pcm_first_wav_rms_envelope", ())
    pcm_level_samples = (
        collect_obs_input_meter_levels(
            observation, since=pcm_first_received_at,
            until=pcm_first_received_at + 12)
        if type(pcm_first_received_at) in (int, float)
        and math.isfinite(pcm_first_received_at) and pcm_first_received_at > 0
        else ()
    )
    ws_pcm_score, ws_pcm_used, ws_pcm_lag = compare_official_pcm_obs_levels(
        pcm_first_envelope, pcm_first_received_at, pcm_level_samples)
    # 동일 공식 WebSocket WAV와 같은 공식 렌더러가 실제 반환한 RMS.
    # 이 비교에서도 PCM WAV 본문이나 WebView2 PCM 원본을 저장하지 않는다.
    rendered_rms = getattr(lip, "official_pcm_live2d_rms_samples", ())
    renderer_levels = (
        tuple((pcm_first_received_at + offset, level)
              for offset, level in rendered_rms)
        if type(pcm_first_received_at) in (int, float)
        and math.isfinite(pcm_first_received_at)
        and pcm_first_received_at > 0
        else ()
    )
    render_score, render_used, render_lag = compare_official_pcm_obs_levels(
        pcm_first_envelope, pcm_first_received_at, renderer_levels)
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
    matched_first_audio = combined_audio_times[0] if combined_audio_times else None
    first_obs_latency = (
        round(matched_first_audio - prompt_started_at, 6)
        if (type(matched_first_audio) in (float, int)
            and math.isfinite(matched_first_audio)
            and prompt_started_at <= matched_first_audio <= time.monotonic())
        else None
    )
    # 기존 승인 단일 질문의 실제 monotonic 관측 시각만 사용한다.
    # 관측이 겹치지 않거나 과거 발화의 WAV/입이면 수치를 만들지 않는다.
    stage_timing = measure_official_media_stages(
        prompt_started_at=prompt_started_at,
        prompt_finished_at=prompt_finished_at,
        wav_received_at=pcm_first_received_at,
        mouth_first_at=mouth_first if valid_mouth_window else None,
        obs_first_at=matched_first_audio,
        obs_observation_ended_at=max(ended for _, ended, _ in observation),
        same_utterance_overlap=bool(matching and combined_audio_times),
    )
    return OfficialChatObsEvidence(
        lip=lip, obs=selected, temporal_overlap_candidate=bool(matching),
        local_roundtrip_seconds=round(prompt_finished_at - prompt_started_at, 6),
        first_cubism_audio_seconds=first_cubism_latency,
        first_obs_audio_seconds=first_obs_latency,
        obs_audio_sample_times=combined_audio_times,
        obs_audio_window_count=matched_window_count,
        official_wav_obs_score=ws_pcm_score,
        official_wav_obs_sample_count=ws_pcm_used,
        official_wav_obs_lag_seconds=ws_pcm_lag,
        official_wav_live2d_rms_score=render_score,
        official_wav_live2d_rms_samples=render_used,
        official_wav_live2d_rms_lag_seconds=render_lag,
        media_stage_timing=stage_timing)
