"""Original 092: operator-selected MOCK past-broadcast memory cards, offline only.

Never scans folders, captures real data, queries an AI, or injects prompts into it.
Original 093 covers searching and attaching memories to future dialogues.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from .offline_broadcast_journal import OfflineBroadcastJournal, _line

SCHEMA = 'aisting_offline_mock_past_broadcast_memory_v1'
MAX_CARDS = 20
MAX_EXCERPTS = 12
MAX_FILE_BYTES = 300_000


def _digest(body: dict) -> str:
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class MemoryCard:
    session_label: str
    source_checksum_sha256: str
    excerpts: tuple[str, ...]
    includes_mock_chat: bool


class OfflinePastBroadcastMemory:
    """Opt-in collection of compact synthetic-session notes, never real memory AI."""

    def __init__(self) -> None:
        self._cards: list[MemoryCard] = []

    @property
    def cards(self) -> tuple[MemoryCard, ...]:
        return tuple(self._cards)

    def add_journal(self, journal: OfflineBroadcastJournal, *, include_mock_chat: bool = False) -> MemoryCard:
        if type(journal) is not OfflineBroadcastJournal or type(include_mock_chat) is not bool:
            raise ValueError('검증된 가상 회차와 명시적인 모의 채팅 포함 선택이 필요합니다.')
        if not journal.entries:
            raise ValueError('내용이 없는 가상 회차는 기억 카드로 만들 수 없습니다.')
        if len(self._cards) >= MAX_CARDS:
            raise ValueError('기억 카드 최대 20개에 도달했습니다.')
        checksum = journal.preview()['checksum_sha256']
        if any(card.source_checksum_sha256 == checksum for card in self._cards):
            raise ValueError('같은 가상 회차 원본은 중복 보관하지 않습니다.')
        rows = [entry for entry in journal.entries if include_mock_chat or entry.kind != 'chat_mock']
        if not rows:
            raise ValueError('운영자 사건 메모가 없습니다. 모의 채팅 포함 여부를 명시적으로 선택하세요.')
        excerpts = tuple(f'{entry.kind}: {entry.text}' for entry in rows[:MAX_EXCERPTS])
        card = MemoryCard(journal.session_label, checksum, excerpts, include_mock_chat)
        self._validate_card(card)
        self._cards.append(card)
        return card

    @staticmethod
    def _validate_card(card: MemoryCard) -> None:
        if type(card) is not MemoryCard:
            raise ValueError('기억 카드 구조가 올바르지 않습니다.')
        _line(card.session_label, '가상 회차 이름', 80)
        if (type(card.source_checksum_sha256) is not str
                or len(card.source_checksum_sha256) != 64
                or any(c not in '0123456789abcdef' for c in card.source_checksum_sha256)):
            raise ValueError('원본 체크섬이 올바르지 않습니다.')
        if type(card.includes_mock_chat) is not bool:
            raise ValueError('모의 채팅 포함 여부가 올바르지 않습니다.')
        if (type(card.excerpts) is not tuple
                or not 1 <= len(card.excerpts) <= MAX_EXCERPTS):
            raise ValueError('기억 카드 요약 항목 수가 올바르지 않습니다.')
        for excerpt in card.excerpts:
            value = _line(excerpt, '기억 요약 문구', 1020)
            if not any(value.startswith(kind + ': ') for kind in
                       ('chat_mock', 'game_mock', 'support_mock', 'operator_note', 'other_mock')):
                raise ValueError('지원하지 않는 기억 기록 유형입니다.')
            if value.startswith('chat_mock: ') and not card.includes_mock_chat:
                raise ValueError('명시적으로 선택되지 않은 모의 채팅이 섞였습니다.')

    def remove_card(self, index: int) -> None:
        if type(index) is not int or not 0 <= index < len(self._cards):
            raise ValueError('삭제할 기억 카드 번호가 올바르지 않습니다.')
        del self._cards[index]

    def preview(self) -> dict:
        body = {
            'schema': SCHEMA, 'stage': 92, 'mock_only': True,
            'auto_collected': False, 'real_platform_collected': False,
            'ai_connected': False, 'actual_broadcast_verified': False,
            'approval': 'pending',
            'cards': [dict(asdict(card), excerpts=list(card.excerpts)) for card in self._cards],
        }
        return dict(body, checksum_sha256=_digest(body))

    def export_json(self, destination: Path) -> None:
        if not isinstance(destination, Path):
            raise ValueError('운영자가 지정한 로컬 파일 경로만 사용할 수 있습니다.')
        if not self._cards:
            raise ValueError('저장할 기억 카드가 없습니다.')
        raw = (json.dumps(self.preview(), ensure_ascii=False,
                          indent=2, sort_keys=True) + '\n').encode('utf-8')
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError('기억 카드 저장 파일이 너무 큽니다.')
        with destination.open('xb') as output:
            output.write(raw)

    @classmethod
    def load_json(cls, source: Path) -> 'OfflinePastBroadcastMemory':
        if not isinstance(source, Path):
            raise ValueError('운영자가 선택한 로컬 파일만 읽을 수 있습니다.')
        with source.open('rb') as handle:
            raw = handle.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError('기억 파일의 크기 제한을 초과했습니다.')
        try:
            data = json.loads(raw.decode('utf-8'))
        except (UnicodeError, ValueError) as exc:
            raise ValueError('기억 파일 JSON을 읽을 수 없습니다.') from exc
        expected = set(cls().preview())
        if type(data) is not dict or set(data) != expected:
            raise ValueError('기억 파일의 필드 구성이 올바르지 않습니다.')
        rows = data['cards']
        if type(rows) is not list or len(rows) > MAX_CARDS:
            raise ValueError('기억 카드 개수가 잘못됐습니다.')
        restored = cls()
        seen: set[str] = set()
        for row in rows:
            if type(row) is not dict or set(row) != set(asdict(MemoryCard('', '', (), False))):
                raise ValueError('기억 카드 필드 구성이 올바르지 않습니다.')
            if type(row['excerpts']) is not list:
                raise ValueError('기억 요약 문구 목록이 올바르지 않습니다.')
            card = MemoryCard(row['session_label'], row['source_checksum_sha256'],
                              tuple(row['excerpts']), row['includes_mock_chat'])
            cls._validate_card(card)
            if card.source_checksum_sha256 in seen:
                raise ValueError('중복 가상 회차 기억이 발견됐습니다.')
            seen.add(card.source_checksum_sha256)
            restored._cards.append(card)
        if restored.preview() != data:
            raise ValueError('기억 파일 손상 또는 실제 방송/승인 플래그 변경을 감지했습니다.')
        return restored
