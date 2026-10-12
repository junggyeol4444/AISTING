"""윈도우 데스크톱 UI 선택값의 변환과 무료·PC 전용 검증."""
from __future__ import annotations
from typing import Any
from .operator_settings import DEFAULT_SETTINGS, validate_settings

PLATFORM_LABELS = {"치지직": "chzzk", "유튜브": "youtube", "트위치": "twitch"}
CONTENT_LABELS = {"나중에 선택": "undecided", "수다 방송": "chat", "게임 방송": "game", "수다 + 게임": "both"}
VOICE_LABELS = {"나중에 선택": "undecided", "무료 로컬 기본 음성": "local_basic", "본인 목소리": "own_recording", "허락받은 목소리": "licensed_recording"}
AVATAR_LABELS = {"나중에 선택": "undecided", "2D": "2d", "3D": "3d"}
PERSONA_LABELS = {"기본값 사용": "default", "직접 만들기": "custom"}

def label_for(options: dict[str, str], value: str) -> str:
    return next(label for label, code in options.items() if code == value)

def from_screen(
    existing: dict[str, Any], *,
    platforms: list[str], content: str, persona_mode: str,
    persona_fields: dict[str, str], voice: str, avatar: str,
) -> dict[str, Any]:
    saved = validate_settings(existing)
    if len(platforms) != len(set(platforms)) or any(label not in PLATFORM_LABELS for label in platforms):
        raise ValueError("방송 플랫폼 선택을 확인해 주세요.")
    for options, label in (
        (CONTENT_LABELS, content), (PERSONA_LABELS, persona_mode),
        (VOICE_LABELS, voice), (AVATAR_LABELS, avatar),
    ):
        if label not in options:
            raise ValueError("알 수 없는 설정 선택입니다.")
    result = saved.copy()
    result["platforms"] = [PLATFORM_LABELS[label] for label in platforms]
    result["content"] = CONTENT_LABELS[content]
    result["voice"] = VOICE_LABELS[voice]
    result["avatar"] = AVATAR_LABELS[avatar]
    if PERSONA_LABELS[persona_mode] == "default":
        result["persona"] = DEFAULT_SETTINGS["persona"].copy()
    else:
        keys = {"name", "gender", "traits", "speech_style"}
        if not isinstance(persona_fields, dict) or set(persona_fields) != keys:
            raise ValueError("캐릭터 항목이 누락되었습니다.")
        if not all(isinstance(x, str) for x in persona_fields.values()):
            raise ValueError("캐릭터는 문자로 입력해야 합니다.")
        result["persona"] = {"mode": "custom", **{k: v.strip() for k,v in persona_fields.items()}}
    # 기존 승인 금지 정책을 바꾸지 않는다.
    return validate_settings(result)
