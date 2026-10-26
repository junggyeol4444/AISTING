"""승인된 동일 WAV의 OBS 실제 미디어 입력 상태·커서 진행 SQLite 영구 기록.

기존 음성/입/OBS 인과·사용자 채팅 SQLite를 변경하지 않는다.
OBS GetMediaInputStatus 관측 결과만 저장하며 실제 방송 인코딩/시청자
수신의 증거가 아니다. 재생 요청만으로 성공 표시하지 않는다.
"""
from __future__ import annotations

import hashlib
import math
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir

_APPLICATION_ID = 0x41564D31  # AVM1
_TABLE = "approved_live_voice_media_receipts"
_COLUMNS = (
    "turn_key", "part_id", "wav_sha256", "source_uuid", "observed_state",
    "samples", "playing_samples", "cursor_advances",
    "first_playing_offset_seconds", "last_cursor_ms", "ended_seen",
    "recorded_at",
)


@dataclass(frozen=True)
class VoiceMediaReceipt:
    part_id: str
    observed_state: str
    samples: int
    playing_samples: int
    cursor_advances: int
    first_playing_offset_seconds: float | None
    last_cursor_ms: int | None
    ended_seen: bool


class ApprovedLiveVoiceMediaReceipts:
    """한 발화 구간의 WAV 해시와 OBS 미디어 재생 진행 관측을 1회 보존."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_live_voice_media_receipts.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("OBS 미디어 관측 장부 바로가기는 사용하지 않습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        if existed and not self.path.is_file():
            raise ValueError("OBS 미디어 관측 장부가 일반 파일이 아닙니다.")
        with self._connection() as db:
            appid = int(db.execute("PRAGMA application_id").fetchone()[0])
            tables = {
                row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'")}
            if (appid not in (0, _APPLICATION_ID) or (existed and not tables)
                    or (tables and (appid != _APPLICATION_ID
                                    or tables != {_TABLE}))):
                raise ValueError("다른 프로그램의 SQLite 장부는 건드리지 않습니다.")
            db.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_live_voice_media_receipts("
                "turn_key TEXT NOT NULL, part_id TEXT NOT NULL,"
                "wav_sha256 TEXT NOT NULL, source_uuid TEXT NOT NULL,"
                "observed_state TEXT NOT NULL,"
                "samples INTEGER NOT NULL, playing_samples INTEGER NOT NULL,"
                "cursor_advances INTEGER NOT NULL,"
                "first_playing_offset_seconds REAL,"
                "last_cursor_ms INTEGER, ended_seen INTEGER NOT NULL,"
                "recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "PRIMARY KEY(turn_key,part_id))")
            found = tuple(
                row[1] for row in db.execute(
                    "PRAGMA table_info(approved_live_voice_media_receipts)"))
            if found != _COLUMNS:
                raise ValueError("기존 OBS 미디어 관측 테이블 구조가 다릅니다.")

    @contextmanager
    def _connection(self):
        with closing(sqlite3.connect(str(self.path), timeout=10)) as db:
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db

    def record(self, *, turn_key: str, part_id: str,
               wav_data: bytes, source_uuid: str,
               observation) -> VoiceMediaReceipt:
        if (type(turn_key) is not str or len(turn_key) != 64
                or any(ch not in "0123456789abcdef" for ch in turn_key)):
            raise ValueError("미디어 관측 발화 ID가 올바르지 않습니다.")
        if (type(part_id) is not str or not 1 <= len(part_id) <= 24
                or any(ch not in "0123456789." for ch in part_id)):
            raise ValueError("미디어 관측 구간 번호가 올바르지 않습니다.")
        if type(wav_data) is not bytes or not wav_data:
            raise ValueError("실제 동일 WAV 데이터가 필요합니다.")
        if type(source_uuid) is not str or not 1 <= len(source_uuid) <= 128:
            raise ValueError("OBS 실제 임시 소스 UUID가 올바르지 않습니다.")
        from .approved_live_voice_playback_watch import LivePlaybackObservation
        if not isinstance(observation, LivePlaybackObservation):
            raise TypeError("실제 OBS 미디어 관측 결과가 아닙니다.")
        offset = observation.media_first_playing_offset_seconds
        if offset is not None and (
                type(offset) not in (float, int) or
                not math.isfinite(offset) or offset < 0):
            raise ValueError("재생 시작 관측 시각이 올바르지 않습니다.")
        result = VoiceMediaReceipt(
            part_id=part_id,
            observed_state=observation.media_state,
            samples=observation.media_samples,
            playing_samples=observation.media_playing_samples,
            cursor_advances=observation.media_cursor_advances,
            first_playing_offset_seconds=offset,
            last_cursor_ms=observation.media_last_cursor_ms,
            ended_seen=observation.media_ended_seen)
        with self._connection() as db:
            db.execute(
                "INSERT INTO approved_live_voice_media_receipts "
                "(turn_key,part_id,wav_sha256,source_uuid,observed_state,"
                "samples,playing_samples,cursor_advances,"
                "first_playing_offset_seconds,last_cursor_ms,ended_seen)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (turn_key, part_id, hashlib.sha256(wav_data).hexdigest(),
                 source_uuid, result.observed_state, result.samples,
                 result.playing_samples, result.cursor_advances,
                 result.first_playing_offset_seconds, result.last_cursor_ms,
                 int(result.ended_seen)))
        return result

    def recent(self, *, limit: int = 20) -> tuple[VoiceMediaReceipt, ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("OBS 미디어 관측 조회 수는 1~100이어야 합니다.")
        if not self.path.is_file():
            return ()
        with self._connection() as db:
            rows = db.execute(
                "SELECT part_id,observed_state,samples,playing_samples,"
                "cursor_advances,first_playing_offset_seconds,"
                "last_cursor_ms,ended_seen "
                "FROM approved_live_voice_media_receipts "
                "ORDER BY recorded_at DESC,rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        return tuple(
            VoiceMediaReceipt(str(part), str(state), int(samples),
                              int(playing), int(advances),
                              float(offset) if offset is not None else None,
                              int(cursor) if cursor is not None else None,
                              bool(ended))
            for part, state, samples, playing, advances,
                offset, cursor, ended in rows)
