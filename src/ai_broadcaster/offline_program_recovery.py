"""Original 094: fail-closed, *memory-only* recovery for synthetic FIFO replies.

Reuses the original 062/063/065 objects. This does not restart Python,
reconnect platforms, retry a failed reply, touch the filesystem, or broadcast.
Only the known recoverable 'blocked after a failed mock reply' state is reset
once after strict source/queue comparison. Actual production recovery is pending.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_chat_order import OfflineChatOrder
from .offline_chat_receiver import OfflineChatReceiveBuffer
from .offline_chat_reactions import OfflineChatReactions, ReactionSnapshot
from .platform_chat_connector import OfflinePlatformChatConnector


@dataclass(frozen=True)
class RecoveryDecision:
    state: str
    preserved: bool
    resumed: bool
    reply_created: bool
    pending: int
    replied: int
    failure_count: int
    mock_only: bool = True
    actual_process_restarted: bool = False
    actual_stream_recovered: bool = False

    def describe(self) -> str:
        return ('원본 094 · 로컬 모의 처리 오류 안전 복구\n'
                f'상태: {self.state} / 미처리 {self.pending}건 / 모의 응답 {self.replied}건\n'
                f'오류 감지 {self.failure_count}건 / 기록 보존 {self.preserved} / 자동 차단 해제 {self.resumed}\n'
                '오류 당시 응답 재시도: 없음 · 작업 재개/다음 처리: 사용자 수동 버튼 필요\n'
                '실제 프로세스/Windows/AI/OBS/플랫폼 장애 자동 복구: 구현·검증하지 않음')


class RecoveryDenied(ValueError):
    """The supervisor cannot prove that it is safe to reset the mock failure."""


class OfflineProgramRecovery:
    """One safe reset for a failed, unchanged synthetic reply, never a replay.

    This is not a generic try/except wrapper: it only accepts a known stage-065
    blocked failure, checks the immutable prefixes and holds on corruption.
    This class makes no network or file calls and never schedules work.
    """

    def __init__(self, receiver: OfflineChatReceiveBuffer, order: OfflineChatOrder,
                 reactions: OfflineChatReactions):
        if not isinstance(receiver, OfflineChatReceiveBuffer) or \
                not isinstance(order, OfflineChatOrder) or order._receiver is not receiver or \
                not isinstance(reactions, OfflineChatReactions) or \
                reactions._receiver is not receiver or reactions._order is not order:
            raise ValueError('동일한 062/063/065 가상 수신·순서·응답 세션이 필요합니다.')
        self.receiver = receiver
        self.order = order
        self.reactions = reactions
        self.failure_count = 0
        self._busy = False
        self._quarantined = False

    def _same_records(self, before: ReactionSnapshot, incoming_before: tuple, order_before: tuple,
                      connector_before: object, connection_before: object) -> bool:
        try:
            self.reactions._validate_source()
            now = self.reactions.snapshot()
            incoming = self.receiver.snapshot().buffered
            ordering = self.order.snapshot()
            return (self.receiver._connector is connector_before
                    and connector_before is not None
                    and connector_before.snapshot() == connection_before
                    and self.receiver.snapshot().attached
                    and incoming == incoming_before
                    and ordering.queued == order_before
                    and ordering.queued == incoming
                    and not ordering.paused
                    and now.received == before.received
                    and now.staged == before.staged
                    and now.responded == before.responded
                    and now.pending == before.pending
                    and now.unsynced == before.unsynced)
        except (ValueError, TypeError, IndexError, AttributeError):
            return False

    def _decision(self, state: str, *, preserved: bool, resumed: bool,
                  reply_created: bool) -> RecoveryDecision:
        now = self.reactions.snapshot()
        return RecoveryDecision(state, preserved, resumed, reply_created,
                                len(now.pending), len(now.responded), self.failure_count)

    def process_one(self, *, simulate_failure: bool = False) -> RecoveryDecision:
        """Single operator-triggered processing attempt; no hidden retry."""
        if type(simulate_failure) is not bool:
            raise ValueError('가상 실패 여부는 불리언이어야 합니다.')
        if self._quarantined or self._busy:
            raise RecoveryDenied('이전 복구 불가 상태 또는 중첩 실행입니다. 새 모의 세션이 필요합니다.')
        if self.reactions.snapshot().blocked or self.order.snapshot().paused:
            raise RecoveryDenied('이전 중단 상태를 임의로 해제하지 않습니다.')
        self.reactions._validate_source()
        connector_before = self.receiver._connector
        if connector_before is None or not self.receiver.snapshot().attached:
            raise RecoveryDenied('수신 연결이 해제돼 있어 자동 복구를 수행하지 않습니다.')
        connection_before = connector_before.snapshot()
        before = self.reactions.snapshot()
        incoming_before = self.receiver.snapshot().buffered
        order_before = self.order.snapshot().queued
        if not before.pending:
            raise RecoveryDenied('처리할 가상 채팅이 없습니다.')
        self._busy = True
        try:
            try:
                self.reactions.reply_next(simulate_failure=simulate_failure)
            except ValueError:
                self.failure_count += 1
                if not self.reactions.snapshot().blocked or not self._same_records(before, incoming_before, order_before, connector_before, connection_before):
                    self._quarantined = True
                    raise RecoveryDenied('수신/응답 기록 불일치 또는 알 수 없는 오류: 자동 복구 차단') from None
                try:
                    self.reactions.resume()  # one reset only; NEVER calls reply_next again
                except (ValueError, TypeError):
                    self._quarantined = True
                    raise RecoveryDenied('차단 상태 해제 실패: 자동 복구 차단') from None
                if self.reactions.snapshot().blocked or not self._same_records(before, incoming_before, order_before, connector_before, connection_before):
                    self._quarantined = True
                    raise RecoveryDenied('복구 후 기록 불일치: 자동 복구 차단')
                return self._decision('모의 오류 감지 → 처리 상태만 복원 · 실패한 작업 대기',
                                      preserved=True, resumed=True, reply_created=False)
            except Exception:
                self.failure_count += 1
                self._quarantined = True
                raise RecoveryDenied('예상 밖의 오류: 자동 복구 차단 · 원인 별도 점검') from None
            after = self.reactions.snapshot()
            if (self.receiver._connector is not connector_before or
                    connector_before.snapshot() != connection_before or
                    not self.receiver.snapshot().attached or
                    self.receiver.snapshot().buffered != incoming_before or
                    self.order.snapshot().queued != order_before or
                    after.staged != before.staged or
                    after.received != before.received or
                    len(after.responded) != len(before.responded) + 1 or
                    after.responded[:-1] != before.responded or
                    after.responded[-1].event != before.pending[0] or
                    after.pending != before.pending[1:]):
                self._quarantined = True
                raise RecoveryDenied('응답 순서가 불일치하여 추가 처리를 차단합니다.')
            return self._decision('단일 모의 응답 정상 처리', preserved=True,
                                  resumed=False, reply_created=True)
        finally:
            self._busy = False


def run_offline_program_recovery_audit() -> tuple[RecoveryDecision, ...]:
    """Isolated deterministic 3-message drill, independent of user sessions."""
    connector = OfflinePlatformChatConnector(['chzzk'])
    connector.connect()
    receiver = OfflineChatReceiveBuffer()
    receiver.attach(connector)
    order = OfflineChatOrder(receiver)
    for text in ('모의 인사', '중복 보존', '중복 보존'):
        receiver.inject('chzzk', '가상시청자', text)
    order.sync()
    reactions = OfflineChatReactions(receiver, order)
    reactions.sync()
    recovery = OfflineProgramRecovery(receiver, order, reactions)
    first = recovery.process_one()
    failure = recovery.process_one(simulate_failure=True)
    if failure.reply_created or not failure.resumed or failure.pending != 2:
        raise RecoveryDenied('모의 오류 후 미처리 기록을 안전하게 보존하지 못했습니다.')
    second = recovery.process_one()  # explicit operator action in drill, not auto retry
    third = recovery.process_one()
    if not reactions.snapshot().all_responded or not (first.reply_created and second.reply_created and third.reply_created):
        raise RecoveryDenied('처리 완료 검증에 실패했습니다.')
    return first, failure, second, third
