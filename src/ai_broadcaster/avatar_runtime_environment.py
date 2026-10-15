"""Stage 052: operator-authored *offline draft* for avatar rendering environment.

This module does not inspect the machine, model files, processes or installed software.
All external renderers are names of unconnected candidates, not executable adapters.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import AVATARS, data_dir
from .avatar_renderer import BACKGROUND_COLORS
from .runtime_profile import _assert_safe_path

FILE_NAME = 'avatar_runtime_environment_draft.json'
SCHEMA_VERSION = 1
MAX_BYTES = 4096
MAX_NOTE = 200
RENDERERS = {
    '미정': 'undecided',
    '내장 2D 샘플 (기존 Tk 미리보기)': 'builtin_2d',
    '외부 Live2D 후보 (미연결)': 'external_live2d',
    '외부 VRM 후보 (미연결)': 'external_vrm',
}
COMPATIBLE = {
    'undecided': frozenset(('undecided',)),
    '2d': frozenset(('undecided', 'builtin_2d', 'external_live2d')),
    '3d': frozenset(('undecided', 'external_vrm')),
}


@dataclass(frozen=True)
class AvatarRuntimeDraft:
    avatar: str
    renderer: str = 'undecided'
    background: str = '남색 스튜디오'
    note: str = ''

    def __post_init__(self) -> None:
        if type(self.avatar) is not str or self.avatar not in COMPATIBLE:
            raise ValueError('아바타 선택은 미정/2D/3D 중 하나여야 합니다.')
        if type(self.renderer) is not str or self.renderer not in COMPATIBLE[self.avatar]:
            raise ValueError('현재 아바타 형태와 맞지 않는 렌더러 후보입니다.')
        if type(self.background) is not str or self.background not in BACKGROUND_COLORS:
            raise ValueError('등록된 내장 배경만 선택할 수 있습니다.')
        # Background is a *sample canvas* attribute, not a parameter to external renderers.
        if self.renderer != 'builtin_2d' and self.background != '남색 스튜디오':
            raise ValueError('내장 2D 샘플 외의 렌더러에는 배경 설정을 전달하지 않습니다.')
        if type(self.note) is not str or len(self.note) > MAX_NOTE or any(ord(c) < 32 or ord(c) == 127 for c in self.note):
            raise ValueError('메모는 줄바꿈 없이 200자 이내로 입력하세요.')

    @property
    def has_existing_preview(self) -> bool:
        return self.avatar == '2d' and self.renderer == 'builtin_2d'

    def describe(self) -> str:
        avatar_label = next(label for label, code in AVATARS.items() if code == self.avatar)
        renderer_label = next(label for label, code in RENDERERS.items() if code == self.renderer)
        state = ('기존 Tk 2D 샘플 미리보기만 사용 가능 (실제 모델 아님)'
                 if self.has_existing_preview else '실제 렌더러 연결·설치·실행 미확인')
        return (f'원본 052단계 · 아바타 실행 환경 구성 초안\n아바타 형태: {avatar_label}\n'
                f'렌더러 선택 후보: {renderer_label}\n'
                f'기존 내장 배경(샘플 전용): {self.background}\n'
                f'운영자 메모: {self.note or "(없음)"}\n상태: {state}\n'
                '실행 대상: 이 앱의 기존 Tk 미리보기 외에는 없음. 외부 실행 파일/모델 경로 없음.\n'
                '※ 후보 선택은 설치·호환성 실측·모델 파일 확인·렌더링 권한을 뜻하지 않습니다.\n'
                '※ 외부 프로세스 실행, OS/PC 사양 조회, 모델 스캔, 연결, 방송 및 송출 없음.\n'
                '※ 기존 모델 준비표의 체크는 실제 권리/사용 승인이나 010 최종 승인이 아닙니다.')


def runtime_environment_path(directory: Path | None = None) -> Path:
    return (Path(directory) if directory is not None else data_dir()) / FILE_NAME


def _payload(draft: AvatarRuntimeDraft) -> dict:
    return dict(schema_version=SCHEMA_VERSION, kind='avatar_runtime_candidate_only',
                avatar=draft.avatar, renderer=draft.renderer, background=draft.background,
                note=draft.note, pc_inspected=False, model_accessed=False,
                software_installed=False, external_process_launched=False,
                renderer_connected=False, license_verified=False,
                streaming_authorized=False, final_approval=False)


def validate_runtime_record(value: object) -> AvatarRuntimeDraft:
    expected = set(_payload(AvatarRuntimeDraft('undecided')))
    flags = ('pc_inspected', 'model_accessed', 'software_installed',
             'external_process_launched', 'renderer_connected', 'license_verified',
             'streaming_authorized', 'final_approval')
    if (type(value) is not dict or set(value) != expected
        or type(value['schema_version']) is not int or value['schema_version'] != SCHEMA_VERSION
        or type(value['kind']) is not str or value['kind'] != 'avatar_runtime_candidate_only'
        or any(value[name] is not False for name in flags)):
        raise ValueError('아바타 환경 구성 기록에 잘못된 필드 또는 권한 값이 있습니다.')
    return AvatarRuntimeDraft(value['avatar'], value['renderer'], value['background'], value['note'])


def save_runtime_environment(path: Path, draft: AvatarRuntimeDraft, *, operator_confirmed: bool = False) -> Path:
    if operator_confirmed is not True:
        raise PermissionError('사용자가 확인하지 않은 구성 초안은 저장하지 않습니다.')
    if type(draft) is not AvatarRuntimeDraft:
        raise ValueError('구성 초안 형식이 올바르지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 저장할 수 있습니다.')
    raw = json.dumps(_payload(draft), ensure_ascii=False, indent=2).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValueError('구성 기록 크기를 초과했습니다.')
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(target)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.avatar-env-', suffix='.tmp', delete=False) as fh:
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


def load_runtime_environment(path: Path, *, selected_avatar: str) -> AvatarRuntimeDraft | None:
    if type(selected_avatar) is not str or selected_avatar not in COMPATIBLE:
        raise ValueError('현재 아바타 종류를 확인하세요.')
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
        raise ValueError('기록 크기를 초과했습니다.')
    try:
        draft = validate_runtime_record(json.loads(raw.decode('utf-8')))
    except (ValueError, UnicodeError, TypeError, KeyError) as exc:
        raise ValueError('저장된 아바타 환경 초안의 형식이 올바르지 않습니다.') from exc
    if draft.avatar != selected_avatar:
        raise ValueError('현재 아바타 종류와 다른 기록입니다. 재사용하지 않습니다.')
    return draft


def delete_runtime_environment(path: Path, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('명시적 삭제 확인이 필요합니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 삭제할 수 있습니다.')
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True
