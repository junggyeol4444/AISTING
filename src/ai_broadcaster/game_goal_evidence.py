"""운영자 목표의 OBS 실제 게임 화면 근거를 보수적으로 분류.

로컬 시각 AI가 반환한 두 시점의 설명과 운영자 목표를 기존 로컬
Ollama에 전달해 엄격한 JSON을 받는다. 이는 'AI가 추정한 목표 후보'
일 뿐 게임 내부 상태/API, 실제 보상, 플랫폼 시청자 수신을 증명하지
않는다. 자동 게임 재시작·실제 입력·OBS/계정 조작은 수행하지 않는다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

from .local_llm import LocalModelConfig, LocalOllamaReplyGenerator
from .offline_settings import active_persona, load_settings as load_gui_settings
from .operator_settings import load_settings as load_operator_settings
from .session import ChatMessage


@dataclass(frozen=True)
class GameGoalEvidence:
    status: str
    evidence: str
    source: str = "로컬 AI가 설명한 OBS 화면 두 시점 · 실제 게임 내부 결과 미확인"


def parse_goal_evidence(reply: str) -> GameGoalEvidence:
    if type(reply) is not str or not 2 <= len(reply) <= 1200:
        raise ValueError("게임 목표 판정 응답 길이가 올바르지 않습니다.")
    data = json.loads(reply)
    if type(data) is not dict or set(data) != {"status", "evidence"}:
        raise ValueError("게임 목표 판정은 status/evidence JSON만 허용됩니다.")
    status, evidence = data["status"], data["evidence"]
    if status not in ("진행중", "달성후보", "불확실"):
        raise ValueError("게임 목표 판정 상태가 올바르지 않습니다.")
    if (type(evidence) is not str or not 1 <= len(evidence.strip()) <= 300
            or any(ord(c) < 32 or ord(c) == 127 for c in evidence)):
        raise ValueError("화면 근거 설명이 올바르지 않습니다.")
    return GameGoalEvidence(status, evidence.strip())


def assess_game_goal_from_two_observations(
    *, goal: str, before: str, after: str, model: str,
) -> GameGoalEvidence:
    """모델은 운영자가 이미 선택한 localhost Ollama 모델만 사용."""
    if not all(type(v) is str and v.strip() for v in (goal, before, after, model)):
        raise ValueError("게임 목표/두 화면/기존 모델 입력이 필요합니다.")
    settings = load_operator_settings()
    persona = active_persona(load_gui_settings())
    settings["persona"]["name"] = persona["name"]
    settings["persona"]["traits"] = persona["character"]
    settings["persona"]["speech_style"] = persona["style"]
    generator = LocalOllamaReplyGenerator(
        LocalModelConfig(model=model), settings, memory=None)
    generator.system = (
        "당신은 기존 로컬 게임 화면 관찰의 목표 상태 분류 담당입니다. "
        "게임 내부 API나 보상 확인이 아닌 AI의 화면 추정임을 유지하세요. "
        "서로 다른 두 시점의 화면 설명에 목표 완료의 명확한 근거가 "
        "모두 있을 때에만 달성후보를 선택하세요. 불명확하면 불확실. "
        "JSON 객체 한 개만 출력하세요: "
        '{"status":"진행중","evidence":"화면에 보이는 근거"}, '
        '{"status":"달성후보","evidence":"두 시점에서 공통 확인된 표시"}, '
        '{"status":"불확실","evidence":"불확실한 이유"}. '
        "이외 문장/코드/마크다운 출력 금지."
    )
    prompt = (
        f"운영자 게임 목표: {goal[:300]}\n"
        f"이전 실제 OBS 화면 관찰: {before[:1500]}\n"
        f"이후 실제 OBS 화면 관찰: {after[:1500]}\n"
        "화면 설명 외의 추측 없이 JSON 판정 하나만 반환하세요."
    )
    reply = generator.generate(ChatMessage(
        str(uuid4()), "게임 목표 화면 근거", prompt))
    return parse_goal_evidence(reply)
