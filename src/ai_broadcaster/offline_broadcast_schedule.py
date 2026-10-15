"""Stage 081: operator-managed *draft* of weekly broadcast start times.

A pure calendar calculation plus explicitly requested local JSON operations.
NO timers, scheduler registration, auto-run, OBS, platforms, accounts or network.
Every time value is Korean local wall time (UTC+09:00, no DST in modern KST).
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .offline_settings import data_dir
from .runtime_profile import _assert_safe_path

KST = timezone(timedelta(hours=9), name='Asia/Seoul')
FILE_NAME = 'broadcast_schedule_draft.json'
SCHEMA = 1
MAX_BYTES = 4096
MAX_SLOTS = 14
WEEKDAYS = ('월', '화', '수', '목', '금', '토', '일')


def _validate_time_text(time_text: str) -> tuple[int, int]:
    if type(time_text) is not str or len(time_text) != 5 or time_text[2] != ':' or not (
        time_text[:2].isascii() and time_text[:2].isdigit()
        and time_text[3:].isascii() and time_text[3:].isdigit()
    ):
        raise ValueError('시각은 24시간 HH:MM 형식으로 입력해야 합니다.')
    hour, minute = int(time_text[:2]), int(time_text[3:])
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError('시각 범위는 00:00~23:59입니다.')
    return hour, minute


@dataclass(frozen=True)
class WeeklyStartSlot:
    weekday: int
    start_time: str

    def __post_init__(self):
        if type(self.weekday) is not int or not 0 <= self.weekday <= 6:
            raise ValueError('요일은 월요일(0)~일요일(6)이어야 합니다.')
        _validate_time_text(self.start_time)

    @property
    def label(self) -> str:
        return f'{WEEKDAYS[self.weekday]}요일 {self.start_time}'


@dataclass(frozen=True)
class BroadcastScheduleDraft:
    slots: tuple[WeeklyStartSlot, ...] = ()

    def __post_init__(self):
        if type(self.slots) is not tuple or len(self.slots) > MAX_SLOTS:
            raise ValueError(f'일정은 최대 {MAX_SLOTS}개까지 등록할 수 있습니다.')
        if any(type(slot) is not WeeklyStartSlot for slot in self.slots):
            raise ValueError('일정 항목 형식이 올바르지 않습니다.')
        ordered = tuple(sorted(self.slots, key=lambda slot: (slot.weekday, slot.start_time)))
        if ordered != self.slots:
            raise ValueError('일정은 요일·시각 순서대로 정렬해야 합니다.')
        if len(set(self.slots)) != len(self.slots):
            raise ValueError('동일 요일·시각 일정은 중복할 수 없습니다.')

    def add(self, weekday: int, start_time: str) -> 'BroadcastScheduleDraft':
        slot = WeeklyStartSlot(weekday, start_time)
        if slot in self.slots:
            raise ValueError('이미 등록된 방송 시작 일정입니다.')
        return BroadcastScheduleDraft(tuple(sorted(self.slots + (slot,), key=lambda s: (s.weekday, s.start_time))))

    def remove(self, weekday: int, start_time: str) -> 'BroadcastScheduleDraft':
        slot = WeeklyStartSlot(weekday, start_time)
        if slot not in self.slots:
            raise ValueError('삭제할 일정이 등록되어 있지 않습니다.')
        return BroadcastScheduleDraft(tuple(s for s in self.slots if s != slot))

    def upcoming(self, reference: datetime, limit: int = 5) -> tuple[datetime, ...]:
        """Return next occurrences strictly AFTER reference; no system clock read."""
        if not isinstance(reference, datetime) or reference.tzinfo is None or reference.utcoffset() is None:
            raise ValueError('기준 시각은 시간대가 지정된 날짜·시각이어야 합니다.')
        if reference.utcoffset() != timedelta(hours=9):
            raise ValueError('한국 시간(UTC+09:00) 기준만 사용할 수 있습니다.')
        if type(limit) is not int or not 1 <= limit <= 30:
            raise ValueError('예정 시각 조회 개수는 1~30이어야 합니다.')
        if not self.slots:
            return ()
        reference = reference.astimezone(KST)
        results = []
        for slot in self.slots:
            hour, minute = _validate_time_text(slot.start_time)
            days = (slot.weekday - reference.weekday()) % 7
            proposed_date = reference.date() + timedelta(days=days)
            proposed = datetime(proposed_date.year, proposed_date.month, proposed_date.day,
                                hour, minute, tzinfo=KST)
            if proposed <= reference:
                proposed += timedelta(days=7)
            for week in range((limit // len(self.slots)) + 2):
                results.append(proposed + timedelta(days=7 * week))
        return tuple(sorted(results)[:limit])

    def description(self) -> str:
        display = ', '.join(slot.label for slot in self.slots) or '등록된 일정 없음'
        return (f'081 한국 시간(KST) 방송 시작 일정 초안 · {display} · '
                '자동 방송 시작 비활성 / 실제 OBS·플랫폼 연결 없음 / 사용자 승인 대기')


def parse_reference(text: str) -> datetime:
    """Strict manual YYYY-MM-DD HH:MM input; never reads local device time."""
    if (type(text) is not str or len(text) != 16 or text[10] != ' '
            or text[4] != '-' or text[7] != '-'):
        raise ValueError('기준 시각은 YYYY-MM-DD HH:MM 형식이어야 합니다.')
    pieces = text[:10].split('-')
    if (len(pieces) != 3 or any(len(p) != n or not p.isascii() or not p.isdigit()
                                for p, n in zip(pieces, (4, 2, 2)))):
        raise ValueError('기준 날짜 형식이 잘못되었습니다.')
    hour, minute = _validate_time_text(text[11:])
    try:
        return datetime(int(pieces[0]), int(pieces[1]), int(pieces[2]),
                        hour, minute, tzinfo=KST)
    except ValueError as exc:
        raise ValueError('존재하지 않는 기준 날짜입니다.') from exc


def schedule_path(directory: Path | None = None) -> Path:
    return (Path(directory) if directory is not None else data_dir()) / FILE_NAME


def _record(draft: BroadcastScheduleDraft) -> dict:
    if type(draft) is not BroadcastScheduleDraft:
        raise ValueError('검증된 방송 일정 초안만 저장할 수 있습니다.')
    return {'schema_version': SCHEMA, 'kind': 'offline_weekly_broadcast_draft',
            'timezone': 'Asia/Seoul',
            'slots': [{'weekday': s.weekday, 'start_time': s.start_time} for s in draft.slots],
            'scheduled_execution': False, 'broadcasting_authorized': False,
            'obs_connected': False, 'final_approval': False}


def validate_schedule_record(obj: object) -> BroadcastScheduleDraft:
    expected = _record(BroadcastScheduleDraft())
    if type(obj) is not dict or set(obj) != set(expected):
        raise ValueError('일정 저장 데이터 구성이 올바르지 않습니다.')
    if (type(obj['schema_version']) is not int or obj['schema_version'] != SCHEMA
            or type(obj['kind']) is not str or obj['kind'] != expected['kind']
            or type(obj['timezone']) is not str or obj['timezone'] != 'Asia/Seoul'
            or any(obj[key] is not False for key in
                   ('scheduled_execution', 'broadcasting_authorized', 'obs_connected', 'final_approval'))):
        raise ValueError('일정이 자동 실행이나 승인 상태를 활성화하려 합니다.')
    rows = obj['slots']
    if type(rows) is not list or len(rows) > MAX_SLOTS:
        raise ValueError('일정 목록 형식이나 개수가 올바르지 않습니다.')
    if any(type(row) is not dict or set(row) != {'weekday', 'start_time'} for row in rows):
        raise ValueError('일정 목록의 항목이 올바르지 않습니다.')
    return BroadcastScheduleDraft(tuple(WeeklyStartSlot(row['weekday'], row['start_time']) for row in rows))


def _safe_file(path: Path) -> None:
    _assert_safe_path(path)
    if path.exists() and (not path.is_file() or path.is_symlink()):
        raise ValueError('일반 로컬 파일만 허용합니다.')


def save_schedule(path: Path, draft: BroadcastScheduleDraft, *, operator_confirmed: bool = False) -> Path:
    if operator_confirmed is not True:
        raise PermissionError('운영자가 저장 버튼으로 명시적으로 요청해야 합니다.')
    raw = json.dumps(_record(draft), ensure_ascii=False, indent=2).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValueError('일정 저장 크기 제한을 초과했습니다.')
    target = Path(path)
    _safe_file(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _safe_file(target)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.aisting-schedule-',
                                         suffix='.tmp', delete=False) as fp:
            temp = Path(fp.name)
            fp.write(raw)
            fp.flush()
            os.fsync(fp.fileno())
        _safe_file(target)
        os.replace(temp, target)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return target


def load_schedule(path: Path) -> BroadcastScheduleDraft | None:
    target = Path(path)
    _safe_file(target)
    try:
        with target.open('rb') as fp:
            raw = fp.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(raw) > MAX_BYTES:
        raise ValueError('일정 파일이 너무 큽니다.')
    try:
        return validate_schedule_record(json.loads(raw.decode('utf-8')))
    except (UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise ValueError('일정 파일을 신뢰할 수 없어 불러오지 않았습니다.') from exc


def delete_schedule(path: Path, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('운영자가 삭제를 명시적으로 요청해야 합니다.')
    target = Path(path)
    _safe_file(target)
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True
