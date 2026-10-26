"""승인된 동일 한국어 WAV의 OBS 요청·공식 Cubism 입 관측을 구간별 기록.

실제 WAV 내용/시청자/음성 모델/토큰은 보관하지 않는다.
공식 Live2D WebView의 원래 모델 매개변수 관측만 기록하며
음성·영상이 플랫폼 시청자에게 동기화되어 도달했다는 보증은 하지 않는다.
기존 원본 채팅/기억/음성 사건 SQLite와 분리해 추가만 수행한다.
"""
from __future__ import annotations

import hashlib
import math
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir

_APP_ID = 0x41565332
_TABLE = "approved_live_wav_sync_receipts"


@dataclass(frozen=True)
class VoiceSyncReceipt:
    part_id: str
    state: str
    obs_request_gap_seconds: float | None
    first_lip_relative_ms: float | None
    actual_lip_calls: int
    actual_lip_changes: int


class ApprovedLiveVoiceSyncReceipts:
    """원본 영구 발화 장부에 손대지 않는 추가 읽기·기록 장부."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_live_wav_sync_receipts.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("음성/입 실관측 장부 바로가기를 사용할 수 없습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        if existed and not self.path.is_file():
            raise ValueError("음성/입 실관측 장부는 일반 파일이어야 합니다.")
        with self._connection() as db:
            appid = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")}
            if ((existed and not tables) or
                    (tables and (appid != _APP_ID or tables != {_TABLE})) or
                    appid not in (0, _APP_ID)):
                raise ValueError("기존 다른 SQLite는 변경하지 않습니다.")
            db.execute(f"PRAGMA application_id={_APP_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_live_wav_sync_receipts("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "turn_key TEXT NOT NULL,"
                "part_id TEXT NOT NULL,"
                "wav_sha256 TEXT NOT NULL,"
                "obs_source_uuid TEXT NOT NULL,"
                "obs_request_gap_seconds REAL,"
                "first_lip_relative_ms REAL,"
                "actual_lip_calls INTEGER NOT NULL,"
                "actual_lip_positive_calls INTEGER NOT NULL,"
                "actual_lip_samples INTEGER NOT NULL,"
                "actual_lip_changes INTEGER NOT NULL,"
                "actual_mouth_range REAL,"
                "state TEXT NOT NULL,"
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "UNIQUE(turn_key,part_id))")
            columns = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(approved_live_wav_sync_receipts)"))
            if columns != (
                "id", "turn_key", "part_id", "wav_sha256", "obs_source_uuid",
                "obs_request_gap_seconds", "first_lip_relative_ms",
                "actual_lip_calls", "actual_lip_positive_calls",
                "actual_lip_samples", "actual_lip_changes",
                "actual_mouth_range", "state", "created_at"):
                raise ValueError("기존 실관측 장부의 원본 구조가 다릅니다.")

    @contextmanager
    def _connection(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db

    def record(
        self, *, turn_key: str, part_id: str, wav_data: bytes,
        obs_source_uuid: str, obs_request_gap_seconds: float | None,
        observation: dict, obs_triggered: bool,
    ) -> VoiceSyncReceipt:
        if (type(turn_key) is not str or len(turn_key) != 64
                or any(c not in "0123456789abcdef" for c in turn_key)
                or type(part_id) is not str or not 1 <= len(part_id) <= 64
                or any(ch not in "0123456789." for ch in part_id)
                or type(wav_data) is not bytes or not wav_data
                or type(obs_source_uuid) is not str or not obs_source_uuid
                or len(obs_source_uuid) > 128
                or type(obs_triggered) is not bool
                or type(observation) is not dict):
            raise ValueError("같은 WAV·공식 입 관측 식별값이 올바르지 않습니다.")
        if obs_request_gap_seconds is not None and (
                type(obs_request_gap_seconds) not in (float, int)
                or not math.isfinite(obs_request_gap_seconds)
                or obs_request_gap_seconds < 0
                or obs_request_gap_seconds > 30):
            raise ValueError("OBS 요청 간격 값은 실제 단조 시각이어야 합니다.")
        numbers = {}
        for key in ("calls", "positiveCalls", "samples", "changes"):
            value = observation.get(key)
            if type(value) is not int or not 0 <= value <= 100_000:
                raise ValueError("공식 Cubism 실제 입 관측 계수가 유효하지 않습니다.")
            numbers[key] = value
        first = observation.get("mouthFirstMs")
        mouth_range = observation.get("mouthRange")
        for value in (first, mouth_range):
            if value is not None and (
                    type(value) not in (int, float)
                    or not math.isfinite(value) or value < 0
                    or value > 30_000):
                raise ValueError("실제 Cubism 입 변화 시각·폭이 유효하지 않습니다.")
        # 단조 시각으로 잰 Python OBS 요청과 JS 입변화 첫 시점의
        # 대략적인 상대값이다. 서로 다른 시계의 절대 시각 결합이 아님.
        relative = (
            float(first) - float(obs_request_gap_seconds) * 1000
            if first is not None and obs_request_gap_seconds is not None
            else None)
        state = (
            "OBS재생요청미확인" if not obs_triggered else
            "공식Cubism입변화관측"
            if numbers["positiveCalls"] > 0 and numbers["changes"] > 0
            and numbers["samples"] > 0 and mouth_range is not None
            and mouth_range > 0.01
            else "공식Cubism입변화미확인")
        sha = hashlib.sha256(wav_data).hexdigest()
        with self._connection() as db:
            result = db.execute(
                "INSERT OR IGNORE INTO approved_live_wav_sync_receipts("
                "turn_key,part_id,wav_sha256,obs_source_uuid,"
                "obs_request_gap_seconds,first_lip_relative_ms,"
                "actual_lip_calls,actual_lip_positive_calls,actual_lip_samples,"
                "actual_lip_changes,actual_mouth_range,state)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (turn_key, part_id, sha, obs_source_uuid,
                 obs_request_gap_seconds, relative, numbers["calls"],
                 numbers["positiveCalls"], numbers["samples"],
                 numbers["changes"], mouth_range, state))
            if result.rowcount != 1:
                raise RuntimeError(
                    "이미 같은 발화 WAV 구간의 입 관측이 기록되어 중복 저장하지 않습니다.")
        return VoiceSyncReceipt(
            part_id, state, obs_request_gap_seconds, relative,
            numbers["calls"], numbers["changes"])

    def recent(self, *, limit: int = 20) -> tuple[VoiceSyncReceipt, ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("동일 WAV·입 관측 조회 개수가 유효하지 않습니다.")
        with self._connection() as db:
            rows = db.execute(
                "SELECT part_id,state,obs_request_gap_seconds,"
                "first_lip_relative_ms,actual_lip_calls,actual_lip_changes "
                "FROM approved_live_wav_sync_receipts "
                "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return tuple(VoiceSyncReceipt(*row) for row in rows)
