"""승인된 동일 WAV와 OBS 현재 송출 프로필의 오디오 트랙 후보 영구 기록.

OBS 설정 읽기 근거이며 인코더 패킷/플랫폼·시청자 수신 성공 증거가 아니다.
기존 캐릭터·채팅·개인 기억·음성 SQLite는 변경하지 않는다.
"""
from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir
from .approved_live_voice_audio_route_watch import ApprovedLiveVoiceAudioRouteGuard

_APPLICATION_ID = 0x41535431  # AST1
_TABLE = "approved_live_voice_stream_track_receipts"
_COLUMNS = (
    "turn_key", "part_id", "wav_sha256", "source_uuid", "scene",
    "profile_name", "profile_mode", "selected_track", "track_origin",
    "enabled_tracks", "samples", "recorded_at",
)


@dataclass(frozen=True)
class VoiceStreamTrackReceipt:
    part_id: str
    profile_mode: str
    selected_track: int
    enabled_tracks: tuple[int, ...]
    samples: int


class ApprovedLiveVoiceStreamTrackReceipts:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_live_voice_stream_track_receipts.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("OBS 스트림 트랙 장부에 바로가기는 금지됩니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        if existed and not self.path.is_file():
            raise ValueError("OBS 스트림 트랙 장부가 일반 파일이 아닙니다.")
        with self._connection() as db:
            appid = int(db.execute("PRAGMA application_id").fetchone()[0])
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")}
            if (appid not in (0, _APPLICATION_ID)
                    or (existed and not tables)
                    or (tables and (appid != _APPLICATION_ID
                                    or tables != {_TABLE}))):
                raise ValueError("다른 OBS 스트림 트랙 장부는 변경할 수 없습니다.")
            db.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_live_voice_stream_track_receipts("
                "turn_key TEXT NOT NULL,part_id TEXT NOT NULL,"
                "wav_sha256 TEXT NOT NULL,source_uuid TEXT NOT NULL,"
                "scene TEXT NOT NULL,profile_name TEXT NOT NULL,"
                "profile_mode TEXT NOT NULL,selected_track INTEGER NOT NULL,"
                "track_origin TEXT NOT NULL,enabled_tracks TEXT NOT NULL,"
                "samples INTEGER NOT NULL,recorded_at TEXT NOT NULL "
                "DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(turn_key,part_id))")
            cols = tuple(row[1] for row in db.execute(
                f"PRAGMA table_info({_TABLE})"))
            if cols != _COLUMNS:
                raise ValueError("기존 OBS 스트림 트랙 장부 구조가 다릅니다.")

    @contextmanager
    def _connection(self):
        with closing(sqlite3.connect(str(self.path), timeout=10)) as db:
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db

    def record(self, *, turn_key: str, part_id: str, wav_data: bytes,
               guard: ApprovedLiveVoiceAudioRouteGuard) -> VoiceStreamTrackReceipt:
        if (type(turn_key) is not str or len(turn_key) != 64
                or any(ch not in "0123456789abcdef" for ch in turn_key)):
            raise ValueError("OBS 트랙 발화 식별자가 잘못되었습니다.")
        if (type(part_id) is not str or not 1 <= len(part_id) <= 24
                or any(ch not in "0123456789." for ch in part_id)):
            raise ValueError("OBS 트랙 구간 번호가 잘못되었습니다.")
        if type(wav_data) is not bytes or not wav_data:
            raise ValueError("OBS 트랙 WAV 원본이 없습니다.")
        if not isinstance(guard, ApprovedLiveVoiceAudioRouteGuard):
            raise TypeError("OBS 트랙 관측 출처가 잘못되었습니다.")
        baseline = guard.baseline
        count = guard.samples
        if (count < 2 or baseline.profile_mode not in ("Simple", "Advanced")
                or type(baseline.stream_track) is not int
                or baseline.stream_track not in baseline.enabled_tracks
                or not baseline.profile_name or not baseline.stream_track_origin):
            raise RuntimeError("OBS 송출 프로필 트랙 관측이 부족합니다.")
        receipt = VoiceStreamTrackReceipt(
            part_id, baseline.profile_mode, baseline.stream_track,
            baseline.enabled_tracks, count)
        with self._connection() as db:
            db.execute(
                f"INSERT INTO {_TABLE} "
                "(turn_key,part_id,wav_sha256,source_uuid,scene,"
                "profile_name,profile_mode,selected_track,track_origin,"
                "enabled_tracks,samples) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (turn_key, part_id, hashlib.sha256(wav_data).hexdigest(),
                 baseline.source_uuid, baseline.scene, baseline.profile_name,
                 baseline.profile_mode, baseline.stream_track,
                 baseline.stream_track_origin,
                 ",".join(str(t) for t in baseline.enabled_tracks), count))
        return receipt

    def recent(self, *, limit: int = 20) -> tuple[VoiceStreamTrackReceipt, ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("OBS 송출 트랙 조회 범위는 1~100입니다.")
        with self._connection() as db:
            rows = db.execute(
                f"SELECT part_id,profile_mode,selected_track,enabled_tracks,samples "
                f"FROM {_TABLE} ORDER BY recorded_at DESC,rowid DESC LIMIT ?",
                (limit,)).fetchall()
        return tuple(VoiceStreamTrackReceipt(
            str(part), str(mode), int(track),
            tuple(int(x) for x in str(tracks).split(",") if x), int(samples))
            for part, mode, track, tracks, samples in rows)
