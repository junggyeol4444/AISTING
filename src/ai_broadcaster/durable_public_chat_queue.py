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
import time
import math
from collections import deque
from datetime import datetime, timezone
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir
from .multiplatform_readonly import PlatformChat

_DEFAULT_PATH = data_dir() / "pending_public_chat.sqlite3"
_APPLICATION_ID = 0x41535447  # ASTG
_MAX_RECORDS = 200_000
_MAX_MESSAGE = 4000
_INCIDENT_STATES = frozenset(("로컬AI확정실패", "공식AI전달불명"))


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
            tables = {row[0] for row in existing}
            if existing and (appid != _APPLICATION_ID
                             or "pending_public_chat" not in tables
                             or not tables.issubset({
                                 "pending_public_chat", "confirmed_server_events",
                                 "public_chat_processing_incidents"})):
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
            # 기존 pending 데이터/열은 변경하지 않는 추가 기록 장부.
            # 실제 완료 ACK와 서버 ID 기록을 같은 SQLite 트랜잭션으로
            # 커밋하여 정상 재연결 시 처리 완료된 동일 이벤트를 다시 AI에
            # 전달하지 않는다. ID 없는 별도 채팅은 절대 병합하지 않는다.
            db.execute(
                "CREATE TABLE IF NOT EXISTS confirmed_server_events("
                "platform TEXT NOT NULL, channel TEXT NOT NULL,"
                "event_id TEXT NOT NULL,"
                "confirmed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "PRIMARY KEY(platform,channel,event_id))")
            completed_columns = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(confirmed_server_events)").fetchall())
            if completed_columns != (
                    "platform", "channel", "event_id", "confirmed_at"):
                raise ValueError(
                    "기존 채팅 완료 ID 기록 장부 구조가 일치하지 않습니다.")
            # AI 처리 확정에 실패한 원래 미처리 sequence만 사건 기록.
            # 원본 채팅 본문/닉네임, 서버 이벤트 ID, SQLite 기억은 불변.
            db.execute(
                "CREATE TABLE IF NOT EXISTS public_chat_processing_incidents("
                "sequence INTEGER NOT NULL, "
                "incident_kind TEXT NOT NULL, "
                "recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "PRIMARY KEY(sequence,incident_kind))")
            incident_columns = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(public_chat_processing_incidents)").fetchall())
            if incident_columns != ("sequence", "incident_kind", "recorded_at"):
                raise ValueError("기존 공개 채팅 장애 장부 구조가 일치하지 않습니다.")
            # 동일 본문/사용자의 별개 채팅은 보존. 플랫폼이 실제 발급한
            # 이벤트 ID의 보류 중/처리 완료 재전송만 중복 작업으로 막는다.
            db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "idx_aisting_pending_chat_server_event "
                "ON pending_public_chat(platform,channel,event_id) "
                "WHERE event_id IS NOT NULL")
            # 4플랫폼 수신 중에는 선택 방송 채널의 시퀀스 범위 복구와
            # 재부팅 후 잔여 건수 조회가 가장 빈번하다. 기존 보류 행은
            # 변경하지 않고 채널·순번 복합 인덱스만 추가한다.
            db.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_aisting_pending_chat_channel_sequence "
                "ON pending_public_chat(platform,channel,sequence)")
            self._pending = int(db.execute(
                "SELECT COUNT(*) FROM pending_public_chat").fetchone()[0])
            # 재시작 전 남아 있던 채팅까지 플랫폼별로 정확히 포함한다.
            # 원본 행이나 서버 이벤트 ID는 수정하지 않고, 실제 커밋
            # 이후에만 갱신되는 읽기 전용 운영 상태 카운터를 유지한다.
            self._pending_by_platform = {
                platform: int(count) for platform, count in db.execute(
                    "SELECT platform, COUNT(*) FROM pending_public_chat "
                    "GROUP BY platform").fetchall()
            }
            # 원본 DB 열을 바꾸지 않고 이미 기록된 UTC 접수 시각을
            # 플랫폼별 최장 미처리 채팅의 시작점으로 복구한다.
            self._oldest_pending = {
                platform: (int(sequence), str(created_at))
                for platform, sequence, created_at in db.execute(
                    "SELECT p.platform,p.sequence,p.created_at "
                    "FROM pending_public_chat AS p "
                    "JOIN (SELECT platform,MIN(sequence) AS first_sequence "
                    "FROM pending_public_chat GROUP BY platform) AS first "
                    "ON p.platform=first.platform "
                    "AND p.sequence=first.first_sequence").fetchall()
            }
        # 다른 방송 채널의 장기 미처리 메시지를 현재 채널 적체로
        # 잘못 표시하지 않도록 채널별 실제 SQLite 잔여 건수를 복원한다.
        # 새 표나 기존 채팅 열은 만들거나 변경하지 않는다.
        # DB 연결은 위 with 블록에서 닫혔으므로 별도 읽기 연결 사용.
        with self._connection() as db:
            self._pending_by_channel = {
                (platform, channel): int(count)
                for platform, channel, count in db.execute(
                    "SELECT platform,channel,COUNT(*) FROM pending_public_chat "
                    "GROUP BY platform,channel").fetchall()
            }
            self._oldest_pending_by_channel = {
                (platform, channel): (int(sequence), str(created_at))
                for platform, channel, sequence, created_at in db.execute(
                    "SELECT p.platform,p.channel,p.sequence,p.created_at "
                    "FROM pending_public_chat AS p JOIN "
                    "(SELECT platform,channel,MIN(sequence) AS first_sequence "
                    "FROM pending_public_chat GROUP BY platform,channel) AS first "
                    "ON p.platform=first.platform AND p.channel=first.channel "
                    "AND p.sequence=first.first_sequence").fetchall()
            }
        # AI 완료와 새 채팅의 최근 처리율은 메모리에만 유지한다.
        # 이전 실행의 측정치를 만들어내지 않고 새 프로세스에서 다시 센다.
        self._rate_started_at = time.monotonic()
        self._recent_ingress = {
            code: deque() for code in ("twitch", "chzzk", "soop", "youtube")}
        self._recent_confirmed = {
            code: deque() for code in ("twitch", "chzzk", "soop", "youtube")}

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
                        handle.write(bytes((0,)))
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
        """서버 ID가 이미 완료되거나 보류 중일 때만 중복 등록을 차단.

        실제 수신 이벤트를 로컬 SQLite에 먼저 커밋하고 sequence를
        반환한다. 본문·닉네임만 같은 별개의 메시지는 각각 저장한다.
        """
        fields = self._fields(chat)
        with self._lock:
            inserted = None
            inserted_created_at = None
            with self._connection() as db:
                if fields[-1] is not None:
                    completed = db.execute(
                        "SELECT 1 FROM confirmed_server_events "
                        "WHERE platform=? AND channel=? AND event_id=?",
                        (fields[0], fields[1], fields[-1])).fetchone()
                    if completed is not None:
                        return None
                    old = db.execute(
                        "SELECT sequence FROM pending_public_chat "
                        "WHERE platform=? AND channel=? AND event_id=?",
                        (fields[0], fields[1], fields[-1])).fetchone()
                    if old is not None:
                        return None
                # 기존 단일 소비자 락과 이 인스턴스의 RLock으로
                # 모든 성공 커밋의 건수를 유지한다. 수백 명 동시 채팅마다
                # 전체 테이블 COUNT를 수행하면 24시간 수신 병목이 된다.
                if self._pending >= _MAX_RECORDS:
                    raise RuntimeError(
                        "미처리 채팅 보호 한도에 도달했습니다. 조용히 폐기하지 않습니다.")
                cursor = db.execute(
                    "INSERT OR IGNORE INTO pending_public_chat "
                    "(platform,channel,sender,message,event_id) VALUES(?,?,?,?,?)",
                    fields)
                if cursor.rowcount == 1:
                    inserted = int(cursor.lastrowid)
                    inserted_created_at = db.execute(
                        "SELECT created_at FROM pending_public_chat WHERE sequence=?",
                        (inserted,)).fetchone()[0]
            # COMMIT에 실패하면 메모리 카운터도 성공으로 올리지 않는다.
            if inserted is not None:
                self._pending += 1
                platform = fields[0]
                self._pending_by_platform[platform] = (
                    self._pending_by_platform.get(platform, 0) + 1)
                self._recent_ingress[platform].append(time.monotonic())
                if platform not in self._oldest_pending:
                    self._oldest_pending[platform] = (
                        inserted, str(inserted_created_at))
                channel_key = (platform, fields[1])
                self._pending_by_channel[channel_key] = (
                    self._pending_by_channel.get(channel_key, 0) + 1)
                if channel_key not in self._oldest_pending_by_channel:
                    self._oldest_pending_by_channel[channel_key] = (
                        inserted, str(inserted_created_at))
            return inserted

    def confirm(self, sequence: int) -> bool:
        """실제 AI/공식 전달 완료 시 서버 ID+삭제를 하나의 트랜잭션으로 확정."""
        if type(sequence) is not int or sequence < 1:
            raise ValueError("미처리 채팅 식별자가 올바르지 않습니다.")
        with self._lock:
            removed = False
            was_oldest = False
            was_channel_oldest = False
            next_oldest = None
            next_channel_oldest = None
            with self._connection() as db:
                row = db.execute(
                    "SELECT platform,channel,event_id FROM pending_public_chat "
                    "WHERE sequence=?", (sequence,)).fetchone()
                if row is not None:
                    was_oldest = (
                        self._oldest_pending.get(row[0], (None,))[0] == sequence)
                    channel_key = (row[0], row[1])
                    was_channel_oldest = (
                        self._oldest_pending_by_channel.get(
                            channel_key, (None,))[0] == sequence)
                    if row[2] is not None:
                        db.execute(
                            "INSERT OR IGNORE INTO confirmed_server_events "
                            "(platform,channel,event_id) VALUES(?,?,?)", row)
                    removed = db.execute(
                        "DELETE FROM pending_public_chat WHERE sequence=?",
                        (sequence,)).rowcount == 1
                    if removed and was_oldest:
                        next_oldest = db.execute(
                            "SELECT sequence,created_at FROM pending_public_chat "
                            "WHERE platform=? ORDER BY sequence LIMIT 1",
                            (row[0],)).fetchone()
                    if removed and was_channel_oldest:
                        next_channel_oldest = db.execute(
                            "SELECT sequence,created_at FROM pending_public_chat "
                            "WHERE platform=? AND channel=? "
                            "ORDER BY sequence LIMIT 1",
                            (row[0], row[1])).fetchone()
            if removed:
                self._pending = max(0, self._pending - 1)
                platform = row[0]
                self._pending_by_platform[platform] = max(
                    0, self._pending_by_platform.get(platform, 0) - 1)
                self._recent_confirmed[platform].append(time.monotonic())
                if was_oldest:
                    if next_oldest is None:
                        self._oldest_pending.pop(platform, None)
                    else:
                        self._oldest_pending[platform] = (
                            int(next_oldest[0]), str(next_oldest[1]))
                channel_key = (row[0], row[1])
                remaining = max(
                    0, self._pending_by_channel.get(channel_key, 0) - 1)
                if remaining:
                    self._pending_by_channel[channel_key] = remaining
                else:
                    self._pending_by_channel.pop(channel_key, None)
                if was_channel_oldest:
                    if next_channel_oldest is None:
                        self._oldest_pending_by_channel.pop(channel_key, None)
                    else:
                        self._oldest_pending_by_channel[channel_key] = (
                            int(next_channel_oldest[0]),
                            str(next_channel_oldest[1]))
            return removed


    def record_processing_incident(self, sequence: int, kind: str) -> bool:
        """실제 FIFO 실패를 채팅 본문 없이 append-only로 영구 보존.

        원본 pending 채팅이 존재하는 경우만 기록한다. 한 sequence/종류는
        여러 실행에서 발생해도 최초 1회만 저장한다. DB 장애는 호출자에게
        전달하며 원본 pending 건을 완료 처리하거나 삭제하지 않는다.
        """
        if type(sequence) is not int or sequence < 1:
            raise ValueError("AI 처리 실패 원본 순번이 올바르지 않습니다.")
        if type(kind) is not str or kind not in _INCIDENT_STATES:
            raise ValueError("공개 채팅 실패 종류가 올바르지 않습니다.")
        with self._lock, self._connection() as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO public_chat_processing_incidents "
                "(sequence,incident_kind) SELECT sequence,? "
                "FROM pending_public_chat WHERE sequence=?", (kind, sequence))
            if cursor.rowcount == 1:
                return True
            known = db.execute(
                "SELECT 1 FROM public_chat_processing_incidents "
                "WHERE sequence=? AND incident_kind=?", (sequence, kind)).fetchone()
            if known is None:
                raise RuntimeError("실패 사건에 해당하는 미처리 채팅이 없습니다.")
            return False

    def recent_processing_incidents(self, *, limit: int = 25
                                    ) -> tuple[tuple[int, str, str], ...]:
        """원본 발화·작성자 없이 최근 실패 사건만 운영자에게 제공."""
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("공개 채팅 장애 내역 조회 범위가 올바르지 않습니다.")
        with self._lock, self._connection() as db:
            rows = db.execute(
                "SELECT sequence,incident_kind,recorded_at "
                "FROM public_chat_processing_incidents "
                "ORDER BY recorded_at DESC, sequence DESC LIMIT ?",
                (limit,)).fetchall()
        return tuple((int(sequence), str(kind), str(at))
                     for sequence, kind, at in rows)

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

    def recovery_ceiling(self, channels: dict[str, str]) -> int:
        """현재 선택한 방송의 복구 대상 마지막 순번만 빠르게 조회한다.

        최초 복구 건수는 기존 recovery_snapshot()으로 한 번 확인한다.
        상시 수신 작업에서는 SQLite COUNT 전체 스캔을 반복하지 않고
        기존 채널·순번 인덱스의 MAX만 조회해 읽기와 AI 등록을 분리한다.
        이 값은 접수 순번이며 실제 채팅 총량/무누락 증거가 아니다.
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
            row = db.execute(
                "SELECT COALESCE(MAX(sequence), 0) "
                f"FROM pending_public_chat WHERE {clauses}", args).fetchone()
        return int(row[0])


    def iter_recovery(self, channels: dict[str, str], *,
                      through_sequence: int, batch_size: int = 256,
                      after_sequence: int = 0):
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
                or type(batch_size) is not int or not 1 <= batch_size <= 4096
                or type(after_sequence) is not int
                or not 0 <= after_sequence <= through_sequence):
            raise ValueError("미처리 채팅 순차 복구 조건이 잘못되었습니다.")
        clauses = " OR ".join("(platform=? AND channel=?)" for _ in channels)
        args = [value for platform, channel in channels.items()
                for value in (platform, channel)]
        # 실행 중 도착한 실제 플랫폼 메시지는 새 seq를 발급받는다.
        # 이전 페이지를 중복 AI 등록하지 않고 이어받는 커서이다.
        cursor = after_sequence
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

    def pending_by_platform_snapshot(self) -> dict[str, int]:
        """실제 SQLite 성공 커밋을 기준으로 플랫폼별 잔여 건수를 반환한다.

        GUI는 5초마다 이 메모리 스냅샷만 조회한다. 사용자 채팅
        본문·닉네임·이벤트 ID를 로그로 내보내거나 DB를 재조회하지 않는다.
        이 건수는 이미 AI FIFO에 등록했으나 아직 처리 완료하지 않은
        채팅까지 포함하므로, 미등록 큐 길이나 서버 무누락 증거가 아니다.
        """
        with self._lock:
            return dict(self._pending_by_platform)

    def pending_selected_channels_snapshot(
            self, channels: dict[str, str]) -> dict[str, dict[str, object]]:
        """현재 운영자가 선택한 방송 채널의 실제 미처리만 조회한다.

        다른 채널의 미처리 자료는 디스크에 그대로 보존한다. GUI는
        SQLite 파일을 열지 않고 성공 커밋 뒤 갱신된 메모리만 읽는다.
        시청자에게 전달됐는지 또는 서버에서 누락됐는지는 증명하지 않는다.
        """
        if (type(channels) is not dict or not channels
                or any(code not in ("twitch", "chzzk", "soop", "youtube")
                       or type(channel) is not str or not channel.strip()
                       for code, channel in channels.items())):
            raise ValueError("운영 중인 플랫폼·채널 선택이 올바르지 않습니다.")
        with self._lock:
            utc_now = datetime.now(timezone.utc)
            result = {}
            for code, channel in channels.items():
                key = (code, channel)
                oldest = self._oldest_pending_by_channel.get(key)
                age = None
                if oldest is not None:
                    try:
                        recorded = datetime.strptime(
                            oldest[1], "%Y-%m-%d %H:%M:%S"
                        ).replace(tzinfo=timezone.utc)
                        age = max(0.0, (utc_now - recorded).total_seconds())
                    except (TypeError, ValueError, OverflowError):
                        pass
                result[code] = {
                    "미처리": self._pending_by_channel.get(key, 0),
                    "최장미처리초": age,
                    "최초순번": oldest[0] if oldest is not None else None,
                }
            return result

    def pending_capacity_snapshot(self) -> dict[str, object]:
        """SQLite 보호 한도 접근을 GUI에서 사전에 관찰한다.

        80% 이상이면 운영자에게 적체 위험을 알리기 위한 수치만
        제공한다. 실제 수신을 임의로 중지·삭제하거나 메시지를 건너뛰지
        않으며 보호 한도와 사용자 설정을 변경하지 않는다.
        """
        with self._lock:
            return {
                "미처리": self._pending,
                "보호한도": _MAX_RECORDS,
                "사용률": self._pending / _MAX_RECORDS,
                "플랫폼별": dict(self._pending_by_platform),
            }

    def pending_operating_snapshot(self, *, window_seconds: float = 60.0) -> dict:
        """기존 원본 채팅을 읽지 않고 4플랫폼 처리율·최장 대기를 관찰한다.

        최근 처리율은 이번 실행에서 실제 SQLite 성공 커밋한 것만 센다.
        과거 실행의 수신·처리율은 알 수 없으며, 소진 시간은 보장이 아니다.
        """
        if (type(window_seconds) not in (int, float)
                or not math.isfinite(window_seconds)
                or not 1.0 <= window_seconds <= 3600.0):
            raise ValueError("채팅 처리율 관측 구간이 올바르지 않습니다.")
        with self._lock:
            now = time.monotonic()
            duration = max(1.0, min(float(window_seconds),
                                    now - self._rate_started_at))
            cutoff = now - float(window_seconds)
            utc_now = datetime.now(timezone.utc)
            platforms = {}
            for code in ("twitch", "chzzk", "soop", "youtube"):
                arrivals = self._recent_ingress[code]
                confirmed = self._recent_confirmed[code]
                while arrivals and arrivals[0] < cutoff:
                    arrivals.popleft()
                while confirmed and confirmed[0] < cutoff:
                    confirmed.popleft()
                ingress_rate = len(arrivals) / duration
                completed_rate = len(confirmed) / duration
                oldest = self._oldest_pending.get(code)
                oldest_age = None
                if oldest is not None:
                    try:
                        recorded = datetime.strptime(
                            oldest[1], "%Y-%m-%d %H:%M:%S"
                        ).replace(tzinfo=timezone.utc)
                        oldest_age = max(
                            0.0, (utc_now - recorded).total_seconds())
                    except (TypeError, ValueError, OverflowError):
                        # 원본 created_at이 잘못됐어도 기존 채팅은 보존.
                        pass
                pending = self._pending_by_platform.get(code, 0)
                platforms[code] = {
                    "미처리": pending,
                    "최장미처리초": oldest_age,
                    "최근접수": len(arrivals),
                    "최근완료": len(confirmed),
                    "접수초당": ingress_rate,
                    "완료초당": completed_rate,
                    "순증초당": ingress_rate - completed_rate,
                    "추정소진초": (
                        pending / completed_rate if completed_rate > 0
                        else None),
                }
            total_ingress = sum(
                len(self._recent_ingress[code])
                for code in ("twitch", "chzzk", "soop", "youtube"))
            total_confirmed = sum(
                len(self._recent_confirmed[code])
                for code in ("twitch", "chzzk", "soop", "youtube"))
            net_growth = (total_ingress - total_confirmed) / duration
            # 10초 미만 표본이나 순감소·정체에는 허위 마감 시간을 표시하지 않는다.
            projected_limit = (
                max(0, _MAX_RECORDS - self._pending) / net_growth
                if duration >= 10.0 and net_growth > 0.0 else None)
            return {
                "측정창초": duration,
                "실행중측정": True,
                "전체순증초당": net_growth,
                "추정보호한도도달초": projected_limit,
                "플랫폼별": platforms,
                "시각기준": "SQLite UTC 접수 시각·운영체제 현재 시각",
            }
