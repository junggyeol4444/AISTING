"""Roadmap 041: operator-entered voice rights checklist, not legal verification.

Strictly offline; does not inspect devices, open audio, record sound, perform
voice cloning, authorize model training, or change the selected voice source.
Nothing is loaded or saved until an explicit UI action.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import VOICES, data_dir
from .runtime_profile import _assert_safe_path

FILE_NAME = 'voice_rights_operator_review.json'
SCHEMA_VERSION = 1
MAX_FILE_BYTES = 4096
MAX_NOTE_LENGTH = 240
SOURCES_WITH_RECORDINGS = frozenset({'own_recording', 'consented_recording', 'licensed_recording'})


@dataclass(frozen=True)
class VoiceRightsReview:
    source: str = 'undecided'
    rights_checked: bool = False
    training_permission_checked: bool = False
    broadcast_permission_checked: bool = False
    evidence_reviewed: bool = False
    note: str = ''

    def __post_init__(self):
        if type(self.source) is not str or self.source not in VOICES.values():
            raise ValueError('지원하지 않는 음성 확보 방식입니다.')
        for value in (self.rights_checked, self.training_permission_checked,
                      self.broadcast_permission_checked, self.evidence_reviewed):
            if type(value) is not bool:
                raise ValueError('권리 확인 항목은 명시적으로 선택한 참/거짓 값이어야 합니다.')
        if (type(self.note) is not str or len(self.note) > MAX_NOTE_LENGTH
                or any(ord(c) < 32 or ord(c) == 127 for c in self.note)):
            raise ValueError(f'참고 메모는 한 줄 {MAX_NOTE_LENGTH}자 이하로 입력하세요.')

    @property
    def checklist_complete(self) -> bool:
        """Only operator-declared prerequisites for *future review*, never an approval."""
        return (self.source in SOURCES_WITH_RECORDINGS
                and self.rights_checked and self.training_permission_checked
                and self.broadcast_permission_checked and self.evidence_reviewed)

    def describe(self) -> str:
        label = next(k for k, v in VOICES.items() if v == self.source)
        status = '권리 확인 항목 자체 신고 완료 · 실제 음성 사용 승인 대기' if self.checklist_complete else '권리 확인 항목 미완료 · 사용·학습 승인 대기'
        yesno = lambda value: '운영자 확인' if value else '미확인'
        return ('원본 041단계 · 음성 자료 권리·동의 자체 점검 (오프라인)\n'
                f'현재 선택한 음성 확보 방식: {label}\n'
                f'음성 자료를 사용할 권리: {yesno(self.rights_checked)}\n'
                f'AI 음성 학습/복제에 대한 명시적 허락: {yesno(self.training_permission_checked)}\n'
                f'방송 이용에 대한 명시적 허락: {yesno(self.broadcast_permission_checked)}\n'
                f'동의·라이선스 자료 직접 확인: {yesno(self.evidence_reviewed)}\n'
                f'추가 메모(개인정보·원본 파일 경로 입력 금지): {self.note or "(없음)"}\n'
                f'상태: {status}\n'
                '※ 체크는 운영자의 진술일 뿐 법적 권리·라이선스의 진위 확인이 아닙니다.\n'
                '※ Windows 기본 설치 음성은 학습용 녹음 자료로 간주하지 않습니다. 별도 사용 약관 확인이 필요합니다.\n'
                '※ 이 기능은 음성 파일 수집·재생·학습·복제·실방송·설치·PC 조사 및 최종 승인을 하지 않습니다.\n'
                '※ 저장 기록은 다른 음성으로 전환한 경우 사용할 수 없으며, 수동 검토가 필요합니다.')


def rights_review_path(directory: Path | None = None) -> Path:
    return (Path(directory) if directory is not None else data_dir()) / FILE_NAME


def validate_review_record(obj: object) -> VoiceRightsReview:
    if (type(obj) is not dict or set(obj) != {
            'schema_version', 'source_tag', 'voice_source', 'rights_checked',
            'training_permission_checked', 'broadcast_permission_checked',
            'evidence_reviewed', 'note', 'training_authorized', 'streaming_authorized'
    } or type(obj['schema_version']) is not int or obj['schema_version'] != SCHEMA_VERSION
        or obj['source_tag'] != 'operator_self_report'
        or obj['training_authorized'] is not False
        or obj['streaming_authorized'] is not False):
        raise ValueError('운영자 음성 권리 기록 형식이 올바르지 않습니다.')
    return VoiceRightsReview(obj['voice_source'], obj['rights_checked'],
                             obj['training_permission_checked'],
                             obj['broadcast_permission_checked'],
                             obj['evidence_reviewed'], obj['note'])


def save_rights_review(path: Path, review: VoiceRightsReview, *, operator_confirmed: bool = False) -> Path:
    if operator_confirmed is not True:
        raise PermissionError('운영자가 저장을 명시적으로 확인해야 합니다.')
    if not isinstance(review, VoiceRightsReview):
        raise ValueError('음성 권리 점검값이 올바르지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일에만 저장할 수 있습니다.')
    payload = {
        'schema_version': SCHEMA_VERSION, 'source_tag': 'operator_self_report',
        'voice_source': review.source, 'rights_checked': review.rights_checked,
        'training_permission_checked': review.training_permission_checked,
        'broadcast_permission_checked': review.broadcast_permission_checked,
        'evidence_reviewed': review.evidence_reviewed, 'note': review.note,
        'training_authorized': False, 'streaming_authorized': False,
    }
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('권리 확인 기록 크기가 허용 범위를 초과했습니다.')
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(target)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.voice-rights-',
                                         suffix='.tmp', delete=False) as fh:
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


def load_rights_review(path: Path) -> VoiceRightsReview | None:
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 불러올 수 있습니다.')
    try:
        with target.open('rb') as fh:
            raw = fh.read(MAX_FILE_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('권리 확인 기록 크기가 허용 범위를 초과했습니다.')
    try:
        obj = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeError) as exc:
        raise ValueError('권리 확인 기록을 읽을 수 없습니다.') from exc
    return validate_review_record(obj)


def delete_rights_review(path: Path, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('운영자 확인 없이 기록을 삭제하지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 삭제할 수 있습니다.')
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True
