"""Original stage 039: user-controlled offline feedback/change-request journal.

Nothing is applied to character prompts, stored settings, AI, audio or streaming.
No file is opened until a caller explicitly invokes a storage operation.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir
from .runtime_profile import _assert_safe_path

FEEDBACK_FILE = 'operator_feedback_requests.json'
CATEGORIES = ('말투', '성격·취향', '채팅 반응', '자발적 발화', '기타')
MAX_ENTRIES = 40
MAX_TEXT = 500
MAX_BYTES = 65536
SCHEMA = 1


@dataclass(frozen=True)
class Feedback:
    sequence: int
    category: str
    observation: str
    requested_change: str

    def describe(self) -> str:
        return (f'#{self.sequence} [{self.category}] 검토 대기\n'
                f'운영자가 관찰한 문제: {self.observation}\n'
                f'운영자가 요청한 수정 방향: {self.requested_change}\n'
                '아직 캐릭터·프롬프트·응답 동작에 적용되지 않았습니다.')


def _text(value: object, label: str) -> str:
    if type(value) is not str or not 1 <= len(value.strip()) <= MAX_TEXT:
        raise ValueError(f'{label}은 1~{MAX_TEXT}자여야 합니다.')
    cleaned = value.strip()
    if any(ord(char) < 32 or ord(char) == 127 for char in cleaned):
        raise ValueError(f'{label}에 줄바꿈·제어 문자를 사용할 수 없습니다.')
    return cleaned


def draft_feedback(category: object, observation: object, requested_change: object) -> Feedback:
    if type(category) is not str or category not in CATEGORIES:
        raise ValueError('지원하지 않는 피드백 항목입니다.')
    return Feedback(0, category, _text(observation, '관찰 내용'),
                    _text(requested_change, '요청 수정 방향'))


def feedback_path(storage_dir: Path | None = None) -> Path:
    return (Path(storage_dir) if storage_dir is not None else data_dir()) / FEEDBACK_FILE


def _validate_items(data: object) -> tuple[int, tuple[Feedback, ...]]:
    if type(data) is not dict or set(data) != {'schema_version', 'next_sequence', 'requests'}:
        raise ValueError('피드백 파일 형식이 올바르지 않습니다.')
    if type(data['schema_version']) is not int or data['schema_version'] != SCHEMA:
        raise ValueError('피드백 스키마 버전이 올바르지 않습니다.')
    next_seq, raw = data['next_sequence'], data['requests']
    if type(next_seq) is not int or not 1 <= next_seq <= 2_000_000_000:
        raise ValueError('다음 순번이 올바르지 않습니다.')
    if type(raw) is not list or len(raw) > MAX_ENTRIES:
        raise ValueError('피드백 항목 수가 잘못됐습니다.')
    records: list[Feedback] = []
    prev = 0
    for item in raw:
        if type(item) is not dict or set(item) != {'sequence', 'category', 'observation', 'requested_change'}:
            raise ValueError('피드백 항목 형식이 올바르지 않습니다.')
        seq = item['sequence']
        if type(seq) is not int or seq <= prev or seq >= next_seq:
            raise ValueError('순번 중복·역순 또는 범위 오류입니다.')
        validated = draft_feedback(item['category'], item['observation'], item['requested_change'])
        records.append(Feedback(seq, validated.category, validated.observation, validated.requested_change))
        prev = seq
    return next_seq, tuple(records)


def _blank() -> dict:
    return {'schema_version': SCHEMA, 'next_sequence': 1, 'requests': []}


def _read(path: Path) -> dict:
    _assert_safe_path(path)
    if path.exists() and not path.is_file():
        raise ValueError('피드백 경로가 일반 파일이 아닙니다.')
    try:
        with path.open('rb') as fh:
            payload = fh.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return _blank()
    if len(payload) > MAX_BYTES:
        raise ValueError('피드백 저장 크기를 초과했습니다.')
    try:
        parsed = json.loads(payload.decode('utf-8'))
    except (ValueError, UnicodeError) as exc:
        raise ValueError('피드백 저장 파일이 손상됐습니다.') from exc
    _validate_items(parsed)
    return parsed


def list_feedback(path: Path) -> tuple[Feedback, ...]:
    return _validate_items(_read(Path(path)))[1]


def _write(path: Path, data: dict) -> None:
    _validate_items(data)
    payload = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    if len(payload) > MAX_BYTES:
        raise ValueError('저장 용량을 초과했습니다.')
    _assert_safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(path)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.feedback-', suffix='.tmp', delete=False) as fh:
            temp = Path(fh.name)
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        _assert_safe_path(path)
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def add_feedback(path: Path, draft: Feedback, *, operator_confirmed: bool = False) -> Feedback:
    if operator_confirmed is not True:
        raise PermissionError('사용자가 확인해야 기록할 수 있습니다.')
    if type(draft) is not Feedback or draft.sequence != 0:
        raise ValueError('미리보기로 검증한 신규 피드백만 추가할 수 있습니다.')
    validated = draft_feedback(draft.category, draft.observation, draft.requested_change)
    target = Path(path)
    data = _read(target)
    if len(data['requests']) >= MAX_ENTRIES or data['next_sequence'] >= 2_000_000_000:
        raise ValueError('피드백 저장 상한에 도달했습니다. 사용자 확인 후 정리해 주세요.')
    item = Feedback(data['next_sequence'], validated.category,
                    validated.observation, validated.requested_change)
    data['requests'].append(vars(item))
    data['next_sequence'] += 1
    _write(target, data)
    return item


def revise_feedback(path: Path, sequence: int, draft: Feedback, *, operator_confirmed: bool = False) -> Feedback:
    """Revise only the explicitly selected pending request, never runtime settings."""
    if operator_confirmed is not True:
        raise PermissionError('사용자가 확인해야 수정할 수 있습니다.')
    if type(sequence) is not int or sequence <= 0 or type(draft) is not Feedback or draft.sequence != 0:
        raise ValueError('수정 대상/미리보기가 올바르지 않습니다.')
    validated = draft_feedback(draft.category, draft.observation, draft.requested_change)
    target = Path(path)
    data = _read(target)
    for i, item in enumerate(data['requests']):
        if item['sequence'] == sequence:
            changed = Feedback(sequence, validated.category, validated.observation, validated.requested_change)
            data['requests'][i] = vars(changed)
            _write(target, data)
            return changed
    raise ValueError('수정할 피드백 순번이 없습니다.')


def delete_feedback(path: Path, sequence: int, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('사용자가 확인해야 삭제할 수 있습니다.')
    if type(sequence) is not int or sequence <= 0:
        raise ValueError('삭제할 피드백 순번을 입력해 주세요.')
    target = Path(path)
    data = _read(target)
    remaining = [item for item in data['requests'] if item['sequence'] != sequence]
    if len(remaining) == len(data['requests']):
        return False
    data['requests'] = remaining
    _write(target, data)
    return True
