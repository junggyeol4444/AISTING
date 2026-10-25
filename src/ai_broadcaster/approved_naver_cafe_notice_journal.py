"""실제 네이버 카페 공지의 중복 게시를 차단하는 별도 영구 SQLite.

기존 OBS 방송 슬롯 장부/디스코드 사전 공지/채팅/캐릭터 DB와 분리.
각 KST 방송 슬롯 × 시작/종료 × 카페·게시판을 실제 HTTP 요청 전에
한 번만 청구한다. 실패나 응답 분실 때 자동 재시도하지 않는다.
제목/본문/접근 토큰은 저장하지 않고 SHA-256만 기록한다.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .offline_settings import data_dir

_APP_ID = 0x414E4331  # ANC1
_TABLE = "approved_naver_cafe_notices"
_PHASES = frozenset(("시작", "종료"))
_STATES = frozenset(("서버게시확인", "서버응답불명"))
_ID = re.compile(r"[1-9][0-9]{0,15}\Z")


class ApprovedNaverCafeNoticeJournal:
    """영구 중복 방지·서버 성공 후보 기록; 게시 요청 자체는 하지 않음."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_naver_cafe_notices.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("카페 공지 기록은 바로가기 경로에 만들지 않습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and not self.path.is_file():
            raise ValueError("카페 공지 기록이 일반 파일이 아닙니다.")
        existed = self.path.exists()
        with self._open() as db:
            appid = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {x[0] for x in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'").fetchall()}
            if (appid not in (0, _APP_ID)
                    or (existed and not tables)
                    or (tables and (tables != {_TABLE} or appid != _APP_ID))):
                raise ValueError("다른 프로그램의 카페 공지 SQLite를 수정하지 않습니다.")
            if not tables:
                db.execute(f"PRAGMA application_id={_APP_ID}")
                db.execute(
                    f"CREATE TABLE {_TABLE} ("
                    "occurrence TEXT NOT NULL, phase TEXT NOT NULL,"
                    "club_id TEXT NOT NULL, menu_id TEXT NOT NULL,"
                    "content_sha256 TEXT NOT NULL,"
                    "state TEXT NOT NULL DEFAULT '발신시도',"
                    "article_id INTEGER,"
                    "claimed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                    "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                    "PRIMARY KEY(occurrence,phase,club_id,menu_id))")
            columns = tuple(x[1] for x in db.execute(
                f"PRAGMA table_info({_TABLE})").fetchall())
            if columns != (
                "occurrence", "phase", "club_id", "menu_id",
                "content_sha256", "state", "article_id",
                "claimed_at", "updated_at",
            ):
                raise ValueError("기존 카페 공지 기록 구조를 변경하지 않습니다.")

    @contextmanager
    def _open(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("PRAGMA synchronous=FULL")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _identity(
        occurrence: str, phase: str, club_id: str, menu_id: str,
    ) -> tuple[str, str, str, str]:
        if type(occurrence) is not str or not occurrence.endswith(" KST"):
            raise ValueError("실제 KST 방송 시작 슬롯을 확인하세요.")
        stamp = occurrence[:-4]
        try:
            parsed = datetime.strptime(stamp, "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError("방송 시작 슬롯 날짜 형식 오류") from None
        if parsed.strftime("%Y-%m-%d %H:%M") != stamp:
            raise ValueError("방송 슬롯 날짜 표기 오류")
        if phase not in _PHASES:
            raise ValueError("카페 공지는 시작/종료 두 종류만 가능합니다.")
        if (type(club_id) is not str or _ID.fullmatch(club_id) is None
                or type(menu_id) is not str or _ID.fullmatch(menu_id) is None):
            raise ValueError("카페 번호 또는 게시판 번호 오류")
        return occurrence, phase, club_id, menu_id

    def claim(
        self, occurrence: str, phase: str, club_id: str, menu_id: str,
        subject: str, content: str,
    ) -> bool:
        """HTTP 이전 영구 커밋. 다른 창/강제 종료 후 동일 글 재발신 금지."""
        key = self._identity(occurrence, phase, club_id, menu_id)
        if type(subject) is not str or type(content) is not str:
            raise ValueError("공지 제목/본문 형식 오류")
        digest = hashlib.sha256(
            (subject + "\x00" + content).encode("utf-8")).hexdigest()
        with self._open() as db:
            return db.execute(
                f"INSERT OR IGNORE INTO {_TABLE}"
                "(occurrence,phase,club_id,menu_id,content_sha256) "
                "VALUES(?,?,?,?,?)", (*key, digest)).rowcount == 1

    def mark(
        self, occurrence: str, phase: str, club_id: str, menu_id: str,
        state: str, *, article_id: int | None = None,
    ) -> None:
        key = self._identity(occurrence, phase, club_id, menu_id)
        if state not in _STATES:
            raise ValueError("서버 결과 상태 형식 오류")
        if (state == "서버게시확인"
                and (type(article_id) is not int or article_id <= 0)):
            raise ValueError("서버가 확인한 글 번호가 필요합니다.")
        if state == "서버응답불명" and article_id is not None:
            raise ValueError("응답 불명 글 번호를 기록할 수 없습니다.")
        with self._open() as db:
            row = db.execute(
                f"UPDATE {_TABLE} SET state=?,article_id=?,"
                "updated_at=CURRENT_TIMESTAMP WHERE "
                "occurrence=? AND phase=? AND club_id=? AND menu_id=? "
                "AND state='발신시도'",
                (state, article_id, *key)).rowcount
            if row != 1:
                raise RuntimeError("카페 공지 기존 시도 상태가 불확실합니다.")

    def recent(self, *, limit: int = 20) -> tuple[tuple[str, ...], ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("카페 공지 기록 조회 범위는 1~100입니다.")
        with self._open() as db:
            rows = db.execute(
                f"SELECT occurrence,phase,club_id,menu_id,state,"
                f"COALESCE(CAST(article_id AS TEXT),''),claimed_at "
                f"FROM {_TABLE} ORDER BY claimed_at DESC, rowid DESC LIMIT ?",
                (limit,)).fetchall()
        return tuple(tuple(str(v) for v in row) for row in rows)
