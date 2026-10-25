"""AISTING 네이티브 방송 채팅 미처리 작업의 안전한 SQLite 복구 큐.

기존 ConversationMemory/사용자 설정/캐릭터 DB를 절대 수정하지 않는다.
채팅을 AI 메모리 FIFO에 넣기 전에 단독 DB 트랜잭션을 확정한다.
확인된 AI 처리 또는 공식 실제 전달 뒤에만 해당 항목을 삭제한다.
강제 종료 후 미확인 항목은 보존하며, 재실행 때 동일 채널 선택에 한해
원래 순서대로 복구한다. 장애 직전 처리 완료의 재실행 중복 가능성이 있어
정확히 한 번 전송 보증은 아니며, 송출/녹화/채팅 게시도 수행하지 않는다.
"""
from __future__ import annotations

import os
import sqlite3
import stat
import threading
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir
from .multiplatform_readonly import PlatformChat

_DEFAULT_PATH = data_dir() / "pending_public_chat.sqlite3"
_APPLICATION_ID = 0x41535447  # ASTG
_MAX_RECORDS = 200_000
_MAX_MESSAGE = 4000


@dataclass(frozen=True)
class PendingChat:
    sequence: int
    message: PlatformChat


class DurablePublicChatQueue:
    """사용자 승인 후 선택한 채팅 수신기에 한해 읽고 쓰는 별도 로컬 DB."""

    def __init__(self, path: Path = _DEFAULT_PATH):
        self.path = Path(path)
        existed_before = self.path.exists()
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("미처리 채팅 저장 경로는 바로가기일 수 없습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and not self.path.is_file():
            raise ValueError("미처리 채팅 저장 경로가 일반 파일이 아닙니다.")
        self._lock = threading.RLock()
        self._consumer_lock_file = None
        # DB 연결은 작업마다 짧게 유지하여 Windows 종료 시 핸들 누수 방지.
        with self._connection() as db:
            appid = db.execute("PRAGMA application_id").fetchone()[0]
            existing = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'").fetchall()
            if existing and (appid != _APPLICATION_ID
                             or {row[0] for row in existing} != {"pending_public_chat"}):
                raise ValueError("AISTING 미처리 채팅 DB가 아닌 파일을 변경하지 않습니다.")
            if existed_before and not existing:
                raise ValueError("기존 빈 SQLite 파일의 소유권을 확인할 수 없습니다.")
            if not existing and appid not in (0, _APPLICATION_ID):
                raise ValueError("다른 프로그램의 DB를 덮어쓰지 않습니다.")
            db.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS pending_public_chat("
                "sequence INTEGER PRIMARY KEY AUTOINCREMENT,"
                "platform TEXT NOT NULL, channel TEXT NOT NULL,"
                "sender TEXT NOT NULL, message TEXT NOT NULL,"
                "event_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            # 기존 자료의 다른 스키마를 자동 변경하지 않는다.
            actual = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(pending_public_chat)").fetchall())
            if actual != ("sequence", "platform", "channel", "sender",
                          "message", "event_id", "created_at"):
                raise ValueError("AISTING 미처리 채팅 DB 구조가 일치하지 않습니다.")
            # 동일 본문/사용자의 별개 채팅은 보존. 플랫폼이 실제 발급한
            # 이벤트 ID가 같은 미확인 재전송에 한해서만 중복 작업을 막는다.
            db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "idx_aisting_pending_chat_server_event "
                "ON pending_public_chat(platform,channel,event_id) "
                "WHERE event_id IS NOT NULL")
            self._pending = int(db.execute(
                "SELECT COUNT(*) FROM pending_public_chat").fetchone()[0])

    def acquire_exclusive_consumer(self) -> None:
        """같은 미처리 DB를 둘 이상의 실행 창이 동시에 AI 처리하지 못하게 한다.

        OS 파일 잠금을 프로세스 생존 기간 동안 보유한다. 별도 잠금 파일만
        사용하고 원본 SQLite 스키마·채팅·캐릭터·설정은 변경하지 않는다.
        비정상 종료 시 운영체제가 잠금을 회수하므로 오래된 PID 파일을
        강제로 삭제하거나 기존 세션을 종료할 필요가 없다.
        """
        with self._lock:
            if self._consumer_lock_file is not None:
                return
            lock_path = self.path.with_name(self.path.name + ".consumer.lock")
            if lock_path.is_symlink() or lock_path.parent.is_symlink():
                raise RuntimeError("공개 채팅 처리 잠금 경로가 바로가기여서 중단합니다.")
            flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(lock_path, flags, 0o600)
            handle = os.fdopen(fd, "r+b", buffering=0)
            try:
                if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                    raise RuntimeError("공개 채팅 처리 잠금 경로가 일반 파일이 아닙니다.")
                if os.name == "nt":
                    # Windows msvcrt.locking은 길이 1인 구간을 사용한다.
                    import msvcrt
                    if os.fstat(handle.fileno()).st_size == 0:
                        handle.write(b"\\x00")
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (OSError, RuntimeError) as exc:
                handle.close()
                raise RuntimeError(
                    "이 미처리 채팅 DB는 다른 AISTING 실행 창에서 사용 중이거나 "
                    "잠금을 확보할 수 없습니다. 중복 AI 처리를 막기 위해 "
                    "새 연결을 시작하지 않습니다.") from exc
            self._consumer_lock_file = handle

    def release_exclusive_consumer(self) -> None:
        """작업자 종료 후에만 호출. 잠금 파일은 삭제하지 않는다."""
        with self._lock:
            handle = self._consumer_lock_file
            if handle is None:
                return
            self._consumer_lock_file = None
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()

    @contextmanager
    def _connection(self):
        # 외부 디렉터리나 사용자 DB에 대한 임의 쓰기는 허용되지 않는다.
        with closing(sqlite3.connect(self.path, timeout=5.0)) as db:
            with db:
                yield db

    @staticmethod
    def _fields(chat) -> tuple[str, str, str, str, str | None]:
        platform = getattr(chat, "platform", "twitch")
        channel = getattr(chat, "channel", None)
        sender = getattr(chat, "sender", None)
        message = getattr(chat, "text", None)
        event_id = getattr(chat, "event_id", None)
        if (platform not in ("twitch", "chzzk", "soop", "youtube")
                or any(type(v) is not str or not v.strip()
                       for v in (channel, sender, message))
                or any(len(v) > limit for v, limit in
                       ((channel, 256), (sender, 256), (message, _MAX_MESSAGE)))
                or (event_id is not None and (
                    type(event_id) is not str or len(event_id) > 512))):
            raise ValueError("복구할 공개 채팅의 형식 또는 길이가 잘못되었습니다.")
        return platform, channel, sender, message, (event_id or None)

    def append(self, chat) -> int | None:
        """커밋 뒤 ID 반환. 이미 보류 중인 실제 서버 ID 재전송이면 None.

        본문 같은 별개 채팅 또는 서버 ID 없는 메시지는 절대 합치지 않는다.
        """
        fields = self._fields(chat)
        with self._lock, self._connection() as db:
            if fields[-1] is not None:
                old = db.execute(
                    "SELECT sequence FROM pending_public_chat "
                    "WHERE platform=? AND channel=? AND event_id=?",
                    (fields[0], fields[1], fields[-1])).fetchone()
                if old is not None:
                    return None
            number = db.execute("SELECT COUNT(*) FROM pending_public_chat").fetchone()[0]
            if number >= _MAX_RECORDS:
                raise RuntimeError("미처리 채팅 보호 한도에 도달했습니다. 조용히 폐기하지 않습니다.")
            cursor = db.execute(
                "INSERT OR IGNORE INTO pending_public_chat "
                "(platform, channel, sender, message, event_id) VALUES(?,?,?,?,?)", fields)
            # 외부 동시 인스턴스가 같은 실제 서버 ID를 막 넣은 경우.
            if cursor.rowcount == 1:
                self._pending += 1
                return int(cursor.lastrowid)
            return None

    def confirm(self, sequence: int) -> bool:
        """실제 AI 처리 결과가 끝났거나 공식 텍스트 전달이 확인된 것만 제거."""
        if type(sequence) is not int or sequence < 1:
            raise ValueError("미처리 채팅 식별자가 올바르지 않습니다.")
        with self._lock, self._connection() as db:
            removed = db.execute(
                "DELETE FROM pending_public_chat WHERE sequence=?", (sequence,)
            ).rowcount == 1
            if removed:
                self._pending = max(0, self._pending - 1)
            return removed

    def load_for(self, channels: dict[str, str], *, limit: int = 4096
                 ) -> list[PendingChat]:
        """저장된 전역 수신 순서 유지. 채널이 바뀌면 다른 방송 내용은 격리."""
        if (not isinstance(channels, dict) or not channels
                or any(k not in ("twitch", "chzzk", "soop", "youtube")
                       or type(v) is not str or not v.strip()
                       for k, v in channels.items())):
            raise ValueError("복구할 플랫폼 및 채널 선택을 확인하세요.")
        if type(limit) is not int or not 1 <= limit <= 20_000:
            raise ValueError("복구 한도가 올바르지 않습니다.")
        clauses = " OR ".join("(platform=? AND channel=?)" for _ in channels)
        args = [x for platform, channel in channels.items()
                for x in (platform, channel)]
        with self._lock, self._connection() as db:
            rows = db.execute(
                "SELECT sequence,platform,channel,sender,message,event_id "
                f"FROM pending_public_chat WHERE {clauses} ORDER BY sequence LIMIT ?",
                [*args, limit + 1]).fetchall()
        if len(rows) > limit:
            # 일부만 복구하면 늦은 항목보다 새 채팅이 먼저 들어가 순서 손상.
            raise RuntimeError("복구할 채팅이 작업 한도를 초과하여 새 연결을 중단했습니다.")
        recovered = []
        for seq, platform, channel, sender, message, event_id in rows:
            chat = PlatformChat(channel=channel, sender=sender, text=message,
                                platform=platform, event_id=event_id,
                                parsed_at_monotonic=None)
            recovered.append(PendingChat(int(seq), chat))
        return recovered


    def recovery_snapshot(self, channels: dict[str, str]) -> tuple[int, int]:
        """선택 채널의 복구 대상 건수와 고정된 최종 순번을 한 번에 확인한다.

        전체 미처리 자료를 GUI 메모리에 올리지 않고 읽기 전용 조회만 수행한다.
        """
        if (not isinstance(channels, dict) or not channels
                or any(k not in ("twitch", "chzzk", "soop", "youtube")
                       or type(v) is not str or not v.strip()
                       for k, v in channels.items())):
            raise ValueError("복구할 플랫폼 및 채널 선택을 확인하세요.")
        clauses = " OR ".join("(platform=? AND channel=?)" for _ in channels)
        args = [value for platform, channel in channels.items()
                for value in (platform, channel)]
        with self._lock, self._connection() as db:
            count, last = db.execute(
                "SELECT COUNT(*), COALESCE(MAX(sequence), 0) "
                f"FROM pending_public_chat WHERE {clauses}", args
            ).fetchone()
        return int(count), int(last)

    def iter_recovery(self, channels: dict[str, str], *,
                      through_sequence: int, batch_size: int = 256):
        """한정된 페이지로 전체 미처리 채팅을 원래 전역 순서대로 읽는다.

        마지막 순번을 고정하여 복구 도중 다른 인스턴스의 신규 입력이
        과거 복구에 무한히 합류하지 않도록 한다. 원본 행은 삭제하지 않는다.
        실제 AI 처리 성공 시에만 기존 confirm()이 개별 행을 제거한다.
        """
        if (not isinstance(channels, dict) or not channels
                or any(k not in ("twitch", "chzzk", "soop", "youtube")
                       or type(v) is not str or not v.strip()
                       for k, v in channels.items())
                or type(through_sequence) is not int or through_sequence < 0
                or type(batch_size) is not int or not 1 <= batch_size <= 4096):
            raise ValueError("미처리 채팅 순차 복구 조건이 잘못되었습니다.")
        clauses = " OR ".join("(platform=? AND channel=?)" for _ in channels)
        args = [value for platform, channel in channels.items()
                for value in (platform, channel)]
        cursor = 0
        while cursor < through_sequence:
            with self._lock, self._connection() as db:
                rows = db.execute(
                    "SELECT sequence,platform,channel,sender,message,event_id "
                    f"FROM pending_public_chat WHERE ({clauses}) "
                    "AND sequence>? AND sequence<=? "
                    "ORDER BY sequence LIMIT ?",
                    [*args, cursor, through_sequence, batch_size]
                ).fetchall()
            if not rows:
                return
            for seq, platform, channel, sender, message, event_id in rows:
                cursor = int(seq)
                yield PendingChat(
                    cursor, PlatformChat(
                        channel=channel, sender=sender, text=message,
                        platform=platform, event_id=event_id,
                        parsed_at_monotonic=None))

    def pending_count(self) -> int:
        """GUI 표시에는 DB 파일 잠금/쓰기 없이 이전 확정 값을 사용한다."""
        with self._lock:
            return self._pending
