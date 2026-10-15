"""Original stage 062: explicit, memory-only simulated platform chat reception.

This is not a live receiver. There are no background loops, sockets, timers,
credentials, real timestamps, database writes, or automatic processing.
"""
from __future__ import annotations

from dataclasses import dataclass

from .platform_chat_connector import OfflinePlatformChatConnector, PLATFORM_CODES

MAX_RECEIVED = 500
MAX_SENDER = 100
MAX_TEXT = 4000


@dataclass(frozen=True)
class MockReceivedChat:
    ordinal: int  # local manual acceptance order; NOT a platform message ID
    platform: str
    sender: str
    text: str


@dataclass(frozen=True)
class ReceiveSnapshot:
    buffered: tuple[MockReceivedChat, ...]
    attached: bool
    accepted_count: int
    capacity: int = MAX_RECEIVED

    @property
    def mock_only(self) -> bool:
        return True

    def describe(self) -> str:
        return '\n'.join((
            '원본 062 · 채팅 메시지 수신 구조 · 수동 오프라인 모의',
            f'가상 수신 준비: {"예" if self.attached else "아니오"}',
            f'수동 접수: {self.accepted_count}건 / 메모리 보관: {len(self.buffered)}/{self.capacity}건',
            '실제 플랫폼에서 받은 메시지: 0건 / 자동 실시간 수신: 없음',
            '메시지 순서·중복 검증·AI 답변·방송 송출은 별도 단계입니다.',
            '데이터는 이 실행의 메모리에만 있으며 앱 종료 시 사라집니다.',
        ))


class OfflineChatReceiveBuffer:
    """Explicit mock ingress, tied to an already manually connected 061 session.

    A platform selection change or disconnect makes the binding invalid, but
    does not silently erase accepted messages. Duplicates are retained. No
    messages are processed, filtered or automatically retried by this stage.
    """

    def __init__(self) -> None:
        self._connector: OfflinePlatformChatConnector | None = None
        self._buffer: list[MockReceivedChat] = []

    def attach(self, connector: OfflinePlatformChatConnector) -> ReceiveSnapshot:
        if not isinstance(connector, OfflinePlatformChatConnector):
            raise ValueError('가상 연결 계약이 올바르지 않습니다.')
        state = connector.snapshot()
        if not state.connected or state.connected != state.selected:
            raise ValueError('먼저 61단계 탭에서 가상 연결을 수동으로 시작하세요.')
        self._connector = connector
        return self.snapshot()

    def detach(self) -> ReceiveSnapshot:
        self._connector = None
        return self.snapshot()

    def _active_platforms(self) -> tuple[str, ...]:
        if self._connector is None:
            return ()
        state = self._connector.snapshot()
        return state.connected if state.connected == state.selected else ()

    def snapshot(self) -> ReceiveSnapshot:
        return ReceiveSnapshot(tuple(self._buffer), bool(self._active_platforms()), len(self._buffer))

    def inject(self, platform: str, sender: str, text: str) -> MockReceivedChat:
        """Manually accept exactly one *synthetic* chat; no I/O or response."""
        if type(platform) is not str or platform not in PLATFORM_CODES:
            raise ValueError('지원하지 않는 플랫폼입니다.')
        if type(sender) is not str or not 1 <= len(sender.strip()) <= MAX_SENDER:
            raise ValueError('모의 닉네임은 1~100자여야 합니다.')
        if type(text) is not str or not 1 <= len(text.strip()) <= MAX_TEXT:
            raise ValueError('모의 채팅 내용은 1~4000자여야 합니다.')
        if platform not in self._active_platforms():
            raise ValueError('해당 플랫폼의 수동 가상 연결/수신 준비가 필요합니다.')
        if len(self._buffer) >= MAX_RECEIVED:
            raise ValueError('모의 수신함이 가득 찼습니다. 기존 메시지는 삭제하지 않았습니다.')
        event = MockReceivedChat(len(self._buffer) + 1, platform, sender.strip(), text.strip())
        self._buffer.append(event)
        return event
