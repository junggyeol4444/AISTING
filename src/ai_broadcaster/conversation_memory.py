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
            # 최신 N개만 보존한다. 매 발화마다 최대 10만 개 ID를
            # NOT IN 집합으로 구성하지 않고, 기본키 내림차순의 N번째
            # 경계보다 오래된 행만 삭제한다. 중간에 삭제된 ID가 있어도
            # 남은 대화의 실제 개수 기준으로 보존하며 기존 트랜잭션 유지.
            db.execute(
                "DELETE FROM exchanges WHERE id < "
                "(SELECT id FROM exchanges ORDER BY id DESC LIMIT 1 OFFSET ?)",
                (self.max_exchanges - 1,),
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

    def relevant(self, query: str, *, limit: int = 2,
                 exclude_recent: int = 8) -> list[Exchange]:
        """기존 SQLite의 오래된 대화 중 현재 질문과 관련된 실제 기록만 조회.

        원본 테이블·보존 개수·캐릭터 설정을 변경하지 않는다. 이미 최근
        문맥에 포함된 대화는 제외해 중복 주입하지 않는다. 별도 모델이나
        외부 검색/임베딩 서버를 호출하지 않는다. 일치 기록이 없으면
        과거 사실을 새로 만들지 않고 빈 결과를 반환한다.
        """
        import re

        if type(query) is not str or len(query) > 4000:
            raise ValueError("관련 대화 검색 문구가 잘못되었습니다.")
        if (type(limit) is not int or not 0 <= limit <= 4
                or type(exclude_recent) is not int
                or not 0 <= exclude_recent <= 40):
            raise ValueError("관련 대화 검색 범위가 잘못되었습니다.")
        if limit == 0:
            return []
        stopwords = {
            "그리고", "그런데", "그래서", "이거", "저거", "뭐야",
            "어떻게", "있어", "해줘", "해주세요", "있나요", "할까요",
            "그거", "제가", "나는", "오늘", "내일", "지금",
        }
        words = re.findall(r"[가-힣A-Za-z0-9]{2,}", query.casefold())
        tokens = sorted({
            word for word in words if word not in stopwords
        }, key=lambda value: (-len(value), value))[:8]
        if not tokens:
            return []
        # LIKE 특수문자를 이스케이프하고 반드시 바인딩한다. 기존
        # 최대 5천 개 기록에 대한 읽기만 수행하며 DB 인덱스/스키마 불변.
        patterns = ["%" + token.replace("\\", "\\\\").replace(
            "%", "\\%").replace("_", "\\_") + "%" for token in tokens]
        predicates = " OR ".join(
            "(user_text LIKE ? ESCAPE '\\' OR reply LIKE ? ESCAPE '\\')"
            for _ in patterns)
        parameters: list[object] = [exclude_recent]
        for pattern in patterns:
            parameters.extend((pattern, pattern))
        parameters.append(512)
        with self._connection() as db:
            rows = db.execute(
                "SELECT id,sender,user_text,reply FROM exchanges "
                "WHERE id < (SELECT id FROM exchanges ORDER BY id DESC "
                "LIMIT 1 OFFSET ?) AND (" + predicates + ") "
                "ORDER BY id DESC LIMIT ?",
                parameters,
            ).fetchall()
        ranked: list[tuple[int, int, Exchange]] = []
        for row_id, sender, user_text, reply in rows:
            lower_question = user_text.casefold()
            lower_reply = reply.casefold()
            score = sum(
                (3 if token in lower_question else 0)
                + (1 if token in lower_reply else 0)
                for token in tokens)
            if score:
                ranked.append((
                    score, int(row_id),
                    Exchange(sender[:100], user_text[:700], reply[:700])))
        ranked.sort(key=lambda item: (-item[0], -item[1]))
        # 최종 메시지는 실제 과거 시간 순서로 모델에 제공한다.
        return [item[2] for item in sorted(
            ranked[:limit], key=lambda item: item[1])]

    def count(self) -> int:
        with self._connection() as db:
            return int(db.execute("SELECT COUNT(*) FROM exchanges").fetchone()[0])

    def clear(self) -> None:
        """운영자 요청으로 대화 기록 전체 삭제."""
        with self._connection() as db:
            db.execute("DELETE FROM exchanges")
