"""승인된 실제 한국어 AI 발화의 SQLite 시도/전달 불명 장부.

방송 음성은 한 번 밖으로 나가면 되돌릴 수 없으므로, 재시작 후
성공 여부가 불확실한 발화를 자동 재생하지 않는다. 사용자 채팅 원문,
AI 답변, 참조 음성, 인증정보는 저장하지 않는다. 기존 방송·채팅·
캐릭터 SQLite를 수정하지 않는 별도 독립 소유권 파일만 사용한다.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path

from .offline_settings import data_dir

_APPLICATION_ID = 0x41535631  # ASV1
_TABLE = "approved_live_voice_turns"
_STATES = frozenset(("재생요청완료", "중단", "불명"))
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def voice_turn_key(
    platform: str, channel: str, event_id: str | None, *, nonce: str,
) -> str:
    """실제 서버 이벤트 ID가 있으면 재연결 뒤에도 같은 발화로 인식.

    ID가 없는 별개 메시지는 본문·닉네임이 같아도 합치지 않는다.
    이 경우 발화 시도마다 새로운 무작위 nonce를 받아 독립 처리.
    """
    if (type(platform) is not str or platform not in
            ("twitch", "chzzk", "soop", "youtube")
            or type(channel) is not str or not 1 <= len(channel) <= 256
            or any(ord(c) < 32 for c in channel)
            or type(nonce) is not str or not re.fullmatch(r"[0-9a-f]{32}", nonce)):
        raise ValueError("실제 발화 채팅 출처가 잘못되었습니다.")
    if event_id is not None and (
            type(event_id) is not str or not 1 <= len(event_id) <= 512
            or any(ord(c) < 32 for c in event_id)):
        raise ValueError("실제 서버 채팅 이벤트 ID가 올바르지 않습니다.")
    identity = (
        "server\0" + platform + "\0" + channel + "\0" + event_id
        if event_id is not None
        else "no-id\0" + platform + "\0" + channel + "\0" + nonce
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


class ApprovedLiveVoiceJournal:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_live_voice.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("실제 음성 장부 경로에 바로가기를 사용할 수 없습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        if existed and not self.path.is_file():
            raise ValueError("실제 음성 장부가 일반 파일이 아닙니다.")
        with self._connect() as db:
            appid = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {
                row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'").fetchall()
            }
            if (appid not in (0, _APPLICATION_ID)
                    or (existed and not tables)
                    or tables and (tables != {_TABLE}
                                   or appid != _APPLICATION_ID)):
                raise ValueError("다른 프로그램의 SQLite를 변경하지 않습니다.")
            db.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_live_voice_turns("
                "turn_key TEXT PRIMARY KEY NOT NULL,"
                "reply_sha256 TEXT NOT NULL,"
                "state TEXT NOT NULL DEFAULT '시도',"
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            cols = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(approved_live_voice_turns)").fetchall())
            if cols != ("turn_key", "reply_sha256", "state",
                        "created_at", "updated_at"):
                raise ValueError("기존 발화 장부 구조가 일치하지 않습니다.")

    class _Connection:
        def __init__(self, path: Path) -> None:
            self.path = path
            self.db = None

        def __enter__(self):
            self.db = sqlite3.connect(self.path, timeout=10)
            self.db.execute("PRAGMA busy_timeout=10000")
            self.db.execute("PRAGMA synchronous=FULL")
            return self.db

        def __exit__(self, exc_type, exc, tb):
            try:
                if exc_type is None:
                    self.db.commit()
                else:
                    self.db.rollback()
            finally:
                self.db.close()
            return False

    def _connect(self):
        return self._Connection(self.path)

    @staticmethod
    def _validate_key(turn_key: str) -> None:
        if type(turn_key) is not str or _DIGEST.fullmatch(turn_key) is None:
            raise ValueError("실제 음성 발화 고유 키가 올바르지 않습니다.")

    def claim(self, turn_key: str, reply: str) -> bool:
        """음성 합성/OBS 입력 생성 *전* 영구 커밋. 중복 시 False."""
        self._validate_key(turn_key)
        if type(reply) is not str or not 1 <= len(reply) <= 6000:
            raise ValueError("실제 발화 답변 길이가 잘못되었습니다.")
        digest = hashlib.sha256(reply.encode("utf-8")).hexdigest()
        with self._connect() as db:
            result = db.execute(
                "INSERT OR IGNORE INTO approved_live_voice_turns"
                "(turn_key,reply_sha256,state) VALUES (?,?,'시도')",
                (turn_key, digest))
            return result.rowcount == 1

    def finish(self, turn_key: str, state: str) -> None:
        self._validate_key(turn_key)
        if state not in _STATES:
            raise ValueError("발화 결과는 완료 요청·중단·불명 중 하나여야 합니다.")
        with self._connect() as db:
            result = db.execute(
                "UPDATE approved_live_voice_turns SET state=?, "
                "updated_at=CURRENT_TIMESTAMP "
                "WHERE turn_key=? AND state='시도'",
                (state, turn_key))
            if result.rowcount != 1:
                raise RuntimeError("실제 음성 발화 시도 장부 상태가 일치하지 않습니다.")

    def recent(self, *, limit: int = 20) -> tuple[tuple[str, str, str], ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("발화 장부 조회 범위는 1~100건입니다.")
        with self._connect() as db:
            rows = db.execute(
                "SELECT substr(turn_key,1,12),state,created_at "
                "FROM approved_live_voice_turns "
                "ORDER BY created_at DESC,rowid DESC LIMIT ?",
                (limit,)).fetchall()
        return tuple((str(k), str(s), str(t)) for k,s,t in rows)
