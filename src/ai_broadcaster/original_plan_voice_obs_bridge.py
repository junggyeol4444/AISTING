"""One-shot REAL GPT-SoVITS WAV -> official OBS media-source meter proof.

This is a real path when the operator has licensed reference audio and a
running local GPT-SoVITS model, not a fake TTS engine or automatic broadcast.
Never start stream/record, post chats or clone/train any voice.
"""
from __future__ import annotations

import hashlib
import math
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .original_plan_tts import synthesize_local_gpt_sovits
from .original_plan_obs import OfficialObsWebsocket
from .voice_waveform_meter_match import compare_voice_meter_envelope
from .voice_observed_segments import compare_wav_obs_active_silence


@dataclass(frozen=True)
class RealVoiceObsResult:
    sample_rate: int
    channels: int
    frames: int
    obs_version: str
    audio_input_events: int
    actual_signal: bool
    wav_duration_seconds: float = 0.0
    meter_observation_seconds: float = 0.0
    observation_covers_wav_duration: bool = False
    # 재생 명령 직전의 Python monotonic 시점부터 실제 미터 양성 시점까지.
    # WAV와 OBS 믹서 사이의 로컬 관측 후보이며 출력 지연은 아님.
    restart_requested_monotonic: float | None = None
    restart_returned_monotonic: float | None = None
    first_obs_signal_after_restart_seconds: float | None = None
    last_obs_signal_after_restart_seconds: float | None = None
    obs_positive_samples_after_restart: int = 0
    obs_signal_during_wav_candidate: bool = False
    # 실제 GPT-SoVITS 16-bit PCM 음량 변화와 OBS 선택 미터의
    # 비율·시간 근접 유사성. 원본 파형 일치/동일 화자 증명 아님.
    obs_wav_envelope_correlation: float | None = None
    obs_wav_envelope_mapped_samples: int = 0
    obs_wav_envelope_candidate: bool = False
    # 동일 1회 WAV 재생 요청 후, 발화/쉼 패턴의 실제 관찰값.
    obs_wav_segment_score: float | None = None
    obs_wav_segment_samples: int = 0
    obs_wav_segment_lag_seconds: float | None = None
    obs_wav_segment_candidate: bool = False
    obs_wav_speech_samples: int = 0
    obs_wav_silence_samples: int = 0
    # 독립 단계별 실제 monotonic 시각 계측. 시청자 종단간 지연 아님.
    obs_connect_seconds: float | None = None
    tts_synthesis_seconds: float | None = None
    obs_source_prepare_seconds: float | None = None
    obs_meter_observed_seconds: float | None = None
    tts_done_to_first_meter_seconds: float | None = None
    # 동일 실제 WAV를 공식 Cubism RMS 경로와 OBS 임시 입력에 연결한
    # 경우에만 기록. 입·화면·미터의 실제 관찰과 시청자 송출은 별개.
    actual_pcm_cubism_requested: bool = False
    cubism_renderer_rms_calls: int = 0
    cubism_actual_mouth_samples: int = 0
    cubism_actual_mouth_changes: int = 0
    cubism_mouth_range: float | None = None
    cubism_wav_mouth_candidate: bool = False
    obs_program_frame_observed: bool = False
    obs_program_capture_candidate: bool = False
    # 실제 WAV가 OBS 입력에 재생되는 동안 캡처한 프로그램 화면의
    # PNG 변화 후보. 입 움직임의 시각적 인과관계·송출 증명은 아님.
    obs_program_frames_during_wav: int = 0
    obs_program_motion_near_wav_candidate: bool = False
    same_wav_cubism_obs_candidate: bool = False
    # 서로 다른 OS/브라우저 단조시계를 대입하지 않고
    # 실제 IPC 시작 전후 시각 범위와 WebView 상대 시간을 사용한 구간 후보.
    cubism_obs_time_overlap_candidate: bool = False
    cubism_first_mouth_seconds: float | None = None
    cubism_last_mouth_seconds: float | None = None


def verify_gpt_sovits_to_obs(
    reference_audio: Path,
    reference_text: str,
    sentence: str,
    *,
    obs_password: str,
    obs_port: int = 4455,
    api_url: str = "http://127.0.0.1:9880/tts",
    operator_approved: bool = False,
    rights_confirmed: bool = False,
    couple_live2d: bool = False,
) -> RealVoiceObsResult:
    """Synthesize real Korean speech, route one bounded WAV through actual OBS.

    Only a stopped OBS stream is permitted for this one-shot test. A temporary
    input/source is removed in finally; no original user sources or files are
    touched, and playback bytes are never logged.
    """
    if operator_approved is not True or rights_confirmed is not True:
        raise PermissionError("이번 실제 GPT-SoVITS→OBS 연결 및 음성 사용 권리 승인이 필요합니다.")
    if type(couple_live2d) is not bool:
        raise ValueError("실제 Cubism 연동 선택값이 올바르지 않습니다.")

    # Check OBS status BEFORE voice synthesis, so no audio is generated when
    # OBS is broadcasting or cannot be authenticated.
    connection_started_at = time.monotonic()
    obs = OfficialObsWebsocket(obs_password, port=obs_port)
    state = obs.connect()
    connection_ended_at = time.monotonic()
    if state.streaming:
        raise RuntimeError("OBS가 실제 방송 중일 때 임시 음성 입력 검사를 실행하지 않습니다.")
    client = obs._client

    def ensure_not_recording():
        # Recording would capture our temporary voice source even when the
        # public stream is off. Fail closed if OBS cannot confirm this status.
        try:
            active = client.get_record_status().output_active
        except Exception as exc:
            raise RuntimeError("OBS 녹화 상태를 확인하지 못했습니다.") from exc
        if type(active) is not bool:
            raise RuntimeError("OBS 녹화 상태 응답이 올바르지 않습니다.")
        if active:
            raise RuntimeError("OBS가 녹화 중일 때 임시 음성 입력 검사를 실행하지 않습니다.")

    ensure_not_recording()
    frontend = None
    obs_capture_candidate = False
    if couple_live2d:
        from . import original_plan_frontend as frontend
        child = frontend._native_viewer
        if (child is None or child.poll() is not None
                or frontend._native_bridge is None):
            raise RuntimeError("공식 Live2D Windows 창이 연결되지 않았습니다.")
        # 실제 사용자 장면을 바꾸거나 OBS 캡처 소스를 생성하지 않는다.
        # 활성 캡처 경로가 없으면 실제 영상 결합의 후보로도 진행하지 않는다.
        media_path = obs.read_scene_media_path()
        from .obs_live2d_frame_link import active_official_window_capture
        obs_capture_candidate = active_official_window_capture(
            media_path.capture_sources)
        if not obs_capture_candidate:
            raise RuntimeError(
                "OBS 현재 장면에 실제 공식 AISTING Live2D 창 제목과 일치하는 "
                "활성 창 캡처가 없습니다. 임의 모니터·게임·다른 창은 증거가 아닙니다.")
    kind_list = client.get_input_kind_list(False).input_kinds
    if "ffmpeg_source" not in kind_list:
        raise RuntimeError("실제 OBS 미디어 입력이 지원되지 않습니다.")
    synthesis_started_at = time.monotonic()
    utterance = synthesize_local_gpt_sovits(
        reference_audio, reference_text, sentence, api_url=api_url,
        operator_approved=True, rights_confirmed=True,
        play_to_speaker=False, return_audio_bytes=True,
    )
    synthesis_ended_at = time.monotonic()
    raw = utterance.wav_data
    if not raw or len(raw) < 44:
        raise RuntimeError("실제 GPT-SoVITS 음성 WAV를 전달받지 못했습니다.")
    # 기존의 고정 3초 미터 관찰은 5~8초 한국어 WAV의 후반 신호를
    # 놓칠 수 있다. 실제 반환된 WAV 프레임/샘플레이트에 맞춰,
    # OBS API의 기존 읽기 상한 8초 안에서만 기간을 확대한다.
    if (type(utterance.sample_rate) is not int or utterance.sample_rate <= 0
            or type(utterance.frame_count) is not int or utterance.frame_count <= 0):
        raise RuntimeError("실제 GPT-SoVITS WAV 재생 시간을 계산할 수 없습니다.")
    wav_duration = utterance.frame_count / utterance.sample_rate
    if not math.isfinite(wav_duration) or wav_duration <= 0:
        raise RuntimeError("실제 GPT-SoVITS WAV 재생 시간이 유효하지 않습니다.")
    # 최소 기존 3초, 최대 OBS의 허용된 8초. 8초 초과 WAV는
    # 관찰 창이 전체를 포함하지 않았음을 UI에 명시한다.
    meter_duration = min(8.0, max(3.0, wav_duration + 0.25))
    covers_duration = meter_duration >= wav_duration
    envelope = ()
    if couple_live2d:
        from .same_wav_cubism_driver import authorized_pcm_envelope
        # 실제 생성된 WAV의 전체 0.4~8초 음량을 그대로 사용하고
        # 길이 초과를 가짜 보간/무음 대체로 처리하지 않는다.
        envelope = authorized_pcm_envelope(raw)
    # Use a unique source name; never replace the operator's existing input.
    import secrets
    input_name = "AISTING-verification-" + secrets.token_hex(8)
    created = False
    creation_attempted = False
    owned_input_uuid = None
    owned_scene_item_id = None
    mouth_token = None
    mouth_summary = None
    mouth_start_call_begin_at = None
    mouth_start_call_end_at = None
    program_frame_observed = False
    program_frames: list[tuple[float, str, str]] = []

    def confirm_owned_input():
        # 같은 이름이라도 다른 UUID로 교체된 입력은 절대로 재생·삭제하지 않는다.
        if not callable(getattr(client, "get_input_list", None)):
            return None  # 기존 구형 테스트용 주입 클라이언트
        inputs = client.get_input_list().inputs
        if not isinstance(inputs, list):
            raise RuntimeError("OBS 임시 음성 입력 목록을 확인하지 못했습니다.")
        matches = [item for item in inputs if isinstance(item, dict)
                   and item.get("inputName") == input_name]
        if len(matches) != 1 or matches[0].get("inputKind") != "ffmpeg_source":
            raise RuntimeError("OBS 임시 음성 소스의 동일성을 확인하지 못했습니다.")
        uuid = matches[0].get("inputUuid")
        if not isinstance(uuid, str) or not uuid:
            raise RuntimeError("OBS 임시 음성 소스 UUID를 확인하지 못했습니다.")
        if owned_input_uuid is not None and uuid != owned_input_uuid:
            raise RuntimeError("OBS 임시 음성 소스가 다른 입력으로 교체되었습니다.")
        return uuid

    with tempfile.TemporaryDirectory(prefix="AISTING_real_voice_") as root:
        wav_path = Path(root) / "one_shot.wav"
        wav_path.write_bytes(raw)
        try:
            # Synthesis can take minutes. OBS may have started streaming or
            # changed scenes since the original pre-synthesis permission check.
            # Refuse any new source before sending audio to an unknown scene.
            source_prepare_started_at = time.monotonic()
            before_input = obs.status()
            if before_input.streaming:
                raise RuntimeError("음성 합성 중 OBS 방송이 시작되어 입력 검사를 중단했습니다.")
            if before_input.scene != state.scene:
                raise RuntimeError("음성 합성 중 OBS 프로그램 장면이 변경되어 검사를 중단했습니다.")
            ensure_not_recording()
            # OBS media source plays the WAV into the OBS mixer only.
            # It does not start recording or stream output.
            creation_attempted = True
            creation_result = client.create_input(state.scene, input_name, "ffmpeg_source", {
                "is_local_file": True,
                "local_file": str(wav_path),
                # One authorized voice probe is never indefinite replay.
                "looping": False,
                "restart_on_activate": False,
                "close_when_inactive": bool(couple_live2d),
            }, not couple_live2d)
            created = True
            owned_input_uuid = getattr(creation_result, "input_uuid", None)
            if couple_live2d:
                owned_scene_item_id = getattr(creation_result, "scene_item_id", None)
                if type(owned_scene_item_id) is not int:
                    raise RuntimeError("OBS 임시 WAV의 전용 장면 항목을 확인하지 못했습니다.")
            confirmed_uuid = confirm_owned_input()
            if confirmed_uuid is not None:
                if owned_input_uuid is not None and owned_input_uuid != confirmed_uuid:
                    raise RuntimeError("OBS 새 임시 음성 소스 UUID가 일치하지 않습니다.")
                owned_input_uuid = confirmed_uuid
            # The OBS state can change while CreateInput is in flight.
            # Never claim a safe offline proof if a stream just began.
            after_input = obs.status()
            if after_input.streaming or after_input.scene != state.scene:
                raise RuntimeError("OBS 음성 입력 생성 도중 송출 또는 장면 상태가 변경되었습니다.")
            ensure_not_recording()

            source_prepare_ended_at = time.monotonic()
            restart_requested_at = None
            restart_returned_at = None

            def start_exact_created_media_after_meter_subscription():
                nonlocal restart_requested_at, restart_returned_at, mouth_token
                nonlocal mouth_start_call_begin_at, mouth_start_call_end_at
                # The only mutable target is the unique temporary source we
                # created for THIS licensed utterance, never an existing
                # recording/stream or the user's named OBS media input.
                fresh = obs.status()
                if fresh.streaming or fresh.scene != state.scene:
                    raise RuntimeError(
                        "OBS 미터 연결 도중 방송 또는 장면이 바뀌어 재생을 중단합니다.")
                ensure_not_recording()
                confirm_owned_input()
                if couple_live2d:
                    # OBS 구독 준비 뒤 동일 실제 WAV를 공식 Cubism 입에
                    # 공급한다. 권리 있는 실제 PCM에서 나온 50ms RMS만 사용.
                    mouth_start_call_begin_at = time.monotonic()
                    mouth_token = frontend.start_authorized_pcm_live2d_mouth(
                        envelope, operator_approved=True, rights_confirmed=True)
                    mouth_start_call_end_at = time.monotonic()
                    # 이번에 생성한 비활성 임시 항목만 활성화한다.
                    # 사용자 기존 장면이나 소스의 on/off는 변경하지 않는다.
                    client.set_scene_item_enabled(
                        state.scene, owned_scene_item_id, True)
                restart_requested_at = time.monotonic()
                client.trigger_media_input_action(
                    input_name, "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART")
                restart_returned_at = time.monotonic()

            def capture_actual_program_frame():
                # 승인된 실제 OBS의 현재 프로그램 PNG를 메모리에서만
                # SHA256으로 변환. PNG 원본·개인 화면을 기록/저장하지 않는다.
                frame = obs.read_current_scene_frame(operator_approved=True)
                program_frames.append((
                    time.monotonic(), frame.scene,
                    hashlib.sha256(frame.png_data).hexdigest(),
                ))

            if couple_live2d:
                capture_actual_program_frame()
            meter_probe_started_at = time.monotonic()
            try:
                meters = obs.read_actual_audio_meters(
                    operator_approved=True, input_name=input_name,
                    duration=meter_duration,
                    start_action=start_exact_created_media_after_meter_subscription,
                    **({"program_frame_probe": capture_actual_program_frame}
                       if couple_live2d else {}))
            finally:
                if mouth_token is not None:
                    # 오디오 미터 성공/예외와 무관하게 원래 Cubism getRms를 복원.
                    mouth_summary = frontend.finish_authorized_pcm_live2d_mouth(
                        mouth_token, operator_approved=True)
                    mouth_token = None
            meter_probe_ended_at = time.monotonic()
            if couple_live2d:
                # 실제 WAV 전/중/후 프레임: 입술의 영상 인과성·OBS
                # 인코딩·시청자 수신을 증명하지 않는 약한 변화 후보.
                capture_actual_program_frame()
                program_frame_observed = len(program_frames) >= 3
            # OBS 서버는 미터 이벤트를 비동기로 전달한다. 재생 명령을
            # 보내기 이전의 양성 신호를 이번 WAV의 증거로 세지 않는다.
            # 늦게 도착한 실제 양성 시각은 추정하지 않고 별도 구분한다.
            positive_times = tuple(getattr(meters, "selected_signal_sample_times", ()))
            valid_restart_times = (
                type(restart_requested_at) in (int, float)
                and type(restart_returned_at) in (int, float)
                and math.isfinite(restart_requested_at)
                and math.isfinite(restart_returned_at)
                and 0 < restart_requested_at <= restart_returned_at
            )
            after_restart = (
                tuple(t for t in positive_times
                      if type(t) in (int, float) and math.isfinite(t)
                      and t >= restart_requested_at)
                if valid_restart_times else ()
            )
            # OBS 동기화/재생 지연은 기기마다 다르므로 실제 시간만
            # 보고하며 0.5초는 안전한 오탐 방지의 엄격한 판정이 아니다.
            # WAV 예상 종료 후의 소리는 이 발화로 단정하지 않는다.
            during_wav = (
                tuple(t for t in after_restart
                      if t <= restart_returned_at + wav_duration + 0.5)
                if valid_restart_times else ()
            )
            first_delay = (
                round(during_wav[0] - restart_requested_at, 6)
                if during_wav else None
            )
            last_delay = (
                round(during_wav[-1] - restart_requested_at, 6)
                if during_wav else None
            )
            # 비교는 권리 확인 후 합성된 메모리 내 실제 WAV 바이트와
            # OBS 고유 임시 입력의 실제 미터 콜백 강도만 사용한다.
            # PCM 미지원 WAV는 허위 추론하지 않고 미측정으로 남긴다.
            similarity, mapped_count = compare_voice_meter_envelope(
                raw,
                getattr(meters, "selected_signal_peak_samples", ()),
                restart_requested_at if valid_restart_times else None,
            )
            segment_result = compare_wav_obs_active_silence(
                raw,
                getattr(meters, "selected_all_meter_level_samples", ()),
                restart_requested_at if valid_restart_times else None,
            )
            mouth_first = (
                mouth_summary.get("mouthFirstMs") if mouth_summary else None)
            mouth_last = (
                mouth_summary.get("mouthLastMs") if mouth_summary else None)
            # 실제 JS 상대시간은 WebView와 Python의 단조시계 기준이
            # 다르므로 관찰 시작 IPC의 두 실제 Python 시각으로 범위를 만든다.
            # 이 시간 범위와 OBS 미터가 가까워도 송출 인과관계 확정은 아님.
            valid_mouth_clock = (
                type(mouth_start_call_begin_at) in (int, float)
                and type(mouth_start_call_end_at) in (int, float)
                and type(mouth_first) in (int, float)
                and type(mouth_last) in (int, float)
                and math.isfinite(mouth_first) and math.isfinite(mouth_last)
                and 0 <= mouth_first <= mouth_last <= wav_duration * 1000 + 1000
                and mouth_start_call_begin_at <= mouth_start_call_end_at
            )
            mouth_obs_overlap = bool(
                valid_mouth_clock and any(
                    mouth_start_call_begin_at + mouth_first / 1000 - 0.5
                    <= moment <=
                    mouth_start_call_end_at + mouth_last / 1000 + 0.5
                    for moment in during_wav
                ))
            from .obs_live2d_frame_link import program_motion_near_audio
            observed_program_motion = bool(
                couple_live2d and valid_restart_times
                and program_motion_near_audio(
                    tuple(program_frames), after_restart,
                    restart_at=restart_requested_at, wav_seconds=wav_duration))
            cubism_driver_valid = bool(
                mouth_summary and mouth_summary.get("reason")
                in ("끝", "종료요청")
                and mouth_summary.get("positiveCalls", 0) > 0
                and mouth_summary.get("calls", 0) >= 3
                and mouth_summary.get("samples", 0) >= 3
                and mouth_summary.get("changes", 0) >= 1
                and (mouth_summary.get("mouthRange") or 0) > 0.02)
            result = RealVoiceObsResult(
                sample_rate=utterance.sample_rate,
                channels=utterance.channels,
                frames=utterance.frame_count,
                obs_version=state.version,
                audio_input_events=meters.selected_meter_events,
                actual_signal=bool(meters.usable_output_candidate),
                wav_duration_seconds=round(wav_duration, 3),
                meter_observation_seconds=round(meter_duration, 3),
                observation_covers_wav_duration=covers_duration,
                restart_requested_monotonic=restart_requested_at,
                restart_returned_monotonic=restart_returned_at,
                first_obs_signal_after_restart_seconds=first_delay,
                last_obs_signal_after_restart_seconds=last_delay,
                obs_positive_samples_after_restart=len(during_wav),
                obs_signal_during_wav_candidate=bool(
                    meters.usable_output_candidate and during_wav),
                obs_wav_envelope_correlation=similarity,
                obs_wav_envelope_mapped_samples=mapped_count,
                obs_wav_envelope_candidate=bool(
                    meters.usable_output_candidate
                    and during_wav and similarity is not None and similarity >= 0.8
                    and mapped_count >= 8),
                obs_wav_segment_score=segment_result.score,
                obs_wav_segment_samples=segment_result.samples,
                obs_wav_segment_lag_seconds=segment_result.lag_seconds,
                obs_wav_segment_candidate=bool(
                    meters.usable_output_candidate
                    and during_wav and segment_result.candidate),
                obs_wav_speech_samples=segment_result.voiced_samples,
                obs_wav_silence_samples=segment_result.silent_samples,
                obs_connect_seconds=round(
                    connection_ended_at - connection_started_at, 6),
                tts_synthesis_seconds=round(
                    synthesis_ended_at - synthesis_started_at, 6),
                obs_source_prepare_seconds=round(
                    source_prepare_ended_at - source_prepare_started_at, 6),
                obs_meter_observed_seconds=round(
                    meter_probe_ended_at - meter_probe_started_at, 6),
                tts_done_to_first_meter_seconds=(
                    round(during_wav[0] - synthesis_ended_at, 6)
                    if during_wav else None),
                actual_pcm_cubism_requested=couple_live2d,
                cubism_renderer_rms_calls=(
                    mouth_summary.get("calls", 0) if mouth_summary else 0),
                cubism_actual_mouth_samples=(
                    mouth_summary.get("samples", 0) if mouth_summary else 0),
                cubism_actual_mouth_changes=(
                    mouth_summary.get("changes", 0) if mouth_summary else 0),
                cubism_mouth_range=(
                    mouth_summary.get("mouthRange") if mouth_summary else None),
                cubism_wav_mouth_candidate=cubism_driver_valid,
                obs_program_frame_observed=program_frame_observed,
                obs_program_capture_candidate=obs_capture_candidate,
                obs_program_frames_during_wav=(
                    max(0, len(program_frames) - 2) if couple_live2d else 0),
                obs_program_motion_near_wav_candidate=observed_program_motion,
                same_wav_cubism_obs_candidate=bool(
                    couple_live2d and obs_capture_candidate
                    and program_frame_observed and observed_program_motion
                    and meters.usable_output_candidate
                    and cubism_driver_valid and mouth_obs_overlap
                    and during_wav and similarity is not None and similarity >= 0.8
                    and mapped_count >= 8),
                cubism_obs_time_overlap_candidate=mouth_obs_overlap,
                cubism_first_mouth_seconds=(
                    round(mouth_first / 1000, 6)
                    if valid_mouth_clock else None),
                cubism_last_mouth_seconds=(
                    round(mouth_last / 1000, 6)
                    if valid_mouth_clock else None),
            )
            if not result.actual_signal:
                raise RuntimeError("OBS가 GPT-SoVITS 실제 WAV 입력 신호를 확인하지 못했습니다.")
            after_meter = obs.status()
            if after_meter.streaming or after_meter.scene != state.scene:
                raise RuntimeError("OBS 미터 검사 중 송출 또는 장면 상태가 변경되었습니다.")
            ensure_not_recording()
            return result
        finally:
            # 공식 모델 복원 실패가 나더라도 임시 OBS 소스 제거를 건너뛰지 않는다.
            restore_error = None
            if mouth_token is not None:
                try:
                    frontend.finish_authorized_pcm_live2d_mouth(
                        mouth_token, operator_approved=True)
                except Exception as exc:
                    restore_error = exc
                mouth_token = None
            source_error = None
            try:
                if created:
                    # 삭제 직전에도 UUID를 재확인한다. 다른 사용자의 소스는 보호한다.
                    try:
                        confirm_owned_input()
                        client.remove_input(input_name)
                    except Exception as exc:
                        # Never report success when our temporary input may remain.
                        raise RuntimeError("OBS 임시 음성 소스 정리에 실패했습니다.") from exc
                elif creation_attempted:
                    # OBS can CREATE the source and then lose the RPC response.
                    # Do not leave a live audio input behind merely because the
                    # create_input call raised before setting created=True.
                    try:
                        inputs = client.get_input_list().inputs
                        if not isinstance(inputs, list):
                            raise ValueError("OBS 입력 목록 형식 오류")
                        matches = [item for item in inputs if isinstance(item, dict)
                                   and item.get("inputName") == input_name]
                        if len(matches) > 1:
                            raise ValueError("OBS 임시 소스 이름 중복")
                        if matches:
                            if matches[0].get("inputKind") != "ffmpeg_source":
                                raise ValueError("OBS 임시 음성 소스 유형 불일치")
                            client.remove_input(input_name)
                    except Exception as exc:
                        raise RuntimeError(
                            "OBS 임시 음성 소스 생성 오류 후 정리 상태를 확인하지 못했습니다."
                        ) from exc
            except Exception as exc:
                source_error = exc
            if source_error is not None:
                raise source_error
            if restore_error is not None:
                raise RuntimeError(
                    "공식 Cubism 원래 음성 입 구동을 복원하지 못했습니다."
                ) from restore_error
