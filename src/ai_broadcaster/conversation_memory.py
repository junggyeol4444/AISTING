"""무료 PC 전용 SQLite 대화 기록과 최근 맥락 검색.

응답이 출력된 뒤에만 기록하는 용도로 설계되었다.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .operator_settings import DEFAULT_FILE
from .session import ChatMessage

DEFAULT_MEMORY_FILE = DEFAULT_FILE.with_name("conversation_history.sqlite3")


@dataclass(frozen=True)
class Exchange:
    sender: str
    user_text: str
    reply: str


class ConversationMemory:
    """답변 전달이 끝난 대화 쌍만 저장한다. 동일 문장이라도 누락시키지 않는다."""

    def __init__(self, path: Path = DEFAULT_MEMORY_FILE, max_exchanges: int = 5000) -> None:
        if type(max_exchanges) is not int or not 1 <= max_exchanges <= 100000:
            raise ValueError("max_exchanges는 1~100000 범위 정수여야 합니다.")
        self.path = Path(path)
        self.max_exchanges = max_exchanges
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS exchanges ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "sender TEXT NOT NULL, user_text TEXT NOT NULL, "
                "reply TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )

    def _connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=5.0)

    def append(self, message: ChatMessage, reply: str) -> None:
        if not isinstance(message, ChatMessage):
            raise TypeError("ChatMessage만 기록할 수 있습니다.")
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("빈 답변은 기록하지 않습니다.")
        with self._connection() as db:
            db.execute(
                "INSERT INTO exchanges(sender, user_text, reply) VALUES (?, ?, ?)",
                (message.sender[:100], message.text[:4000], reply[:6000]),
            )
            db.execute(
                "DELETE FROM exchanges WHERE id NOT IN "
                "(SELECT id FROM exchanges ORDER BY id DESC LIMIT ?)",
                (self.max_exchanges,),
            )

    def recent(self, limit: int = 8) -> list[Exchange]:
        if type(limit) is not int or not 0 <= limit <= 100:
            raise ValueError("최근 기억 범위는 0~100이어야 합니다.")
        if limit == 0:
            return []
        with self._connection() as db:
            rows = db.execute(
                "SELECT sender, user_text, reply FROM exchanges "
                "ORDER BY id DESC LIMIT ?", (limit,),
            ).fetchall()
        return [Exchange(*row) for row in reversed(rows)]

    def count(self) -> int:
        with self._connection() as db:
            return int(db.execute("SELECT COUNT(*) FROM exchanges").fetchone()[0])

    def clear(self) -> None:
        """운영자 요청으로 대화 기록 전체 삭제."""
        with self._connection() as db:
            db.execute("DELETE FROM exchanges")
