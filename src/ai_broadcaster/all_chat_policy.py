"""Original roadmap 037: explicit all-chat response policy on an isolated mock queue.

No filtering, implicit delay, automatic retry, external chat/model/OBS, filesystem,
PC inspection or persistence. Each accepted event has a distinct sequence number.
The operator decides when to enqueue and process, and whether to retry failures.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .core_execution import OfflineCoreSession, LocalReplyPort, MockCoreReplyPort
from .core_ports import CoreInput, CoreReply
from .offline_chat import parse_script

MAX_POLICY_MESSAGES = 500
MAX_POLICY_BATCH = 50


@dataclass(frozen=True)
class PolicyTurn:
    sequence: int
    sender: str
    input_text: str
    reply: str


@dataclass(frozen=True)
class PolicyAudit:
    accepted: int
    replied: tuple[PolicyTurn, ...]
    pending: tuple[tuple[int, str, str], ...]
    attempts: int
    failed_sequence: int | None
    stopped_reason: str = ""

    @property
    def all_responded(self) -> bool:
        return self.accepted > 0 and not self.pending and not self.stopped_reason and self.failed_sequence is None and len(self.replied) == self.accepted

    def describe(self) -> str:
        lines = [
            "원본 037단계 · 전체 채팅 반응 원칙 (격리된 오프라인 모의 대기열)",
            f"접수 {self.accepted}건 · 응답 {len(self.replied)}건 · 대기 {len(self.pending)}건 · 시도 {self.attempts}회",
            "접수된 채팅은 중복 여부나 발신자에 따라 선별·삭제하지 않습니다.",
            "자동 재시도·인위적 응답 지연·시간 기준 합격 판정 없음; 사용자가 버튼으로만 진행",
            "실제 채팅 연결/AI 품질/음성/방송/PC 성능은 검증하지 않았습니다.",
            "설정/SQLite/금기 파일 저장·네트워크·OBS·PC 정보 수집 없음",
        ]
        if self.failed_sequence is not None:
            lines.append(f"실패 대기 항목: #{self.failed_sequence} · 수동 재시도만 가능")
        if self.stopped_reason:
            lines.append("처리 중단: " + self.stopped_reason)
        if self.all_responded:
            lines.append("모의 대기열의 모든 접수 건에 응답 완료 (실제 방송 검증 아님)")
        for turn in self.replied:
            lines.append(f"#{turn.sequence} {turn.sender}: {turn.input_text[:100]} → {turn.reply[:160]}")
        for seq, sender, content in self.pending:
            lines.append(f"대기 #{seq} {sender}: {content[:100]}")
        return "\n".join(lines)


class AllChatPolicySession:
    """Single in-memory audit session; FIFO exactly-once SUCCESS, no silent drops."""

    def __init__(self, settings: Mapping[str, object], *, reply_port: LocalReplyPort | None = None):
        self._core = OfflineCoreSession(dict(settings), reply_port=reply_port if reply_port is not None else MockCoreReplyPort())
        self._accepted: list[CoreInput] = []
        self._replied: list[PolicyTurn] = []
        self._attempts = 0
        self._blocked = False
        self._reason = ""

    def append(self, script: str) -> int:
        """Validate complete batch before changing the queue, including overall limits."""
        if type(script) is not str:
            raise ValueError("대본은 문자열이어야 합니다.")
        parsed = parse_script(script)
        if len(self._accepted) + len(parsed) > MAX_POLICY_MESSAGES:
            raise ValueError(f"한 시험 세션에서 최대 {MAX_POLICY_MESSAGES}건까지 접수합니다.")
        self._core.enqueue(script)
        self._accepted.extend(CoreInput(p.sender, p.text) for p in parsed)
        return len(parsed)

    def _append_success(self, reply: CoreReply) -> None:
        index = len(self._replied)
        expected = self._accepted[index]
        if reply.input != expected:
            # No acknowledgement for misordered output; never claim policy satisfied.
            self._blocked = True
            self._reason = "응답과 접수 순서 불일치 · 수동 재검토 필요"
            return
        self._replied.append(PolicyTurn(index + 1, expected.sender, expected.text, reply.text))
        self._blocked = False
        self._reason = ""

    def run_next(self, *, manual_retry: bool = False) -> PolicyAudit:
        if self._blocked and not manual_retry:
            return self.audit()
        if manual_retry and not self._blocked:
            raise ValueError("실패 항목이 없어 수동 재시도를 할 수 없습니다.")
        if self._core.pending_count == 0:
            if manual_retry:
                raise ValueError("재시도할 채팅이 없습니다.")
            return self.audit()
        self._attempts += 1
        try:
            reply = self._core.retry_failed() if manual_retry else self._core.process_one()
        except Exception:
            self._blocked = True
            # Never expose provider exception content (may contain tokens or file paths).
            failure = self._core.last_failure
            self._reason = ((failure.message + " · 수동 재시도 또는 초기화 필요")
                            if failure else "모의 응답 처리 실패 · 수동 확인 필요")
            return self.audit()
        if reply is not None:
            self._append_success(reply)
        return self.audit()

    def run_batch(self, count: int = MAX_POLICY_BATCH) -> PolicyAudit:
        if type(count) is not int or not 1 <= count <= MAX_POLICY_BATCH:
            raise ValueError(f"한 번에 1~{MAX_POLICY_BATCH}건을 처리할 수 있습니다.")
        for _ in range(min(count, self._core.pending_count)):
            if self._blocked:
                break
            self.run_next()
        return self.audit()

    def audit(self) -> PolicyAudit:
        pending_count = self._core.pending_count
        # The identity of every accepted chat is preserved, including duplicate text.
        if len(self._replied) + pending_count != len(self._accepted):
            return PolicyAudit(len(self._accepted), tuple(self._replied), (), self._attempts,
                               len(self._replied) + 1, "처리 수 불일치 · 완료 판정 보류")
        remaining = tuple((idx + 1, msg.sender, msg.text)
                          for idx, msg in enumerate(self._accepted)
                          if idx >= len(self._replied))
        failure = len(self._replied) + 1 if self._blocked else None
        return PolicyAudit(len(self._accepted), tuple(self._replied), remaining,
                           self._attempts, failure, self._reason)
