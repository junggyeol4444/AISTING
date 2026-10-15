"""선택형 방송 콘텐츠 설정의 오프라인 표시 및 로컬 AI 대화 지침.

플랫폼 연결, 채팅 수집, 방송 실행과 별개인 데이터/문구만 정의한다.
"""
from __future__ import annotations

from .offline_settings import CONTENTS


CONTENT_PREVIEWS = {
    "undecided": "콘텐츠 미선택 · 언제든 선택할 수 있고 방송은 시작하지 않습니다.",
    "chat": "수다 · 시청자와 자연스럽게 이야기하는 응답 방향입니다.",
    "game": "게임 · 게임에 관한 대화를 중심으로 합니다. 실제 게임 조작은 하지 않습니다.",
    "both": "수다 + 게임 · 두 주제를 함께 다루되 실제 게임 화면은 연결하지 않습니다.",
}

CONTENT_GUIDANCE = {
    "undecided": "콘텐츠 유형은 운영자가 아직 선택하지 않았어. 수다 또는 게임으로 단정하지 마.",
    "chat": "운영자가 선택한 방송 주제는 수다야. 시청자의 대화에 자연스럽게 답해.",
    "game": "운영자가 선택한 방송 주제는 게임이야. 게임 이야기에는 답하되 실제 게임을 플레이하거나 화면을 보는 척하지 마.",
    "both": "운영자가 선택한 방송 주제는 수다와 게임 모두야. 시청자 메시지에 따라 두 주제를 자연스럽게 다뤄.",
}


def validate_content(code: str) -> str:
    """저장·설정 화면에서 사용하는 네 가지 콘텐츠 모드만 허용한다."""
    if not isinstance(code, str) or code not in CONTENTS.values():
        raise ValueError("방송 콘텐츠는 미정·수다·게임·수다 + 게임 중에서 선택해야 합니다.")
    return code


def content_preview(code: str) -> str:
    return CONTENT_PREVIEWS[validate_content(code)]


def content_guidance(code: str) -> str:
    return CONTENT_GUIDANCE[validate_content(code)]
