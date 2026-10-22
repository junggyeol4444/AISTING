"""One-shot REAL GPT-SoVITS WAV -> official OBS media-source meter proof.

This is a real path when the operator has licensed reference audio and a
running local GPT-SoVITS model, not a fake TTS engine or automatic broadcast.
Never start stream/record, post chats or clone/train any voice.
"""
from __future__ import annotations

import math
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .original_plan_tts import synthesize_local_gpt_sovits
from .original_plan_obs import OfficialObsWebsocket


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
) -> RealVoiceObsResult:
    """Synthesize real Korean speech, route one bounded WAV through actual OBS.

    Only a stopped OBS stream is permitted for this one-shot test. A temporary
    input/source is removed in finally; no original user sources or files are
    touched, and playback bytes are never logged.
    """
    if operator_approved is not True or rights_confirmed is not True:
        raise PermissionError("이번 실제 GPT-SoVITS→OBS 연결 및 음성 사용 권리 승인이 필요합니다.")
    # Check OBS status BEFORE voice synthesis, so no audio is generated when
    # OBS is broadcasting or cannot be authenticated.
    obs = OfficialObsWebsocket(obs_password, port=obs_port)
    state = obs.connect()
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
    kind_list = client.get_input_kind_list(False).input_kinds
    if "ffmpeg_source" not in kind_list:
        raise RuntimeError("실제 OBS 미디어 입력이 지원되지 않습니다.")
    utterance = synthesize_local_gpt_sovits(
        reference_audio, reference_text, sentence, api_url=api_url,
        operator_approved=True, rights_confirmed=True,
        play_to_speaker=False, return_audio_bytes=True,
    )
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
    # Use a unique source name; never replace the operator's existing input.
    import secrets
    input_name = "AISTING-verification-" + secrets.token_hex(8)
    created = False
    creation_attempted = False
    owned_input_uuid = None

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
                "close_when_inactive": False,
            }, True)
            created = True
            owned_input_uuid = getattr(creation_result, "input_uuid", None)
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

            def start_exact_created_media_after_meter_subscription():
                # The only mutable target is the unique temporary source we
                # created for THIS licensed utterance, never an existing
                # recording/stream or the user's named OBS media input.
                fresh = obs.status()
                if fresh.streaming or fresh.scene != state.scene:
                    raise RuntimeError(
                        "OBS 미터 연결 도중 방송 또는 장면이 바뀌어 재생을 중단합니다.")
                ensure_not_recording()
                confirm_owned_input()
                client.trigger_media_input_action(
                    input_name, "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART")

            meters = obs.read_actual_audio_meters(
                operator_approved=True, input_name=input_name,
                duration=meter_duration,
                start_action=start_exact_created_media_after_meter_subscription)
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
            )
            if not result.actual_signal:
                raise RuntimeError("OBS가 GPT-SoVITS 실제 WAV 입력 신호를 확인하지 못했습니다.")
            after_meter = obs.status()
            if after_meter.streaming or after_meter.scene != state.scene:
                raise RuntimeError("OBS 미터 검사 중 송출 또는 장면 상태가 변경되었습니다.")
            ensure_not_recording()
            return result
        finally:
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
