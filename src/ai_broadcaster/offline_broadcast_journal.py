"""Original 091: operator-opt-in offline MOCK dialogue/event journal.

No real input capture, live chat, OS clock, background save, remote IO or memory
retrieval. Only manually received synthetic chat may be imported on button click.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from .offline_chat_receiver import ReceiveSnapshot, MockReceivedChat
from .offline_settings import PLATFORMS

MAX_ENTRIES = 500
MAX_FILE_BYTES = 3_000_000
EVENT_KINDS = ('game_mock', 'support_mock', 'operator_note', 'other_mock')
SCHEMA = 'aisting_offline_mock_broadcast_journal_v1'


def _line(value: str, label: str, limit: int) -> str:
    if type(value) is not str or not 1 <= len(value.strip()) <= limit:
        raise ValueError(f'{label}: 1~{limit}자 문자열이 필요합니다.')
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f'{label}: 제어 문자는 허용되지 않습니다.')
    return value.strip()


@dataclass(frozen=True)
class JournalEntry:
    index: int
    kind: str
    text: str
    platform: str = ''
    sender_mock: str = ''
    source_ordinal: int | None = None


class OfflineBroadcastJournal:
    """Synthetic diary with explicit one-shot export and strict import verification."""

    def __init__(self, session_label: str = '가상 방송 회차') -> None:
        self.session_label = _line(session_label, '가상 회차 이름', 80)
        self._entries: list[JournalEntry] = []
        self._source_chats: tuple[MockReceivedChat, ...] = ()

    @property
    def entries(self) -> tuple[JournalEntry, ...]:
        return tuple(self._entries)

    @property
    def imported_chats(self) -> int:
        return len(self._source_chats)

    def import_mock_chats(self, snapshot: ReceiveSnapshot) -> int:
        """Manually import new synthetic messages once, preserving duplicate content."""
        if type(snapshot) is not ReceiveSnapshot or snapshot.mock_only is not True:
            raise ValueError('실제 채팅이 아닌 062단계 모의 수신 기록만 수동 가져올 수 있습니다.')
        incoming = snapshot.buffered
        if type(incoming) is not tuple or snapshot.accepted_count != len(incoming):
            raise ValueError('모의 수신 기록 개수가 일치하지 않습니다.')
        if incoming[:len(self._source_chats)] != self._source_chats:
            raise ValueError('기존에 가져온 채팅 기록이 변경됐습니다. 기록을 보존하고 중단합니다.')
        if len(self._entries) + len(incoming) - len(self._source_chats) > MAX_ENTRIES:
            raise ValueError('가상 기록 용량을 초과합니다. 기존 기록은 보존합니다.')
        for ordinal, chat in enumerate(incoming, 1):
            if (type(chat) is not MockReceivedChat or type(chat.ordinal) is not int
                    or chat.ordinal != ordinal or type(chat.platform) is not str
                    or chat.platform not in PLATFORMS.values()):
                raise ValueError('모의 수신 순번 또는 플랫폼이 올바르지 않습니다.')
            _line(chat.sender, '모의 닉네임', 100)
            _line(chat.text, '모의 채팅', 4000)
        fresh = incoming[len(self._source_chats):]
        for chat in fresh:
            self._entries.append(JournalEntry(len(self._entries) + 1, 'chat_mock', chat.text,
                                              chat.platform, chat.sender, chat.ordinal))
        self._source_chats = incoming
        return len(fresh)

    def add_mock_event(self, kind: str, text: str) -> JournalEntry:
        if type(kind) is not str or kind not in EVENT_KINDS:
            raise ValueError('가상 사건 유형이 올바르지 않습니다.')
        note = _line(text, '가상 사건·운영자 메모', 1000)
        if len(self._entries) >= MAX_ENTRIES:
            raise ValueError('가상 기록 용량을 초과합니다. 기존 기록은 보존합니다.')
        entry = JournalEntry(len(self._entries) + 1, kind, note)
        self._entries.append(entry)
        return entry

    def _body(self) -> dict:
        return {
            'schema': SCHEMA, 'stage': 91, 'session_label_operator_input': self.session_label,
            'mock_only': True, 'actual_broadcast_verified': False,
            'real_platform_collected': False, 'memory_integrated': False,
            'auto_saved': False, 'approval': 'pending',
            'entries': [asdict(entry) for entry in self._entries],
            'source_chat_count': len(self._source_chats),
        }

    def preview(self) -> dict:
        body = self._body()
        digest = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                           separators=(',', ':')).encode('utf-8')).hexdigest()
        return dict(body, checksum_sha256=digest)

    def export_json(self, destination: Path) -> None:
        """Only explicit call writes; never mkdir, enumerate user files, or overwrite."""
        if not isinstance(destination, Path):
            raise ValueError('운영자가 지정한 저장 파일 경로가 필요합니다.')
        if not self._entries:
            raise ValueError('저장할 모의 채팅·사건 기록이 없습니다.')
        encoded = (json.dumps(self.preview(), ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
        if len(encoded) > MAX_FILE_BYTES:
            raise ValueError('파일 크기 한도를 초과합니다.')
        with destination.open('xb') as output:
            output.write(encoded)

    @classmethod
    def load_json(cls, source: Path) -> 'OfflineBroadcastJournal':
        """Manually open one supplied file and verify its structure and checksum.

        This only restores a draft; it does NOT provide long-term memory search.
        """
        if not isinstance(source, Path):
            raise ValueError('운영자가 지정한 파일만 읽을 수 있습니다.')
        with source.open('rb') as input_file:
            raw = input_file.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError('기록 파일 크기 제한을 초과했습니다.')
        try:
            stored = json.loads(raw.decode('utf-8'))
        except (UnicodeError, ValueError) as exc:
            raise ValueError('기록 파일 JSON 형식이 올바르지 않습니다.') from exc
        if type(stored) is not dict or set(stored) != set(cls().preview()):
            raise ValueError('기록 파일의 필드 구성이 올바르지 않습니다.')
        journal = cls(stored['session_label_operator_input'])
        entries = stored['entries']
        if type(entries) is not list or len(entries) > MAX_ENTRIES:
            raise ValueError('기록 항목 개수가 잘못됐습니다.')
        source_chats: list[MockReceivedChat] = []
        for i, row in enumerate(entries, 1):
            if type(row) is not dict or set(row) != set(asdict(JournalEntry(1, '', ''))):
                raise ValueError('기록 항목 필드가 올바르지 않습니다.')
            if type(row['index']) is not int or row['index'] != i:
                raise ValueError('기록 순서가 변경됐습니다.')
            kind, platform, sender, ordinal = (row[k] for k in ('kind', 'platform', 'sender_mock', 'source_ordinal'))
            if kind == 'chat_mock':
                if (type(platform) is not str or platform not in PLATFORMS.values()
                        or type(ordinal) is not int or ordinal != len(source_chats) + 1):
                    raise ValueError('가상 채팅의 플랫폼·원본 순번이 잘못됐습니다.')
                sender = _line(sender, '모의 닉네임', 100)
                content = _line(row['text'], '모의 채팅', 4000)
                source_chats.append(MockReceivedChat(ordinal, platform, sender, content))
            elif type(kind) is str and kind in EVENT_KINDS:
                if platform != '' or sender != '' or ordinal is not None:
                    raise ValueError('가상 사건에 외부 채팅 정보가 혼입됐습니다.')
                content = _line(row['text'], '가상 사건', 1000)
            else:
                raise ValueError('지원하지 않는 기록 유형입니다.')
            journal._entries.append(JournalEntry(i, kind, content, platform, sender, ordinal))
        journal._source_chats = tuple(source_chats)
        if (type(stored['source_chat_count']) is not int or stored['source_chat_count'] != len(source_chats)
                or journal.preview() != stored):
            raise ValueError('기록 무결성 검사 실패 또는 실방송/승인 상태 변조 감지')
        return journal
