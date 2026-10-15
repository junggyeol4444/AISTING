"""095: local, operator-triggered abnormal-state safety rehearsal.

Only reads the existing 061/062/063/065 mock session. This is NOT wired to
real OBS, TTS, AI, live platform chat or a running broadcast. No polling,
sockets, file writes, process control, filtering or automatic message retries.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_chat_receiver import OfflineChatReceiveBuffer, MockReceivedChat
from .offline_chat_order import OfflineChatOrder
from .offline_chat_reactions import OfflineChatReactions


class SafetyDenied(ValueError):
    """Unsafe, unknown or unverified state; never auto-clear the hold."""


@dataclass(frozen=True)
class SafetyDecision:
    issues: tuple[str, ...]
    held: bool
    received: int
    replied: int
    pending: int
    virtual_seconds: int
    mock_only: bool = True
    actual_output_stopped: bool = False
    actual_stream_stopped: bool = False

    @property
    def safe_for_mock_review(self) -> bool:
        return not self.issues and not self.held

    def describe(self) -> str:
        return ('원본 095 · 가상 방송 안전 감시 (실제 장치 제어 없음)\n'
                f'판정: {"수동 확인 필요 / 보류" if self.held else "모의 상태 이상 없음"}\n'
                f'가상 초 {self.virtual_seconds} / 수신 {self.received}건 / 응답 {self.replied}건 / 대기 {self.pending}건\n'
                '이상 항목: ' + (', '.join(self.issues) if self.issues else '없음') + '\n'
                '위험 상태는 감시기 내부에서만 유지됩니다. 실제 송출·음성 정지 아님.\n'
                '실제 시청자·방송·OBS·장비 모니터링 및 운영자 승인: 미검증')


class OfflineBroadcastSafetyGate:
    """Read-only, fail-closed *mock* safety guard with manual re-arm.

    Virtual time is provided by an operator/test; not wall clock or scheduler.
    Long-pending is operational only, not a reason to discard or censor chats.
    If any integrity check throws, the internal hold latches on. A later
    healthy check does not clear the latch without manual_acknowledge().
    """

    def __init__(self, receiver: OfflineChatReceiveBuffer, order: OfflineChatOrder,
                 reactions: OfflineChatReactions, *, backlog_limit: int = 50,
                 timeout_seconds: int = 120):
        if (not isinstance(receiver, OfflineChatReceiveBuffer)
                or not isinstance(order, OfflineChatOrder) or order._receiver is not receiver
                or not isinstance(reactions, OfflineChatReactions)
                or reactions._receiver is not receiver or reactions._order is not order):
            raise ValueError('같은 062/063/065 모의 세션만 검사할 수 있습니다.')
        if type(backlog_limit) is not int or not 1 <= backlog_limit <= 500:
            raise ValueError('가상 대기열 경고 기준이 잘못됐습니다.')
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 86400:
            raise ValueError('가상 처리 정체 기준이 잘못됐습니다.')
        self.receiver, self.order, self.reactions = receiver, order, reactions
        self.backlog_limit, self.timeout_seconds = backlog_limit, timeout_seconds
        self._held = False
        self._last_second: int | None = None
        self._pending_since: int | None = None
        self._last_replied = 0
        self._last_accepted = 0
        self._initial_connector = receiver._connector
        self._initial_connection = (receiver._connector.snapshot()
                                    if receiver._connector is not None else None)

    @property
    def held(self) -> bool:
        return self._held

    def _check_records(self) -> tuple[list[str], int, int, int]:
        issues: list[str] = []
        incoming = self.receiver.snapshot()
        ordering = self.order.snapshot()
        reaction = self.reactions.snapshot()
        count = len(incoming.buffered)
        staged = len(reaction.staged)
        replied = len(reaction.responded)
        pending = len(reaction.pending) + reaction.unsynced
        # No content is copied to decisions/logs. Explicit prefix consistency.
        if (not incoming.attached or self.receiver._connector is None
                or not self.receiver._connector.snapshot().connected):
            issues.append('가상 연결 끊김')
        if (self.receiver._connector is not self._initial_connector
                or (self.receiver._connector is not None and
                    self.receiver._connector.snapshot() != self._initial_connection)):
            issues.append('가상 연결 세션 변경')
        if (ordering.paused or reaction.blocked):
            issues.append('모의 처리 중단')
        if (tuple(incoming.buffered[:len(ordering.queued)]) != ordering.queued
                or tuple(ordering.queued[:staged]) != reaction.staged
                or staged > len(ordering.queued)
                or len(ordering.queued) > count
                or type(self.order._cursor) is not int
                or not 0 <= self.order._cursor <= len(ordering.queued)
                or len(ordering.processed) > len(ordering.queued)
                or ordering.processed != ordering.queued[:len(ordering.processed)]
                or ordering.pending != ordering.queued[len(ordering.processed):]
                or replied > staged
                or tuple(x.event for x in reaction.responded) != reaction.staged[:replied]
                or reaction.pending != reaction.staged[replied:]
                or reaction.unsynced != count-staged
                or incoming.accepted_count != count
                or any(type(x) is not MockReceivedChat or type(x.ordinal) is not int
                       or x.ordinal != i for i, x in enumerate(incoming.buffered, 1))):
            issues.append('모의 채팅 기록 불일치')
        if count < self._last_accepted or replied < self._last_replied:
            issues.append('처리 기록 역행')
        if pending > self.backlog_limit:
            issues.append('모의 대기열 경고')
        return issues, count, replied, pending

    def _evaluate(self, second: int, operator_incident: bool, *, update: bool) -> SafetyDecision:
        if type(second) is not int or second < 0:
            raise ValueError('가상 초는 0 이상의 정수여야 합니다.')
        if type(operator_incident) is not bool:
            raise ValueError('운영자 수동 사고 제보 값이 올바르지 않습니다.')
        try:
            issues, count, replied, pending = self._check_records()
        except Exception:
            issues, count, replied, pending = ['모의 상태 조회 오류'], 0, 0, 0
        if self._last_second is not None and second < self._last_second:
            issues.append('가상 시계 역행')
        since = self._pending_since
        # Progress of successful answers restarts the pending-age clock.
        if replied != self._last_replied or pending == 0:
            since = second if pending else None
        elif pending and since is None:
            since = second
        if pending and since is not None and second >= since and second - since >= self.timeout_seconds:
            issues.append('가상 응답 진행 정체')
        if operator_incident:
            issues.append('운영자 수동 이상 제보')
        unique = tuple(dict.fromkeys(issues))
        if update:
            self._held = self._held or bool(unique)
            self._last_second = second if self._last_second is None else max(self._last_second, second)
            self._pending_since = since
            self._last_replied = max(self._last_replied, replied)
            self._last_accepted = max(self._last_accepted, count)
        return SafetyDecision(unique, self._held or bool(unique), count, replied, pending, second)

    def inspect(self, second: int, *, operator_incident: bool = False) -> SafetyDecision:
        """Read existing mock state; latch a local hold on anomaly."""
        return self._evaluate(second, operator_incident, update=True)

    def manual_acknowledge(self, second: int) -> SafetyDecision:
        """An operator-only release after a verified healthy state, never a retry.

        The old pending age is kept: acknowledgement must not pretend that a
        queue has made progress. A full reset requires a new gate/session.
        """
        if not self._held:
            raise SafetyDenied('확인할 가상 안전 보류 상태가 없습니다.')
        current = self._evaluate(second, False, update=False)
        if current.issues:
            raise SafetyDenied('이상이 남아 있어 수동 해제를 거부했습니다.')
        self._held = False
        self._last_second = max(self._last_second or 0, second)
        return SafetyDecision((), False, current.received, current.replied,
                              current.pending, second)


def run_offline_broadcast_safety_audit() -> tuple[tuple[str, SafetyDecision], ...]:
    """Fully isolated synthetic scenarios; no inspection of operator files."""
    from .platform_chat_connector import OfflinePlatformChatConnector

    def session():
        connector = OfflinePlatformChatConnector(['chzzk'])
        connector.connect()
        receiver = OfflineChatReceiveBuffer()
        receiver.attach(connector)
        order = OfflineChatOrder(receiver)
        receiver.inject('chzzk', 'synthetic-viewer', 'synthetic-message')
        order.sync()
        reactions = OfflineChatReactions(receiver, order)
        reactions.sync()
        return connector, receiver, order, reactions, OfflineBroadcastSafetyGate(receiver, order, reactions)

    _, _, _, reactions, gate = session()
    healthy = gate.inspect(0)
    timeout = gate.inspect(120)
    if not timeout.held or '가상 응답 진행 정체' not in timeout.issues:
        raise SafetyDenied('가상 처리 정체 감지가 실패했습니다.')
    reactions.reply_next()  # explicit synthetic action, not a live response
    latched = gate.inspect(121)
    if not latched.held or latched.issues:
        raise SafetyDenied('보류 상태가 자동으로 사라졌습니다.')
    released = gate.manual_acknowledge(122)

    connector, _, _, _, gate2 = session()
    connector.disconnect()
    disconnected = gate2.inspect(0)
    if '가상 연결 끊김' not in disconnected.issues:
        raise SafetyDenied('가상 연결 끊김을 감지하지 못했습니다.')
    _, receiver, _, _, gate3 = session()
    receiver._buffer.pop()  # injection of deliberate corruption only in separate audit
    corrupt = gate3.inspect(0)
    if '모의 채팅 기록 불일치' not in corrupt.issues:
        raise SafetyDenied('기록 손상을 감지하지 못했습니다.')
    outcomes = (('정상', healthy), ('정체 감지', timeout), ('보류 유지', latched),
                ('수동 해제', released), ('연결 끊김', disconnected), ('기록 손상', corrupt))
    if not healthy.safe_for_mock_review or not released.safe_for_mock_review:
        raise SafetyDenied('안전 상태 검증이 실패했습니다.')
    return outcomes
