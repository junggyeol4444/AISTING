"""운영자 승인형 실제 방송의 주간 시작 슬롯을 재시작 이후에도 단 한 번만 청구.

기존 캐릭터·채팅·설정·방송 기록 DB와 별도의 로컬 SQLite 파일 사용.
OBS 제어·방송·공지·채팅 발신은 이 모듈에서 전혀 수행하지 않는다.
시작을 시도하기 *전에* 슬롯을 확정해 Windows 강제 종료/앱 중복
실행 때 동일 분의 무단 재송출을 막는다. 실패 슬롯 자동 재시도 없음.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .offline_settings import data_dir

_APPLICATION_ID = 0x41534A31  # ASJ1: 독립 소유권
_TABLE = "approved_live_slot_attempts"


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
            if (tables and (tables != {_TABLE} or appid != _APPLICATION_ID)):
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
