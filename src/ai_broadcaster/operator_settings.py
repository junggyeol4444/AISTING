"""운영자가 PC에서 선택하는 AI 방송인 설정. 외부 패키지 불필요.

사용자 설정은 공개 GitHub 저장소가 아닌 PC의 data/ 폴더에만 저장한다.
설정 저장 자체는 방송 시작·음성 복제·외부 계정 연결을 수행하지 않는다.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def default_settings_path() -> Path:
    """Windows EXE의 임시 폴더가 아닌 사용자 데이터 폴더에 저장."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Local") / "AISTING" / "operator_settings.json"
    return ROOT / "data" / "operator_settings.json"


DEFAULT_FILE = default_settings_path()

PLATFORMS = ("chzzk", "youtube", "twitch")
CONTENTS = ("undecided", "chat", "game", "both")
VOICES = ("undecided", "local_basic", "own_recording", "licensed_recording")
AVATARS = ("undecided", "2d", "3d")

DEFAULT_SETTINGS: dict[str, Any] = {
    "platforms": [],
    "content": "undecided",
    "persona": {
        "mode": "default",
        "name": "아이스팅",
        "gender": "미정",
        "traits": "친근함, 호기심, 활발함",
        "speech_style": "자연스러운 한국어",
    },
    "voice": "undecided",
    "avatar": "undecided",
    "operation": {
        "host": "local_pc",
        "budget_mode": "free_only",
        "allow_paid_api": False,
        "allow_paid_assets": False,
        "allow_external_broadcast": False,
        "allow_voice_cloning": False,
    },
}


class SettingsError(ValueError):
    """사용자 입력이 프로젝트 요구사항에 맞지 않을 때 발생."""


def default_settings() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_SETTINGS)


def _object_has_exact_keys(value: object, expected: dict[str, Any], name: str) -> None:
    if not isinstance(value, dict) or set(value) != set(expected):
        raise SettingsError(f"{name}: 설정 필드가 올바르지 않습니다.")


def validate_settings(value: object) -> dict[str, Any]:
    """미선택 상태를 허용하면서 유료 연동과 무단 외부 작업은 금지한다."""
    _object_has_exact_keys(value, DEFAULT_SETTINGS, "설정")
    assert isinstance(value, dict)
    platforms = value["platforms"]
    if (not isinstance(platforms, list)
            or len(platforms) != len(set(map(str, platforms)))
            or any(x not in PLATFORMS for x in platforms)):
        raise SettingsError("방송 플랫폼 선택이 잘못됐습니다.")
    if value["content"] not in CONTENTS:
        raise SettingsError("방송 콘텐츠 선택이 잘못됐습니다.")
    if value["voice"] not in VOICES:
        raise SettingsError("목소리 선택이 잘못됐습니다.")
    if value["avatar"] not in AVATARS:
        raise SettingsError("아바타 선택이 잘못됐습니다.")

    persona = value["persona"]
    _object_has_exact_keys(persona, DEFAULT_SETTINGS["persona"], "캐릭터")
    if persona["mode"] not in ("default", "custom"):
        raise SettingsError("캐릭터 모드는 기본값 또는 직접 설정만 가능합니다.")
    for key in ("name", "gender", "traits", "speech_style"):
        text = persona[key]
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 100:
            raise SettingsError(f"캐릭터 {key}는 1~100글자로 입력해 주세요.")

    operation = value["operation"]
    _object_has_exact_keys(operation, DEFAULT_SETTINGS["operation"], "운영")
    # 사용자가 승인한 것은 PC 전용 및 무료 이용 정책이다.
    for key in ("host", "budget_mode"):
        if operation[key] != DEFAULT_SETTINGS["operation"][key]:
            raise SettingsError("PC 실행 및 무료 운영 정책은 변경할 수 없습니다.")
    for key in ("allow_paid_api", "allow_paid_assets",
                "allow_external_broadcast", "allow_voice_cloning"):
        if operation[key] is not False:
            raise SettingsError(f"{key}: 해당 실행은 승인되지 않았습니다.")
    return copy.deepcopy(value)


def load_settings(path: Path = DEFAULT_FILE) -> dict[str, Any]:
    if not path.exists():
        return default_settings()
    with path.open("r", encoding="utf-8") as f:
        return validate_settings(json.load(f))


def save_settings(value: object, path: Path = DEFAULT_FILE) -> dict[str, Any]:
    """유효성 확인 후 임시 파일과 원자적 교체로 안전하게 저장."""
    valid = validate_settings(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".operator_", suffix=".tmp", delete=False
        ) as f:
            temp_path = f.name
            os.chmod(temp_path, 0o600)
            json.dump(valid, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
    return valid
