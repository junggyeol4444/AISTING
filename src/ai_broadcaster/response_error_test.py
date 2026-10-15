"""27단계: 오류를 의도적으로 주입하는 완전 오프라인 응답 복구 회귀 시험.

모의 코어의 실패 분류, FIFO/이력 불변, 명시적 재시도/제외를 확인한다.
실제 모델/네트워크/설정/SQLite/PC 장치에는 접근하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .core_execution import (
    MAX_REPLY, CoreBatchError, CoreRetryLimitError, OfflineCoreSession,
)

SCENARIOS = (
    "timeout", "connection", "generation", "invalid_type",
    "empty_reply", "oversized_reply", "retry_limit", "partial_batch",
)
SCENARIO_LABELS = {
    "timeout": "시간 초과 후 수동 재시도",
    "connection": "모의 포트 연결 오류 후 재시도",
    "generation": "답변 생성 예외 후 재시도",
    "invalid_type": "문자열 아닌 응답 차단",
    "empty_reply": "빈 응답 차단",
    "oversized_reply": "응답 길이 초과 차단",
    "retry_limit": "3회 시도 상한과 확인 후 제외",
    "partial_batch": "일부 성공 후 실패/복구 순서",
}


class FaultPort:
    """주어진 출력/예외만 순서대로 반환하는 독립 모의 포트."""

    def __init__(self, outcomes: tuple[object, ...]):
        self.outcomes = outcomes
        self.calls = 0

    def generate(self, item, history):
        index = self.calls
        self.calls += 1
        outcome = self.outcomes[index] if index < len(self.outcomes) else "복구된 모의 답변"
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@dataclass(frozen=True)
class ResponseErrorCheck:
    code: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ResponseErrorReport:
    checks: tuple[ResponseErrorCheck, ...]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    @property
    def passed_count(self) -> int:
        return sum(check.passed for check in self.checks)

    def describe(self) -> str:
        lines = [
            "27단계 · 기본 응답 오류 처리 (독립 오프라인 모의 포트)",
            f"결과: {'통과' if self.passed else '실패'} {self.passed_count}/{len(self.checks)} 시나리오",
            "오류 분류·실패 입력 보존·순서 유지·명시적 수동 재시도·3회 상한·확인 후 제외 검사",
            "실제 Ollama/모델 연결·응답 품질·Windows 실기기 검증은 수행하지 않았습니다.",
            "설정/SQLite/PC 조회/파일 저장/네트워크/방송 없음 · 10단계 승인 대기 · 공식 9/100",
        ]
        for check in self.checks:
            lines.append(f"[{'통과' if check.passed else '실패'}] {SCENARIO_LABELS[check.code]}: {check.detail}")
        return "\n\n".join(lines)


def _run_scenario(settings: Mapping[str, object], code: str,
                  session_factory: Callable[..., OfflineCoreSession]) -> ResponseErrorCheck:
    """결함을 관찰하지 못하면 통과시키지 않는다."""
    faults = {
        "timeout": (TimeoutError("비밀 원문: token=abc"), "복구 답변"),
        "connection": (ConnectionError("비밀 원문: token=abc"), "복구 답변"),
        "generation": (RuntimeError("비밀 원문: token=abc"), "복구 답변"),
        "invalid_type": (object(), "복구 답변"),
        "empty_reply": ("  ", "복구 답변"),
        "oversized_reply": ("가" * (MAX_REPLY + 1), "복구 답변"),
        "retry_limit": (TimeoutError("private"), TimeoutError("private"),
                        TimeoutError("private")),
        "partial_batch": ("첫 답변", TimeoutError("private"), "둘째 답변", "셋째 답변"),
    }
    expected = {
        "timeout": "timeout", "connection": "connection", "generation": "generation",
        "invalid_type": "invalid_type", "empty_reply": "empty_reply",
        "oversized_reply": "oversized_reply", "retry_limit": "timeout",
        "partial_batch": "timeout",
    }
    port = FaultPort(faults[code])
    session = session_factory(dict(settings), reply_port=port)
    script = ("가: 첫 입력\n나: 두 번째 입력\n다: 세 번째 입력" if code == "partial_batch"
              else "가: 실패 입력\n나: 다음 입력")
    session.enqueue(script)
    try:
        session.run_batch(3)
        return ResponseErrorCheck(code, False, "결함이 있었는데 오류가 감지되지 않았습니다.")
    except CoreBatchError as exc:
        failure = session.last_failure
        expected_processed = 1 if code == "partial_batch" else 0
        expected_remaining = 2 if code == "partial_batch" else 2
        safe = ("token=abc" not in str(exc) and "private" not in str(exc)
                and "token=abc" not in (failure.message if failure else ""))
        if not (failure and failure.code == expected[code] and failure.attempts == 1
                and exc.failure == failure and len(exc.processed) == expected_processed
                and session.pending_count == expected_remaining
                and len(session.history) == expected_processed and safe):
            return ResponseErrorCheck(code, False, "실패 분류/보존/민감 원문 차단 검증 실패")
    if code == "retry_limit":
        try:
            for attempts in (2, 3):
                try:
                    session.retry_failed()
                    return ResponseErrorCheck(code, False, "결함이 있는 재시도가 성공 처리됨")
                except (RuntimeError, ValueError):
                    if not session.last_failure or session.last_failure.attempts != attempts:
                        return ResponseErrorCheck(code, False, "시도 횟수 보존 실패")
            calls_before = port.calls
            try:
                session.retry_failed()
                return ResponseErrorCheck(code, False, "시도 상한을 초과함")
            except CoreRetryLimitError:
                pass
            try:
                session.discard_failed()
                return ResponseErrorCheck(code, False, "사용자 확인 없이 실패 건 제외됨")
            except PermissionError:
                pass
            if port.calls != calls_before or session.pending_count != 2:
                return ResponseErrorCheck(code, False, "시도 상한에서 상태가 변경됨")
            removed = session.discard_failed(confirmed=True)
            following = session.process_one()
            ok = (removed.text == "실패 입력" and following is not None
                  and following.input.text == "다음 입력" and session.pending_count == 0
                  and session.total_processed == 1 and session.last_failure is None)
        except Exception as exc:
            return ResponseErrorCheck(code, False, f"상한/제외 검증 예외: {type(exc).__name__}")
        return ResponseErrorCheck(code, ok, "3회 상한, 승인 없는 제외 차단, 다음 입력 정상 처리" if ok else "상한/제외 상태 불일치")
    try:
        recovered = session.retry_failed()
        after = session.run_batch(2)
        if code == "partial_batch":
            ok = (recovered.input.text == "두 번째 입력"
                  and [r.input.text for r in session.history] ==
                  ["첫 입력", "두 번째 입력", "세 번째 입력"])
        else:
            ok = (recovered.input.text == "실패 입력"
                  and [r.input.text for r in session.history] == ["실패 입력", "다음 입력"])
        ok = ok and after.remaining == 0 and session.last_failure is None
    except Exception as exc:
        return ResponseErrorCheck(code, False, f"복구 중 예외: {type(exc).__name__}")
    return ResponseErrorCheck(code, ok, "실패 건 재시도 후 FIFO/이력 복구" if ok else "복구 후 순서/이력 불일치")


def run_response_error_test(
    settings: Mapping[str, object], scenario: str = "all", *,
    session_factory: Callable[..., OfflineCoreSession] = OfflineCoreSession,
) -> ResponseErrorReport:
    if scenario != "all" and scenario not in SCENARIOS:
        raise ValueError("알 수 없는 응답 오류 시나리오입니다.")
    codes = SCENARIOS if scenario == "all" else (scenario,)
    checks = []
    for code in codes:
        try:
            checks.append(_run_scenario(settings, code, session_factory))
        except Exception as exc:
            checks.append(ResponseErrorCheck(code, False, f"검증 중 예외: {type(exc).__name__}"))
    return ResponseErrorReport(tuple(checks))
