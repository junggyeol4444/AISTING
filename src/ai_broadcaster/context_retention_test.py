"""26단계: 승인 없는 메모리 전용 대화 맥락 전달 계약 회귀 시험.

'맥락 이해'를 평가하지 않는다. 독립 모의 포트가 받은 이력이 직전 최대
8건의 실제 처리 결과와 정확히 일치하는지 검증한다. 파일/장치/네트워크 없음.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .core_execution import MAX_CONTEXT_TURNS, LocalReplyPort, OfflineCoreSession
from .core_ports import CoreInput, CoreReply
from .offline_chat import parse_script

MAX_CONTEXT_TEST_TURNS = 30
MAX_CONTEXT_SCRIPT = 10000
SAMPLE_CONTEXT_SCRIPT = (
    "가람: 제 별명은 은하예요.\n"
    "누리: 오늘은 어떤 주제로 이야기하나요?\n"
    "가람: 방금 말한 제 별명은 뭐였죠?\n"
    "누리: 오늘은 어떤 주제로 이야기하나요?\n"
    "가람: 이전 질문이 두 번 나왔나요?\n"
    "다온: 앞선 대화가 순서대로 남아 있나요?\n"
    "가람: 마지막으로 제 별명을 다시 물어볼게요.\n"
    "누리: 대화는 몇 번 이어졌나요?\n"
    "가람: 앞에서 한 말도 기록되나요?\n"
    "누리: 오래된 맥락은 잘리는지 확인해요.\n"
    "가람: 마지막 질문입니다."
)


class ContextWitnessPort:
    """오직 전달받은 맥락만 관찰하는 모의 포트. AI 이해력과 무관."""

    def __init__(self) -> None:
        self.calls: list[tuple[CoreInput, tuple[CoreReply, ...]]] = []

    def generate(self, item: CoreInput, history: tuple[CoreReply, ...]) -> str:
        snapshot = tuple(history)
        self.calls.append((item, snapshot))
        previous = snapshot[-1].input.text if snapshot else "(첫 대화)"
        # 서로 같은 입력도 순서를 식별할 수 있도록 일련번호를 응답에 포함.
        return f"모의 응답 {len(self.calls)}: 직전 입력={previous} / 현재 입력={item.text}"


@dataclass(frozen=True)
class ContextTurnCheck:
    index: int
    sender: str
    history_count: int
    expected_count: int
    passed: bool
    reason: str = ""


@dataclass(frozen=True)
class ContextRetentionReport:
    turns: tuple[ContextTurnCheck, ...]
    total: int
    remaining: int
    error: str = ""

    @property
    def passed_count(self) -> int:
        return sum(turn.passed for turn in self.turns)

    @property
    def passed(self) -> bool:
        return (self.total >= 2 and not self.error and self.remaining == 0
                and len(self.turns) == self.total and self.passed_count == self.total)

    @property
    def window_boundary_checked(self) -> bool:
        return len(self.turns) > MAX_CONTEXT_TURNS + 1

    def describe(self) -> str:
        lines = [
            "26단계 · 대화 맥락 전달 구조 시험 (오프라인 모의 전용)",
            f"판정: {'구조 통과' if self.passed else '구조 실패'} · {self.passed_count}/{self.total}건 · 대기 {self.remaining}건",
            f"검사: 직전 최대 {MAX_CONTEXT_TURNS}건의 입력·응답 순서/중복/잘림, 매 응답 직전의 스냅샷",
            "이력 상한 초과 검사: " + ("실행됨" if self.window_boundary_checked else "미실행 (10건 이상 대본 필요)"),
            "주의: 모의 포트의 맥락 '전달'만 확인. 실제 AI의 기억·의미 이해·대명사 해석·장기 맥락 품질은 미검증.",
            "기존 설정·SQLite·PC 정보·네트워크·Ollama·OBS·방송 접근 없음 · 공식 9/100",
            "실제 Windows/로컬 AI 맥락 검증은 사용자 승인 대기",
        ]
        if self.error:
            lines.append("중단 원인: " + self.error)
        for turn in self.turns:
            lines.append(f"[{turn.index}] {'통과' if turn.passed else '실패'} · {turn.sender} · "
                         f"전달 이력 {turn.history_count}/{turn.expected_count}건"
                         + (f" · {turn.reason}" if turn.reason else ""))
        return "\n\n".join(lines)


def run_context_retention_test(
    settings: Mapping[str, object], script: str = SAMPLE_CONTEXT_SCRIPT,
    *, session_factory: Callable[..., OfflineCoreSession] = OfflineCoreSession,
    reply_port: LocalReplyPort | None = None,
) -> ContextRetentionReport:
    """기존 코어/사용자 데이터를 건드리지 않고 새 모의 세션의 이력 전달을 확인.

    session_factory/reply_port는 회귀 테스트의 결함 주입 전용이다.
    """
    if type(script) is not str or len(script) > MAX_CONTEXT_SCRIPT:
        raise ValueError(f"대본은 {MAX_CONTEXT_SCRIPT}자 이하 문자열이어야 합니다.")
    parsed = parse_script(script)
    if not 2 <= len(parsed) <= MAX_CONTEXT_TEST_TURNS:
        raise ValueError(f"맥락 시험은 2~{MAX_CONTEXT_TEST_TURNS}건이 필요합니다.")
    witness = reply_port if reply_port is not None else ContextWitnessPort()
    # 기본 포트는 모든 호출을 기록. 테스트용 주입 포트도 calls 계약을 충족해야 한다.
    if not isinstance(witness, ContextWitnessPort):
        raise TypeError("맥락 시험은 기록 가능한 ContextWitnessPort를 사용해야 합니다.")
    session = session_factory(dict(settings), reply_port=witness)
    session.enqueue(script)
    checks: list[ContextTurnCheck] = []
    processed: list[CoreReply] = []
    error = ""
    for i, expected_input in enumerate(parsed, 1):
        try:
            reply = session.process_one()
        except Exception as exc:
            error_kind = "ValueError" if isinstance(exc, ValueError) else "RuntimeError" if isinstance(exc, RuntimeError) else type(exc).__name__
            error = f"모의 처리 중단 ({error_kind}): {exc}"
            break
        if reply is None:
            error = "입력이 예정보다 일찍 소진되었습니다."
            break
        processed.append(reply)
        expected_history = tuple(processed[:-1][-MAX_CONTEXT_TURNS:])
        if len(witness.calls) < i:
            checks.append(ContextTurnCheck(i, expected_input.sender, -1, len(expected_history),
                                           False, "응답 포트 호출 기록 없음"))
            continue
        seen_input, seen_history = witness.calls[i - 1]
        same_input = (seen_input.sender == expected_input.sender
                      and seen_input.text == expected_input.text
                      and reply.input == seen_input)
        same_history = seen_history == expected_history
        valid_reply = (type(reply.text) is str and bool(reply.text.strip())
                       and reply.text.startswith(f"모의 응답 {i}:"))
        ok = same_input and same_history and valid_reply
        reason = ("" if ok else "입력 순서/원문 불일치" if not same_input else
                  "전달된 이전 이력/순서/잘림 불일치" if not same_history else "응답 식별 불일치")
        checks.append(ContextTurnCheck(i, expected_input.sender, len(seen_history),
                                       len(expected_history), ok, reason))
    if len(witness.calls) != len(processed) and not error:
        error = "응답 포트 호출 횟수가 처리 건수와 다릅니다."
    return ContextRetentionReport(tuple(checks), len(parsed), session.pending_count, error)
