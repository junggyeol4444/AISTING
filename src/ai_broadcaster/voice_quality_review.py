"""Roadmap 043: operator-entered quality observations, never audio analysis.

Records are pinned to the exact manual stage-042 manifest. No audio, device,
network, model, or training access; even all-positive observations are NOT proof
of sample quality or permission to train/broadcast.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir
from .runtime_profile import _assert_safe_path
from .voice_material_plan import VoiceMaterialDraft, MAX_ITEMS

FILE_NAME = 'voice_quality_operator_review.json'
SCHEMA_VERSION = 1
MAX_FILE_BYTES = 12288
MAX_NOTE_LENGTH = 160
CRITERIA = ('background_noise', 'clipping', 'intelligibility', 'volume_consistency')
ASSESSMENTS = ('unreviewed', 'operator_ok', 'needs_rework')
ASSESSMENT_LABELS = {'unreviewed': '미평가', 'operator_ok': '운영자 양호 기재',
                     'needs_rework': '보완 필요'}
CRITERION_LABELS = {'background_noise': '배경 잡음', 'clipping': '잘림·왜곡',
                    'intelligibility': '발화 명료도', 'volume_consistency': '음량 일관성'}


def manifest_digest(plan: VoiceMaterialDraft) -> str:
    if type(plan) is not VoiceMaterialDraft:
        raise ValueError('42단계 준비표가 올바르지 않습니다.')
    raw = json.dumps({'source': plan.source,
                      'items': [[i.alias, i.declared_seconds] for i in plan.items]},
                     ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _safe_note(note: object) -> str:
    if type(note) is not str or len(note) > MAX_NOTE_LENGTH or any(ord(c) < 32 or ord(c) == 127 for c in note):
        raise ValueError(f'평가 메모는 한 줄 {MAX_NOTE_LENGTH}자 이내로 입력하세요.')
    if any(c in note for c in '/\\@|') or '..' in note or '://' in note:
        raise ValueError('평가 메모에 파일 경로, 연락처, URL을 기록하지 마세요.')
    return note


@dataclass(frozen=True)
class QualityItem:
    alias: str
    assessments: tuple[str, str, str, str] = ('unreviewed',) * 4
    note: str = ''

    def __post_init__(self):
        if type(self.alias) is not str or not self.alias.strip() or len(self.alias) > 48:
            raise ValueError('평가 자료별칭이 올바르지 않습니다.')
        if type(self.assessments) is not tuple or len(self.assessments) != len(CRITERIA) or any(
                type(v) is not str or v not in ASSESSMENTS for v in self.assessments):
            raise ValueError('품질 평가 항목은 미평가/운영자 양호 기재/보완 필요 중에서 선택하세요.')
        _safe_note(self.note)

    @property
    def review_state(self) -> str:
        if 'needs_rework' in self.assessments:
            return '보완 필요 (운영자 기재)'
        if 'unreviewed' in self.assessments:
            return '미평가 항목 남음'
        return '4개 항목 모두 운영자 양호 기재 · 실제 검증 아님'


@dataclass(frozen=True)
class QualityReview:
    source: str
    plan_digest: str
    items: tuple[QualityItem, ...]

    def __post_init__(self):
        if type(self.source) is not str or not self.source:
            raise ValueError('음성 출처가 올바르지 않습니다.')
        if (type(self.plan_digest) is not str or len(self.plan_digest) != 64
                or any(c not in '0123456789abcdef' for c in self.plan_digest)):
            raise ValueError('준비표 연결 코드가 올바르지 않습니다.')
        if type(self.items) is not tuple or len(self.items) > MAX_ITEMS or any(type(v) is not QualityItem for v in self.items):
            raise ValueError('품질 검토 목록이 올바르지 않습니다.')
        if len({i.alias.casefold() for i in self.items}) != len(self.items):
            raise ValueError('중복된 품질 검토 항목이 있습니다.')

    def matches(self, plan: VoiceMaterialDraft) -> bool:
        return (self.source == plan.source and self.plan_digest == manifest_digest(plan)
                and tuple(i.alias for i in self.items) == tuple(i.alias for i in plan.items))

    def summarize(self, plan: VoiceMaterialDraft) -> str:
        if not self.matches(plan):
            raise ValueError('42단계 준비표가 변경되어 기존 품질 검토를 사용할 수 없습니다.')
        counts = {state: sum(state in item.assessments for item in self.items)
                  for state in ASSESSMENTS}
        lines = ['원본 043단계 · 수동 음성 자료 품질 관찰표 (실제 음성 분석 아님)',
                 f'운영자 메타데이터 목록: {len(self.items)}건 / 준비표 연결 검증 완료',
                 f'미평가 포함 {counts["unreviewed"]}건 · 보완 필요 포함 {counts["needs_rework"]}건',
                 '※ 양호로 표시해도 실제 파일 품질·권리·동의가 검증되거나 학습/방송이 허용되지 않습니다.']
        for number, item in enumerate(self.items, 1):
            lines.append(f'{number}. {item.alias} — {item.review_state}')
            for criterion, assessment in zip(CRITERIA, item.assessments):
                lines.append(f'   {CRITERION_LABELS[criterion]}: {ASSESSMENT_LABELS[assessment]}')
            if item.note:
                lines.append(f'   운영자 메모: {item.note}')
        lines.append('※ 원본 파일·마이크·장치·OS 정보에 접근하지 않았습니다. 자동 승인 없음.')
        return '\n'.join(lines)


def blank_quality_review(plan: VoiceMaterialDraft) -> QualityReview:
    return QualityReview(plan.source, manifest_digest(plan),
                         tuple(QualityItem(i.alias) for i in plan.items))


def set_quality_item(review: QualityReview, plan: VoiceMaterialDraft, alias: str,
                     values: tuple[str, str, str, str], note: str = '') -> QualityReview:
    if not review.matches(plan):
        raise ValueError('음성 자료 준비표가 변경되었습니다. 평가표를 새로 시작하세요.')
    if alias not in (i.alias for i in review.items):
        raise ValueError('준비표에 없는 자료별칭은 평가할 수 없습니다.')
    replacement = QualityItem(alias, values, note)
    return QualityReview(review.source, review.plan_digest,
                         tuple(replacement if i.alias == alias else i for i in review.items))


def quality_review_path(directory: Path | None = None) -> Path:
    return (Path(directory) if directory is not None else data_dir()) / FILE_NAME


def validate_quality_record(data: object) -> QualityReview:
    keys = {'schema_version', 'kind', 'source', 'plan_digest', 'items',
            'audio_analyzed', 'training_authorized', 'broadcast_authorized'}
    if (type(data) is not dict or set(data) != keys or
        type(data['schema_version']) is not int or data['schema_version'] != SCHEMA_VERSION or
        data['kind'] != 'operator_manual_quality_notes' or
        data['audio_analyzed'] is not False or data['training_authorized'] is not False or
        data['broadcast_authorized'] is not False or type(data['items']) is not list):
        raise ValueError('수동 음성 품질 기록 형식이 잘못되었습니다.')
    items = []
    for item in data['items']:
        if type(item) is not dict or set(item) != {'alias', 'assessments', 'note'} or type(item['assessments']) is not list:
            raise ValueError('품질 항목 형식이 잘못되었습니다.')
        items.append(QualityItem(item['alias'], tuple(item['assessments']), item['note']))
    return QualityReview(data['source'], data['plan_digest'], tuple(items))


def save_quality_review(path: Path, review: QualityReview, plan: VoiceMaterialDraft, *,
                        operator_confirmed: bool = False) -> Path:
    if operator_confirmed is not True:
        raise PermissionError('운영자 확인 없이 품질 관찰표를 저장하지 않습니다.')
    if type(review) is not QualityReview or not review.matches(plan) or not review.items:
        raise ValueError('일치하는 비어 있지 않은 음성 자료 준비표가 필요합니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 저장할 수 있습니다.')
    data = {'schema_version': SCHEMA_VERSION, 'kind': 'operator_manual_quality_notes',
            'source': review.source, 'plan_digest': review.plan_digest,
            'items': [{'alias': i.alias, 'assessments': list(i.assessments), 'note': i.note}
                      for i in review.items],
            'audio_analyzed': False, 'training_authorized': False, 'broadcast_authorized': False}
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('품질 기록이 허용 크기를 넘었습니다.')
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(target)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.voice-quality-',
                                         suffix='.tmp', delete=False) as fh:
            temp = Path(fh.name)
            fh.write(raw)
            fh.flush()
            os.fsync(fh.fileno())
        _assert_safe_path(target)
        os.replace(temp, target)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return target


def load_quality_review(path: Path, plan: VoiceMaterialDraft) -> QualityReview | None:
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 읽을 수 있습니다.')
    try:
        with target.open('rb') as fh:
            raw = fh.read(MAX_FILE_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('품질 기록이 허용 크기를 넘었습니다.')
    try:
        review = validate_quality_record(json.loads(raw.decode('utf-8')))
    except (UnicodeError, ValueError) as exc:
        raise ValueError('품질 기록을 읽을 수 없습니다.') from exc
    if not review.matches(plan):
        raise ValueError('준비표와 품질 기록의 음성 출처/별칭/예상 길이가 다릅니다. 불러오기 차단.')
    return review


def delete_quality_review(path: Path, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('운영자 확인 없이 품질 기록을 삭제하지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 삭제할 수 있습니다.')
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True
