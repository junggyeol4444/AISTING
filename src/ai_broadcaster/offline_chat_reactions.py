"""Original stage 065: operator-triggered replies for EVERY staged mock chat.

Bridges existing 062 receiver and 063 FIFO queue to the existing 022 mock
reply port (also used by 037). No live platform, real LLM, background polling,
automatic retries, delay timers, file writes, audio or streaming.
"""
from __future__ import annotations

from dataclasses import dataclass

from .core_execution import LocalReplyPort, MockCoreReplyPort, MAX_REPLY, MAX_CONTEXT_TURNS
from .core_ports import CoreInput, CoreReply
from .offline_chat_receiver import OfflineChatReceiveBuffer, MockReceivedChat
from .offline_chat_order import OfflineChatOrder

MAX_REACTION_BATCH = 50


@dataclass(frozen=True)
class MockReaction:
    event: MockReceivedChat
    text: str


@dataclass(frozen=True)
class ReactionSnapshot:
    received: int
    staged: tuple[MockReceivedChat, ...]
    responded: tuple[MockReaction, ...]
    pending: tuple[MockReceivedChat, ...]
    unsynced: int
    blocked: bool
    reason: str
    attempts: int
    mock_only: bool = True

    @property
    def all_responded(self) -> bool:
        return self.received > 0 and not self.pending and not self.unsynced and not self.blocked \
            and len(self.responded) == self.received

    def describe(self) -> str:
        lines = [
            '원본 065 · 모든 채팅 기본 반응 구조 · 수동 오프라인 모의',
            f'수동 접수 {self.received}건 / 순서 동기화 {len(self.staged)}건 / 모의 응답 {len(self.responded)}건 / 대기 {len(self.pending)}건',
            f'미동기화 {self.unsynced}건 (반응 누락으로 간주하지 않음) / 시도 {self.attempts}회',
            f'처리 상태: {"실패 중단 · 수동 재개 필요" if self.blocked else "대기"}',
            '내용이 같은 채팅도 각 접수 순번대로 1회씩 모의 응답하며 임의 선별·인위적 지연을 넣지 않습니다.',
            '실제 플랫폼 채팅 0건 · 실제 AI 생성 0건 · 실제 음성·아바타·방송 없음',
            '62/63단계 원본 기록과 기존 설정/사용자 파일은 수정하지 않습니다.',
        ]
        if self.reason:
            lines.append('중단 이유: ' + self.reason)
        if self.all_responded:
            lines.append('현재 수동 접수된 모든 모의 채팅에 응답 구조 확인 (실제 방송 검증 아님)')
        lines.extend(f'응답 #{item.event.ordinal} [{item.event.platform}] {item.event.sender}: {item.text[:140]}'
                     for item in self.responded[-10:])
        lines.extend(f'대기 #{event.ordinal} [{event.platform}] {event.sender}: {event.text[:100]}'
                     for event in self.pending[:10])
        return '\n'.join(lines)


class OfflineChatReactions:
    """An explicit, bounded FIFO mock response view of 062/063.

    The 063 acknowledgement cursor is deliberately separate: confirming a
    sequence number must not falsely count as a generated response.
    """

    def __init__(self, receiver: OfflineChatReceiveBuffer, order: OfflineChatOrder,
                 *, reply_port: LocalReplyPort | None = None) -> None:
        if not isinstance(receiver, OfflineChatReceiveBuffer):
            raise ValueError('62단계 수신함이 필요합니다.')
        if not isinstance(order, OfflineChatOrder) or order._receiver is not receiver:
            raise ValueError('같은 수신함의 63단계 순서 관리가 필요합니다.')
        self._receiver = receiver
        self._order = order
        self._reply_port = reply_port if reply_port is not None else MockCoreReplyPort()
        self._staged: list[MockReceivedChat] = []
        self._replied: list[MockReaction] = []
        self._blocked = False
        self._reason = ''
        self._attempts = 0
        self._viewer_context_enabled = False  # 067: explicit opt-in before first response

    def snapshot(self) -> ReactionSnapshot:
        received = self._receiver.snapshot().buffered
        staged = tuple(self._staged)
        return ReactionSnapshot(len(received), staged, tuple(self._replied),
                                staged[len(self._replied):], max(0, len(received) - len(staged)),
                                self._blocked, self._reason, self._attempts)

    def _validate_source(self) -> tuple[MockReceivedChat, ...]:
        received = self._receiver.snapshot().buffered
        ordered = self._order.snapshot().queued
        staged = tuple(self._staged)
        if received[:len(ordered)] != ordered or len(received) < len(ordered):
            raise ValueError('수신함과 순서 관리 기록이 일치하지 않습니다. 응답을 차단합니다.')
        if ordered[:len(staged)] != staged or len(ordered) < len(staged):
            raise ValueError('이미 동기화한 채팅 기록이 변경되었습니다. 응답을 차단합니다.')
        if any(not isinstance(event, MockReceivedChat) or type(event.ordinal) is not int
               or event.ordinal != i for i, event in enumerate(ordered, start=1)):
            raise ValueError('메시지 순번이 잘못되었습니다. 응답을 차단합니다.')
        return ordered

    def sync(self) -> ReactionSnapshot:
        """Explicit sync only, all-or-nothing; never silently ingest a message."""
        ordered = self._validate_source()
        self._staged.extend(ordered[len(self._staged):])
        return self.snapshot()

    @property
    def viewer_context_enabled(self) -> bool:
        return self._viewer_context_enabled

    def enable_viewer_context(self) -> None:
        """067: switch only before any reply; never mix history policies mid-session."""
        self._validate_source()
        if self._replied:
            raise ValueError('이미 응답한 기록이 있어 맥락 방식을 변경할 수 없습니다. 새 모의 세션이 필요합니다.')
        if self._blocked:
            raise ValueError('응답 오류 중단 상태입니다. 먼저 수동 재개하세요.')
        self._viewer_context_enabled = True

    def viewer_history(self, event: MockReceivedChat) -> tuple[CoreReply, ...]:
        """Successful prior replies for this exact (platform, sender), newest eight."""
        self._validate_source()
        if not isinstance(event, MockReceivedChat) or event not in self._staged:
            raise ValueError('동기화된 수신 기록에서만 시청자 맥락을 조회할 수 있습니다.')
        matches = [item for item in self._replied
                   if item.event.platform == event.platform and item.event.sender == event.sender
                   and item.event.ordinal < event.ordinal]
        return tuple(CoreReply(CoreInput(item.event.sender, item.event.text), item.text)
                     for item in matches[-MAX_CONTEXT_TURNS:])

    def reply_next(self, *, simulate_failure: bool = False) -> MockReaction:
        if type(simulate_failure) is not bool:
            raise ValueError('모의 실패 선택값이 올바르지 않습니다.')
        self._validate_source()
        if self._order.snapshot().paused:
            raise ValueError('63단계 순서 관리가 중단 상태입니다. 먼저 수동 재개하세요.')
        if self._blocked:
            raise ValueError('모의 응답 오류 중단 상태입니다. 운영자가 수동 재개해야 합니다.')
        if len(self._replied) >= len(self._staged):
            raise ValueError('응답할 동기화 채팅이 없습니다. 먼저 수동 동기화하세요.')
        event = self._staged[len(self._replied)]
        self._attempts += 1
        if simulate_failure:
            self._blocked = True
            self._reason = '모의 응답 실패 · 현재 채팅 보존'
            raise ValueError(self._reason)
        try:
            history = (self.viewer_history(event) if self._viewer_context_enabled else
                       tuple(CoreReply(CoreInput(item.event.sender, item.event.text), item.text)
                             for item in self._replied[-MAX_CONTEXT_TURNS:]))
            response = self._reply_port.generate(CoreInput(event.sender, event.text), history)
        except Exception:
            self._blocked = True
            self._reason = '모의 응답 생성 실패 · 오류 상세 내용 비공개'
            raise ValueError(self._reason) from None
        if type(response) is not str or not response.strip() or len(response) > MAX_REPLY:
            self._blocked = True
            self._reason = '모의 응답 형식 오류 · 현재 채팅 보존'
            raise ValueError(self._reason)
        item = MockReaction(event, response)
        self._replied.append(item)
        return item

    def reply_batch(self, count: int = MAX_REACTION_BATCH) -> ReactionSnapshot:
        if type(count) is not int or not 1 <= count <= MAX_REACTION_BATCH:
            raise ValueError(f'한 번에 1~{MAX_REACTION_BATCH}건만 수동 처리할 수 있습니다.')
        for _ in range(min(count, len(self.snapshot().pending))):
            self.reply_next()  # on failure, retain head and stop; no automatic retry
        return self.snapshot()

    def resume(self) -> ReactionSnapshot:
        if not self._blocked:
            raise ValueError('재개할 모의 응답 실패가 없습니다.')
        self._blocked = False
        self._reason = ''
        return self.snapshot()
