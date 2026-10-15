"""6단계: 운영자가 원하는 성격·말투 '초안'을 직접 편집하는 보조 도구.

예시는 선택 전 적용되지 않으며 기본 캐릭터/닉네임/외부 정책을 임의 변경하지 않는다.
인터넷 요청, LLM 호출, 사운드 출력, 자동 방송을 절대 수행하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass

from .persona_modes import chosen_persona, persona_guidance, validate_persona_fields


@dataclass(frozen=True)
class DraftExample:
    personality: str
    speech_style: str
    explanation: str


# 고정 방송 컨셉이 아니라 운영자가 참고해 자유롭게 수정하는 예시 문구다.
EXAMPLE_DRAFTS: dict[str, DraftExample] = {
    "차분한 설명형 (예시)": DraftExample(
        "차분하고 호기심이 많으며 질문을 들은 뒤 핵심을 이해하기 쉽게 설명함",
        "존댓말 위주로 명료하게 답하며, 필요한 경우 쉬운 예시를 덧붙임",
        "설명을 짧고 친절하게 이어가는 초안",
    ),
    "활기찬 소통형 (예시)": DraftExample(
        "밝고 다정하며 시청자와의 대화를 즐기되 특정 메시지를 선별하지 않음",
        "가벼운 감탄과 자연스러운 한국어를 사용하되 과한 반복을 피함",
        "분위기 좋은 수다를 위한 초안",
    ),
    "담백한 게임형 (예시)": DraftExample(
        "침착하고 집중력이 좋으며 게임 상황을 함께 이해하려고 노력함",
        "짧고 명확하게 반응하며 긴 설명이 필요할 때만 자세히 말함",
        "게임 중 과도한 대사 없이 반응하는 초안",
    ),
}


def apply_draft_example(fields: dict[str, str], example_name: str) -> dict[str, str]:
    """운영자가 버튼을 누를 때만 성격·말투 입력란 변경; 이름은 항상 보존."""
    if not isinstance(example_name, str) or example_name not in EXAMPLE_DRAFTS:
        raise ValueError("예시 초안을 선택해 주세요.")
    if not isinstance(fields, dict) or set(fields) != {"name", "style", "character"}:
        raise ValueError("캐릭터 입력 항목이 맞지 않습니다.")
    # 예시 적용 과정에서도 기존 잘못된 이름/필드를 조용히 고치지 않는다.
    checked = validate_persona_fields(fields)
    example = EXAMPLE_DRAFTS[example_name]
    checked["character"] = example.personality
    checked["style"] = example.speech_style
    return validate_persona_fields(checked)


def preview_persona_guidance(mode: str, fields: dict[str, str]) -> str:
    """실제 Ollama에 전달할 캐릭터 핵심 지침을 연결 없이 문자열로 확인."""
    persona = chosen_persona(mode, fields)
    return persona_guidance(persona)


def compact_persona_preview(mode: str, fields: dict[str, str], max_field: int = 68) -> str:
    """상단 설정 화면용 간결한 미리보기. LLM 생성물이라고 주장하지 않음."""
    if type(max_field) is not int or not 10 <= max_field <= 200:
        raise ValueError("미리보기 글자 수는 10~200 범위여야 합니다.")
    selected = chosen_persona(mode, fields)

    def clip(text: str) -> str:
        return text if len(text) <= max_field else text[:max_field-1] + "…"

    return (
        f"적용 이름: {clip(selected['name'])}\n"
        f"성격 초안: {clip(selected['character'])}\n"
        f"말투 초안: {clip(selected['style'])}\n"
        "※ 실제 AI가 생성한 대사는 아닙니다. 로컬 AI 설정 미리보기입니다."
    )
