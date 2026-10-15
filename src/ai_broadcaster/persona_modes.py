"""기본값 / 직접 제작 AI 캐릭터 로컬 선택 및 자유로운 모드 변경.

실제 외부 서비스·결제·계정 등록 없이 UI와 로컬 Ollama 프롬프트에만 사용한다.
"""
from __future__ import annotations

from copy import deepcopy
from .offline_settings import DEFAULTS, PERSONA_MODES


def validate_persona_fields(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != set(DEFAULTS["persona"]):
        raise ValueError("캐릭터는 이름·말투·성격이 필요합니다.")
    for key, text in value.items():
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 200:
            raise ValueError(f"캐릭터 {key}: 1~200글자여야 합니다.")
    return {key: value[key].strip() for key in DEFAULTS["persona"]}


def chosen_persona(mode: str, draft: dict[str, str]) -> dict[str, str]:
    """캐릭터 기본/직접 입력 선택을 명확하게 구분한다."""
    if type(mode) is not str or mode not in PERSONA_MODES.values():
        raise ValueError("캐릭터 방식은 기본 캐릭터 또는 직접 만들기 중에서 선택해야 합니다.")
    if mode == "default":
        return deepcopy(DEFAULTS["persona"])
    return validate_persona_fields(draft)


def persona_guidance(fields: dict[str, str]) -> str:
    p = validate_persona_fields(fields)
    return (
        f"너의 방송 캐릭터 이름은 '{p['name']}'이야. "
        f"캐릭터 성격: {p['character']}. "
        f"한국어 말투: {p['style']}. "
        "선택된 캐릭터를 일관되게 반영해. 실제 사람·플랫폼에 연결된 척하지 마."
    )
