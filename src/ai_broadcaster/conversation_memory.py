"""무료 PC 전용 SQLite 대화 기록과 최근 맥락 검색.

응답이 출력된 뒤에만 기록하는 용도로 설계되었다.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager, closing
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

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
        # Never initialize an unrelated SQLite file merely because the
        # chosen path is already occupied. Check read-only BEFORE creating
        # tables, and refuse symbolic-link paths that could target other data.
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("대화 기억 저장 경로가 심볼릭 링크입니다.")
        if self.path.exists():
            if not self.path.is_file():
                raise ValueError("대화 기억 저장 경로가 일반 파일이 아닙니다.")
            self._verify_existing_database()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS exchanges ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "sender TEXT NOT NULL, user_text TEXT NOT NULL, "
                "reply TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )

    def _verify_existing_database(self) -> None:
        """Inspect existing SQLite read-only, preserving unrelated files byte for byte."""
        try:
            # as_uri percent-encodes Windows spaces and non-ASCII paths.
            with closing(sqlite3.connect(
                self.path.resolve().as_uri() + "?mode=ro",
                uri=True, timeout=5.0,
            )) as db:
                if db.execute("PRAGMA application_id").fetchone()[0] != 0:
                    raise ValueError("다른 프로그램의 SQLite 파일입니다.")
                tables = {
                    name for (name,) in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%'"
                    ).fetchall()
                }
                if tables != {"exchanges"}:
                    raise ValueError("대화 기억 전용 데이터베이스 형식이 아닙니다.")
                schema = db.execute("PRAGMA table_info(exchanges)").fetchall()
                expected = (
                    ("id", "INTEGER", 1),
                    ("sender", "TEXT", 0),
                    ("user_text", "TEXT", 0),
                    ("reply", "TEXT", 0),
                    ("created_at", "TEXT", 0),
                )
                if len(schema) != len(expected) or any(
                    (row[1], row[2].upper(), row[5]) != spec
                    or (i > 0 and row[3] != 1)
                    for i, (row, spec) in enumerate(zip(schema, expected))
                ):
                    raise ValueError("기존 대화 기억 DB의 필드 형식이 다릅니다.")
        except sqlite3.DatabaseError as exc:
            raise ValueError("기존 SQLite 기억 파일을 안전하게 읽을 수 없습니다.") from exc

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """트랜잭션 종료에 더해 DB 핸들도 반드시 닫는다 (Windows 파일 잠금 방지)."""
        db = sqlite3.connect(self.path, timeout=5.0)
        try:
            with db:
                yield db
        finally:
            db.close()

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
