"""22단계: 사용자가 직접 구동하는 **메모리 전용** 기본 코어.

채팅 입력 -> 모의 답변 -> 메모리 내 이력으로 연결하는 작은 실행 조정기.
기존 ChatRehearsal/SQLite 기억과는 독립적이며 외부 포트(방송/음성/아바타),
Ollama/네트워크/파일/장치/OS 정보를 사용하지 않는다.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from secrets import token_hex
from typing import Protocol, Sequence

from .core_foundation import CoreBlueprint, build_core_blueprint
from .core_ai_connection import CoreAIConnectionPlan, build_core_ai_plan, validate_core_ai_plan
from .core_ports import CoreInput, CoreReply
from .offline_chat import Answer, ChatMessage, MockReplyGenerator, parse_script

MAX_PENDING = 500
MAX_BATCH = 50
MAX_REPLY = 6000
MAX_HISTORY = 500
MAX_CONTEXT_TURNS = 8  # 메모리 내 직전 8건만 응답 포트에 전달
MAX_RESPONSE_ATTEMPTS = 3  # 최초 1회 + 사용자가 요청하는 재시도 최대 2회


class LocalReplyPort(Protocol):
    def generate(self, item: CoreInput, history: Sequence[CoreReply]) -> str: ...


class MockCoreReplyPort:
    """기존 모의 응답기를 CoreInput/CoreReply 계약에 맞게 사용."""

    def __init__(self) -> None:
        self._generator = MockReplyGenerator()

    def generate(self, item: CoreInput, history: Sequence[CoreReply]) -> str:
        old_history = [Answer(ChatMessage(r.input.sender, r.input.text), r.text) for r in history]
        return self._generator.generate(ChatMessage(item.sender, item.text), old_history)


@dataclass(frozen=True)
class CoreRunResult:
    processed: tuple[CoreReply, ...]
    remaining: int
    total_processed: int
    mode: str = "mock"

    def describe(self) -> str:
        lines = [
            "22단계 · 기본 코어 수동 실행 결과 (오프라인 모의 답변)",
            f"이번 처리 {len(self.processed)}건 · 대기 {self.remaining}건 · 누적 {self.total_processed}건",
            "채팅 입력 → 모의 답변 → 메모리 내 이력: 연결됨",
            "Ollama·외부 채팅·SQLite·음성·아바타·OBS·방송: 연결/실행 안 함",
        ]
        for reply in self.processed:
            lines.append(f"{reply.input.sender}: {reply.input.text}\nAI(모의): {reply.text}")
        return "\n\n".join(lines)


@dataclass(frozen=True)
class CoreResponseFailure:
    """대기열 선두 입력의 오류 상태. 예외 원문/민감 정보는 저장하지 않는다."""

    code: str
    message: str
    attempts: int
    input: CoreInput


class CoreGenerationError(RuntimeError):
    """답변 포트 예외를 사용자에게 안전한 고정 문구로 바꾼 오류."""


class CoreInvalidReplyError(ValueError):
    """답변 타입·내용·길이 계약 위반."""


class CoreRetryLimitError(RuntimeError):
    """동일 대기 입력에 대한 수동 재시도 상한 도달."""


_FAILURE_MESSAGES = {
    "timeout": "모의 답변 처리 시간이 초과되었습니다.",
    "connection": "모의 답변 포트에서 연결 오류가 발생했습니다.",
    "generation": "모의 답변 생성 중 오류가 발생했습니다.",
    "invalid_type": "모의 답변이 문자열이 아닙니다.",
    "empty_reply": "모의 답변이 비어 있습니다.",
    "oversized_reply": "모의 답변이 6000자를 초과합니다.",
}


class OfflineCoreSession:
    """사용자 수동 클릭에서만 호출하는, 명시적 무송출 모의 코어."""

    def __init__(self, settings: dict[str, object], reply_port: LocalReplyPort | None = None) -> None:
        self._blueprint = build_core_blueprint(settings, "mock")
        self._reply_port = reply_port if reply_port is not None else MockCoreReplyPort()
        # 23단계는 라우팅 계획만 보관; 실행 포트는 22단계 모의 포트 그대로.
        self._ai_plan = build_core_ai_plan()
        self._pending: deque[CoreInput] = deque()
        self._history: list[CoreReply] = []
        self._total = 0
        self._last_failure: CoreResponseFailure | None = None
        self._failed_head: CoreInput | None = None
        # 28단계: 저장 후보를 사용자가 요청할 때만 임시 세션 식별자 생성.
        self._response_recording_key: str | None = None

    def response_recording_key(self) -> str:
        """사용자 수동 저장/미리보기용 식별자. 파일/PC 정보 수집 없음."""
        if self._response_recording_key is None:
            self._response_recording_key = token_hex(16)
        return self._response_recording_key

    @property
    def blueprint(self) -> CoreBlueprint:
        return self._blueprint

    @property
    def ai_plan(self) -> CoreAIConnectionPlan:
        return self._ai_plan

    def configure_ai_plan(self, plan: CoreAIConnectionPlan) -> None:
        """연결 계획만 수동 반영; 실제 reply_port/대기열/이력 불변."""
        validate_core_ai_plan(plan)
        # 변조된 dataclass 참조를 보관하지 않고 정규화된 새 인스턴스만 유지.
        self._ai_plan = build_core_ai_plan(plan.mode, plan.model_name)

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def total_processed(self) -> int:
        return self._total

    @property
    def last_failure(self) -> CoreResponseFailure | None:
        """실패한 대기열 선두의 읽기 전용 오류 분류와 시도 횟수."""
        return self._last_failure

    @property
    def history(self) -> tuple[CoreReply, ...]:
        return tuple(self._history)

    @property
    def context_for_next_turn(self) -> tuple[CoreReply, ...]:
        """다음 답변 포트에 전달할 최근 이력의 읽기 전용 스냅샷."""
        return tuple(self._history[-MAX_CONTEXT_TURNS:])

    def update_selection(self, settings: dict[str, object]) -> None:
        """선택값만 갱신; 입력/답변 대기열, 기존 데이터는 보존."""
        updated = build_core_blueprint(settings, "mock")
        self._blueprint = updated

    def enqueue(self, script: str) -> int:
        """전체 입력을 먼저 검사한 뒤 원자적으로 대기열에 추가."""
        parsed = parse_script(script)
        if len(parsed) + len(self._pending) > MAX_PENDING:
            raise ValueError(f"모의 코어 대기열은 최대 {MAX_PENDING}건입니다.")
        self._pending.extend(CoreInput(x.sender, x.text) for x in parsed)
        return len(parsed)

    def _record_failure(self, item: CoreInput, code: str) -> CoreResponseFailure:
        attempts = (self._last_failure.attempts + 1
                    if self._failed_head is item and self._last_failure else 1)
        failure = CoreResponseFailure(code, _FAILURE_MESSAGES[code], attempts, item)
        self._failed_head = item
        self._last_failure = failure
        return failure

    def process_one(self) -> CoreReply | None:
        """오류 시 선두/FIFO/이력 유지, 분류된 오류 기록. 자동 재시도는 하지 않는다."""
        if not self._pending:
            return None
        item = self._pending[0]
        if self._failed_head is item and self._last_failure is not None \
                and self._last_failure.attempts >= MAX_RESPONSE_ATTEMPTS:
            raise CoreRetryLimitError("수동 시도 상한(3회)입니다. 실패 건을 확인하고 직접 제외하거나 초기화하세요.")
        try:
            result = self._reply_port.generate(item, self.context_for_next_turn)
        except Exception as exc:
            code = ("timeout" if isinstance(exc, TimeoutError) else
                    "connection" if isinstance(exc, ConnectionError) else "generation")
            failure = self._record_failure(item, code)
            # 포트 예외 원문에 포함될 수 있는 개인 정보/토큰을 UI로 전달하지 않는다.
            raise CoreGenerationError(failure.message) from None
        if type(result) is not str:
            code = "invalid_type"
        elif not result.strip():
            code = "empty_reply"
        elif len(result) > MAX_REPLY:
            code = "oversized_reply"
        else:
            code = ""
        if code:
            failure = self._record_failure(item, code)
            raise CoreInvalidReplyError(failure.message)
        reply = CoreReply(item, result)
        self._pending.popleft()
        self._history.append(reply)
        if len(self._history) > MAX_HISTORY:
            del self._history[:-MAX_HISTORY]
        self._total += 1
        self._last_failure = None
        self._failed_head = None
        return reply

    def retry_failed(self) -> CoreReply:
        """사용자 명시 동작에서만 선두 실패 건을 1회 재시도 (자동 루프 없음)."""
        if self._last_failure is None or not self._pending or self._failed_head is not self._pending[0]:
            raise ValueError("재시도할 실패 건이 없습니다.")
        result = self.process_one()
        assert result is not None
        return result

    def discard_failed(self, *, confirmed: bool = False) -> CoreInput:
        """사용자가 확인한 경우에만 실패한 선두 1건 제외. 성공 이력은 불변."""
        if confirmed is not True:
            raise PermissionError("실패 건 제외에는 별도 사용자 확인이 필요합니다.")
        if self._last_failure is None or not self._pending or self._failed_head is not self._pending[0]:
            raise ValueError("제외할 실패 건이 없습니다.")
        removed = self._pending.popleft()
        self._last_failure = None
        self._failed_head = None
        return removed

    def run_batch(self, count: int = MAX_BATCH) -> CoreRunResult:
        if type(count) is not int or not 1 <= count <= MAX_BATCH:
            raise ValueError(f"한 번에 처리할 수 있는 범위는 1~{MAX_BATCH}건입니다.")
        results: list[CoreReply] = []
        # 기본 코어는 모의 답변만. 외부 호출 가능 객체를 자동 선택하지 않는다.
        for _ in range(min(count, len(self._pending))):
            try:
                answer = self.process_one()
            except Exception as exc:
                # 앞서 성공한 결과는 보존, 실패한 항목은 그대로 재시도 가능.
                failure = self._last_failure
                safe_message = (str(exc) if isinstance(exc, CoreRetryLimitError) else
                                failure.message if failure else
                                "모의 코어 응답 처리를 진행할 수 없습니다.")
                raise CoreBatchError(safe_message, tuple(results), self.pending_count,
                                     failure=failure) from None
            if answer is not None:
                results.append(answer)
        return CoreRunResult(tuple(results), self.pending_count, self.total_processed)

    def reset(self) -> None:
        """모의 세션 데이터만 초기화. 설정/파일/SQLite는 변경하지 않음."""
        self._pending.clear()
        self._history.clear()
        self._total = 0
        self._last_failure = None
        self._failed_head = None
        # 새 모의 세션의 동일 순번은 이전 저장 기록과 구별한다.
        self._response_recording_key = None


class CoreBatchError(RuntimeError):
    def __init__(self, message: str, processed: tuple[CoreReply, ...], remaining: int,
                 *, failure: CoreResponseFailure | None = None):
        super().__init__(message)
        self.processed = processed
        self.remaining = remaining
        self.failure = failure
