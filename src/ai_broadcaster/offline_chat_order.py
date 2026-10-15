"""Stage 063: manual FIFO ordering of stage-062 synthetic chat events.

No network, timer, automatic reply, persistence or background processing.
The queue is a *view* of immutable manually accepted events, not a new receiver.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_chat_receiver import OfflineChatReceiveBuffer, MockReceivedChat


@dataclass(frozen=True)
class OrderSnapshot:
    queued: tuple[MockReceivedChat, ...]
    processed: tuple[MockReceivedChat, ...]
    pending: tuple[MockReceivedChat, ...]
    paused: bool
    mock_only: bool = True

    def describe(self) -> str:
        return (f'원본 063 · 수동 FIFO 처리 순서 모의\n'
                f'동기화 {len(self.queued)}건 · 순서 확인 {len(self.processed)}건 · '
                f'미처리 {len(self.pending)}건 · '
                f'{"오류 중단/수동 재개 필요" if self.paused else "대기"}\n'
                '원본 수신 순번 보존 / 중복 내용도 별도 건 / 실제 플랫폼 메시지 0건\n'
                '순서 확인은 AI 응답·방송 처리 완료를 의미하지 않습니다.')


class OfflineChatOrder:
    """Manually sync and acknowledge a strictly ordered prefix of mock ingress."""

    def __init__(self, receiver: OfflineChatReceiveBuffer) -> None:
        if not isinstance(receiver, OfflineChatReceiveBuffer):
            raise ValueError('62단계 모의 수신함이 필요합니다.')
        self._receiver = receiver
        self._events: list[MockReceivedChat] = []
        self._cursor = 0
        self._paused = False

    def snapshot(self) -> OrderSnapshot:
        events = tuple(self._events)
        return OrderSnapshot(events, events[:self._cursor], events[self._cursor:], self._paused)

    def sync(self) -> OrderSnapshot:
        """Manual append-only sync; reject mutations/gaps without changing state."""
        incoming = self._receiver.snapshot().buffered
        prefix = tuple(self._events)
        if incoming[:len(prefix)] != prefix or len(incoming) < len(prefix):
            raise ValueError('수신함 기록이 변경되었습니다. 기존 처리 순서를 유지합니다.')
        if any(event.ordinal != index for index, event in enumerate(incoming, start=1)):
            raise ValueError('수신 순번에 누락/역전이 있습니다. 기존 처리 순서를 유지합니다.')
        self._events.extend(incoming[len(prefix):])
        return self.snapshot()

    def acknowledge_next(self, *, simulate_failure: bool = False) -> MockReceivedChat:
        """Manually mark next event as order-checked; never call an AI or drop it."""
        if self._paused:
            raise ValueError('오류 중단 상태입니다. 운영자가 수동 재개해야 합니다.')
        if self._cursor >= len(self._events):
            raise ValueError('순서 확인할 미처리 채팅이 없습니다. 먼저 수동 동기화하세요.')
        if type(simulate_failure) is not bool:
            raise ValueError('모의 실패 선택값이 올바르지 않습니다.')
        if simulate_failure:
            self._paused = True
            raise ValueError('모의 처리 실패 · 현재 채팅 보존 · 수동 재개 필요')
        event = self._events[self._cursor]
        self._cursor += 1
        return event

    def resume(self) -> OrderSnapshot:
        """Explicit operator resume, with pending events untouched."""
        if not self._paused:
            raise ValueError('재개할 중단 상태가 없습니다.')
        self._paused = False
        return self.snapshot()
