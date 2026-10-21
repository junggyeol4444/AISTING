"""Read-only preflight for the saved official Korean GPT-SoVITS selection.

This does not run the server, synthesize, install models or establish rights.
"""
from __future__ import annotations

from pathlib import Path

from .original_plan_config_io import decode_official_utf8
from .original_plan_studio import check_official_project, StageOneUnavailable
from .original_plan_tts import (
    validate_local_gpt_sovits_url,
    inspect_reference_audio_container,
    VoiceConfigurationError,
)


def read_saved_korean_gpt_sovits_config(project: str | Path) -> tuple[str, Path, str]:
    """Validated configuration for real local inference; no network or writes."""
    root = check_official_project(project)
    conf = root / "conf.yaml"
    if conf.is_symlink() or not conf.is_file():
        raise StageOneUnavailable("공식 음성 설정 conf.yaml을 확인할 수 없습니다.")
    data = conf.read_bytes()
    if not data or len(data) > 1_000_000:
        raise StageOneUnavailable("공식 음성 설정 파일 크기가 올바르지 않습니다.")
    try:
        source, _ = decode_official_utf8(data)
    except (UnicodeError, ValueError) as exc:
        raise StageOneUnavailable("공식 음성 설정을 UTF-8로 읽지 못했습니다.") from exc
    lines = source.splitlines()

    def children(start: int, indent: int) -> tuple[int, int]:
        prefix = " " * indent
        end = next((i for i in range(start + 1, len(lines))
                    if lines[i].strip() and not lines[i].startswith(prefix)
                    and not lines[i].lstrip().startswith("#")), len(lines))
        return start + 1, end

    def one(start: int, end: int, indent: int, key: str) -> tuple[int, str]:
        prefix = " " * indent + key + ":"
        rows = [(i, s[len(prefix):].strip()) for i, s in enumerate(lines)
                if start <= i < end and s.startswith(prefix)]
        if len(rows) != 1:
            raise StageOneUnavailable("공식 GPT-SoVITS 설정 키 누락 또는 중복: " + key)
        return rows[0]

    root_i, _ = one(0, len(lines), 0, "character_config")
    start, end = children(root_i, 2)
    tts_i, _ = one(start, end, 2, "tts_config")
    start, end = children(tts_i, 4)
    _, engine = one(start, end, 4, "tts_model")
    if engine.strip("'\"") != "gpt_sovits_tts":
        raise StageOneUnavailable("현재 공식 TTS 엔진이 GPT-SoVITS가 아닙니다.")
    opts_i, _ = one(start, end, 4, "gpt_sovits_tts")
    start, end = children(opts_i, 6)

    def selected(name: str) -> str:
        return one(start, end, 6, name)[1].strip("'\"")

    if selected("text_lang") != "ko" or selected("prompt_lang") != "ko":
        raise StageOneUnavailable("공식 GPT-SoVITS 음성/참조 언어가 한국어가 아닙니다.")
    try:
        validate_local_gpt_sovits_url(selected("api_url"))
    except ValueError as exc:
        raise StageOneUnavailable("GPT-SoVITS 음성 API가 로컬 주소가 아닙니다.") from exc
    # A nonempty path string is NOT an actual voice reference. The
    # configuration writer stores an absolute, existing, validated file;
    # a deleted/renamed reference after app restart must fail *before* the
    # official Live2D user message is sent. Inspect headers only: no sound
    # playback, voice training, network access or implied licensing proof.
    reference_path = selected("ref_audio_path")
    spoken_words = selected("prompt_text")
    if not reference_path or not spoken_words:
        raise StageOneUnavailable("실제 GPT-SoVITS 참조 음성/대사 설정이 없습니다.")
    if (len(spoken_words.strip()) < 1 or len(spoken_words) > 500
            or any(ord(ch) < 32 for ch in spoken_words)):
        raise StageOneUnavailable("실제 참조 음성 녹음 대사가 올바르지 않습니다.")
    reference = Path(reference_path)
    if not reference.is_absolute():
        raise StageOneUnavailable("GPT-SoVITS 참조 음성은 절대 경로로 지정해야 합니다.")
    try:
        inspect_reference_audio_container(reference)
    except (VoiceConfigurationError, OSError, ValueError) as exc:
        raise StageOneUnavailable(
            "GPT-SoVITS 참조 음성이 실제 WAV/FLAC 파일인지 확인하지 못했습니다."
        ) from exc

    return selected("api_url"), reference, spoken_words


def require_saved_korean_gpt_sovits(project: str | Path) -> None:
    """Original read-only readiness contract: never start synthesis."""
    read_saved_korean_gpt_sovits_config(project)


def synthesize_saved_korean_gpt_sovits(
    project: str | Path, utterance: str, *,
    operator_approved: bool = False, rights_confirmed: bool = False,
    timeout: float = 90.0,
):
    """Real, one-shot LOCAL inference using the exact validated upstream config.

    No audio files, playback, training, OBS changes, accounts or remote requests.
    A successful WAV is a speech signal only, not proof of Live2D/OBS or audience.
    """
    if operator_approved is not True or rights_confirmed is not True:
        raise PermissionError("참조 음성 권리와 이번 실제 합성 승인이 필요합니다.")
    url, reference, spoken_words = read_saved_korean_gpt_sovits_config(project)
    from .original_plan_tts import synthesize_local_gpt_sovits
    return synthesize_local_gpt_sovits(
        reference, spoken_words, utterance, api_url=url,
        operator_approved=True, rights_confirmed=True,
        play_to_speaker=False, return_audio_bytes=False, timeout=timeout,
    )
