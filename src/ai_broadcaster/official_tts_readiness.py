"""Read-only preflight for the saved official Korean GPT-SoVITS selection.

This does not run the server, synthesize, install models or establish rights.
"""
from __future__ import annotations

from pathlib import Path

from .original_plan_config_io import decode_official_utf8
from .original_plan_studio import check_official_project, StageOneUnavailable
from .original_plan_tts import validate_local_gpt_sovits_url


def require_saved_korean_gpt_sovits(project: str | Path) -> None:
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
    if not selected("ref_audio_path") or not selected("prompt_text"):
        raise StageOneUnavailable("실제 GPT-SoVITS 참조 음성/대사 설정이 없습니다.")
