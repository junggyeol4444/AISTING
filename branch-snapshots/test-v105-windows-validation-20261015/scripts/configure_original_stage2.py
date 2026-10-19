"""Original plan 7-3: integrate GPT-SoVITS into the REAL Open-LLM-VTuber.

Edits only an already-existing official Open-LLM-VTuber conf.yaml, and ONLY
when the operator invokes --apply. It never trains/clones, installs, connects
to a server, plays audio, downloads, opens OBS, or changes AISTING settings.

Upstream config reference: Open-LLM-VTuber/Open-LLM-VTuber,
config_templates/conf.default.yaml, character_config.tts_config.
Run from AISTING repository:
    python scripts/configure_original_stage2.py --project-dir PATH \
      --reference-audio YOUR_LICENSED_REFERENCE.wav \
      --reference-text "REFERENCE_AUDIO_EXACT_SPEECH"
    # inspect diff; rerun with --apply to create an exact backup and edit.
"""
from __future__ import annotations

import argparse
import difflib
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.offline_settings import active_persona, load_settings


def yaml_string(value: str) -> str:
    """Single-quoted YAML plain string. Reject control characters."""
    if not isinstance(value, str) or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError("YAML 문자열에는 개행·제어 문자를 넣을 수 없습니다.")
    return "'" + value.replace("'", "''") + "'"


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _section(lines: list[str], key: str, indent: int,
             start: int = 0, end: int | None = None) -> tuple[int, int]:
    """Locate exactly one YAML mapping child, respecting indentation."""
    stop = len(lines) if end is None else end
    found = []
    for i in range(start, stop):
        line = lines[i]
        if (_line_indent(line) == indent
                and re.match(r"^" + " " * indent + re.escape(key) + r":(?:\s|$)", line)):
            found.append(i)
    if len(found) != 1:
        raise ValueError(f"공식 Open-LLM-VTuber 설정에서 {key} 항목을 정확히 하나 찾을 수 없습니다.")
    i = found[0]
    j = i + 1
    while j < stop:
        line = lines[j]
        if line.strip() and _line_indent(line) <= indent:
            break
        j += 1
    return i, j


def _under(lines: list[str], path: tuple[tuple[str, int], ...]) -> tuple[int, int]:
    left, right = 0, len(lines)
    for label, indent in path:
        at, right = _section(lines, label, indent, left, right)
        left = at + 1
    return left, right


CHARACTER = (("character_config", 0),)
TTS = CHARACTER + (("tts_config", 2),)
GPT = TTS + (("gpt_sovits_tts", 4),)


def _set_scalar(lines: list[str], parent: tuple[tuple[str, int], ...],
                key: str, indent: int, value: str) -> None:
    lo, hi = _under(lines, parent)
    i, j = _section(lines, key, indent, lo, hi)
    # Only scalar fields are modified. Unknown/complex upstream config fails.
    if j != i + 1:
        # Blank or comment-only trailing lines may appear before next sibling.
        if any(x.strip() and not x.lstrip().startswith("#") for x in lines[i + 1:j]):
            raise ValueError(f"{key}: 단일 YAML 값이 아닙니다. 설정 변경 중단")
    lines[i] = " " * indent + key + ": " + yaml_string(value)


def _set_persona(lines: list[str], fields: dict[str, str]) -> None:
    lo, hi = _under(lines, CHARACTER)
    i, j = _section(lines, "persona_prompt", 2, lo, hi)
    for field in ("name", "character", "style"):
        if not fields.get(field) or len(fields[field]) > 200:
            raise ValueError("이름·성격·말투는 저장된 캐릭터의 유효한 값이어야 합니다.")
    prompt = [
        "너는 AI 방송인 " + fields["name"] + "이다.",
        "성격: " + fields["character"],
        "말투: " + fields["style"],
    ]
    # YAML block scalar: indentation, including operator-provided text, is
    # explicitly controlled and does not permit keys escaping to YAML fields.
    block = ["  persona_prompt: |"]
    for sentence in prompt:
        block.extend("    " + x for x in sentence.splitlines())
    lines[i:j] = block


def build_upstream_config(source: str, persona: dict[str, str],
                          reference_audio: Path, reference_text: str,
                          api_url: str = "http://127.0.0.1:9880/tts") -> str:
    """Patch the actual upstream character and TTS fields; no new fake core."""
    if not isinstance(source, str) or not source.strip():
        raise ValueError("공식 conf.yaml 파일이 비어 있습니다.")
    if not isinstance(reference_text, str) or not reference_text.strip():
        raise ValueError("참조 음성에서 실제로 말한 문장이 필요합니다.")
    if len(reference_text) > 500:
        raise ValueError("참조 문장이 너무 깁니다.")
    if api_url != "http://127.0.0.1:9880/tts":
        raise ValueError("승인되지 않은 외부 TTS 주소는 사용하지 않습니다.")
    if not reference_audio.is_file() or reference_audio.suffix.lower() not in (".wav", ".flac"):
        raise ValueError("권리가 확인된 실제 WAV/FLAC 참조 음성 파일이 필요합니다.")
    lines = source.splitlines()
    _set_scalar(lines, CHARACTER, "character_name", 2, persona["name"])
    _set_persona(lines, persona)
    _set_scalar(lines, TTS, "tts_model", 4, "gpt_sovits_tts")
    for field, value in (
        ("api_url", api_url),
        ("text_lang", "ko"),
        ("ref_audio_path", str(reference_audio.resolve())),
        ("prompt_lang", "ko"),
        ("prompt_text", reference_text.strip()),
    ):
        _set_scalar(lines, GPT, field, 6, value)
    ending = "\r\n" if "\r\n" in source else "\n"
    return ending.join(lines) + (ending if source.endswith(("\r\n", "\n")) else "")


def configure(project_dir: Path, reference_audio: Path,
              reference_text: str, *, apply: bool) -> bool:
    root = project_dir.expanduser().resolve(strict=True)
    config = root / "conf.yaml"
    if not root.is_dir() or not (root / "run_server.py").is_file():
        raise ValueError("원본 Open-LLM-VTuber 서버가 있는 프로젝트 폴더를 지정하세요.")
    if not config.is_file() or config.is_symlink():
        raise ValueError("실제 공식 conf.yaml 일반 파일이 필요합니다. 자동 생성·링크 변경 없음")
    if not reference_audio.is_file() or reference_audio.is_symlink():
        raise ValueError("본인 또는 동의·라이선스 확보된 실제 참조 음성 파일을 선택하세요.")
    if reference_audio.resolve() == config.resolve():
        raise ValueError("참조 음성과 설정 파일은 동일할 수 없습니다.")
    persona = active_persona(load_settings())
    original = config.read_bytes()
    if len(original) > 1_000_000:
        raise ValueError("conf.yaml 크기가 비정상적입니다.")
    data = original.decode("utf-8-sig")
    updated = build_upstream_config(
        data, persona, reference_audio, reference_text
    )
    if updated == data:
        print("이미 동일한 캐릭터와 GPT-SoVITS 연결 설정이 저장되어 있습니다.")
        return False
    diff = difflib.unified_diff(
        data.splitlines(keepends=True), updated.splitlines(keepends=True),
        fromfile="원본 conf.yaml", tofile="GPT-SoVITS 실제 연결 conf.yaml",
    )
    print("".join(diff))
    if not apply:
        print("\n미리보기만 수행했습니다. 승인 없는 파일 수정 없음.")
        print("실제 적용하려면 같은 명령에 --apply를 추가하세요.")
        return False
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = root / ("conf.yaml.before-aisting-" + now + ".bak")
    # A backup is mandatory, and is never overwritten.
    with backup.open("xb") as out:
        out.write(original)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("wb", prefix=".aisting-conf-",
                                         suffix=".tmp", dir=root, delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(updated.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, stat.S_IMODE(config.stat().st_mode))
        if config.read_bytes() != original or config.is_symlink():
            raise RuntimeError("설정이 작업 중 변경되었습니다. 덮어쓰지 않았습니다.")
        os.replace(temp_path, config)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    print("\n실제 공식 프로젝트의 GPT-SoVITS 연결 설정 기록:", config)
    print("변경 전 백업:", backup)
    print("실제 학습·합성·Live2D 동작은 사용자 PC에서 실행 검증이 필요합니다.")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Original plan stage 2: configure actual official Open-LLM-VTuber GPT-SoVITS"
    )
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--reference-audio", type=Path, required=True)
    parser.add_argument("--reference-text", required=True)
    parser.add_argument("--apply", action="store_true",
                        help="Explicitly edit real conf.yaml with a mandatory backup")
    args = parser.parse_args(argv)
    try:
        configure(args.project_dir, args.reference_audio,
                  args.reference_text, apply=args.apply)
    except (ValueError, OSError, UnicodeError, RuntimeError) as exc:
        print("원본 2단계 GPT-SoVITS 설정 오류: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
