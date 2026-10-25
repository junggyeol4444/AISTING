"""실제 한 WAV가 공식 Cubism 입과 OBS 오디오 입력으로 전달된 순서 기록.

실제 방송 실행 중에만 호출하는 제품 기능. 동일 WAV SHA-256, 장면,
OBS 임시 소스 UUID, 입 시작/OBS 재생 요청의 단조 시각을 남긴다.
미디어가 시청자에게 전달되거나 실제 입/음성 동기화에 성공했다는
검증 증거로 사용하지 않는다. WAV·시청자 원문·암호·토큰은 저장 안 함.
"""
from __future__ import annotations

import hashlib
import math
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .offline_settings import data_dir

_APP_ID = 0x41564331  # AVC1
_TABLE = "approved_live_voice_segments"


class ApprovedVoiceCausalJournal:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_live_voice_segments.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("실제 음성 인과 기록 경로에 바로가기를 사용할 수 없습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        if existed and not self.path.is_file():
            raise ValueError("실제 음성 인과 기록이 일반 파일이 아닙니다.")
        with self._connect() as db:
            appid = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")}
            if (appid not in (0, _APP_ID)
                    or existed and not tables
                    or tables and (tables != {_TABLE} or appid != _APP_ID)):
                raise ValueError("다른 프로그램의 SQLite를 변경하지 않습니다.")
            db.execute(f"PRAGMA application_id={_APP_ID}")
            db.execute(
                f"CREATE TABLE IF NOT EXISTS {_TABLE}("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "turn_key TEXT NOT NULL,"
                "part_id TEXT NOT NULL,"
                "wav_sha256 TEXT NOT NULL,"
                "wav_seconds REAL NOT NULL,"
                "obs_scene TEXT NOT NULL,"
                "obs_source_uuid TEXT NOT NULL,"
                "mouth_started_at REAL NOT NULL,"
                "obs_triggered_at REAL,"
                "state TEXT NOT NULL DEFAULT '입시작',"
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            columns = tuple(r[1] for r in db.execute(f"PRAGMA table_info({_TABLE})"))
            if columns != (
                "id", "turn_key", "part_id", "wav_sha256", "wav_seconds",
                "obs_scene", "obs_source_uuid", "mouth_started_at",
                "obs_triggered_at", "state", "created_at", "updated_at"):
                raise ValueError("기존 실제 발화 인과 장부 구조가 다릅니다.")

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

    def mouth_started(
        self, *, turn_key: str, part_id: str, wav_data: bytes,
        wav_seconds: float, obs_scene: str, obs_source_uuid: str,
    ) -> int:
        if (type(turn_key) is not str or len(turn_key) != 64
                or any(c not in "0123456789abcdef" for c in turn_key)
                or type(part_id) is not str or not 1 <= len(part_id) <= 64
                or not all(c.isdigit() or c == "." for c in part_id)
                or type(wav_data) is not bytes or not wav_data
                or type(wav_seconds) not in (int, float)
                or not math.isfinite(wav_seconds) or wav_seconds <= 0
                or type(obs_scene) is not str or not obs_scene
                or len(obs_scene) > 256
                or type(obs_source_uuid) is not str or not obs_source_uuid
                or len(obs_source_uuid) > 128):
            raise ValueError("동일 WAV 방송 인과 기록의 원본 값이 올바르지 않습니다.")
        with self._connect() as db:
            cursor = db.execute(
                f"INSERT INTO {_TABLE}("
                "turn_key,part_id,wav_sha256,wav_seconds,obs_scene,"
                "obs_source_uuid,mouth_started_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (turn_key, part_id, hashlib.sha256(wav_data).hexdigest(),
                 float(wav_seconds), obs_scene, obs_source_uuid,
                 time.monotonic()))
            return int(cursor.lastrowid)

    def obs_triggered(self, row_id: int) -> None:
        if type(row_id) is not int or row_id < 1:
            raise ValueError("실제 WAV 재생 요청 기록 ID 오류")
        with self._connect() as db:
            updated = db.execute(
                f"UPDATE {_TABLE} SET state='OBS재생요청',"
                "obs_triggered_at=?,updated_at=CURRENT_TIMESTAMP "
                "WHERE id=? AND state='입시작'",
                (time.monotonic(), row_id))
            if updated.rowcount != 1:
                raise RuntimeError("동일 WAV 입·OBS 요청 순서가 일치하지 않습니다.")

    def finish(self, row_id: int, *, completed: bool) -> None:
        if type(row_id) is not int or row_id < 1:
            raise ValueError("실제 WAV 재생 종료 기록 ID 오류")
        with self._connect() as db:
            updated = db.execute(
                f"UPDATE {_TABLE} SET state=?,updated_at=CURRENT_TIMESTAMP "
                "WHERE id=? AND state IN ('입시작','OBS재생요청')",
                ("재생시간경과" if completed else "전달불명", row_id))
            if updated.rowcount != 1:
                raise RuntimeError("동일 WAV 입·OBS 요청 종료 상태가 일치하지 않습니다.")

    def recent(self, *, limit: int = 30) -> tuple[tuple, ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("동일 WAV 발화 인과 기록 조회 범위 오류")
        with self._connect() as db:
            rows = db.execute(
                f"SELECT substr(turn_key,1,12),part_id,"
                "substr(wav_sha256,1,12),wav_seconds,state,"
                "CASE WHEN obs_triggered_at IS NULL THEN NULL "
                "ELSE obs_triggered_at-mouth_started_at END "
                f"FROM {_TABLE} ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        return tuple(rows)
