"""Original stage 054: operator-selected expressions for the *built-in* 2D sample.

No expression inference, model loading, OS probing, network use or automatic
persistence. The operator must confirm every save/delete and manually load.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir
from .runtime_profile import _assert_safe_path

EXPRESSIONS = {'기본': 'neutral', '미소': 'smile', '놀람': 'surprised', '걱정': 'concerned'}
ALLOWED_AVATARS = frozenset({'undecided', '2d'})
SCHEMA_VERSION = 1
MAX_BYTES = 1024
FILE_NAME = 'avatar_expression_choice.json'


@dataclass(frozen=True)
class AvatarExpressionChoice:
    avatar: str
    expression: str = 'neutral'

    def __post_init__(self) -> None:
        if type(self.avatar) is not str or self.avatar not in ALLOWED_AVATARS:
            raise ValueError('내장 2D 샘플 또는 미정 아바타에서만 표정을 선택할 수 있습니다.')
        if type(self.expression) is not str or self.expression not in EXPRESSIONS.values():
            raise ValueError('지원하지 않는 기본 표정입니다.')

    def describe(self) -> str:
        label = next(k for k, v in EXPRESSIONS.items() if v == self.expression)
        return (f'54단계 · 내장 2D 샘플 기본 표정: {label}\n'
                '현재 화면의 본 창과 별도 창에 같은 표정을 적용합니다.\n'
                '표정은 운영자가 수동 선택하며 AI 대사·실제 감정에서 자동 추론하지 않습니다.\n'
                '실제 Live2D/VRM 모델 적용, 방송 송출 또는 운영자 최종 승인 아님.')


def expression_path(directory: Path | None = None) -> Path:
    return (Path(directory) if directory is not None else data_dir()) / FILE_NAME


def _record(choice: AvatarExpressionChoice) -> dict:
    return {'schema_version': SCHEMA_VERSION, 'kind': 'builtin_2d_expression_only',
            'avatar': choice.avatar, 'expression': choice.expression,
            'model_loaded': False, 'auto_emotion_enabled': False,
            'streaming_authorized': False, 'final_approval': False}


def validate_expression_record(value: object) -> AvatarExpressionChoice:
    if (type(value) is not dict or set(value) != set(_record(AvatarExpressionChoice('2d')))
            or type(value['schema_version']) is not int or value['schema_version'] != SCHEMA_VERSION
            or value['kind'] != 'builtin_2d_expression_only'
            or any(value[k] is not False for k in ('model_loaded', 'auto_emotion_enabled',
                                                  'streaming_authorized', 'final_approval'))):
        raise ValueError('표정 설정 기록 형식 또는 승인 필드가 올바르지 않습니다.')
    return AvatarExpressionChoice(value['avatar'], value['expression'])


def save_expression(path: Path, choice: AvatarExpressionChoice, *, operator_confirmed: bool = False) -> Path:
    if operator_confirmed is not True:
        raise PermissionError('운영자 저장 확인이 필요합니다.')
    if type(choice) is not AvatarExpressionChoice:
        raise ValueError('표정 설정 형식이 올바르지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 저장할 수 있습니다.')
    raw = json.dumps(_record(choice), ensure_ascii=False, indent=2).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValueError('표정 설정 크기를 초과했습니다.')
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(target)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.avatar-expression-', suffix='.tmp', delete=False) as fh:
            temporary = Path(fh.name)
            fh.write(raw)
            fh.flush()
            os.fsync(fh.fileno())
        _assert_safe_path(target)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def load_expression(path: Path, *, selected_avatar: str) -> AvatarExpressionChoice | None:
    if selected_avatar not in ALLOWED_AVATARS:
        raise ValueError('현재 아바타는 내장 2D 샘플이 아닙니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 불러올 수 있습니다.')
    try:
        with target.open('rb') as fh:
            raw = fh.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(raw) > MAX_BYTES:
        raise ValueError('표정 설정 기록 크기를 초과했습니다.')
    try:
        choice = validate_expression_record(json.loads(raw.decode('utf-8')))
    except (UnicodeError, TypeError, ValueError, KeyError) as exc:
        raise ValueError('저장된 표정 기록의 형식이 올바르지 않습니다.') from exc
    if choice.avatar != selected_avatar:
        raise ValueError('다른 아바타 선택의 표정 기록입니다. 자동 재사용하지 않습니다.')
    return choice


def delete_expression(path: Path, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('운영자 삭제 확인이 필요합니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 삭제할 수 있습니다.')
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True


def expression_matches(canvas, expression: str) -> bool:
    """Inspect local Tk Canvas tags only (not screen pixels or remote model)."""
    if type(expression) is not str or expression not in EXPRESSIONS.values():
        raise ValueError('지원하지 않는 표정입니다.')
    expected = 'aisting_expression_' + expression
    return (len(canvas.find_withtag(expected)) >= 2 and
            all(not canvas.find_withtag('aisting_expression_' + other)
                for other in EXPRESSIONS.values() if other != expression))
