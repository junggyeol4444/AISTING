"""사용자가 켰을 때만 활성화되는 로컬 장기 대화 기억 보관소.

기존 conversation_history.sqlite3의 스키마·최근 5000건 보존 정책은
변경하지 않는다. 별도 SQLite에 실제 확정된 대화를 삭제 기한 없이
누적하고, 기존 최근 대화와 중복되지 않는 과거 관련 기록을 조회한다.
원본 대화와 장기 보관소에 대한 INSERT는 한 SQLite 트랜잭션에 포함된다.
원본이 이미 5000건 보존 정책으로 삭제한 과거 대화는 복구할 수 없다.
외부 서버·임베딩·새 모델·무단 계정 연결은 사용하지 않는다.
"""
from __future__ import annotations

import heapq
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from .conversation_memory import ConversationMemory, DEFAULT_MEMORY_FILE, Exchange
from .session import ChatMessage

_APP_ID = 0x414C4D31  # ALM1
_TABLE = "archived_exchanges"
_STOPWORDS = frozenset((
    "그리고", "그런데", "그래서", "이거", "저거", "뭐야",
    "어떻게", "있어", "해줘", "해주세요", "있나요", "할까요",
    "그거", "제가", "나는", "오늘", "내일", "지금",
))


def archive_path_for(memory_path: Path = DEFAULT_MEMORY_FILE) -> Path:
    path = Path(memory_path)
    return path.with_name(path.stem + "_long_term.sqlite3")


class LongTermConversationMemory(ConversationMemory):
    """사용자 선택형 장기 기억: 원래 최근 기록 + 별도 전체 확정 대화."""

    def __init__(
        self, path: Path = DEFAULT_MEMORY_FILE, *,
        archive_path: Path | None = None,
        max_exchanges: int = 5000,
    ) -> None:
        super().__init__(path=path, max_exchanges=max_exchanges)
        self.archive_path = (
            Path(archive_path) if archive_path is not None
            else archive_path_for(self.path))
        if (self.archive_path == self.path
                or self.archive_path.is_symlink()
                or self.archive_path.parent.is_symlink()):
            raise ValueError("장기 기억은 원본과 다른 일반 SQLite 경로여야 합니다.")
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)
        if self.archive_path.exists():
            if not self.archive_path.is_file():
                raise ValueError("장기 기억 경로가 일반 파일이 아닙니다.")
            self._verify_archive()
        else:
            # 원본 DB를 직접 수정하지 않고, 새 장기 보관소만 생성.
            with closing(sqlite3.connect(self.archive_path, timeout=10)) as db:
                with db:
                    db.execute("BEGIN IMMEDIATE")
                    existing = db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%'").fetchall()
                    if existing:
                        raise ValueError("다른 SQLite를 장기 기억으로 사용하지 않습니다.")
                    db.execute(f"PRAGMA application_id={_APP_ID}")
                    db.execute(
                        "CREATE TABLE archived_exchanges("
                        "origin_id INTEGER PRIMARY KEY,"
                        "sender TEXT NOT NULL,user_text TEXT NOT NULL,"
                        "reply TEXT NOT NULL,created_at TEXT NOT NULL)")
        self._verify_archive()
        # 장기 보관을 처음 켠 순간 원본에 남은 실제 대화만 1회 복사.
        # UNIQUE origin_id로 재시작/동시 프로세스의 중복 삽입을 방지.
        with self._connection() as db:
            self._attach(db)
            db.execute(
                "INSERT OR IGNORE INTO archive.archived_exchanges "
                "(origin_id,sender,user_text,reply,created_at) "
                "SELECT id,sender,user_text,reply,created_at FROM main.exchanges")

    def _verify_archive(self) -> None:
        try:
            with closing(sqlite3.connect(
                self.archive_path.resolve().as_uri() + "?mode=ro",
                uri=True, timeout=5,
            )) as db:
                if db.execute("PRAGMA application_id").fetchone()[0] != _APP_ID:
                    raise ValueError("다른 프로그램의 장기 기억 DB는 변경하지 않습니다.")
                tables = {row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'")}
                if tables != {_TABLE}:
                    raise ValueError("장기 기억 테이블 소유권이 다릅니다.")
                cols = tuple((row[1], row[2].upper(), row[5])
                             for row in db.execute(f"PRAGMA table_info({_TABLE})"))
                expected = (
                    ("origin_id", "INTEGER", 1),
                    ("sender", "TEXT", 0),
                    ("user_text", "TEXT", 0),
                    ("reply", "TEXT", 0),
                    ("created_at", "TEXT", 0),
                )
                if cols != expected:
                    raise ValueError("장기 기억 DB의 원래 필드 구성이 다릅니다.")
        except sqlite3.DatabaseError as exc:
            raise ValueError("장기 기억 DB의 소유권을 확인하지 못했습니다.") from exc

    def _attach(self, db: sqlite3.Connection) -> None:
        db.execute("ATTACH DATABASE ? AS archive", (str(self.archive_path),))
        if db.execute("PRAGMA archive.application_id").fetchone()[0] != _APP_ID:
            raise ValueError("연결한 장기 기억 DB가 다른 파일입니다.")

    def append(self, message: ChatMessage, reply: str) -> None:
        """원본 대화 INSERT·장기 보관 INSERT·최근 5000건 정리를 원자적으로 수행."""
        if not isinstance(message, ChatMessage):
            raise TypeError("ChatMessage만 장기 기억에 저장할 수 있습니다.")
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("빈 답변은 장기 기억에 기록하지 않습니다.")
        with self._connection() as db:
            self._attach(db)
            inserted = db.execute(
                "INSERT INTO main.exchanges(sender,user_text,reply) VALUES(?,?,?)",
                (message.sender[:100], message.text[:4000], reply[:6000]))
            db.execute(
                "INSERT INTO archive.archived_exchanges"
                "(origin_id,sender,user_text,reply,created_at) "
                "SELECT id,sender,user_text,reply,created_at "
                "FROM main.exchanges WHERE id=?", (inserted.lastrowid,))
            db.execute(
                "DELETE FROM main.exchanges WHERE id < "
                "(SELECT id FROM main.exchanges ORDER BY id DESC LIMIT 1 OFFSET ?)",
                (self.max_exchanges - 1,))

    def relevant(self, query: str, *, limit: int = 2,
                 exclude_recent: int = 8) -> list[Exchange]:
        """장기 보관 전체에서 실제 질문 연관 대화를 순위 검색한다."""
        if type(query) is not str or len(query) > 4000:
            raise ValueError("장기 기억 검색 질문이 올바르지 않습니다.")
        if (type(limit) is not int or not 0 <= limit <= 4
                or type(exclude_recent) is not int
                or not 0 <= exclude_recent <= 40):
            raise ValueError("장기 기억 검색 개수가 올바르지 않습니다.")
        if limit == 0:
            return []
        words = re.findall(r"[가-힣A-Za-z0-9]{2,}", query.casefold())
        tokens = sorted({w for w in words if w not in _STOPWORDS},
                        key=lambda value: (-len(value), value))[:8]
        if not tokens:
            return []
        patterns = ["%" + t.replace("\\", "\\\\").replace(
            "%", "\\%").replace("_", "\\_") + "%" for t in tokens]
        predicates = " OR ".join(
            "(user_text LIKE ? ESCAPE '\\' OR reply LIKE ? ESCAPE '\\')"
            for _ in patterns)
        args: list[object] = [exclude_recent]
        for pattern in patterns:
            args.extend((pattern, pattern))
        # 전체 장기 보관소를 검색하되 상위 결과 4개만 메모리에 유지.
        # 최근 순으로 잘라 과거 고득점 기록을 영구 누락하지 않는다.
        best: list[tuple[int, int, Exchange]] = []
        with self._connection() as db:
            self._attach(db)
            cursor = db.execute(
                "SELECT origin_id,sender,user_text,reply "
                "FROM archive.archived_exchanges "
                "WHERE origin_id < COALESCE(("
                "SELECT origin_id FROM archive.archived_exchanges "
                "ORDER BY origin_id DESC LIMIT 1 OFFSET ?), -1) "
                "AND (" + predicates + ") ORDER BY origin_id DESC", args)
            for origin_id, sender, user_text, reply in cursor:
                lower_q, lower_r = user_text.casefold(), reply.casefold()
                score = sum((3 if t in lower_q else 0)
                            + (1 if t in lower_r else 0) for t in tokens)
                if not score:
                    continue
                item = (score, int(origin_id), Exchange(
                    sender[:100], user_text[:700], reply[:700]))
                if len(best) < limit:
                    heapq.heappush(best, item)
                elif item[:2] > best[0][:2]:
                    heapq.heapreplace(best, item)
        return [item[2] for item in sorted(best, key=lambda x: x[1])]

    def archive_count(self) -> int:
        with self._connection() as db:
            self._attach(db)
            return int(db.execute(
                "SELECT COUNT(*) FROM archive.archived_exchanges").fetchone()[0])

    def clear(self) -> None:
        """사용자가 전체 기억 삭제를 승인하면 최근/장기 양쪽을 함께 삭제."""
        with self._connection() as db:
            self._attach(db)
            db.execute("DELETE FROM main.exchanges")
            db.execute("DELETE FROM archive.archived_exchanges")
