"""운영자 승인형 실제 방송의 주간 시작 슬롯을 재시작 이후에도 단 한 번만 청구.

기존 캐릭터·채팅·설정·방송 기록 DB와 별도의 로컬 SQLite 파일 사용.
OBS 제어·방송·공지·채팅 발신은 이 모듈에서 전혀 수행하지 않는다.
시작을 시도하기 *전에* 슬롯을 확정해 Windows 강제 종료/앱 중복
실행 때 동일 분의 무단 재송출을 막는다. 실패 슬롯 자동 재시도 없음.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from .offline_settings import data_dir

_APPLICATION_ID = 0x41534A31  # ASJ1: 독립 소유권
_TABLE = "approved_live_slot_attempts"
_EVENTS = "approved_live_slot_events"
_PRE_NOTICES = "approved_live_pre_notices"
_EVENT_STATES = frozenset((
    "송출시작확인", "송출시작실패", "송출종료확인", "송출종료실패",
    "OBS재연결감지", "OBS혼잡지속", "OBS프레임정체", "OBS전송프레임누락",
))


class ApprovedLiveSlotJournal:
    """정상 승인된 방송 시작 요청만 기록하는 영구 중복 방지 장부."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_live_slots.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("방송 시작 장부 경로에 바로가기를 사용할 수 없습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and not self.path.is_file():
            raise ValueError("방송 시작 장부 경로가 일반 파일이 아닙니다.")
        existed = self.path.exists()
        with self._open() as db:
            appid = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {
                row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            }
            if (tables and (not tables.issubset({_TABLE, _EVENTS, _PRE_NOTICES})
                            or _TABLE not in tables
                            or appid != _APPLICATION_ID)):
                raise ValueError("다른 프로그램의 SQLite 파일을 변경하지 않습니다.")
            if existed and not tables:
                raise ValueError("소유권이 불명확한 기존 SQLite 파일을 변경하지 않습니다.")
            if appid not in (0, _APPLICATION_ID):
                raise ValueError("방송 장부의 소유권 식별자가 일치하지 않습니다.")
            db.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_live_slot_attempts ("
                "occurrence TEXT PRIMARY KEY NOT NULL,"
                "claimed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            columns = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(approved_live_slot_attempts)").fetchall())
            if columns != ("occurrence", "claimed_at"):
                raise ValueError("기존 방송 시작 장부 구조가 일치하지 않습니다.")
            # 기존 시작 슬롯을 손대지 않고 사건을 append-only 기록.
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_live_slot_events ("
                "event_no INTEGER PRIMARY KEY AUTOINCREMENT,"
                "occurrence TEXT NOT NULL, state TEXT NOT NULL,"
                "logged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            event_columns = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(approved_live_slot_events)").fetchall())
            if event_columns != ("event_no", "occurrence", "state", "logged_at"):
                raise ValueError("기존 방송 결과 장부 구조가 일치하지 않습니다.")

        # 시작 슬롯보다 먼저 승인된 사전 공지를 발송해야 하므로
        # 별도의 영구 UNIQUE 슬롯 장부를 사용한다. 기존 기록은 보존.
        with self._open() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_live_pre_notices ("
                "occurrence TEXT PRIMARY KEY NOT NULL,"
                "claimed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            pre_columns = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(approved_live_pre_notices)").fetchall())
            if pre_columns != ("occurrence", "claimed_at"):
                raise ValueError("기존 사전 공지 장부 구조가 일치하지 않습니다.")

    def _open(self):
        # 매 호출 후 파일 핸들을 닫고 트랜잭션 원자성을 유지한다.
        class Transaction:
            def __init__(self, path: Path):
                self.path = path
                self.db = None

            def __enter__(self):
                self.db = sqlite3.connect(self.path, timeout=10)
                self.db.execute("PRAGMA busy_timeout=10000")
                self.db.execute("PRAGMA synchronous=FULL")
                return self.db

            def __exit__(self, exc_type, exc_value, traceback):
                try:
                    if exc_type is None:
                        self.db.commit()
                    else:
                        self.db.rollback()
                finally:
                    self.db.close()
                return False

        return Transaction(self.path)

    def claim(self, occurrence: str) -> bool:
        """같은 KST 방송 슬롯을 첫 호출만 원자적으로 확보한다.

        중복이면 False. DB 기록이 실패하면 예외를 올려 송출 시작 차단.
        날짜/시각은 실제 스케줄러의 KST 슬롯 문자열만 받아들인다.
        """
        if type(occurrence) is not str or not occurrence.endswith(" KST"):
            raise ValueError("한국 시간 방송 슬롯 형식이 올바르지 않습니다.")
        stamp = occurrence[:-4]
        try:
            parsed = datetime.strptime(stamp, "%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise ValueError("방송 슬롯 날짜 형식이 올바르지 않습니다.") from exc
        if parsed.strftime("%Y-%m-%d %H:%M") != stamp:
            raise ValueError("방송 슬롯 날짜 표기가 올바르지 않습니다.")
        with self._open() as db:
            return db.execute(
                "INSERT OR IGNORE INTO approved_live_slot_attempts "
                "(occurrence) VALUES (?)", (occurrence,)
            ).rowcount == 1

    def claim_pre_notice(self, occurrence: str) -> bool:
        """사전 공지를 같은 KST 시작 슬롯당 하나만 원자적으로 예약.

        HTTP 요청 시작 전에 DB 커밋하여 실패/강제종료 때도 자동 중복
        발송하지 않는다. 송신 성공 여부는 이 반환값으로 주장할 수 없다.
        """
        if type(occurrence) is not str or not occurrence.endswith(" KST"):
            raise ValueError("한국 시간 사전 공지 슬롯 형식이 올바르지 않습니다.")
        value = occurrence[:-4]
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise ValueError("사전 공지 슬롯 시각 형식이 올바르지 않습니다.") from exc
        if parsed.strftime("%Y-%m-%d %H:%M") != value:
            raise ValueError("사전 공지 슬롯 표기가 올바르지 않습니다.")
        with self._open() as db:
            return db.execute(
                "INSERT OR IGNORE INTO approved_live_pre_notices "
                "(occurrence) VALUES (?)", (occurrence,)
            ).rowcount == 1

    def record_event(self, occurrence: str, state: str) -> None:
        """OBS가 실제 확인한 시작/종료 결과만 기존 슬롯에 누적 기록.

        이벤트 기록 실패는 호출자에게 예외로 전달한다. 방송 제어와
        원본 캐릭터/채팅 SQLite는 이 장부가 직접 변경하지 않는다.
        """
        if type(state) is not str or state not in _EVENT_STATES:
            raise ValueError("기록할 방송 상태가 올바르지 않습니다.")
        if type(occurrence) is not str or not occurrence.endswith(" KST"):
            raise ValueError("기록할 방송 슬롯이 올바르지 않습니다.")
        with self._open() as db:
            result = db.execute(
                "INSERT INTO approved_live_slot_events(occurrence,state) "
                "SELECT occurrence, ? FROM approved_live_slot_attempts "
                "WHERE occurrence=?", (state, occurrence))
            if result.rowcount != 1:
                raise ValueError("확정된 방송 시작 슬롯이 없어 결과를 기록하지 않습니다.")

    def recent_events(self, *, limit: int = 20) -> tuple[tuple[str, str, str], ...]:
        """로컬 OBS 시작·종료 결과를 읽기 전용으로 반환.

        채팅/시청자/인증정보를 저장하지 않으며 최근 사건만 표시한다.
        '시작 확인' 뒤 '종료 확인'이 없으면 송출 중이라는 증거가 아니라
        운영자가 OBS 실제 상태를 확인해야 하는 미종결 기록이다.
        """
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("방송 기록 조회 개수는 1~100이어야 합니다.")
        with self._open() as db:
            rows = db.execute(
                "SELECT occurrence,state,logged_at FROM "
                "approved_live_slot_events ORDER BY event_no DESC LIMIT ?",
                (limit,)).fetchall()
        return tuple((str(a), str(b), str(c)) for a,b,c in rows)

    def recent_claims(self, *, limit: int = 20) -> tuple[tuple[str, str], ...]:
        """종료 이벤트가 없는 강제 종료 슬롯도 조회할 수 있는 원본 시도 장부."""
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("방송 시작 시도 조회 개수는 1~100이어야 합니다.")
        with self._open() as db:
            rows = db.execute(
                "SELECT occurrence,claimed_at FROM approved_live_slot_attempts "
                "ORDER BY occurrence DESC LIMIT ?", (limit,)).fetchall()
        return tuple((str(a), str(b)) for a,b in rows)
