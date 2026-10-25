"""실제 한국어 AI 발화의 Windows 사용자 전용 DPAPI·SQLite 영구 대기함.

기존 발화 시도 장부/사용자 채팅·캐릭터 DB는 건드리지 않는다.
AI 답변은 Windows 현재 사용자 DPAPI로 암호화해 저장하고, 실제
OBS·Cubism·음성 합성 전에 원자적으로 '시도'로 전환한다.

강제 종료 뒤 이전 세션의 '대기'는 자동으로 다른 방송에 발화하지
않으며 '시도' 상태는 전달 여부 불명으로 간주해 자동 재발화하지 않는다.
"""
from __future__ import annotations

import ctypes
import hashlib
import re
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

from .offline_settings import data_dir

_APP_ID = 0x41564F31  # AVO1
_TABLE = "approved_live_voice_outbox"
_KEY = re.compile(r"[0-9a-f]{64}\Z")
_SESSION = re.compile(r"[0-9a-f]{32}\Z")
_MAX_PENDING = 200_000
_FINAL = frozenset(("완료", "중단", "불명", "중복"))
_ENTROPY = b"AISTING-approved-live-voice-outbox-v1"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32),
                ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(data: bytes) -> tuple[_DataBlob, object]:
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(
        buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


class _WindowsUserDPAPI:
    """Windows 계정 로그인 범위 암호화. 암호·복호화 실패 시 원문 저장 금지."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSError("실제 방송 영구 음성 대기함은 Windows DPAPI가 필요합니다.")
        self._crypt = ctypes.WinDLL("crypt32", use_last_error=True)
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        ptr = ctypes.POINTER(_DataBlob)
        self._crypt.CryptProtectData.argtypes = (
            ptr, ctypes.c_wchar_p, ptr, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_uint32, ptr)
        self._crypt.CryptProtectData.restype = ctypes.c_int
        self._crypt.CryptUnprotectData.argtypes = (
            ptr, ctypes.c_void_p, ptr, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_uint32, ptr)
        self._crypt.CryptUnprotectData.restype = ctypes.c_int
        self._kernel.LocalFree.argtypes = (ctypes.c_void_p,)
        self._kernel.LocalFree.restype = ctypes.c_void_p

    def _transform(self, data: bytes, *, decrypt: bool) -> bytes:
        source, keep = _blob(data)
        entropy, entropy_keep = _blob(_ENTROPY)
        result = _DataBlob()
        if decrypt:
            ok = self._crypt.CryptUnprotectData(
                ctypes.byref(source), None, ctypes.byref(entropy),
                None, None, 0x01, ctypes.byref(result))
        else:
            ok = self._crypt.CryptProtectData(
                ctypes.byref(source), None, ctypes.byref(entropy),
                None, None, 0x01, ctypes.byref(result))
        if not ok:
            raise OSError("현재 Windows 사용자 계정에서 음성 대기함 암호 처리 실패")
        try:
            if not result.pbData or result.cbData <= 0:
                raise RuntimeError("Windows 음성 대기함 암호 결과가 비어 있습니다.")
            return ctypes.string_at(result.pbData, result.cbData)
        finally:
            if result.pbData:
                self._kernel.LocalFree(
                    ctypes.cast(result.pbData, ctypes.c_void_p))

    def protect(self, reply: str) -> bytes:
        return self._transform(reply.encode("utf-8"), decrypt=False)

    def unprotect(self, payload: bytes) -> str:
        try:
            return self._transform(payload, decrypt=True).decode("utf-8")
        except UnicodeError as exc:
            raise RuntimeError("암호화된 한국어 발화 원문을 복원할 수 없습니다.") from exc


class ApprovedLiveVoiceOutbox:
    """같은 방송 실행 세션에서만 원순서대로 처리하는 영구 대기함."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_live_voice_outbox.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("음성 영구 대기함에 바로가기 경로를 사용할 수 없습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        if existed and not self.path.is_file():
            raise ValueError("음성 영구 대기함이 일반 파일이 아닙니다.")
        self._dpapi = _WindowsUserDPAPI()
        with self._connect() as db:
            appid = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")}
            if (appid not in (0, _APP_ID)
                    or existed and not tables
                    or tables and (not tables.issubset({_TABLE, "approved_live_voice_recovery_audit"})
                                   or _TABLE not in tables or appid != _APP_ID)):
                raise ValueError("다른 프로그램의 SQLite 파일은 변경하지 않습니다.")
            db.execute(f"PRAGMA application_id={_APP_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_live_voice_outbox("
                "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
                "session_id TEXT NOT NULL,"
                "turn_key TEXT NOT NULL UNIQUE,"
                "encrypted_reply BLOB NOT NULL,"
                "reply_sha256 TEXT NOT NULL,"
                "state TEXT NOT NULL DEFAULT '대기',"
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute(
                f"CREATE INDEX IF NOT EXISTS avo_session_fifo "
                f"ON {_TABLE}(session_id,state,seq)")
            db.execute(
                f"CREATE INDEX IF NOT EXISTS avo_state_count "
                f"ON {_TABLE}(state)")
            # 기존 음성 원문·세션을 보존하며 수동 인계의 출처만 별도 기록.
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_live_voice_recovery_audit("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "old_session_id TEXT NOT NULL,new_session_id TEXT NOT NULL,"
                "first_seq INTEGER NOT NULL,last_seq INTEGER NOT NULL,"
                "moved_count INTEGER NOT NULL,created_at TEXT NOT NULL "
                "DEFAULT CURRENT_TIMESTAMP)")
            audit_cols = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(approved_live_voice_recovery_audit)"))
            if audit_cols != ("id", "old_session_id", "new_session_id",
                              "first_seq", "last_seq", "moved_count", "created_at"):
                raise ValueError("기존 음성 수동 복구 기록 구조가 다릅니다.")
            columns = tuple(r[1] for r in db.execute(
                f"PRAGMA table_info({_TABLE})"))
            if columns != ("seq", "session_id", "turn_key",
                           "encrypted_reply", "reply_sha256", "state",
                           "created_at", "updated_at"):
                raise ValueError("기존 음성 영구 대기함 구조가 다릅니다.")

    @contextmanager
    def _connect(self):
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
    def _validate(session_id: str, turn_key: str | None = None) -> None:
        if type(session_id) is not str or not _SESSION.fullmatch(session_id):
            raise ValueError("승인된 실제 방송 세션 식별자가 잘못되었습니다.")
        if turn_key is not None and (
                type(turn_key) is not str or not _KEY.fullmatch(turn_key)):
            raise ValueError("실제 발화 원본 이벤트 키가 잘못되었습니다.")

    def enqueue(self, session_id: str, turn_key: str, reply: str) -> tuple[int, bool]:
        """DPAPI 암호문을 디스크에 영구 확정한 뒤에만 대기 접수로 반환."""
        self._validate(session_id, turn_key)
        if type(reply) is not str or not 1 <= len(reply.strip()) <= 6000:
            raise ValueError("실제 한국어 발화 원문 길이가 올바르지 않습니다.")
        ciphertext = self._dpapi.protect(reply)
        digest = hashlib.sha256(reply.encode("utf-8")).hexdigest()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute(
                f"SELECT COUNT(*) FROM {_TABLE} WHERE state='대기'").fetchone()[0]
            if count >= _MAX_PENDING:
                raise RuntimeError("영구 음성 대기함 20만 건 한도 · 원문 삭제하지 않음")
            inserted = db.execute(
                f"INSERT OR IGNORE INTO {_TABLE}"
                "(session_id,turn_key,encrypted_reply,reply_sha256,state)"
                " VALUES (?,?,?,?,'대기')",
                (session_id, turn_key, ciphertext, digest))
            row = db.execute(
                f"SELECT seq,reply_sha256 FROM {_TABLE} WHERE turn_key=?",
                (turn_key,)).fetchone()
            if row is None or row[1] != digest:
                raise RuntimeError("같은 서버 이벤트에 서로 다른 AI 발화가 연결되었습니다.")
            return int(row[0]), inserted.rowcount == 1

    def claim_next(self, session_id: str) -> tuple[int, str, str] | None:
        """같은 세션 대기 1건을 실제 합성 전 원자적으로 '시도'로 고정."""
        self._validate(session_id)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                f"SELECT seq,turn_key,encrypted_reply,reply_sha256 "
                f"FROM {_TABLE} WHERE session_id=? AND state='대기' "
                "ORDER BY seq LIMIT 1", (session_id,)).fetchone()
            if row is None:
                return None
            seq, key, cipher, digest = row
            reply = self._dpapi.unprotect(bytes(cipher))
            if hashlib.sha256(reply.encode("utf-8")).hexdigest() != digest:
                raise RuntimeError("실제 음성 원문 무결성이 일치하지 않습니다.")
            updated = db.execute(
                f"UPDATE {_TABLE} SET state='시도',"
                "updated_at=CURRENT_TIMESTAMP WHERE seq=? AND state='대기'",
                (seq,))
            if updated.rowcount != 1:
                raise RuntimeError("영구 음성 FIFO 소유권이 변경되었습니다.")
            return int(seq), str(key), reply

    def finish(self, seq: int, state: str) -> None:
        """최종 상태와 동시에 암호문을 비워 불필요한 원문 보유를 줄임."""
        if type(seq) is not int or seq < 1 or state not in _FINAL:
            raise ValueError("음성 발화 완료 기록이 올바르지 않습니다.")
        with self._connect() as db:
            updated = db.execute(
                f"UPDATE {_TABLE} SET state=?,encrypted_reply=X'',"
                "updated_at=CURRENT_TIMESTAMP WHERE seq=? AND state='시도'",
                (state, seq))
            if updated.rowcount != 1:
                raise RuntimeError("영구 음성 발화 시도 상태가 일치하지 않습니다.")

    def pending(self, session_id: str) -> int:
        self._validate(session_id)
        with self._connect() as db:
            return int(db.execute(
                f"SELECT COUNT(*) FROM {_TABLE} "
                "WHERE session_id=? AND state='대기'",
                (session_id,)).fetchone()[0])

    def unresolved_totals(self) -> tuple[int, int]:
        """현재 사용자 모든 방송 세션의 미발화/불명 시도 수만 반환."""
        with self._connect() as db:
            rows = db.execute(
                f"SELECT state,COUNT(*) FROM {_TABLE} "
                "WHERE state IN ('대기','시도') GROUP BY state").fetchall()
        values = dict(rows)
        return int(values.get("대기", 0)), int(values.get("시도", 0))

    def previous_unresolved(self, session_id: str) -> tuple[int, int]:
        """과거 방송 대기/불명 건수만 조회. 자동 재전송하지 않는다."""
        self._validate(session_id)
        with self._connect() as db:
            rows = db.execute(
                f"SELECT state,COUNT(*) FROM {_TABLE} WHERE session_id<>? "
                "AND state IN ('대기','시도') GROUP BY state",
                (session_id,)).fetchall()
        values = dict(rows)
        return int(values.get("대기", 0)), int(values.get("시도", 0))

    def previous_sessions(self, current_session_id: str, *,
                          limit: int = 30) -> tuple[tuple[str, int, int, str], ...]:
        """운영자 선택을 위해 과거 세션 ID·대기/시도 건수만 조회한다.

        DPAPI 원문·채팅 본문·권한 정보는 조회/출력하지 않는다.
        이전 '시도'는 절대 수동 인계 대상이 아니다.
        """
        self._validate(current_session_id)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("이전 음성 방송 조회 한도 오류")
        with self._connect() as db:
            rows = db.execute(
                f"SELECT session_id,"
                "SUM(CASE WHEN state='대기' THEN 1 ELSE 0 END),"
                "SUM(CASE WHEN state='시도' THEN 1 ELSE 0 END),"
                f"MIN(created_at) FROM {_TABLE} "
                "WHERE session_id<>? AND state IN ('대기','시도') "
                "GROUP BY session_id ORDER BY MIN(seq) DESC LIMIT ?",
                (current_session_id, limit)).fetchall()
        return tuple((str(s), int(p), int(u), str(t))
                     for s, p, u, t in rows)

    def adopt_previous_pending(
            self, old_session_id: str, new_session_id: str, *,
            operator_approved: bool = False,
            same_broadcast_confirmed: bool = False) -> int:
        """운영자 두 확인 후 과거 *대기*만 현재 승인 세션에 원자적으로 인계.

        외부에서 동일 OBS 방송 확인 후 호출해야 한다. 이 DB만으로
        과거 OBS 출력과 현재 출력의 동일성을 증명할 수 없다.
        이미 합성/OBS 요청 가능성이 있는 '시도'는 절대 이동하지 않는다.
        기존 현재 세션 대기가 있으면 원래 전역 FIFO를 섞지 않도록 거절.
        """
        self._validate(old_session_id)
        self._validate(new_session_id)
        if old_session_id == new_session_id:
            raise ValueError("과거와 현재 방송 세션은 달라야 합니다.")
        if operator_approved is not True or same_broadcast_confirmed is not True:
            raise PermissionError("운영자 직접 승인과 동일 방송 확인이 모두 필요합니다.")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            occupied = db.execute(
                f"SELECT 1 FROM {_TABLE} WHERE session_id=? "
                "AND state IN ('대기','시도') LIMIT 1",
                (new_session_id,)).fetchone()
            if occupied is not None:
                raise RuntimeError("현재 방송 음성 대기/시도가 있어 이전 순서 인계 금지")
            first_last = db.execute(
                f"SELECT MIN(seq),MAX(seq),COUNT(*) FROM {_TABLE} "
                "WHERE session_id=? AND state='대기'",
                (old_session_id,)).fetchone()
            first, last, count = first_last
            if not count:
                return 0
            updated = db.execute(
                f"UPDATE {_TABLE} SET session_id=?,updated_at=CURRENT_TIMESTAMP "
                "WHERE session_id=? AND state='대기'",
                (new_session_id, old_session_id))
            if updated.rowcount != count:
                raise RuntimeError("과거 발화 인계 도중 대기열 소유권 변경")
            db.execute(
                "INSERT INTO approved_live_voice_recovery_audit("
                "old_session_id,new_session_id,first_seq,last_seq,moved_count)"
                " VALUES(?,?,?,?,?)",
                (old_session_id, new_session_id, int(first), int(last), int(count)))
            return int(count)
