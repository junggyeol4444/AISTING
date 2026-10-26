"""운영자가 승인한 장시간 방송의 관측 상태를 독립 SQLite에 내구 기록.

OBS/실계정/음성/메시지를 직접 호출·조작하지 않는다. 예약 작업자가
이미 읽은 상태만 1분 단위로 기록하므로 이력은 '관측'이지 24시간
무장애 방송·실제 시청자 수신 성공의 입증이 아니다.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .offline_settings import data_dir

_APP_ID = 0x41524831
_TABLE = "approved_live_runtime_checkpoints"
_STATES = ("정상관측", "매체미확인", "채팅미확인", "상태불명")


@dataclass(frozen=True)
class RuntimeCheckpoint:
    occurrence: str
    observed_at: str
    state: str
    obs_streaming: bool
    media_alive: bool | None
    chat_alive: bool | None


class ApprovedLiveRuntimeCheckpoint:
    """원본 승인형 OBS 방송 사건 DB를 변경하지 않는 별도 장부."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_live_runtime_checkpoints.sqlite3")
        if (self.path.is_symlink() or self.path.parent.is_symlink()):
            raise ValueError("실제 방송 상태 장부의 바로가기를 사용할 수 없습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        if existed and not self.path.is_file():
            raise ValueError("실제 방송 상태 장부는 일반 파일이어야 합니다.")
        with self._db() as db:
            appid = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")}
            if ((existed and not tables) or
                    (tables and (appid != _APP_ID or tables != {_TABLE}))
                    or appid not in (0, _APP_ID)):
                raise ValueError("다른 기존 SQLite 장부는 변경하지 않습니다.")
            db.execute(f"PRAGMA application_id={_APP_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_live_runtime_checkpoints ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "occurrence TEXT NOT NULL,"
                "observed_at TEXT NOT NULL,"
                "state TEXT NOT NULL,"
                "obs_streaming INTEGER NOT NULL,"
                "media_alive INTEGER,"
                "chat_alive INTEGER)")
            columns = tuple(r[1] for r in db.execute(
                "PRAGMA table_info(approved_live_runtime_checkpoints)"))
            if columns != ("id", "occurrence", "observed_at", "state",
                           "obs_streaming", "media_alive", "chat_alive"):
                raise ValueError("기존 방송 상태 기록 구조를 변경하지 않습니다.")

    @contextmanager
    def _db(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db

    def record(self, occurrence: str, *, obs_streaming: bool,
               media_alive: bool | None, chat_alive: bool | None
               ) -> RuntimeCheckpoint:
        if (type(occurrence) is not str or not 1 <= len(occurrence) <= 120
                or any(ord(ch) < 32 for ch in occurrence)):
            raise ValueError("승인한 방송 슬롯 식별자가 올바르지 않습니다.")
        if (type(obs_streaming) is not bool
                or media_alive is not None and type(media_alive) is not bool
                or chat_alive is not None and type(chat_alive) is not bool):
            raise ValueError("송출·매체·채팅 관측 상태가 올바르지 않습니다.")
        state = (
            "상태불명" if not obs_streaming else
            "매체미확인" if media_alive is False else
            "채팅미확인" if chat_alive is False else "정상관측")
        at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._db() as db:
            db.execute(
                "INSERT INTO approved_live_runtime_checkpoints "
                "(occurrence,observed_at,state,obs_streaming,media_alive,chat_alive) "
                "VALUES(?,?,?,?,?,?)",
                (occurrence, at, state, int(obs_streaming),
                 None if media_alive is None else int(media_alive),
                 None if chat_alive is None else int(chat_alive)))
        return RuntimeCheckpoint(
            occurrence, at, state, obs_streaming, media_alive, chat_alive)

    def recent(self, *, limit: int = 30) -> tuple[RuntimeCheckpoint, ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("장시간 방송 기록 조회는 1~100개입니다.")
        with self._db() as db:
            rows = db.execute(
                "SELECT occurrence,observed_at,state,obs_streaming,"
                "media_alive,chat_alive FROM approved_live_runtime_checkpoints "
                "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return tuple(RuntimeCheckpoint(
            occurrence, at, state, bool(obs),
            None if media is None else bool(media),
            None if chat is None else bool(chat))
            for occurrence, at, state, obs, media, chat in rows)
