"""기존 AISTING 방송 공지 초안을 운영자 승인하에 Discord 공식 Bot API에 실제 발신.

자동 실행이나 무단 발신 없음. 토큰·공지 본문·개인정보는 DB/로그에 저장하지 않음.
각 방송/채널/공지종류마다 최초 요청을 SQLite에 선기록해 불명 상태 재전송 차단.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .offline_settings import data_dir

_APP_ID = 0x41444E31
_SCHEMA = ("occurrence", "channel_id", "kind", "content_hash",
           "status", "message_id", "updated_at")


class UncertainDiscordDelivery(RuntimeError):
    """발신 결과가 불명확하므로 같은 회차 재발신하면 안 됨."""


class _DenyRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise UncertainDiscordDelivery("Discord 외부 게시 경로 변경은 허용하지 않습니다.")


@dataclass(frozen=True)
class DiscordNoticeReceipt:
    occurrence: str
    channel_id: str
    kind: str
    message_id: str


class ApprovedDiscordNoticeDelivery:
    """운영자가 선택한 실제 Discord 채널에 한 번만 공지를 게시."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_discord_notice.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("공지 영구 장부 바로가기를 사용할 수 없습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        if existed and not self.path.is_file():
            raise ValueError("공지 영구 장부는 일반 파일이어야 합니다.")
        with self._db() as db:
            app_id = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")}
            if ((existed and not tables) or
                    (tables and (app_id != _APP_ID or
                                 tables != {"approved_discord_notices"})) or
                    app_id not in (0, _APP_ID)):
                raise ValueError("소유권이 다른 기존 SQLite 파일은 변경할 수 없습니다.")
            db.execute(f"PRAGMA application_id={_APP_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_discord_notices("
                "occurrence TEXT NOT NULL, channel_id TEXT NOT NULL, "
                "kind TEXT NOT NULL, content_hash TEXT NOT NULL, "
                "status TEXT NOT NULL, message_id TEXT, "
                "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "PRIMARY KEY(occurrence,channel_id,kind))")
            columns = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(approved_discord_notices)"))
            if columns != _SCHEMA:
                raise ValueError("기존 공지 장부 구조가 일치하지 않습니다.")

    @contextmanager
    def _db(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db

    @staticmethod
    def validate(occurrence: str, channel_id: str, kind: str,
                 content: str, bot_token: str):
        if (type(occurrence) is not str or len(occurrence) != 16
                or occurrence[4] != "-" or occurrence[7] != "-"
                or occurrence[10] != " " or occurrence[13] != ":"
                or not all(occurrence[i].isascii() and occurrence[i].isdigit()
                           for i in (0,1,2,3,5,6,8,9,11,12,14,15))):
            raise ValueError("승인된 KST 시작 시각 형식이 잘못되었습니다.")
        if (type(channel_id) is not str or not 17 <= len(channel_id) <= 20
                or not channel_id.isascii() or not channel_id.isdecimal()):
            raise ValueError("Discord 채널 숫자 ID는 17~20자리입니다.")
        if kind not in ("시작", "종료"):
            raise ValueError("공지 종류는 시작·종료만 허용합니다.")
        if (type(content) is not str or not content.strip()
                or len(content) > 2000
                or any(ord(ch) < 32 and ch not in "\n\t" for ch in content)):
            raise ValueError("공지 본문은 1~2000자여야 합니다.")
        if (type(bot_token) is not str or not 20 <= len(bot_token) <= 300
                or not bot_token.isascii()
                or any(ord(ch) <= 32 or ord(ch) == 127 for ch in bot_token)):
            raise ValueError("Discord 공식 봇 토큰 형식이 올바르지 않습니다.")

    def send_once(self, *, occurrence: str, channel_id: str, kind: str,
                  content: str, bot_token: str, operator_approved: bool = False,
                  timeout: int = 12) -> DiscordNoticeReceipt:
        if operator_approved is not True:
            raise PermissionError("이 Discord 실제 게시를 운영자가 별도로 승인해야 합니다.")
        self.validate(occurrence, channel_id, kind, content, bot_token)
        if type(timeout) is not int or not 1 <= timeout <= 30:
            raise ValueError("Discord API 제한 시간이 잘못되었습니다.")
        fingerprint = hashlib.sha256(content.encode("utf-8")).hexdigest()
        with self._db() as db:
            changed = db.execute(
                "INSERT OR IGNORE INTO approved_discord_notices "
                "(occurrence,channel_id,kind,content_hash,status) "
                "VALUES(?,?,?,?,'시도')",
                (occurrence, channel_id, kind, fingerprint)).rowcount
            if changed != 1:
                raise UncertainDiscordDelivery(
                    "같은 방송·채널·공지 종류의 기존 시도가 있어 재발신하지 않습니다.")
        # 선기록 성공 이후 모든 오류·타임아웃은 불명 상태로 보존한다.
        body = json.dumps(
            {"content": content, "allowed_mentions": {"parse": []}},
            ensure_ascii=False).encode("utf-8")
        request = Request(
            "https://discord.com/api/v10/channels/" + channel_id + "/messages",
            data=body, method="POST",
            headers={"Authorization": "Bot " + bot_token,
                     "Content-Type": "application/json",
                     "User-Agent": "AISTING/1.0"})
        try:
            with build_opener(_DenyRedirect).open(request, timeout=timeout) as response:
                if response.status not in (200, 201):
                    raise UncertainDiscordDelivery("게시 성공 확인 실패")
                raw = response.read(65537)
            if len(raw) > 65536:
                raise UncertainDiscordDelivery("게시 확인 응답 크기 초과")
            payload = json.loads(raw)
            message_id = payload.get("id") if isinstance(payload, dict) else None
            if (type(message_id) is not str or not message_id.isascii()
                    or not message_id.isdecimal()):
                raise UncertainDiscordDelivery("게시 ID 확인 불가")
            with self._db() as db:
                updated = db.execute(
                    "UPDATE approved_discord_notices SET status='확인', "
                    "message_id=?, updated_at=CURRENT_TIMESTAMP "
                    "WHERE occurrence=? AND channel_id=? AND kind=? AND status='시도'",
                    (message_id, occurrence, channel_id, kind)).rowcount
                if updated != 1:
                    raise UncertainDiscordDelivery("공지 완료 장부 불일치")
            return DiscordNoticeReceipt(occurrence, channel_id, kind, message_id)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError,
                UncertainDiscordDelivery):
            # HTTP 원문(인증/URL/계정 등)은 예외에 포함하지 않는다.
            raise UncertainDiscordDelivery(
                "실제 게시 결과 불명 · 자동 재시도 차단 · 채널 수동 확인 필요") from None

    def recent(self, *, limit: int = 20):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("공지 장부 조회 범위가 올바르지 않습니다.")
        with self._db() as db:
            return tuple(db.execute(
                "SELECT occurrence,channel_id,kind,status,message_id "
                "FROM approved_discord_notices ORDER BY updated_at DESC LIMIT ?",
                (limit,)).fetchall())
