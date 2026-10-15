"""28단계: 사용자 확인 후에만 모의 코어의 *성공한* 답변을 별도 SQLite에 저장.

가져오기, 객체 생성, 미리보기는 파일/네트워크에 접근하지 않는다.
기존 conversation.sqlite3, settings.json 및 운영자 PC 정보와 분리한다.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from .core_execution import OfflineCoreSession
from .offline_settings import data_dir

APP_ID = 0x41495354  # 'AIST' — 다른 SQLite DB 덮어쓰기 방지
MAX_RECORDS = 10_000  # 자동 삭제하지 않고 명시적 용량 초과 오류
MAX_READ = 100
_TABLE = "core_response_records"
_COLUMNS = ("id", "session_key", "turn_no", "sender", "input_text", "reply_text")


def response_records_path() -> Path:
    """경로 계산만 한다. PC 상태·파일 내용 조회 또는 폴더 생성 없음."""
    return data_dir() / "core_response_records.sqlite3"


@dataclass(frozen=True)
class ResponseRecord:
    session_key: str
    turn_no: int
    sender: str
    input_text: str
    reply_text: str


def _validate_record(record: ResponseRecord) -> None:
    if not isinstance(record, ResponseRecord):
        raise ValueError("응답 기록 자료형이 올바르지 않습니다.")
    if (type(record.session_key) is not str or len(record.session_key) != 32
            or any(c not in "0123456789abcdef" for c in record.session_key)):
        raise ValueError("응답 기록 세션 식별자가 올바르지 않습니다.")
    if type(record.turn_no) is not int or not 1 <= record.turn_no <= 1_000_000_000:
        raise ValueError("응답 순번이 올바르지 않습니다.")
    for value, maximum in ((record.sender, 100), (record.input_text, 4000),
                           (record.reply_text, 6000)):
        if (type(value) is not str or not value.strip() or len(value) > maximum
                or "\x00" in value):
            raise ValueError("응답 기록의 텍스트가 비어 있거나 허용 범위를 벗어났습니다.")


@dataclass(frozen=True)
class ResponseSnapshot:
    records: tuple[ResponseRecord, ...]
    total_processed: int

    def describe(self) -> str:
        if not self.records:
            return "저장할 성공 응답이 없습니다. 저장 작업은 실행하지 않았습니다."
        first, last = self.records[0], self.records[-1]
        lines = [
            "28단계 · 수동 응답 기록 저장 미리보기 (아직 파일 생성 없음)",
            f"저장 후보: 성공 응답 {len(self.records)}건 / 이 세션 누적 성공 {self.total_processed}건",
            f"기록 순번: {first.turn_no}~{last.turn_no}",
            "모의 코어의 현재 메모리 이력 최대 500건만 대상입니다.",
            "실패·대기 입력은 포함하지 않습니다. 저장 후 다시 눌러도 중복 저장하지 않습니다.",
            "개인 대화가 포함될 수 있습니다. 저장 버튼과 별도 확인 후에만 PC에 기록됩니다.",
        ]
        for row in self.records[:5]:
            lines.append(f"#{row.turn_no} {row.sender}: {row.input_text[:90]} → {row.reply_text[:90]}")
        if len(self.records) > 5:
            lines.append(f"(이하 {len(self.records) - 5}건 미리보기 생략)")
        return "\n".join(lines)


def snapshot_core_responses(session: OfflineCoreSession) -> ResponseSnapshot:
    """명시적 UI 동작에서만 호출. SQLite/설정/PC 정보를 읽지 않는다."""
    if not isinstance(session, OfflineCoreSession):
        raise TypeError("모의 코어 세션이 필요합니다.")
    history = session.history
    if not history:
        raise ValueError("성공한 모의 답변이 없습니다. 먼저 수동 코어 실행을 해 주세요.")
    total = session.total_processed
    if total < len(history):
        raise ValueError("응답 이력 순번이 올바르지 않습니다.")
    key = session.response_recording_key()
    first = total - len(history) + 1
    records = tuple(ResponseRecord(key, first + index, row.input.sender,
                                   row.input.text, row.text)
                    for index, row in enumerate(history))
    for record in records:
        _validate_record(record)
    return ResponseSnapshot(records, total)


@dataclass(frozen=True)
class SaveResult:
    inserted: int
    already_saved: int
    total_in_file: int


class ResponseRecordStore:
    """기존 SQLite 기억과 독립. 어떤 읽기/쓰기도 메서드 호출 전에는 하지 않는다."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else response_records_path()

    def _guard_path(self) -> None:
        # 중간 조상 폴더의 링크/Windows 정션까지 차단한다.
        for part in (self.path, *self.path.parents):
            if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
                raise ValueError("링크/정션 경로에는 응답 기록을 저장하지 않습니다.")
        if self.path.exists() and not self.path.is_file():
            raise ValueError("응답 기록 위치가 일반 파일이 아닙니다.")

    @staticmethod
    def _validate_database(db: sqlite3.Connection) -> None:
        app_id = db.execute("PRAGMA application_id").fetchone()[0]
        if app_id != APP_ID:
            raise ValueError("기존 파일은 AISTING 응답 기록 DB가 아닙니다. 변경하지 않습니다.")
        columns = tuple(row[1] for row in db.execute(f"PRAGMA table_info({_TABLE})"))
        if columns != _COLUMNS:
            raise ValueError("응답 기록 DB의 테이블 구조가 다릅니다. 변경하지 않습니다.")

    def _readonly(self) -> sqlite3.Connection:
        # mode=ro: 조회만 해도 잘못된 파일이 생성되는 SQLite 기본 동작 방지.
        db = sqlite3.connect(self.path.absolute().as_uri() + "?mode=ro", uri=True, timeout=5)
        try:
            db.execute("PRAGMA query_only=ON")
        except BaseException:
            # A PRAGMA failure must not leave the read-only handle open.
            db.close()
            raise
        return db

    def save(self, snapshot: ResponseSnapshot, *, confirmed: bool = False) -> SaveResult:
        if confirmed is not True:
            raise PermissionError("응답 기록 저장에는 사용자 확인이 필요합니다.")
        if (not isinstance(snapshot, ResponseSnapshot) or type(snapshot.records) is not tuple
                or not snapshot.records or len(snapshot.records) > 500
                or type(snapshot.total_processed) is not int):
            raise ValueError("저장할 성공 응답 스냅샷이 올바르지 않습니다.")
        seen: set[tuple[str, int]] = set()
        for row in snapshot.records:
            _validate_record(row)
            key = (row.session_key, row.turn_no)
            if key in seen or row.turn_no > snapshot.total_processed:
                raise ValueError("중복/잘못된 응답 순번이 있습니다.")
            seen.add(key)
        if len(snapshot.records) > MAX_RECORDS:
            raise ValueError("응답 기록 최대 건수를 초과합니다.")
        self._guard_path()
        existed = self.path.exists()
        if existed:
            with closing(self._readonly()) as db:
                self._validate_database(db)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._guard_path()
        created_here = False
        committed = False
        db: sqlite3.Connection | None = None
        try:
            if not existed:
                # 기존 파일을 절대 덮어쓰지 않고, 신규 DB 생성 실패 시 파일을 정리한다.
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                created_here = True
            db = sqlite3.connect(self.path, timeout=5)
            db.execute("BEGIN IMMEDIATE")
            if existed:
                self._validate_database(db)
            else:
                db.execute(f"PRAGMA application_id={APP_ID}")
                db.execute(f"""CREATE TABLE {_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_key TEXT NOT NULL,
                    turn_no INTEGER NOT NULL,
                    sender TEXT NOT NULL,
                    input_text TEXT NOT NULL,
                    reply_text TEXT NOT NULL,
                    UNIQUE(session_key, turn_no)
                )""")
            total = db.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()[0]
            inserted = duplicate = 0
            for row in snapshot.records:
                previous = db.execute(
                    f"SELECT sender,input_text,reply_text FROM {_TABLE} WHERE session_key=? AND turn_no=?",
                    (row.session_key, row.turn_no),
                ).fetchone()
                if previous is not None:
                    if previous != (row.sender, row.input_text, row.reply_text):
                        raise ValueError("이미 저장된 동일 순번의 내용이 다릅니다. 덮어쓰지 않습니다.")
                    duplicate += 1
                    continue
                if total + inserted >= MAX_RECORDS:
                    raise ValueError("응답 기록은 최대 10000건입니다. 기존 기록을 자동 삭제하지 않습니다.")
                db.execute(
                    f"INSERT INTO {_TABLE}(session_key,turn_no,sender,input_text,reply_text) VALUES(?,?,?,?,?)",
                    (row.session_key, row.turn_no, row.sender, row.input_text, row.reply_text),
                )
                inserted += 1
            db.commit()
            committed = True
            return SaveResult(inserted, duplicate, total + inserted)
        except BaseException:
            if db is not None:
                db.rollback()
            raise
        finally:
            if db is not None:
                db.close()
            if created_here and not committed:
                self.path.unlink(missing_ok=True)

    def recent(self, limit: int = 30) -> tuple[ResponseRecord, ...]:
        if type(limit) is not int or not 1 <= limit <= MAX_READ:
            raise ValueError("조회 건수는 1~100건이어야 합니다.")
        self._guard_path()
        if not self.path.exists():
            return ()
        with closing(self._readonly()) as db:
            self._validate_database(db)
            rows = db.execute(
                f"SELECT session_key,turn_no,sender,input_text,reply_text FROM {_TABLE} ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple(ResponseRecord(*row) for row in rows)

    def clear(self, *, confirmed: bool = False) -> int:
        """별도 명시적 확인에서만 이 전용 DB의 기록을 지운다. 다른 DB는 건드리지 않는다."""
        if confirmed is not True:
            raise PermissionError("기록 삭제에는 사용자 확인이 필요합니다.")
        self._guard_path()
        if not self.path.exists():
            return 0
        with closing(self._readonly()) as db:
            self._validate_database(db)
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                self._validate_database(db)
                count = db.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()[0]
                db.execute(f"DELETE FROM {_TABLE}")
            return count
        finally:
            db.close()
