"""Original 069: manually simulated disconnect/reconnect of existing offline chat.

No socket, timer, worker, persistence, account, real service or automatic retry.
The source 061 connector, 062 receiver, 063 order and 065 replies are reused.
"""
from __future__ import annotations

from dataclasses import dataclass

from .platform_chat_connector import OfflinePlatformChatConnector
from .offline_chat_receiver import OfflineChatReceiveBuffer, MockReceivedChat
from .offline_chat_order import OfflineChatOrder
from .offline_chat_reactions import OfflineChatReactions


@dataclass(frozen=True)
class RecoverySnapshot:
    phase: str
    connected: bool
    attached: bool
    same_session: bool
    source_consistent: bool
    accepted: int
    staged: int
    replied: int
    pending: int
    reconnect_attempts: int
    failed_attempts: int
    recovery_complete: bool
    mock_only: bool = True

    def describe(self) -> str:
        return '\n'.join((
            '원본 069 · 채팅 연결 장애·복구 · 오프라인 수동 모의',
            f'상태: {self.phase} / 동일 세션: {"예" if self.same_session else "아니오"}',
            f'가상 연결: {"예" if self.connected else "아니오"} / 수신 재준비: {"예" if self.attached else "아니오"}',
            f'수동 재연결 시도 {self.reconnect_attempts}회 / 모의 실패 {self.failed_attempts}회',
            f'수신 {self.accepted}건 / 순서 동기화 {self.staged}건 / 응답 {self.replied}건 / 대기 {self.pending}건',
            f'원본 기록 보존: {"확인" if self.source_consistent else "불일치 또는 기준 없음"}',
            f'복구 점검: {"오프라인 통과" if self.recovery_complete else "미완료"}',
            '연결 장애 중 새 수신 차단 · 이미 접수된 모든 메시지와 중복 기록 보존',
            '재연결/수신 재준비는 각각 운영자 버튼 필요 · 자동 재시도/타이머/고의 지연 없음',
            '실제 채팅 플랫폼 장애·누락 메시지 복구·실시간 송수신·AI/OBS/Windows 검증 아님',
        ))


class OfflineChatConnectionRecovery:
    """Non-persistent recovery drill; never creates another receiver or queue."""

    def __init__(self, connector: OfflinePlatformChatConnector,
                 receiver: OfflineChatReceiveBuffer, order: OfflineChatOrder,
                 reactions: OfflineChatReactions):
        if not isinstance(connector, OfflinePlatformChatConnector):
            raise ValueError('기존 61단계 가상 연결이 필요합니다.')
        if not isinstance(receiver, OfflineChatReceiveBuffer):
            raise ValueError('기존 62단계 수신함이 필요합니다.')
        if not isinstance(order, OfflineChatOrder) or order._receiver is not receiver:
            raise ValueError('같은 수신함의 63단계 순서 관리가 필요합니다.')
        if not isinstance(reactions, OfflineChatReactions) or reactions._receiver is not receiver or reactions._order is not order:
            raise ValueError('같은 수신함의 65단계 응답 세션이 필요합니다.')
        self._connector = connector
        self._receiver = receiver
        self._order = order
        self._reactions = reactions
        self._baseline: tuple[MockReceivedChat, ...] | None = None
        self._baseline_order: tuple[MockReceivedChat, ...] = ()
        self._baseline_staged: tuple[MockReceivedChat, ...] = ()
        self._baseline_replied = ()
        self._phase = '수동 장애 시험 대기'
        self._attempts = 0
        self._failures = 0
        self._restored = False

    def _require_session(self, current: OfflinePlatformChatConnector) -> None:
        if current is not self._connector:
            raise ValueError('플랫폼 선택/연결 세션이 변경되었습니다. 새 복구 시험을 시작하세요.')

    def _consistent(self) -> bool:
        if self._baseline is None:
            return False
        received = self._receiver.snapshot().buffered
        ordered = self._order.snapshot().queued
        replies = self._reactions.snapshot()
        try:
            self._reactions._validate_source()
            return (received[:len(self._baseline)] == self._baseline
                    and len(received) >= len(self._baseline)
                    and ordered[:len(self._baseline_order)] == self._baseline_order
                    and replies.staged[:len(self._baseline_staged)] == self._baseline_staged
                    and replies.responded[:len(self._baseline_replied)] == self._baseline_replied
                    and all(type(event.ordinal) is int and event.ordinal == index
                            for index, event in enumerate(received, start=1))
                    and ordered == received[:len(ordered)]
                    and replies.staged == ordered[:len(replies.staged)]
                    and all(item.event == replies.staged[index]
                            for index, item in enumerate(replies.responded)))
        except (ValueError, IndexError, TypeError):
            return False

    def snapshot(self, current: OfflinePlatformChatConnector) -> RecoverySnapshot:
        same = current is self._connector
        conn = self._connector.snapshot()
        receiver = self._receiver.snapshot()
        reactions = self._reactions.snapshot()
        connected = bool(conn.connected) and conn.connected == conn.selected
        consistent = self._consistent()
        ready = (self._restored and same and connected and receiver.attached
                 and self._receiver._connector is self._connector and consistent)
        if not same:
            phase = '연결 세션 변경 · 이전 시험 무효'
        elif self._restored and not ready:
            phase = '복구 후 상태 변경 · 재검증 필요'
        else:
            phase = self._phase
        return RecoverySnapshot(phase, connected, receiver.attached, same, consistent,
                                receiver.accepted_count, len(reactions.staged),
                                len(reactions.responded), len(reactions.pending),
                                self._attempts, self._failures, ready)

    def inject_outage(self, current: OfflinePlatformChatConnector) -> RecoverySnapshot:
        self._require_session(current)
        if self._baseline is not None:
            raise ValueError('이 세션에서는 이미 장애 시험을 시작했습니다. 중복 장애를 만들지 않습니다.')
        conn = self._connector.snapshot()
        if not conn.connected or conn.connected != conn.selected or not self._receiver.snapshot().attached \
                or self._receiver._connector is not self._connector:
            raise ValueError('61단계 가상 연결과 62단계 수신 준비를 먼저 수동 완료하세요.')
        self._reactions._validate_source()
        self._baseline = self._receiver.snapshot().buffered
        self._baseline_order = self._order.snapshot().queued
        reply_state = self._reactions.snapshot()
        self._baseline_staged = reply_state.staged
        self._baseline_replied = reply_state.responded
        self._connector.disconnect()
        self._receiver.detach()
        self._phase = '모의 장애 · 연결/수신 차단 · 기존 기록 보존'
        return self.snapshot(current)

    def reconnect(self, current: OfflinePlatformChatConnector, *, fail_handshake: bool = False) -> RecoverySnapshot:
        self._require_session(current)
        if self._baseline is None:
            raise ValueError('먼저 수동으로 가상 장애를 발생시키세요.')
        if type(fail_handshake) is not bool:
            raise ValueError('모의 연결 실패 선택값이 잘못됐습니다.')
        if self._restored or self._connector.snapshot().connected:
            raise ValueError('이미 가상 연결된 상태입니다. 중복 연결을 차단합니다.')
        if not self._consistent():
            raise ValueError('기존 채팅/순서/응답 기록 불일치 · 재연결 차단')
        self._attempts += 1
        self._connector.set_mock_failure(self._connector.snapshot().selected[0] if fail_handshake else None)
        try:
            result = self._connector.connect()
        finally:
            if not self._connector.snapshot().connected:
                self._connector.set_mock_failure(None)
        if not result.connected:
            self._failures += 1
            self._phase = '모의 재연결 실패 · 자동 재시도 없음'
        else:
            self._phase = '가상 재연결됨 · 수신 재준비 버튼 필요'
        return self.snapshot(current)

    def reattach(self, current: OfflinePlatformChatConnector) -> RecoverySnapshot:
        self._require_session(current)
        if self._baseline is None or self._restored:
            raise ValueError('복구 대기 상태가 아니거나 이미 수동 복구했습니다.')
        if not self._consistent():
            raise ValueError('기존 메시지 기록 불일치 · 수신 재준비 차단')
        if not self._connector.snapshot().connected:
            raise ValueError('먼저 가상 재연결을 수동으로 완료하세요.')
        self._receiver.attach(self._connector)
        self._restored = True
        self._phase = '수동 수신 재준비 및 기존 기록 보존 확인'
        return self.snapshot(current)
