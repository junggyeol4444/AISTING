"""Original 051: operator-authored avatar provenance *draft*, never model access.

No file dialogs, scanning, model reading, image processing, licenses inferred,
rendering engines, external services, automatic selection or broadcast authorization.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import AVATARS, data_dir
from .runtime_profile import _assert_safe_path

FILE_NAME = 'avatar_preparation_draft.json'
SCHEMA_VERSION = 1
MAX_BYTES = 4096
MAX_ALIAS = 48
MAX_NOTE = 200
ORIGINS = {
    '미정': 'undecided',
    '직접 제작': 'self_created',
    '제작 의뢰': 'commissioned',
    '라이선스 확보': 'licensed',
}


def _text(value: object, title: str, maximum: int, *, required: bool = False) -> str:
    if type(value) is not str or len(value) > maximum or (required and not value.strip()):
        raise ValueError(f'{title}: {maximum}자 이내로 입력하세요.')
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f'{title}: 줄바꿈·제어문자는 허용하지 않습니다.')
    return value


@dataclass(frozen=True)
class AvatarPreparation:
    avatar: str
    origin: str = 'undecided'
    alias: str = ''
    rights_reviewed: bool = False
    display_permission_reviewed: bool = False
    evidence_reviewed: bool = False
    note: str = ''

    def __post_init__(self) -> None:
        if type(self.avatar) is not str or self.avatar not in AVATARS.values():
            raise ValueError('아바타 형태는 미정/2D/3D 중 선택하세요.')
        if type(self.origin) is not str or self.origin not in ORIGINS.values():
            raise ValueError('자료 출처가 올바르지 않습니다.')
        _text(self.alias, '모델 별칭', MAX_ALIAS)
        # Model metadata must never become a file path or URL or an identifier.
        if any(ch in self.alias for ch in '/\\:@|') or '..' in self.alias:
            raise ValueError('별칭에는 파일 경로·주소·개인정보를 입력하지 마세요.')
        _text(self.note, '준비 메모', MAX_NOTE)
        for flag in (self.rights_reviewed, self.display_permission_reviewed, self.evidence_reviewed):
            if type(flag) is not bool:
                raise ValueError('권리 체크는 참/거짓이어야 합니다.')
        if self.avatar == 'undecided' and (self.alias or self.origin != 'undecided' or
            self.rights_reviewed or self.display_permission_reviewed or self.evidence_reviewed):
            raise ValueError('아바타 미정 상태에서 모델 확정 또는 권리 확인을 적용하지 않습니다.')

    @property
    def checklist_ready(self) -> bool:
        return (self.avatar in ('2d', '3d') and bool(self.alias.strip())
                and self.origin != 'undecided' and self.rights_reviewed
                and self.display_permission_reviewed and self.evidence_reviewed)

    def describe(self) -> str:
        label = next(label for label, code in AVATARS.items() if code == self.avatar)
        origin = next(label for label, code in ORIGINS.items() if code == self.origin)
        checked = lambda value: '운영자 체크' if value else '미확인'
        return ('원본 051단계 · 승인된 아바타 준비 (모델 파일 없는 수동 목록)\n'
                f'현재 아바타 선택: {label}\n자료 출처(자체 신고): {origin}\n'
                f'모델 별칭(경로 아님): {self.alias or "(미입력)"}\n'
                f'모델 사용 권리 확인: {checked(self.rights_reviewed)}\n'
                f'방송·화면 표시 허용 범위 확인: {checked(self.display_permission_reviewed)}\n'
                f'라이선스/동의 증빙 직접 검토: {checked(self.evidence_reviewed)}\n'
                f'메모: {self.note or "(없음)"}\n'
                '상태: ' + ('사용자 자체 신고 체크 완료 · 실제 사용 승인 대기' if self.checklist_ready
                          else '준비 초안 · 권리/모델 확인 대기') + '\n'
                '※ 체크는 운영자 진술일 뿐 실제 라이선스의 법적 진위를 검증하지 않습니다.\n'
                '※ 모델 파일 열기·수집·복사·학습·다운로드·렌더러 실행·방송 없음.\n'
                '※ 2D/3D 모델 구동, 설치, 사용자 PC 정보 조사, 실기기 검증, 최종 승인은 대기입니다.')


def preparation_path(directory: Path | None = None) -> Path:
    return (Path(directory) if directory is not None else data_dir()) / FILE_NAME


def _payload(draft: AvatarPreparation) -> dict:
    return {
        'schema_version': SCHEMA_VERSION, 'kind': 'operator_avatar_metadata_only',
        'avatar': draft.avatar, 'origin': draft.origin, 'alias': draft.alias,
        'rights_reviewed': draft.rights_reviewed,
        'display_permission_reviewed': draft.display_permission_reviewed,
        'evidence_reviewed': draft.evidence_reviewed, 'note': draft.note,
        'model_file_accessed': False, 'license_verified': False,
        'rendering_authorized': False, 'broadcast_authorized': False,
        'pc_inspected': False,
    }


def validate_preparation_record(obj: object) -> AvatarPreparation:
    keys = set(_payload(AvatarPreparation('undecided')))
    if (type(obj) is not dict or set(obj) != keys
            or type(obj['schema_version']) is not int or obj['schema_version'] != SCHEMA_VERSION
            or obj['kind'] != 'operator_avatar_metadata_only'
            or any(obj[field] is not False for field in (
                'model_file_accessed', 'license_verified', 'rendering_authorized',
                'broadcast_authorized', 'pc_inspected'))):
        raise ValueError('아바타 준비 기록의 형식 또는 권한 상태가 올바르지 않습니다.')
    return AvatarPreparation(obj['avatar'], obj['origin'], obj['alias'],
                             obj['rights_reviewed'], obj['display_permission_reviewed'],
                             obj['evidence_reviewed'], obj['note'])


def save_preparation(path: Path, draft: AvatarPreparation, *, operator_confirmed: bool = False) -> Path:
    if operator_confirmed is not True:
        raise PermissionError('운영자 확인 없이 아바타 자료 초안을 저장하지 않습니다.')
    if type(draft) is not AvatarPreparation:
        raise ValueError('아바타 준비 초안 형식이 올바르지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 저장할 수 있습니다.')
    raw = json.dumps(_payload(draft), ensure_ascii=False, indent=2).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValueError('저장 내용이 제한 크기를 넘었습니다.')
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(target)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.avatar-prep-', suffix='.tmp', delete=False) as fh:
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


def load_preparation(path: Path, *, selected_avatar: str) -> AvatarPreparation | None:
    if type(selected_avatar) is not str or selected_avatar not in AVATARS.values():
        raise ValueError('현재 아바타 선택값이 올바르지 않습니다.')
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
        raise ValueError('아바타 준비 기록 크기를 초과했습니다.')
    try:
        draft = validate_preparation_record(json.loads(raw.decode('utf-8')))
    except (ValueError, UnicodeError, TypeError, KeyError) as exc:
        raise ValueError('저장된 아바타 준비 기록이 올바르지 않습니다.') from exc
    if draft.avatar != selected_avatar:
        raise ValueError('현재 선택한 아바타 종류와 저장된 기록이 다릅니다. 재사용 차단.')
    return draft


def delete_preparation(path: Path, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('운영자 확인 없이 아바타 준비 기록을 삭제하지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 삭제할 수 있습니다.')
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True
