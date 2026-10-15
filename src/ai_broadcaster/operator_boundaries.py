"""Operator-entered optional persona boundaries; strictly local and manual.

The module does not filter model output or claim live enforcement. Boundaries are
not loaded or saved without an explicit GUI action. Original settings and chat
memory remain untouched.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir
from .personality_preferences import review_preferences
from .runtime_profile import _assert_safe_path

MAX_LINES = 12
MAX_LINE_LENGTH = 200
SCHEMA = 1
FILE_NAME = 'operator_persona_boundaries.json'
MAX_BYTES = 8192


@dataclass(frozen=True)
class BoundaryReview:
    boundaries: tuple[str, ...]
    guidance: str
    checks: tuple[tuple[str, bool], ...]

    @property
    def passed(self) -> bool:
        return all(ok for _, ok in self.checks)

    def describe(self) -> str:
        items = '\n'.join(f'{i}. {line}' for i, line in enumerate(self.boundaries, 1))
        return ('35단계 · 운영자 지정 금기·제한사항 미리보기\n'
                f'구조 검사 {sum(ok for _, ok in self.checks)}/{len(self.checks)} 통과\n'
                + '\n'.join(('통과' if ok else '실패') + ' · ' + label for label, ok in self.checks)
                + '\n입력한 제한사항:\n' + (items or '(미설정)') + '\n\n'
                + self.guidance + '\n'
                '※ 실제 모델 답변을 필터링하거나 방송에 적용한 것은 아닙니다.')


def validate_boundaries(lines: object) -> tuple[str, ...]:
    """Preserve operator ordering, reject blanks, control chars and duplicates."""
    if not isinstance(lines, (tuple, list)) or len(lines) > MAX_LINES:
        raise ValueError(f'제한사항은 최대 {MAX_LINES}개까지 입력할 수 있습니다.')
    output = []
    for line in lines:
        if not isinstance(line, str) or not 1 <= len(line.strip()) <= MAX_LINE_LENGTH:
            raise ValueError(f'제한사항 한 줄은 1~{MAX_LINE_LENGTH}글자여야 합니다.')
        cleaned = line.strip()
        if any(ord(c) < 32 or ord(c) == 127 for c in cleaned):
            raise ValueError('줄바꿈·제어 문자가 포함된 제한사항은 사용할 수 없습니다.')
        if cleaned in output:
            raise ValueError('동일한 제한사항을 중복 입력할 수 없습니다.')
        output.append(cleaned)
    return tuple(output)


def review_boundaries(mode: str, persona: dict[str, str], lines: object,
                      likes: str = '', dislikes: str = '') -> BoundaryReview:
    base = review_preferences(mode, persona, likes, dislikes)
    checked = validate_boundaries(lines)
    appendix = ('\n운영자가 직접 입력한 금기·제한사항 (선택):\n'
                + '\n'.join(f'- {line}' for line in checked)) if checked else ''
    guidance = base.guidance + appendix
    checks = (
        ('캐릭터 이름·성격·말투 보존', all(base.persona[k] in guidance for k in ('name', 'character', 'style'))),
        ('기존 취향 보존', all(t in guidance for t in (base.likes, base.dislikes) if t)),
        ('운영자 입력만 순서대로 포함', all(f'- {line}' in appendix for line in checked)),
        ('미설정 시 제한사항 임의 추가 없음', bool(checked) or not appendix),
    )
    return BoundaryReview(checked, guidance, checks)


def boundaries_path(directory: Path | None = None) -> Path:
    return (Path(directory) if directory is not None else data_dir()) / FILE_NAME


def save_boundaries(path: Path, lines: object, *, operator_confirmed: bool = False) -> Path:
    if operator_confirmed is not True:
        raise PermissionError('사용자가 확인한 뒤에만 제한사항을 저장합니다.')
    checked = validate_boundaries(lines)
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일에만 저장할 수 있습니다.')
    payload = json.dumps({'schema_version': SCHEMA, 'source': 'operator_input',
                          'boundaries': list(checked)}, ensure_ascii=False, indent=2).encode('utf-8')
    if len(payload) > MAX_BYTES:
        raise ValueError('저장 가능한 제한사항 데이터 크기를 초과했습니다.')
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(target)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.boundaries-',
                                         suffix='.tmp', delete=False) as fh:
            temporary = Path(fh.name)
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        _assert_safe_path(target)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def load_boundaries(path: Path) -> tuple[str, ...] | None:
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('제한사항 기록이 일반 파일이 아닙니다.')
    try:
        with target.open('rb') as fh:
            payload = fh.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(payload) > MAX_BYTES:
        raise ValueError('제한사항 기록 크기가 너무 큽니다.')
    try:
        data = json.loads(payload.decode('utf-8'))
    except (ValueError, UnicodeError) as exc:
        raise ValueError('제한사항 기록 형식이 손상됐습니다.') from exc
    if (type(data) is not dict or set(data) != {'schema_version', 'source', 'boundaries'}
            or type(data['schema_version']) is not int or data['schema_version'] != SCHEMA
            or data['source'] != 'operator_input'):
        raise ValueError('운영자가 입력한 제한사항 기록 형식이 아닙니다.')
    if not isinstance(data['boundaries'], list):
        raise ValueError('저장된 제한사항은 목록이어야 합니다.')
    return validate_boundaries(data['boundaries'])


def delete_boundaries(path: Path, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('사용자가 확인한 뒤에만 제한사항을 삭제합니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 삭제할 수 있습니다.')
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True
