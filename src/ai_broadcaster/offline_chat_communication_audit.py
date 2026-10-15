"""Original 070: operator-triggered, isolated, finite offline chat-chain drill.

This module uses the existing 061-069 classes; it does not listen for live chat,
read credentials, touch disk, run a timer, or modify the application's session.
"""
from __future__ import annotations

from dataclasses import dataclass

from .core_execution import MockCoreReplyPort
from .offline_chat_order import OfflineChatOrder
from .offline_chat_reactions import OfflineChatReactions
from .offline_chat_receiver import OfflineChatReceiveBuffer
from .offline_chat_recovery import OfflineChatConnectionRecovery
from .platform_chat_connector import OfflinePlatformChatConnector


@dataclass(frozen=True)
class CommunicationCheck:
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CommunicationAuditReport:
    selected: tuple[str, ...]
    checks: tuple[CommunicationCheck, ...]
    received: int
    responded: int
    blocked_attempts: int
    simulated_reconnect_failures: int
    mock_only: bool = True

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    def describe(self) -> str:
        lines = [
            '원본 070 · 채팅 소통 전 과정 통합 검증 · 격리된 오프라인 모의',
            '결과: ' + ('모의 통과' if self.passed else '모의 실패/미완료'),
            '선택 플랫폼: ' + ', '.join(self.selected),
            f'모의 수신 {self.received}건 / 모의 응답 {self.responded}건 / '
            f'차단 확인 {self.blocked_attempts}회 / 의도적 가상 재연결 실패 '
            f'{self.simulated_reconnect_failures}회',
        ]
        lines.extend(('통과' if item.passed else '실패') + ' · ' + item.label +
                     (' · ' + item.detail if item.detail else '') for item in self.checks)
        lines.extend([
            '이 검사는 기존 채팅 세션과 사용자 설정을 변경하지 않는 별도 메모리 시나리오입니다.',
            '모의 테스트 버튼 1회로 유한한 시나리오를 실행합니다. 운영 중 자동 재시도·타이머·고의 지연 없음.',
            '실제 플랫폼 수신/응답 속도, 실시간 연결, AI 대화 자연스러움, 음성, 아바타, OBS, Windows EXE 검증 아님.',
            '사용자 최종 승인 및 실기기 검증은 별도 대기 상태입니다.',
        ])
        return '\n'.join(lines)


class _TraceMockPort:
    """Records only synthetic inputs/history for same-viewer context verification."""

    def __init__(self) -> None:
        self._port = MockCoreReplyPort()
        self.calls = []

    def generate(self, item, history):
        self.calls.append((item, tuple(history)))
        return self._port.generate(item, history)


def run_offline_chat_communication_audit(selected: list[str] | tuple[str, ...]) -> CommunicationAuditReport:
    """Verify a complete 061→070 synthetic path without changing a live app session.

    Deliberate failure/recovery steps occur ONLY inside this finite manual test,
    not in the real application's receive or reply loop. No sleeping/polling.
    """
    # Fail early on invalid/no selection. No implicit platform selection.
    connector = OfflinePlatformChatConnector(selected)
    if not connector.snapshot().selected:
        raise ValueError('먼저 방송 설정에서 모의 시험 플랫폼을 하나 이상 선택하세요.')
    platforms = connector.snapshot().selected
    receiver = OfflineChatReceiveBuffer()
    order = OfflineChatOrder(receiver)
    trace = _TraceMockPort()
    reactions = OfflineChatReactions(receiver, order, reply_port=trace)
    recovery = OfflineChatConnectionRecovery(connector, receiver, order, reactions)
    checks: list[CommunicationCheck] = []
    blocked = 0
    second = platforms[-1]
    events = (
        (platforms[0], '가상A', '안녕하세요'),
        (second, '가상B', '안녕하세요'),
        (platforms[0], '가상A', '안녕하세요'),
        (second, '가상B', '다음 질문'),
        (platforms[0], '가상C', '다른 시청자'),
        (second, '가상A', '플랫폼별 맥락'),
    )

    def verify(label: str, ok: bool, detail: str = '') -> None:
        checks.append(CommunicationCheck(label, bool(ok), detail))
        if not ok:
            raise AssertionError(label + ': ' + detail)

    def denied(action) -> bool:
        """A rejected synthetic operation must not change the successful history."""
        nonlocal blocked
        before = (receiver.snapshot().buffered, reactions.snapshot().responded)
        try:
            action()
        except ValueError:
            blocked += 1
            return before == (receiver.snapshot().buffered, reactions.snapshot().responded)
        return False

    try:
        verify('연결 전 수신 차단', denied(lambda: receiver.inject(*events[0])))
        connector.connect()
        receiver.attach(connector)
        verify('선택 플랫폼 가상 연결 및 수신 준비',
               connector.snapshot().connected == platforms and receiver.snapshot().attached)
        for event in events[:4]:
            receiver.inject(*event)
        order.sync()
        reactions.sync()
        reactions.enable_viewer_context()
        verify('다중 시청자·동일 내용 접수 및 전역 FIFO 동기화',
               tuple(e.ordinal for e in reactions.snapshot().staged) == (1, 2, 3, 4)
               and receiver.snapshot().buffered[0].text == receiver.snapshot().buffered[2].text)
        reactions.reply_next()
        verify('첫 채팅 응답 성공',
               tuple(x.event.ordinal for x in reactions.snapshot().responded) == (1,))
        verify('모의 응답 실패가 선두·대기열을 보존',
               denied(lambda: reactions.reply_next(simulate_failure=True))
               and reactions.snapshot().blocked
               and tuple(e.ordinal for e in reactions.snapshot().pending) == (2, 3, 4))
        verify('응답 실패 후 자동 재시도 없음',
               denied(reactions.reply_next) and reactions.snapshot().attempts == 2)
        reactions.resume()
        reactions.reply_next()
        verify('수동 재개 후 FIFO 진행',
               tuple(x.event.ordinal for x in reactions.snapshot().responded) == (1, 2))
        before_outage = receiver.snapshot().buffered
        recovery.inject_outage(connector)
        verify('장애 발생 시 새 수신 차단 및 기존 접수 보존',
               denied(lambda: receiver.inject(*events[4]))
               and receiver.snapshot().buffered == before_outage)
        failed = recovery.reconnect(connector, fail_handshake=True)
        verify('가상 재연결 실패 · 연결 유지 없음',
               failed.failed_attempts == 1 and not failed.connected and not failed.attached)
        verify('재연결 실패 뒤 자동 재시도 없음',
               connector.snapshot().attempts == 2 and
               denied(lambda: receiver.inject(*events[4])))
        recovery.reconnect(connector)
        verify('가상 재연결만으로 수신 자동 재준비 금지',
               denied(lambda: receiver.inject(*events[4]))
               and not receiver.snapshot().attached)
        restored = recovery.reattach(connector)
        verify('수동 수신 재준비 및 장애 전 기록 보존',
               restored.recovery_complete and receiver.snapshot().buffered == before_outage)
        for event in events[4:]:
            receiver.inject(*event)
        order.sync()
        reactions.sync()
        reactions.reply_batch()
        state = reactions.snapshot()
        verify('장애 복구 후 모든 메시지 순서대로 1회 응답',
               state.all_responded and len(state.responded) == len(events)
               and tuple(item.event.ordinal for item in state.responded) == tuple(range(1, len(events) + 1))
               and tuple(item.event.platform for item in state.responded) == tuple(e[0] for e in events)
               and tuple(item.event.text for item in state.responded) == tuple(e[2] for e in events))
        verify('선택 플랫폼+시청자별 성공 응답 맥락 격리',
               len(trace.calls) == len(events) and all(
                   (item.sender, item.text) == (events[index][1], events[index][2]) and
                   tuple((entry.input.sender, entry.input.text) for entry in history) ==
                   tuple((old.event.sender, old.event.text) for old in state.responded[:index]
                         if (old.event.platform, old.event.sender) == (events[index][0], events[index][1]))[-8:]
                   for index, (item, history) in enumerate(trace.calls)))
        verify('최종 가상 연결/수신 상태 및 응답 무누락',
               recovery.snapshot(connector).recovery_complete and
               receiver.snapshot().attached and not state.pending and not state.unsynced and state.attempts == 7)
    except (AssertionError, ValueError, TypeError, IndexError) as exc:
        # Do not mark a partially executed drill as a success.
        if not checks or checks[-1].passed:
            checks.append(CommunicationCheck('모의 시나리오 실행 중단', False,
                                             f'{type(exc).__name__}: {exc}'))
    return CommunicationAuditReport(platforms, tuple(checks),
                                    len(receiver.snapshot().buffered),
                                    len(reactions.snapshot().responded), blocked,
                                    recovery.snapshot(connector).failed_attempts)
