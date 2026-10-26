"""운영자가 승인한 실제 방송의 주제 순환·무채팅 콘텐츠 진행.

기존 공식 AI/Live2D 한 작업자에게만 사용자 지정 주제 프롬프트를 전달한다.
시청자 채팅이 있거나 기존 SQLite에 미처리 건이 있으면 절대 선행하지 않는다.
발화 시도 전에 독립 SQLite 장부에 영구 기록하여 앱 재시작/중복 창에서
같은 방송·순번을 자동 재전송하지 않는다. 채팅 발신·OBS 송출 제어는 없다.
"""
from __future__ import annotations

import math
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .offline_settings import data_dir

_APPLICATION_ID = 0x41534331  # ASC1, 이 기능의 독립 SQLite 소유권
_TABLE = "approved_live_content_turns"
_MAX_TOPICS = 30
_MAX_TOPIC_LENGTH = 120


def parse_approved_topics(raw: str) -> tuple[str, ...]:
    """운영자가 직접 입력한 방송 주제만 수용. 모델이 임의로 주제를 추가하지 않음."""
    if type(raw) is not str or len(raw) > 5000:
        raise ValueError("방송 주제 원문은 5000자 이하여야 합니다.")
    topics = tuple(line.strip() for line in raw.splitlines() if line.strip())
    if not 1 <= len(topics) <= _MAX_TOPICS:
        raise ValueError("방송 주제는 줄마다 하나씩 1~30개 입력하세요.")
    if any(len(topic) > _MAX_TOPIC_LENGTH or any(
            ord(c) < 32 for c in topic) for topic in topics):
        raise ValueError("각 방송 주제는 제어 문자 없이 120자 이하여야 합니다.")
    return topics


@dataclass(frozen=True)
class ContentTurn:
    occurrence: str
    sequence: int
    topic: str
    prompt: str


class ApprovedLiveContentJournal:
    """방송/채팅/캐릭터 기존 DB와 별개의 콘텐츠 발화 시도 장부."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_live_content.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("방송 콘텐츠 장부에 심볼릭 링크를 사용할 수 없습니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        if existed and not self.path.is_file():
            raise ValueError("방송 콘텐츠 장부가 일반 파일이 아닙니다.")
        with self._connect() as db:
            app_id = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")}
            if (existed and not tables) or (
                tables and (tables != {_TABLE} or app_id != _APPLICATION_ID)
            ) or app_id not in (0, _APPLICATION_ID):
                raise ValueError("소유권이 다른 SQLite 파일을 변경하지 않습니다.")
            db.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_live_content_turns ("
                "occurrence TEXT NOT NULL,"
                "sequence INTEGER NOT NULL CHECK(sequence >= 1),"
                "topic TEXT NOT NULL,"
                "state TEXT NOT NULL CHECK(state IN ('시도', '전달확인', '전달불명')),"
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "PRIMARY KEY (occurrence, sequence))"
            )
            columns = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(approved_live_content_turns)"))
            if columns != (
                "occurrence", "sequence", "topic", "state",
                "created_at", "updated_at"
            ):
                raise ValueError("기존 방송 콘텐츠 장부 구조가 다릅니다.")

    class _Connection:
        def __init__(self, path: Path):
            self.path = path
            self.db = None

        def __enter__(self):
            self.db = sqlite3.connect(self.path, timeout=10)
            self.db.execute("PRAGMA busy_timeout=10000")
            self.db.execute("PRAGMA synchronous=FULL")
            return self.db

        def __exit__(self, typ, value, tb):
            try:
                if typ is None:
                    self.db.commit()
                else:
                    self.db.rollback()
            finally:
                self.db.close()
            return False

    def _connect(self):
        return self._Connection(self.path)

    def next_sequence(self, occurrence: str) -> int:
        self._check_occurrence(occurrence)
        with self._connect() as db:
            row = db.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM "
                "approved_live_content_turns WHERE occurrence=?",
                (occurrence,)).fetchone()
            return int(row[0]) + 1

    @staticmethod
    def _check_occurrence(occurrence: str) -> None:
        if (type(occurrence) is not str
                or not 1 <= len(occurrence) <= 120
                or any(ord(c) < 32 for c in occurrence)):
            raise ValueError("방송 일정 식별자가 잘못되었습니다.")

    def claim(self, turn: ContentTurn) -> bool:
        self._check_occurrence(turn.occurrence)
        if (type(turn.sequence) is not int or turn.sequence < 1
                or type(turn.topic) is not str
                or not 1 <= len(turn.topic) <= _MAX_TOPIC_LENGTH):
            raise ValueError("콘텐츠 시도 기록이 잘못되었습니다.")
        with self._connect() as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO approved_live_content_turns "
                "(occurrence, sequence, topic, state) VALUES (?, ?, ?, '시도')",
                (turn.occurrence, turn.sequence, turn.topic))
            return cursor.rowcount == 1

    def finish(self, turn: ContentTurn, *, delivered: bool) -> None:
        self._check_occurrence(turn.occurrence)
        state = "전달확인" if delivered is True else "전달불명"
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE approved_live_content_turns SET state=?, "
                "updated_at=CURRENT_TIMESTAMP WHERE occurrence=? "
                "AND sequence=? AND state='시도'",
                (state, turn.occurrence, turn.sequence))
            if cursor.rowcount != 1:
                raise RuntimeError("기존 콘텐츠 발화 시도와 상태가 일치하지 않습니다.")

    def last_confirmed_topics(
        self, occurrence: str, *, before_sequence: int,
        limit: int = 3,
    ) -> tuple[tuple[int, str], ...]:
        """같은 승인 방송 안에서 공식 AI로 전달 확인된 주제만 조회.

        실제 발화가 시청자에게 들렸다는 뜻이 아니고, 과거의
        '시도'/'전달불명'은 다음 방송의 확정 기억으로 쓰지 않는다.
        """
        self._check_occurrence(occurrence)
        if (type(before_sequence) is not int or before_sequence < 1
                or type(limit) is not int or not 1 <= limit <= 5):
            raise ValueError("승인 방송 콘텐츠 이어가기 조회 조건이 잘못됐습니다.")
        with self._connect() as db:
            rows = db.execute(
                "SELECT sequence,topic FROM approved_live_content_turns "
                "WHERE occurrence=? AND sequence<? AND state='전달확인' "
                "ORDER BY sequence DESC LIMIT ?",
                (occurrence, before_sequence, limit)).fetchall()
        return tuple((int(seq), str(topic)) for seq, topic in reversed(rows))

    def recent(self, *, limit: int = 20) -> tuple[tuple[str, int, str, str], ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("콘텐츠 기록 조회 범위는 1~100건입니다.")
        with self._connect() as db:
            return tuple(db.execute(
                "SELECT occurrence, sequence, topic, state FROM "
                "approved_live_content_turns ORDER BY created_at DESC, "
                "sequence DESC LIMIT ?", (limit,)).fetchall())


class ApprovedLiveContentAgenda:
    """동일 채팅 FIFO가 비어 있을 때만 주제별 공식 AI 질문 후보를 제공."""

    def __init__(
        self, *, occurrence: str, topics: tuple[str, ...],
        interval_seconds: int, operator_approved: bool,
        journal: ApprovedLiveContentJournal,
        broadcast_alive: Callable[[], bool],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if operator_approved is not True:
            raise PermissionError("실제 방송 콘텐츠 자동 발화 별도 승인이 필요합니다.")
        if type(topics) is not tuple or parse_approved_topics(
                "\n".join(topics)) != topics:
            raise ValueError("운영자가 지정한 방송 주제가 올바르지 않습니다.")
        if type(interval_seconds) is not int or not 60 <= interval_seconds <= 3600:
            raise ValueError("콘텐츠 진행 간격은 60~3600초입니다.")
        if (not isinstance(journal, ApprovedLiveContentJournal)
                or not callable(clock) or not callable(broadcast_alive)):
            raise ValueError("영구 장부·로컬 시계·실제 OBS 방송 상태 연결이 필요합니다.")
        journal._check_occurrence(occurrence)
        self.occurrence = occurrence
        self.topics = topics
        self.interval_seconds = interval_seconds
        self._journal = journal
        self._clock = clock
        self._broadcast_alive = broadcast_alive
        self._last_activity = self._time()
        self._next = journal.next_sequence(occurrence)

    def _time(self) -> float:
        now = self._clock()
        if type(now) not in (int, float) or not math.isfinite(now) or now < 0:
            raise ValueError("실제 콘텐츠 단조 시각이 올바르지 않습니다.")
        return float(now)

    def note_chat(self) -> None:
        self._last_activity = self._time()

    def broadcast_is_active(self) -> bool:
        """실제 예약이 소유한 OBS 방송이 살아 있는 동안만 발화 가능."""
        return self._broadcast_alive() is True

    def next_if_quiet(
        self, *, pending_count: int, sending: bool = False,
    ) -> ContentTurn | None:
        if (type(pending_count) is not int or pending_count < 0
                or type(sending) is not bool):
            raise ValueError("콘텐츠 진행 전 채팅 FIFO 상태가 올바르지 않습니다.")
        now = self._time()
        if (pending_count or sending or not self.broadcast_is_active()
                or now - self._last_activity < self.interval_seconds):
            return None
        sequence = self._next
        topic = self.topics[(sequence - 1) % len(self.topics)]
        confirmed = self._journal.last_confirmed_topics(
            self.occurrence, before_sequence=sequence, limit=3)
        # 단순 입력 시도/전달불명은 기억으로 꾸미지 않고, 같은
        # 승인 방송에서 공식 AI에게 요청 전달이 확인된 순서만 사용.
        # 사용자가 승인한 주제 자체를 AI가 추가/수정하지 않는다.
        continuity = (
            " 같은 방송에서 이전에 공식 AI에 전달 확인된 주제는 "
            + " / ".join(f"{n}회 '{past}'" for n, past in confirmed)
            + "입니다. 전달 확인은 실제 시청자 수신 증거가 아닙니다. "
            "이미 다룬 내용이라고 단정하지 말고 자연스럽게 연결하세요. "
            if confirmed else "")
        prompt = (
            "지금은 운영자가 승인한 방송의 자율 콘텐츠 진행 차례입니다. "
            + continuity +
            "운영자가 지정한 주제 '" + topic + "'에 대해 한국어로 자연스럽게 "
            "이야기를 이어가 주세요. 시청자 메시지를 지어내거나 "
            "시청자가 실제로 반응했다고 단정하지 마세요. "
            "이번 주제 진행 순번은 " + str(sequence) + "입니다."
        )
        turn = ContentTurn(self.occurrence, sequence, topic, prompt)
        # 재시작 후 불명확한 기존 발화는 재전송하지 않는다.
        if not self._journal.claim(turn):
            self._next = self._journal.next_sequence(self.occurrence)
            self._last_activity = now
            return None
        self._next += 1
        self._last_activity = now
        return turn

    def record_delivery(self, turn: ContentTurn, *, delivered: bool) -> None:
        self._journal.finish(turn, delivered=delivered)
