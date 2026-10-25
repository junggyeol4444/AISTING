"""운영자가 승인한 Windows 자율 게임 목표·행동의 영구 로컬 진행 장부.

이 파일은 원래 캐릭터/채팅/방송 SQLite와 분리한다. 한 게임 행동을
SendInput 전에 '입력시도'로 먼저 기록하여 강제 종료 뒤 실행 여부가
불명확한 행동을 무단 재생하지 않는다. 이어하기는 새 운영자 승인으로
새 run_id를 발급하고 이전 관찰/행동 이력만 읽어 목표 문맥으로 사용한다.
이 장부의 기록은 게임 목표 달성이나 실제 키 입력 성공 증명이 아니다.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .offline_settings import data_dir

_APP_ID = 0x41474731  # AGG1, 다른 SQLite 파일과 혼용 방지
_RUNS = "approved_game_goal_runs"
_EVENTS = "approved_game_goal_events"
_STATES = frozenset((
    "실행중", "운영자중지", "횟수종료", "AI종료", "실행실패", "목표후보",
))
_PHASES = frozenset((
    "관찰", "행동계획", "입력시도", "입력반환", "후속관찰", "목표판정", "중단",
))


@dataclass(frozen=True)
class GameGoalRun:
    run_id: str
    game_title: str
    goal: str
    model: str
    max_steps: int
    parent_run_id: str | None
    state: str
    created_at: str


@dataclass(frozen=True)
class GameGoalEvent:
    step_no: int
    phase: str
    detail: str
    created_at: str


class ApprovedGameGoalJournal:
    """프로그램이 만든 별도 로컬 SQLite에서만 승인된 목표 진행 기록."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else (
            data_dir() / "approved_game_goals.sqlite3")
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("게임 진행 장부에 바로가기를 사용할 수 없습니다.")
        if self.path.exists() and not self.path.is_file():
            raise ValueError("게임 진행 장부가 일반 파일이 아닙니다.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        with self._db(write=True) as db:
            app_id = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'").fetchall()}
            if existed and not tables:
                raise ValueError("소유권이 불명확한 기존 SQLite는 변경하지 않습니다.")
            if tables and (tables != {_RUNS, _EVENTS} or app_id != _APP_ID):
                raise ValueError("다른 프로그램의 SQLite는 변경하지 않습니다.")
            if app_id not in (0, _APP_ID):
                raise ValueError("게임 진행 장부 소유권이 일치하지 않습니다.")
            db.execute(f"PRAGMA application_id={_APP_ID}")
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_game_goal_runs ("
                "run_id TEXT PRIMARY KEY NOT NULL,"
                "game_title TEXT NOT NULL, goal TEXT NOT NULL,"
                "model TEXT NOT NULL, max_steps INTEGER NOT NULL,"
                "parent_run_id TEXT, state TEXT NOT NULL,"
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "finished_at TEXT)")
            db.execute(
                "CREATE TABLE IF NOT EXISTS approved_game_goal_events ("
                "event_id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "run_id TEXT NOT NULL, step_no INTEGER NOT NULL,"
                "phase TEXT NOT NULL, detail TEXT NOT NULL,"
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            run_columns = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(approved_game_goal_runs)"))
            event_columns = tuple(row[1] for row in db.execute(
                "PRAGMA table_info(approved_game_goal_events)"))
            if run_columns != (
                "run_id", "game_title", "goal", "model", "max_steps",
                "parent_run_id", "state", "created_at", "finished_at"
            ) or event_columns != (
                "event_id", "run_id", "step_no", "phase", "detail", "created_at"
            ):
                raise ValueError("기존 게임 장부 스키마가 일치하지 않습니다.")

    @contextmanager
    def _db(self, *, write: bool = False):
        db = sqlite3.connect(str(self.path), timeout=10)
        try:
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("PRAGMA synchronous=FULL")
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            if write:
                db.commit()
        except BaseException:
            if write:
                db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _validate_text(value: str, maximum: int, label: str) -> str:
        if (type(value) is not str or not 1 <= len(value.strip()) <= maximum
                or any(ord(c) < 32 or ord(c) == 127 for c in value)):
            raise ValueError(label + " 길이/문자 범위가 올바르지 않습니다.")
        return value.strip()

    @staticmethod
    def _row(row) -> GameGoalRun:
        return GameGoalRun(*row)

    def latest(self, game_title: str, goal: str, model: str) -> GameGoalRun | None:
        """동일 게임/목표/모델의 최근 기록을 읽기만 함."""
        title = self._validate_text(game_title, 200, "게임 창")
        goal = self._validate_text(goal, 300, "게임 목표")
        model = self._validate_text(model, 200, "로컬 모델")
        with self._db() as db:
            row = db.execute(
                "SELECT run_id,game_title,goal,model,max_steps,parent_run_id,"
                "state,created_at FROM approved_game_goal_runs "
                "WHERE game_title=? AND goal=? AND model=? "
                "ORDER BY rowid DESC LIMIT 1", (title, goal, model)).fetchone()
        return self._row(row) if row else None

    def recent_runs(self, *, limit: int = 20) -> tuple[GameGoalRun, ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("게임 목표 조회 개수는 1~100이어야 합니다.")
        with self._db() as db:
            rows = db.execute(
                "SELECT run_id,game_title,goal,model,max_steps,parent_run_id,"
                "state,created_at FROM approved_game_goal_runs "
                "ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
        return tuple(self._row(row) for row in rows)

    def begin(
        self, *, game_title: str, goal: str, model: str, max_steps: int,
        parent_run_id: str | None = None, operator_approved: bool = False,
    ) -> GameGoalRun:
        if operator_approved is not True:
            raise PermissionError("실제 게임 조작을 다시 별도 승인해야 합니다.")
        title = self._validate_text(game_title, 200, "게임 창")
        goal = self._validate_text(goal, 300, "게임 목표")
        model = self._validate_text(model, 200, "로컬 모델")
        if type(max_steps) is not int or not 1 <= max_steps <= 100:
            raise ValueError("이번 승인 행동 수는 1~100회여야 합니다.")
        if parent_run_id is not None:
            if type(parent_run_id) is not str or len(parent_run_id) != 36:
                raise ValueError("이전 게임 기록 ID가 올바르지 않습니다.")
        run_id = str(uuid4())
        with self._db(write=True) as db:
            if parent_run_id is not None:
                row = db.execute(
                    "SELECT game_title,goal,model FROM approved_game_goal_runs "
                    "WHERE run_id=?", (parent_run_id,)).fetchone()
                if row != (title, goal, model):
                    raise ValueError("이전 기록의 게임·목표·모델이 다릅니다.")
            db.execute(
                "INSERT INTO approved_game_goal_runs "
                "(run_id,game_title,goal,model,max_steps,parent_run_id,state)"
                " VALUES (?,?,?,?,?,?,?)",
                (run_id, title, goal, model, max_steps,
                 parent_run_id, "실행중"))
            row = db.execute(
                "SELECT run_id,game_title,goal,model,max_steps,parent_run_id,"
                "state,created_at FROM approved_game_goal_runs "
                "WHERE run_id=?", (run_id,)).fetchone()
        return self._row(row)

    def record(self, run_id: str, step_no: int, phase: str, detail: str) -> None:
        if type(run_id) is not str or len(run_id) != 36:
            raise ValueError("게임 실행 기록 ID가 올바르지 않습니다.")
        if type(step_no) is not int or not 0 <= step_no <= 100:
            raise ValueError("게임 행동 순번이 올바르지 않습니다.")
        if phase not in _PHASES:
            raise ValueError("게임 행동 단계가 올바르지 않습니다.")
        if type(detail) is not str or not 1 <= len(detail) <= 2500:
            raise ValueError("게임 진행 기록 길이가 올바르지 않습니다.")
        with self._db(write=True) as db:
            if db.execute(
                "SELECT state FROM approved_game_goal_runs WHERE run_id=?",
                (run_id,)).fetchone() != ("실행중",):
                raise RuntimeError("종료되거나 존재하지 않는 게임 실행 기록입니다.")
            db.execute(
                "INSERT INTO approved_game_goal_events "
                "(run_id,step_no,phase,detail) VALUES (?,?,?,?)",
                (run_id, step_no, phase, detail))

    def history(
        self, run_id: str, *, limit: int = 12,
    ) -> tuple[GameGoalEvent, ...]:
        if type(run_id) is not str or len(run_id) != 36:
            raise ValueError("게임 실행 기록 ID가 올바르지 않습니다.")
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError("게임 진행 문맥 개수가 올바르지 않습니다.")
        with self._db() as db:
            rows = db.execute(
                "SELECT step_no,phase,detail,created_at "
                "FROM approved_game_goal_events WHERE run_id=? "
                "ORDER BY event_id DESC LIMIT ?", (run_id, limit)).fetchall()
        return tuple(GameGoalEvent(*row) for row in reversed(rows))

    def finish(self, run_id: str, state: str) -> None:
        if state not in _STATES - {"실행중"}:
            raise ValueError("게임 종료 상태가 올바르지 않습니다.")
        with self._db(write=True) as db:
            row = db.execute(
                "UPDATE approved_game_goal_runs SET state=?,"
                "finished_at=CURRENT_TIMESTAMP "
                "WHERE run_id=? AND state='실행중'", (state, run_id))
            if row.rowcount != 1:
                raise RuntimeError("실행 중인 게임 기록이 없어 종료할 수 없습니다.")
