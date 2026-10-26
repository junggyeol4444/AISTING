"""운영자 승인으로 시작한 4플랫폼 채팅 수신·재연결 사건의 SQLite 영구 장부.

원본 공개 채팅 대기열/대화 기억/사용자 설정은 읽거나 변경하지 않는다.
본문·닉네임·OAuth/API 키·소켓 URL·서버 메시지 ID는 기록하지 않는다.
채팅 수신 성공과 네트워크 무누락을 이 사건 기록으로 증명하지 않는다.
"""
from __future__ import annotations

import math
import sqlite3
import threading
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import uuid4

from .offline_settings import data_dir

_APPLICATION_ID = 0x4152434A  # ARCJ
_TABLE = "platform_reconnect_events"
_COLUMNS = (
    "id", "session_id", "platform", "channel", "state",
    "attempt", "gap_seconds", "recorded_at",
)
_PLATFORMS = frozenset(("twitch", "chzzk", "soop", "youtube"))
_STATES = frozenset((
    "수신시작", "연결확인", "연결중단", "재연결시도",
    "재연결완료", "세션중지", "읽기종료",
))


class DurablePlatformReconnectJournal:
    """동일 방송 채널의 실제 수신 상태 전환만 추가하는 별도 로컬 DB."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else (
            data_dir() / "platform_reconnect_events.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("재연결 기록 경로에 심볼릭 링크를 사용할 수 없습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        if existed and not self.path.is_file():
            raise ValueError("재연결 기록 경로가 일반 파일이 아닙니다.")
        self._lock = threading.RLock()
        with self._connect() as db:
            app_id = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")}
            if ((existed and not tables)
                    or (tables and (app_id != _APPLICATION_ID
                                    or tables != {_TABLE}))
                    or app_id not in (0, _APPLICATION_ID)):
                raise ValueError("다른 프로그램의 SQLite를 재연결 장부로 사용하지 않습니다.")
            db.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS platform_reconnect_events("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "session_id TEXT NOT NULL,"
                "platform TEXT NOT NULL,"
                "channel TEXT NOT NULL,"
                "state TEXT NOT NULL,"
                "attempt INTEGER NOT NULL CHECK(attempt >= 0),"
                "gap_seconds REAL,"
                "recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            actual = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(platform_reconnect_events)"))
            if actual != _COLUMNS:
                raise ValueError("기존 재연결 사건 장부 구조가 일치하지 않습니다.")
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_aisting_reconnect_channel "
                "ON platform_reconnect_events(platform,channel,id)")
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_aisting_reconnect_utc "
                "ON platform_reconnect_events(platform,channel,recorded_at)")

    @contextmanager
    def _connect(self):
        with closing(sqlite3.connect(self.path, timeout=5.0)) as db:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db

    @staticmethod
    def new_session_id() -> str:
        """계정·방송 키와 무관한 매 실행 임시 식별자."""
        return uuid4().hex

    @staticmethod
    def _scope(platform: str, channel: str) -> tuple[str, str]:
        if (platform not in _PLATFORMS or type(channel) is not str
                or not channel.strip() or len(channel) > 256
                or any(ord(ch) < 32 for ch in channel)):
            raise ValueError("재연결 사건의 플랫폼·채널 범위가 올바르지 않습니다.")
        return platform, channel

    def record(
        self, session_id: str, platform: str, channel: str,
        state: str, *, attempt: int = 0,
        gap_seconds: float | None = None,
    ) -> int:
        """실제 관측된 사건만 한 트랜잭션으로 영구 확정한다."""
        platform, channel = self._scope(platform, channel)
        if (type(session_id) is not str or len(session_id) != 32
                or any(ch not in "0123456789abcdef" for ch in session_id)):
            raise ValueError("재연결 세션 식별자가 올바르지 않습니다.")
        if state not in _STATES:
            raise ValueError("재연결 사건 종류가 올바르지 않습니다.")
        if type(attempt) is not int or attempt < 0:
            raise ValueError("재연결 시도 횟수가 올바르지 않습니다.")
        if (gap_seconds is not None
                and (type(gap_seconds) not in (int, float)
                     or not math.isfinite(gap_seconds)
                     or gap_seconds < 0)):
            raise ValueError("실제 관측한 재연결 공백이 올바르지 않습니다.")
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "INSERT INTO platform_reconnect_events "
                "(session_id,platform,channel,state,attempt,gap_seconds) "
                "VALUES(?,?,?,?,?,?)",
                (session_id, platform, channel, state, attempt, gap_seconds))
            return int(cursor.lastrowid)

    def recent_for(
        self, channels: dict[str, str], *, limit: int = 20,
    ) -> tuple[tuple[str, str, str, int, float | None, str], ...]:
        """운영자가 선택한 채널의 최근 사건만 조회. 본문·계정정보 없음."""
        if (type(channels) is not dict or not channels
                or any(self._scope(code, channel) != (code, channel)
                       for code, channel in channels.items())
                or type(limit) is not int or not 1 <= limit <= 100):
            raise ValueError("재연결 사건 조회 범위가 올바르지 않습니다.")
        where = " OR ".join("(platform=? AND channel=?)" for _ in channels)
        params = [value for code, channel in channels.items()
                  for value in (code, channel)]
        with self._lock, self._connect() as db:
            rows = db.execute(
                "SELECT platform,channel,state,attempt,gap_seconds,recorded_at "
                f"FROM platform_reconnect_events WHERE {where} "
                "ORDER BY id DESC LIMIT ?", [*params, limit]).fetchall()
        return tuple((str(p), str(c), str(s), int(a),
                      None if gap is None else float(gap), str(at))
                     for p, c, s, a, gap, at in rows)

    def previous_session_health_for(
        self, channels: dict[str, str],
    ) -> dict[str, dict[str, object]]:
        """선택한 채널의 직전 실제 수신 세션만 SQLite에서 복원한다.

        재시작 시 예전 소켓이 살아 있다고 간주하거나 자동 송출/재연결을
        수행하지 않는다. 마지막 상태와 서버가 실제 확인한 재연결 공백만
        반환하며, 예기치 않은 종료·누락된 채팅 건수는 추정하지 않는다.
        채팅 본문·닉네임·토큰·서버 메시지 ID는 조회하지 않는다.
        """
        if (type(channels) is not dict or not channels or len(channels) > 4
                or any(self._scope(code, channel) != (code, channel)
                       for code, channel in channels.items())):
            raise ValueError("이전 수신 세션 조회 범위가 올바르지 않습니다.")
        result: dict[str, dict[str, object]] = {}
        with self._lock, self._connect() as db:
            for code, channel in channels.items():
                latest = db.execute(
                    "SELECT session_id,state,recorded_at "
                    "FROM platform_reconnect_events "
                    "WHERE platform=? AND channel=? "
                    "ORDER BY id DESC LIMIT 1", (code, channel)).fetchone()
                if latest is None:
                    continue
                session_id, state, at = latest
                counts = db.execute(
                    "SELECT "
                    "COALESCE(SUM(CASE WHEN state='재연결시도' "
                    "THEN 1 ELSE 0 END),0),"
                    "COALESCE(SUM(CASE WHEN state='재연결완료' "
                    "THEN 1 ELSE 0 END),0),"
                    "COALESCE(SUM(CASE WHEN state='재연결완료' "
                    "THEN gap_seconds ELSE 0 END),0.0),"
                    "MAX(CASE WHEN state='재연결완료' "
                    "THEN gap_seconds ELSE NULL END) "
                    "FROM platform_reconnect_events "
                    "WHERE platform=? AND channel=? AND session_id=?",
                    (code, channel, session_id)).fetchone()
                # 세션중지는 실제 Stop 요청 관측일 뿐 모든 채팅 수신이나
                # 시청자 출력 성공의 증거가 아니다. 읽기종료는 정상 방송
                # 종료와 예기치 않은 종료가 모두 가능하므로 구분하지 않는다.
                result[code] = {
                    "마지막상태": str(state),
                    "마지막기록UTC": str(at),
                    "명시적중지기록": state == "세션중지",
                    "종료사유불명": state != "세션중지",
                    "재연결시도기록": int(counts[0]),
                    "재연결완료기록": int(counts[1]),
                    "완료공백합계초": round(float(counts[2]), 3),
                    "완료공백최장초": (
                        None if counts[3] is None else round(float(counts[3]), 3)),
                }
        return result

    def last_24h_reconnect_health_for(
        self, channels: dict[str, str],
    ) -> dict[str, dict[str, object]]:
        """현재 UTC 기준 24시간에 실제 기록된 수신/재연결 사건만 집계.

        프로세스 재시작으로 세션이 여러 개여도 선택한 동일 채널에
        한정하여 SQLite 기록을 보존한 채 조회한다. 사건이 없다는 것은
        정상 연결 또는 서버 채팅 무누락을 뜻하지 않는다. 관측된 공백
        합계는 재연결이 *완료*된 구간만 포함한다.
        """
        if (type(channels) is not dict or not channels or len(channels) > 4
                or any(self._scope(code, channel) != (code, channel)
                       for code, channel in channels.items())):
            raise ValueError("24시간 수신 상태 조회 범위가 올바르지 않습니다.")
        result: dict[str, dict[str, object]] = {}
        with self._lock, self._connect() as db:
            for code, channel in channels.items():
                row = db.execute(
                    "SELECT COUNT(*),COUNT(DISTINCT session_id),"
                    "COALESCE(SUM(CASE WHEN state='연결확인' OR "
                    "state='재연결완료' THEN 1 ELSE 0 END),0),"
                    "COALESCE(SUM(CASE WHEN state='재연결시도' "
                    "THEN 1 ELSE 0 END),0),"
                    "COALESCE(SUM(CASE WHEN state='재연결완료' "
                    "THEN 1 ELSE 0 END),0),"
                    "COALESCE(SUM(CASE WHEN state='재연결완료' "
                    "THEN gap_seconds ELSE 0 END),0.0),"
                    "MAX(CASE WHEN state='재연결완료' "
                    "THEN gap_seconds ELSE NULL END),"
                    "MIN(recorded_at),MAX(recorded_at) "
                    "FROM platform_reconnect_events "
                    "WHERE platform=? AND channel=? "
                    "AND recorded_at>=datetime('now','-24 hours')",
                    (code, channel)).fetchone()
                result[code] = {
                    "기록사건": int(row[0]),
                    "기록세션": int(row[1]),
                    "입장확인사건": int(row[2]),
                    "재연결시도": int(row[3]),
                    "재연결완료": int(row[4]),
                    "완료공백합계초": round(float(row[5]), 3),
                    "완료공백최장초": (
                        None if row[6] is None else round(float(row[6]), 3)),
                    "최초기록UTC": None if row[7] is None else str(row[7]),
                    "최종기록UTC": None if row[8] is None else str(row[8]),
                }
        return result
