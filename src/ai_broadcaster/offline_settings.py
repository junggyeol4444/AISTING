"""AISTING operator configuration for local, free-only Windows desktop use.

Never initiates installation, charge, streaming, login, or cloud connections.
"""
from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "platforms": [],
    "content": "undecided",
    "avatar": "undecided",
    "voice": "undecided",
    "voice_profile": {"installed_voice_name": "", "rate": 0, "volume": 85},
    "persona_mode": "default",
    "persona": {
        "name": "아이스팅", "style": "친근하고 명확한 한국어",
        "character": "호기심 많은 AI 방송인",
    },
    "host": "local_pc",
    "budget": "free_only",
    "streaming_enabled": False,
    "scheduled_execution": False,
    "external_publish_enabled": False,
}
PERSONA_MODES = {"기본 캐릭터": "default", "직접 만들기": "custom"}
PLATFORMS = {"치지직": "chzzk", "유튜브": "youtube", "트위치": "twitch"}
CONTENTS = {"미정": "undecided", "수다": "chat", "게임": "game", "수다 + 게임": "both"}
AVATARS = {"미정": "undecided", "2D": "2d", "3D": "3d"}
# 7단계: 방식만 선택. 녹음·학습/복제는 반드시 별도 동의와 PC 설치 승인 후에만.
VOICES = {
    "미정": "undecided",
    "Windows 무료 음성": "windows_system",
    "내 목소리 (추후 직접 녹음)": "own_recording",
    "동의받은 목소리 (추후 확보)": "consented_recording",
    "라이선스 확보 목소리 (추후 확보)": "licensed_recording",
}


def validate_voice_profile(value: Any) -> dict[str, Any]:
    """이미 설치된 OS TTS의 선택값만 저장. 녹음/음성 학습 권한을 뜻하지 않는다."""
    if not isinstance(value, dict) or set(value) != {"installed_voice_name", "rate", "volume"}:
        raise ValueError("Windows 음성 선택 정보 형식이 잘못됐습니다.")
    name = value["installed_voice_name"]
    if (not isinstance(name, str) or len(name) > 160 or "\x00" in name
            or any(ord(char) < 32 for char in name)):
        raise ValueError("설치된 한국어 음성 이름이 올바르지 않습니다.")
    if type(value["rate"]) is not int or not -4 <= value["rate"] <= 4:
        raise ValueError("음성 속도는 -4~4로 선택해 주세요.")
    if type(value["volume"]) is not int or not 0 <= value["volume"] <= 100:
        raise ValueError("음량은 0~100으로 선택해 주세요.")
    return deepcopy(value)



def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else None
    return (Path(base) / "AISTING") if base else (Path.home() / ".aisting")


def settings_file() -> Path:
    return data_dir() / "settings.json"


def validate_settings(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("설정은 JSON 객체여야 합니다.")
    if set(value) != set(DEFAULTS):
        raise ValueError("설정 필드 구성이 올바르지 않습니다.")
    for field in ("host", "budget", "streaming_enabled", "scheduled_execution", "external_publish_enabled"):
        if type(value[field]) is not type(DEFAULTS[field]) or value[field] != DEFAULTS[field]:
            raise ValueError(f"승인받지 않은 실행 설정입니다: {field}")
    platforms = value["platforms"]
    if not isinstance(platforms, list) or len(platforms) != len(set(map(str, platforms))):
        raise ValueError("플랫폼 목록이 잘못됐습니다.")
    if any(p not in PLATFORMS.values() for p in platforms):
        raise ValueError("지원하지 않는 플랫폼입니다.")
    for field, choices in (("content", CONTENTS), ("avatar", AVATARS), ("voice", VOICES), ("persona_mode", PERSONA_MODES)):
        if value[field] not in choices.values():
            raise ValueError(f"지원하지 않는 선택: {field}")
    validate_voice_profile(value["voice_profile"])
    p = value["persona"]
    if not isinstance(p, dict) or set(p) != {"name", "style", "character"}:
        raise ValueError("캐릭터 정보 형식이 잘못됐습니다.")
    for key in p:
        if not isinstance(p[key], str) or not 1 <= len(p[key].strip()) <= 200:
            raise ValueError("캐릭터 이름·설정·말투는 1~200자여야 합니다.")
    return deepcopy(value)


def active_persona(value: dict[str, Any]) -> dict[str, str]:
    """기본 모드에서는 저장된 직접 입력값이 아니라 기본 캐릭터를 사용한다."""
    checked = validate_settings(value)
    choice = DEFAULTS["persona"] if checked["persona_mode"] == "default" else checked["persona"]
    return deepcopy(choice)


def _migrate_legacy_v05(value: Any) -> Any:
    """기존 v05 개인 설정을 삭제하지 않고 선택 모드만 보강한다.

    v05에는 모드 필드가 없으므로 기본값과 다른 직접 입력값이 존재하면
    custom으로 옮긴다. 그 외 설정 필드가 없거나 예상 못한 값이면 검증이 거부한다.
    """
    if (isinstance(value, dict) and "persona_mode" not in value and
        set(value) in (set(DEFAULTS) - {"persona_mode"}, set(DEFAULTS) - {"persona_mode", "voice_profile"})):
        value = deepcopy(value)
        value["persona_mode"] = (
            "default" if value.get("persona") == DEFAULTS["persona"] else "custom"
        )
    return value


def _migrate_legacy_voice(value: Any) -> Any:
    """v07 및 이전 로컬 설정에 새 음성 프리셋만 추가. 알 수 없는 키는 그대로 거부."""
    if isinstance(value, dict) and "voice_profile" not in value and set(value) == set(DEFAULTS) - {"voice_profile"}:
        value = deepcopy(value)
        value["voice_profile"] = deepcopy(DEFAULTS["voice_profile"])
    return value


def load_settings(path: Path | None = None) -> dict[str, Any]:
    target = path if path is not None else settings_file()
    if not target.exists():
        return deepcopy(DEFAULTS)
    with target.open("r", encoding="utf-8") as fh:
        return validate_settings(_migrate_legacy_voice(_migrate_legacy_v05(json.load(fh))))


def save_settings(value: dict[str, Any], path: Path | None = None) -> Path:
    target = path if path is not None else settings_file()
    clean = validate_settings(value)
    target.parent.mkdir(parents=True, exist_ok=True)
    # A fixed settings.tmp path can overwrite an unrelated file (or follow a
    # symlink) and concurrent saves can corrupt each other's temporary data.
    # Create a private, unique sibling and replace only after a full flush.
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=f".{target.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(clean, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
