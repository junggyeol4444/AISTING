"""Original roadmap 035: basic chat reaction coverage in an isolated mock session.

No accounts, network, filesystem, timers, installed-model detection or OS inquiry.
This tests delivery bookkeeping, not human-like response quality or moderation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .core_execution import OfflineCoreSession, MockCoreReplyPort, LocalReplyPort
from .core_ports import CoreInput, CoreReply
from .offline_chat import parse_script

SAMPLE_REACTION_SCRIPT = (
    "별: 안녕!\n"
    "달: ㅋㅋㅋ\n"
    "별: 안녕!\n"
    "구름: 오늘 뭐 해?\n"
    "바람: 고마워 😊\n"
    "해: 처음 왔어요!"
)
MAX_REACTION_TURNS = 30
MAX_REACTION_SCRIPT = 10000


class _CaptureReplyPort:
    """Instrument history size/order without changing or delaying the reply port."""

    def __init__(self, wrapped: LocalReplyPort):
        self.wrapped = wrapped
        self.calls: list[tuple[CoreInput, tuple[CoreReply, ...]]] = []

    def generate(self, item: CoreInput, history: Sequence[CoreReply]) -> str:
        self.calls.append((item, tuple(history)))
        return self.wrapped.generate(item, history)


@dataclass(frozen=True)
class ReactionCheck:
    sender: str
    input_text: str
    reply: str
    checked: bool
    context_count: int
    reason: str = ""


@dataclass(frozen=True)
class BasicReactionReport:
    checks: tuple[ReactionCheck, ...]
    total: int
    remaining: int
    attempts: int
    stopped_reason: str = ""

    @property
    def passed(self) -> bool:
        return (self.total > 0 and not self.stopped_reason and self.remaining == 0
                and self.attempts == self.total and len(self.checks) == self.total
                and all(item.checked for item in self.checks))

    @property
    def passed_count(self) -> int:
        return sum(item.checked for item in self.checks)

    def describe(self) -> str:
        lines = [
            "원본 계획 35단계 · 기본 대화 반응 검사 (오프라인 모의 전용)",
            f"{'구조 검사 통과' if self.passed else '구조 검사 실패'} · 답변 {self.passed_count}/{self.total}건 · 남은 채팅 {self.remaining}건 · 포트 호출 {self.attempts}회",
            "모든 입력 순서대로 1회씩 응답 · 동일 채팅도 별도 보존 · 최근 8건 맥락 전달 검사",
            "기본적으로 채팅 선택/버리기·인위적 대기 시간을 추가하지 않음 (응답 속도 실제 측정은 아님)",
            "실제 AI의 의미 이해·자연스러움·캐릭터 적합성·방송 성능은 검증하지 않음",
            "설정/SQLite/파일 저장·PC 정보 조회·로컬 모델/네트워크/OBS 접근 없음",
        ]
        if self.stopped_reason:
            lines.append("중단: " + self.stopped_reason)
        for index, turn in enumerate(self.checks, 1):
            lines.append(f"[{index}] {'통과' if turn.checked else '실패'} · {turn.sender}: {turn.input_text[:120]} · 맥락 {turn.context_count}건\n"
                         f"모의 응답: {turn.reply[:200]}" + ("\n원인: " + turn.reason if turn.reason else ""))
        return "\n\n".join(lines)


def run_basic_reaction_test(settings: Mapping[str, object], script: str = SAMPLE_REACTION_SCRIPT,
                            *, reply_port: LocalReplyPort | None = None) -> BasicReactionReport:
    """Operator-triggered, non-persistent, deterministic all-chat coverage test."""
    if type(script) is not str or len(script) > MAX_REACTION_SCRIPT:
        raise ValueError(f"시험 대본은 {MAX_REACTION_SCRIPT}자 이하의 문자열이어야 합니다.")
    messages = parse_script(script)
    if len(messages) > MAX_REACTION_TURNS:
        raise ValueError(f"한 번에 최대 {MAX_REACTION_TURNS}개 채팅만 시험할 수 있습니다.")
    # Validate first; each call uses its own isolated session and port.
    capture = _CaptureReplyPort(reply_port if reply_port is not None else MockCoreReplyPort())
    session = OfflineCoreSession(dict(settings), reply_port=capture)
    session.enqueue(script)
    checked: list[ReactionCheck] = []
    failure = ""
    for index, expected in enumerate(messages):
        try:
            reply = session.process_one()
        except Exception:
            # Do not leak arbitrary model error text, paths or tokens.
            failure = f"{index + 1}번째 모의 응답 오류 · 실패 채팅은 대기열에 보존됨 (자동 재시도 없음)"
            break
        if reply is None:
            failure = f"{index + 1}번째 입력이 응답 없이 누락됨"
            break
        call_input, context = capture.calls[-1]
        right_order = (reply.input.sender == expected.sender and reply.input.text == expected.text
                       and call_input.sender == expected.sender and call_input.text == expected.text)
        expected_context = session.history[max(0, len(session.history) - 9):-1]
        right_context = context == expected_context and len(context) == min(index, 8)
        nonempty = type(reply.text) is str and bool(reply.text.strip())
        ok = right_order and right_context and nonempty
        checked.append(ReactionCheck(expected.sender, expected.text, reply.text, ok, len(context),
                     "" if ok else "응답 원문/순서·맥락 또는 내용 구조 불일치"))
    return BasicReactionReport(tuple(checked), len(messages), session.pending_count,
                               len(capture.calls), failure)
