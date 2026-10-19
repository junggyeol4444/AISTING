"""One-shot REAL GPT-SoVITS WAV -> official OBS media-source meter proof.

This is a real path when the operator has licensed reference audio and a
running local GPT-SoVITS model, not a fake TTS engine or automatic broadcast.
Never start stream/record, post chats or clone/train any voice.
"""
from __future__ import annotations

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
    # Use a unique source name; never replace the operator's existing input.
    import secrets
    input_name = "AISTING-verification-" + secrets.token_hex(8)
    created = False
    with tempfile.TemporaryDirectory(prefix="AISTING_real_voice_") as root:
        wav_path = Path(root) / "one_shot.wav"
        wav_path.write_bytes(raw)
        try:
            # OBS media source plays the WAV into the OBS mixer only.
            # It does not start recording or stream output.
            client.create_input(state.scene, input_name, "ffmpeg_source", {
                "is_local_file": True,
                "local_file": str(wav_path),
                "looping": True,
                "restart_on_activate": True,
                "close_when_inactive": False,
            }, True)
            created = True
            import time
            time.sleep(.4)
            meters = obs.read_actual_audio_meters(
                operator_approved=True, input_name=input_name, duration=3)
            result = RealVoiceObsResult(
                sample_rate=utterance.sample_rate,
                channels=utterance.channels,
                frames=utterance.frame_count,
                obs_version=state.version,
                audio_input_events=meters.selected_meter_events,
                actual_signal=bool(meters.selected_signal),
            )
            if not result.actual_signal:
                raise RuntimeError("OBS가 GPT-SoVITS 실제 WAV 입력 신호를 확인하지 못했습니다.")
            if obs.status().streaming:
                raise RuntimeError("OBS 송출 상태가 변경되어 검사를 중단했습니다.")
            return result
        finally:
            if created:
                # Only delete our newly created temporary source.
                try:
                    client.remove_input(input_name)
                except Exception:
                    # Do not report an apparently clean success when source
                    # cleanup fails. File stays isolated in TempDirectory.
                    raise RuntimeError("OBS 임시 음성 소스 정리에 실패했습니다.")
