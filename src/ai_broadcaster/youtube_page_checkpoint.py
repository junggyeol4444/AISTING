"""승인된 실제 YouTube 공개 채팅 페이지의 SQLite 재시작 커서.

유튜브 OAuth/API 키·채팅 본문·닉네임은 저장하지 않는다. 페이지 전체의
메시지가 기존 DurablePublicChatQueue에 수용된 후에만 페이지 커서를
확정하도록 호출자가 사용한다. 미완료 페이지는 재수신 가능하며,
중복 서버 메시지 ID의 실제 영구 제거는 기존 SQLite 보류 큐가 담당한다.

이 파일은 네트워크 접속·OAuth·방송 시작·채팅 게시를 수행하지 않는다.
유튜브 서버에서 애초에 수신하지 못한 사건까지 복원하지는 못한다.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir

_APPLICATION_ID = 0x41594331  # AYC1, 별도 읽기 전용 수신 커서 DB
_TABLE = "youtube_page_checkpoints"
_COLUMNS = ("selected_channel", "live_chat_id", "next_page_token",
            "completed_pages", "ended", "saved_at")


@dataclass(frozen=True)
class YouTubePagePosition:
    next_page_token: str
    completed_pages: int
    ended: bool


class YouTubePageCheckpoint:
    """동일 사용자가 선택한 채널·실제 liveChatId 조합만 이어받는다."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = (Path(path) if path is not None else
                     data_dir() / "youtube_page_checkpoints.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("유튜브 페이지 커서 DB는 심볼릭 링크를 사용할 수 없습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        if existed and not self.path.is_file():
            raise ValueError("유튜브 페이지 커서 DB가 일반 파일이 아닙니다.")
        with self._connect() as db:
            appid = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")}
            if ((existed and not tables) or
                    (tables and (appid != _APPLICATION_ID or
                                 tables != {_TABLE})) or
                    appid not in (0, _APPLICATION_ID)):
                raise ValueError("다른 SQLite 데이터베이스를 커서 DB로 사용하지 않습니다.")
            db.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS youtube_page_checkpoints("
                "selected_channel TEXT NOT NULL,"
                "live_chat_id TEXT NOT NULL,"
                "next_page_token TEXT NOT NULL,"
                "completed_pages INTEGER NOT NULL CHECK(completed_pages >= 0),"
                "ended INTEGER NOT NULL CHECK(ended IN (0,1)),"
                "saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "PRIMARY KEY(selected_channel,live_chat_id))")
            actual = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(youtube_page_checkpoints)"))
            if actual != _COLUMNS:
                raise ValueError("유튜브 페이지 커서 DB 구조가 일치하지 않습니다.")

    @contextmanager
    def _connect(self):
        with closing(sqlite3.connect(self.path, timeout=5.0)) as db:
            with db:
                yield db

    @staticmethod
    def _scope(selected_channel: str, live_chat_id: str) -> tuple[str, str]:
        if (type(selected_channel) is not str or
                type(live_chat_id) is not str or
                not selected_channel.strip() or not live_chat_id.strip() or
                len(selected_channel) > 256 or len(live_chat_id) > 512 or
                any(ord(ch) < 32 for ch in selected_channel + live_chat_id)):
            raise ValueError("유튜브 실제 채널·채팅방 식별자가 올바르지 않습니다.")
        return selected_channel, live_chat_id

    def load(self, selected_channel: str,
             live_chat_id: str) -> YouTubePagePosition | None:
        """현재 실제 방송의 이미 확정된 마지막 페이지 위치만 읽는다."""
        scope = self._scope(selected_channel, live_chat_id)
        with self._connect() as db:
            row = db.execute(
                "SELECT next_page_token,completed_pages,ended "
                "FROM youtube_page_checkpoints "
                "WHERE selected_channel=? AND live_chat_id=?", scope
            ).fetchone()
        if row is None:
            return None
        token, pages, ended = row
        if (type(token) is not str or len(token) > 2048 or
                type(pages) is not int or pages < 0 or ended not in (0, 1)):
            raise ValueError("유튜브 저장 페이지 위치가 손상됐습니다.")
        return YouTubePagePosition(token, pages, bool(ended))

    def commit_completed_page(
            self, selected_channel: str, live_chat_id: str,
            next_page_token: str | None, *, ended: bool) -> None:
        """한 API 페이지의 모든 메시지가 기존 SQLite에 수용된 후만 호출.

        페이지를 부분 수용한 상태에서는 호출하지 않는다. 커서 저장에
        실패하면 호출자가 다음 페이지로 이동하지 않고 수신을 중단한다.
        """
        scope = self._scope(selected_channel, live_chat_id)
        if (next_page_token is not None and
                (type(next_page_token) is not str or
                 len(next_page_token) > 2048)):
            raise ValueError("유튜브 다음 페이지 커서 형식이 올바르지 않습니다.")
        if type(ended) is not bool:
            raise ValueError("유튜브 방송 종료 표시 형식이 올바르지 않습니다.")
        if not ended and not next_page_token:
            raise ValueError("진행 중인 방송의 유튜브 페이지 커서가 없습니다.")
        with self._connect() as db:
            db.execute(
                "INSERT INTO youtube_page_checkpoints "
                "(selected_channel,live_chat_id,next_page_token,"
                "completed_pages,ended) VALUES(?,?,?,1,?) "
                "ON CONFLICT(selected_channel,live_chat_id) DO UPDATE SET "
                "next_page_token=excluded.next_page_token,"
                "completed_pages=youtube_page_checkpoints.completed_pages+1,"
                "ended=excluded.ended,saved_at=CURRENT_TIMESTAMP",
                (*scope, next_page_token or "", int(ended)))
