"""Original 093: manual offline substring recall and next MOCK-session handoff.

No automated gathering, AI calls, prompt injection, persistence, live streaming,
filesystem searches, background tasks or external network I/O.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_broadcast_journal import _line
from .offline_chat import ChatMessage, MockReplyGenerator
from .offline_past_broadcast_memory import OfflinePastBroadcastMemory

MAX_QUERY = 100
MAX_RESULTS = 20
MAX_HANDOFF_EXCERPTS = 5


@dataclass(frozen=True)
class RecallHit:
    source_checksum_sha256: str
    session_label: str
    matching_excerpts: tuple[str, ...]
    includes_mock_chat: bool


@dataclass(frozen=True)
class MockNextSessionContext:
    session_label: str
    source_checksum_sha256: str
    excerpts: tuple[str, ...]
    mock_only: bool = True
    model_connected: bool = False
    automatically_injected: bool = False
    actual_broadcast_verified: bool = False
    approval: str = 'pending'

    def preview(self) -> str:
        return ('[다음 *가상* 방송 참고 메모 · 운영자 수동 선택 · AI 전달 없음]\n'
                + f'출처: {self.session_label} (SHA256 {self.source_checksum_sha256[:12]}…)\n'
                + '\n'.join(f'- {value}' for value in self.excerpts)
                + '\n[가상 기억은 검증된 실제 사건이나 실제 시청자 발언이 아닙니다.]')


class OfflineMemoryRecall:
    """Snapshot-bound manual searching; stale results must never be handed off."""

    def __init__(self, memory: OfflinePastBroadcastMemory) -> None:
        if type(memory) is not OfflinePastBroadcastMemory:
            raise ValueError('092 가상 기억 카드 보관함이 필요합니다.')
        self._memory = memory
        self._hits: tuple[RecallHit, ...] = ()
        self._fingerprint: str | None = None
        self._context: MockNextSessionContext | None = None

    @property
    def hits(self) -> tuple[RecallHit, ...]:
        if self._fingerprint != self._memory.preview()['checksum_sha256']:
            return ()
        return self._hits

    @property
    def context(self) -> MockNextSessionContext | None:
        if self._fingerprint != self._memory.preview()['checksum_sha256']:
            return None
        return self._context

    def clear(self) -> None:
        self._hits = ()
        self._fingerprint = None
        self._context = None

    def search(self, query: str) -> tuple[RecallHit, ...]:
        self.clear()
        query = _line(query, '수동 기억 검색어', MAX_QUERY)
        words = query.casefold().split()
        if not 1 <= len(words) <= 8:
            raise ValueError('검색어는 공백 구분 최대 8단어까지 가능합니다.')
        results: list[RecallHit] = []
        for card in self._memory.cards:
            searchable = (' '.join((card.session_label, *card.excerpts))).casefold()
            if all(word in searchable for word in words):
                matching = tuple(excerpt for excerpt in card.excerpts
                                 if any(word in excerpt.casefold() for word in words))
                results.append(RecallHit(card.source_checksum_sha256, card.session_label,
                                         matching or card.excerpts[:1], card.includes_mock_chat))
                if len(results) >= MAX_RESULTS:
                    break
        self._hits = tuple(results)
        self._fingerprint = self._memory.preview()['checksum_sha256']
        return self._hits

    def prepare_for_next_mock_session(self, index: int) -> MockNextSessionContext:
        self._context = None
        if type(index) is not int or not 0 <= index < len(self.hits):
            raise ValueError('현재 검색 결과에서 운영자가 선택한 가상 기억만 연결할 수 있습니다.')
        hit = self._hits[index]
        card = next((card for card in self._memory.cards
                     if card.source_checksum_sha256 == hit.source_checksum_sha256), None)
        if card is None:
            raise ValueError('선택한 가상 기억이 변경되어 연결을 중단했습니다.')
        # Do not broaden to other cards or excluded chats: only the chosen card.
        chosen = hit.matching_excerpts[:MAX_HANDOFF_EXCERPTS]
        self._context = MockNextSessionContext(card.session_label, card.source_checksum_sha256,
                                               chosen)
        return self._context

    def rehearse_next_mock_reply(self, question: str) -> str:
        """Explicit next synthetic-turn preview through existing 091-era mock reply port.

        Selected memory goes into an ordinary bounded *mock user text*, never a
        system prompt or AI/network call. This does not validate recollection.
        """
        context = self.context
        if context is None:
            raise ValueError('수동으로 검색·선택한 최신 가상 기억이 필요합니다.')
        question = _line(question, '다음 가상 방송 질문', 180)
        prior = ' / '.join(context.excerpts)[:200]
        mock_message = f'[가상 이전 기록, 실제 사실 아님: {prior}] 다음 가상 방송: {question}'
        return MockReplyGenerator().generate(ChatMessage('모의 운영자', mock_message), [])
