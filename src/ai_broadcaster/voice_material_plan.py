"""Roadmap 042: offline, operator-authored *metadata only* voice-material draft.

No audio bytes, directory scan, file pickers, microphones or external APIs.
Does NOT authorize legal use, training, cloning, TTS, or broadcast.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import VOICES, data_dir
from .runtime_profile import _assert_safe_path
from .voice_rights_review import VoiceRightsReview, SOURCES_WITH_RECORDINGS

FILE_NAME = 'voice_material_draft.json'
SCHEMA_VERSION = 1
MAX_RECORD_BYTES = 8192
MAX_ITEMS = 20
MAX_NOTE = 180
MAX_LABEL = 48
MAX_SECONDS = 600


def _single_line(value: object, label: str, limit: int, *, empty: bool = False) -> str:
    if type(value) is not str or len(value) > limit or (not empty and not value.strip()):
        raise ValueError(f'{label}: 내용을 입력하고 {limit}자 이내로 작성하세요.')
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f'{label}: 줄바꿈·제어문자는 입력할 수 없습니다.')
    return value


@dataclass(frozen=True)
class MaterialItem:
    alias: str
    declared_seconds: int

    def __post_init__(self):
        _single_line(self.alias, '자료별칭', MAX_LABEL)
        # Do not encourage collection of identifiers, paths or URLs in a manifest.
        if any(c in self.alias for c in '/\\:@|') or '..' in self.alias:
            raise ValueError('자료별칭에는 파일 경로·주소·개인정보를 적지 마세요.')
        if type(self.declared_seconds) is not int or not 1 <= self.declared_seconds <= MAX_SECONDS:
            raise ValueError('예상 길이는 항목당 1~600초 정수로 적으세요.')


@dataclass(frozen=True)
class VoiceMaterialDraft:
    source: str
    items: tuple[MaterialItem, ...] = ()
    note: str = ''

    def __post_init__(self):
        if type(self.source) is not str or self.source not in VOICES.values():
            raise ValueError('지원하지 않는 목소리 확보 방식입니다.')
        if type(self.items) is not tuple or len(self.items) > MAX_ITEMS:
            raise ValueError(f'자료별칭 목록은 최대 {MAX_ITEMS}개입니다.')
        if any(type(item) is not MaterialItem for item in self.items):
            raise ValueError('자료별칭 항목 형식이 올바르지 않습니다.')
        if len({item.alias.strip().casefold() for item in self.items}) != len(self.items):
            raise ValueError('같은 자료별칭을 두 번 사용할 수 없습니다.')
        _single_line(self.note, '준비 메모', MAX_NOTE, empty=True)

    @property
    def total_declared_seconds(self) -> int:
        return sum(item.declared_seconds for item in self.items)

    def outline(self, rights: VoiceRightsReview | None = None) -> str:
        label = next(k for k, v in VOICES.items() if v == self.source)
        declared = ('같은 출처의 권리 체크 자체 신고 확인 (법적 진위 미검증)'
                    if rights is not None and rights.source == self.source and rights.checklist_complete
                    else '권리 체크 미확인 또는 출처 불일치 · 별도 검토 필요')
        lines = ['원본 042단계 · 승인된 음성 자료 준비표 초안 (메타데이터만)',
                 f'방송 설정의 음성 확보 방식: {label}',
                 f'운영자 기재 자료별칭: {len(self.items)}건 / 예상 총 길이: {self.total_declared_seconds}초',
                 f'41단계 자체 신고 참고: {declared}',
                 f'준비 상태: {"자료별칭 기재됨" if self.items and self.source in SOURCES_WITH_RECORDINGS else "자료별칭 또는 출처 미정"} · 실물/권리/품질/학습 승인 대기']
        lines.extend(f'{i}. {item.alias} · 운영자 예상 {item.declared_seconds}초'
                     for i, item in enumerate(self.items, 1))
        lines += [f'운영자 준비 메모: {self.note or "(없음)"}',
                  '※ 실제 음성 파일·폴더·파일명·주소·실명·계약서/동의서는 읽거나 보관하지 않습니다.',
                  '※ 입력 길이와 권리 기록은 운영자 진술이며 실제 자료의 존재/품질/이용권을 검증하지 않습니다.',
                  '※ 자료 준비 초안은 녹음·복제·학습·방송의 자동 승인이 아닙니다.']
        return '\n'.join(lines)


def parse_material_lines(text: str, source: str, note: str = '') -> VoiceMaterialDraft:
    if type(text) is not str or len(text) > 3000:
        raise ValueError('입력 목록이 너무 깁니다.')
    rows = [line.strip() for line in text.splitlines() if line.strip()]
    if len(rows) > MAX_ITEMS:
        raise ValueError(f'자료별칭은 최대 {MAX_ITEMS}개입니다.')
    items = []
    for row in rows:
        parts = row.split('|')
        if len(parts) != 2:
            raise ValueError('각 줄을 "자료별칭 | 예상초(정수)" 형식으로 작성하세요.')
        alias, seconds = (part.strip() for part in parts)
        if not seconds.isascii() or not seconds.isdecimal():
            raise ValueError('예상 길이는 아라비아 숫자로 된 정수 초를 입력하세요.')
        items.append(MaterialItem(alias, int(seconds)))
    return VoiceMaterialDraft(source, tuple(items), note)


def material_plan_path(directory: Path | None = None) -> Path:
    return (Path(directory) if directory is not None else data_dir()) / FILE_NAME


def validate_plan_record(obj: object) -> VoiceMaterialDraft:
    required = {'schema_version', 'kind', 'source', 'items', 'note',
                'audio_files_stored', 'training_authorized', 'broadcast_authorized'}
    if (type(obj) is not dict or set(obj) != required
            or type(obj['schema_version']) is not int or obj['schema_version'] != SCHEMA_VERSION
            or obj['kind'] != 'operator_metadata_only'
            or obj['audio_files_stored'] is not False
            or obj['training_authorized'] is not False
            or obj['broadcast_authorized'] is not False
            or type(obj['items']) is not list):
        raise ValueError('음성 자료 준비표 형식이 올바르지 않습니다.')
    items = []
    for entry in obj['items']:
        if type(entry) is not dict or set(entry) != {'alias', 'declared_seconds'}:
            raise ValueError('음성 자료별칭 항목 형식이 올바르지 않습니다.')
        items.append(MaterialItem(entry['alias'], entry['declared_seconds']))
    return VoiceMaterialDraft(obj['source'], tuple(items), obj['note'])


def save_material_plan(path: Path, plan: VoiceMaterialDraft, *, operator_confirmed: bool = False) -> Path:
    if operator_confirmed is not True:
        raise PermissionError('운영자 확인 없이 자료 준비표를 저장하지 않습니다.')
    if type(plan) is not VoiceMaterialDraft or not plan.items:
        raise ValueError('최소 1건의 자료별칭을 입력해야 저장할 수 있습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일에만 저장할 수 있습니다.')
    payload = {'schema_version': SCHEMA_VERSION, 'kind': 'operator_metadata_only',
               'source': plan.source, 'items': [vars(item) for item in plan.items],
               'note': plan.note, 'audio_files_stored': False,
               'training_authorized': False, 'broadcast_authorized': False}
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
    if len(raw) > MAX_RECORD_BYTES:
        raise ValueError('준비표가 너무 큽니다.')
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(target)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.voice-material-',
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


def load_material_plan(path: Path) -> VoiceMaterialDraft | None:
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 불러올 수 있습니다.')
    try:
        with target.open('rb') as fh:
            raw = fh.read(MAX_RECORD_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(raw) > MAX_RECORD_BYTES:
        raise ValueError('준비표 파일이 너무 큽니다.')
    try:
        return validate_plan_record(json.loads(raw.decode('utf-8')))
    except (ValueError, UnicodeError) as exc:
        raise ValueError('음성 준비표 내용을 읽을 수 없습니다.') from exc


def delete_material_plan(path: Path, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('운영자 확인 없이 준비표를 삭제하지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 삭제할 수 있습니다.')
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True
