"""OBS 임시 WAV의 실제 음소거·볼륨·장면 오디오 트랙 후보 영구 관측.

기존 채팅·음성·WAV/립싱크/미디어 관측 SQLite를 변경하지 않고
별도 응용 ID/테이블에만 UUID·WAV 해시·OBS 경로 상태를 기록한다.
선택한 스트림 인코더 트랙 및 최종 시청자 수신의 증거는 아니다.
"""
from __future__ import annotations

import hashlib
import math
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir
from .approved_live_voice_audio_route_watch import ApprovedLiveVoiceAudioRouteGuard

_APPLICATION_ID = 0x41565231  # AVR1
_TABLE = "approved_live_voice_audio_route_receipts"
_COLUMNS = (
    "turn_key", "part_id", "wav_sha256", "source_uuid", "scene",
    "origin", "identities", "enabled_tracks", "samples", "min_volume_mul",
    "muted", "recorded_at",
)


@dataclass(frozen=True)
class VoiceAudioRouteReceipt:
    part_id: str
    origin: str
    enabled_tracks: tuple[int, ...]
    samples: int
    min_volume_mul: float
    # OBS route evidence only, not an actual encoded/output-audio PASS.


class ApprovedLiveVoiceAudioRouteReceipts:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_live_voice_audio_route_receipts.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("OBS 오디오 경로 장부에 바로가기는 사용하지 않습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        if existed and not self.path.is_file():
            raise ValueError("OBS 오디오 경로 장부가 일반 파일이 아닙니다.")
        with self._connection() as db:
            appid = int(db.execute("PRAGMA application_id").fetchone()[0])
            tables = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")}
            if (appid not in (0, _APPLICATION_ID)
                    or (existed and not tables)
                    or (tables and (appid != _APPLICATION_ID
                                    or tables != {_TABLE}))):
                raise ValueError("다른 프로그램의 OBS 오디오 경로 장부는 변경 금지")
            db.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_live_voice_audio_route_receipts("
                "turn_key TEXT NOT NULL,part_id TEXT NOT NULL,"
                "wav_sha256 TEXT NOT NULL,source_uuid TEXT NOT NULL,"
                "scene TEXT NOT NULL,origin TEXT NOT NULL,"
                "identities TEXT NOT NULL,enabled_tracks TEXT NOT NULL,"
                "samples INTEGER NOT NULL,min_volume_mul REAL NOT NULL,"
                "muted INTEGER NOT NULL,recorded_at TEXT NOT NULL "
                "DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(turn_key,part_id))")
            cols = tuple(r[1] for r in db.execute(f"PRAGMA table_info({_TABLE})"))
            if cols != _COLUMNS:
                raise ValueError("기존 OBS 오디오 경로 관측 장부 구조가 다릅니다.")

    @contextmanager
    def _connection(self):
        with closing(sqlite3.connect(str(self.path), timeout=10)) as db:
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db

    def record(self, *, turn_key: str, part_id: str, wav_data: bytes,
               guard: ApprovedLiveVoiceAudioRouteGuard) -> VoiceAudioRouteReceipt:
        if (type(turn_key) is not str or len(turn_key) != 64
                or any(ch not in "0123456789abcdef" for ch in turn_key)):
            raise ValueError("OBS 오디오 경로 발화 식별자 오류")
        if (type(part_id) is not str or not 1 <= len(part_id) <= 24
                or any(ch not in "0123456789." for ch in part_id)):
            raise ValueError("OBS 오디오 경로 발화 구간 번호 오류")
        if type(wav_data) is not bytes or not wav_data:
            raise ValueError("OBS 오디오 경로 실제 WAV 바이트가 없습니다.")
        if not isinstance(guard, ApprovedLiveVoiceAudioRouteGuard):
            raise TypeError("OBS 실제 오디오 경로 관측 결과가 아닙니다.")
        sample = guard.baseline
        count = guard.samples
        volume = guard.minimum_volume
        if (count < 2 or not math.isfinite(volume) or volume <= 0.001
                or sample.muted or not sample.enabled_tracks):
            raise RuntimeError("OBS 오디오 경로 관측이 부족하거나 음소거 상태입니다.")
        receipt = VoiceAudioRouteReceipt(
            part_id, sample.origin, sample.enabled_tracks, count, volume)
        with self._connection() as db:
            db.execute(
                f"INSERT INTO {_TABLE} "
                "(turn_key,part_id,wav_sha256,source_uuid,scene,origin,"
                "identities,enabled_tracks,samples,min_volume_mul,muted)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (turn_key, part_id, hashlib.sha256(wav_data).hexdigest(),
                 sample.source_uuid, sample.scene, sample.origin,
                 "\n".join(sample.identities),
                 ",".join(str(track) for track in sample.enabled_tracks),
                 count, volume, int(sample.muted)))
        return receipt

    def recent(self, *, limit: int = 20) -> tuple[VoiceAudioRouteReceipt, ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("OBS 오디오 경로 장부 조회 범위는 1~100입니다.")
        if not self.path.is_file():
            return ()
        with self._connection() as db:
            rows = db.execute(
                f"SELECT part_id,origin,enabled_tracks,samples,min_volume_mul "
                f"FROM {_TABLE} ORDER BY recorded_at DESC,rowid DESC LIMIT ?",
                (limit,)).fetchall()
        return tuple(VoiceAudioRouteReceipt(
            str(part), str(origin),
            tuple(int(x) for x in str(tracks).split(",") if x),
            int(count), float(volume))
            for part, origin, tracks, count, volume in rows)
