"""Stage 048: operator-authored emotion-expression test notes, without audio access.

No automatic emotion inference, synthesis, playback, OS device inspection or network I/O.
The user's desired emotion and subjective impression are *notes*, never model output.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from .offline_settings import data_dir
from .runtime_profile import _assert_safe_path
from .pronunciation_review import context_digest, parse_phrases, _safe_line

FILE_NAME = 'emotion_expression_operator_notes.json'
MAX_FILE_BYTES = 20000
MAX_INTENT = 60
MAX_NOTE = 160
STATES = ('unreviewed', 'operator_ok', 'needs_adjustment')
LABELS = {'unreviewed': '미평가', 'operator_ok': '운영자가 적절하다고 기재',
          'needs_adjustment': '수정 필요'}


@dataclass(frozen=True)
class EmotionItem:
    phrase: str
    intended_emotion: str = ''
    verdict: str = 'unreviewed'
    note: str = ''

    def __post_init__(self):
        _safe_line(self.phrase, 160)
        if type(self.intended_emotion) is not str or (self.intended_emotion and
                _safe_line(self.intended_emotion, MAX_INTENT) != self.intended_emotion):
            raise ValueError('감정 방향은 60자 이내 일반 텍스트만 허용합니다.')
        if type(self.verdict) is not str or self.verdict not in STATES:
            raise ValueError('감정 표현 평가는 지정된 선택지만 허용합니다.')
        if type(self.note) is not str or (self.note and _safe_line(self.note, MAX_NOTE) != self.note):
            raise ValueError('메모는 160자 이내 일반 텍스트만 허용합니다.')
        if self.verdict != 'unreviewed' and not self.intended_emotion:
            raise ValueError('원하는 감정 방향을 적기 전에는 평가할 수 없습니다.')


@dataclass(frozen=True)
class EmotionReview:
    context: str
    items: tuple[EmotionItem, ...]

    def __post_init__(self):
        if (type(self.context) is not str or len(self.context) != 64 or
                any(c not in '0123456789abcdef' for c in self.context)):
            raise ValueError('목소리 연결 정보가 올바르지 않습니다.')
        if type(self.items) is not tuple or not 1 <= len(self.items) <= 12 or any(
                type(item) is not EmotionItem for item in self.items):
            raise ValueError('시험 문장은 1~12건이어야 합니다.')

    def matches(self, source: str, profile: dict, phrases: tuple[str, ...]) -> bool:
        return self.context == context_digest(source, profile) and tuple(
            item.phrase for item in self.items) == tuple(phrases)

    def describe(self) -> str:
        lines = ['원본 048단계 · 감정 표현 운영자 수동 시험표',
                 '실제 음성 재생·감정 분석·모델 연결 없음',
                 '※ 적절함 기재는 음성 품질 검증, 학습 또는 방송 승인이 아닙니다.']
        for i, item in enumerate(self.items, 1):
            lines.append(f'{i}. {item.phrase}')
            lines.append(f'   의도한 감정: {item.intended_emotion or "(운영자 미입력)"} / 평가: {LABELS[item.verdict]}')
            if item.note:
                lines.append(f'   수정 메모: {item.note}')
        lines.append('사용자가 확인하기 전에는 저장하지 않습니다.')
        return '\n'.join(lines)


def blank_review(source: str, profile: dict, phrases: tuple[str, ...]) -> EmotionReview:
    validated = parse_phrases('\n'.join(phrases))
    return EmotionReview(context_digest(source, profile), tuple(EmotionItem(v) for v in validated))


def update_item(review: EmotionReview, index: int, intent: str, verdict: str,
                note: str = '') -> EmotionReview:
    if type(review) is not EmotionReview or type(index) is not int or not 0 <= index < len(review.items):
        raise ValueError('평가 문장 번호가 올바르지 않습니다.')
    item = EmotionItem(review.items[index].phrase, intent, verdict, note)
    return replace(review, items=tuple(item if i == index else old for i, old in enumerate(review.items)))


def review_path(directory: Path | None = None) -> Path:
    return (Path(directory) if directory is not None else data_dir()) / FILE_NAME


def _serialize(review: EmotionReview) -> dict:
    return {'schema_version': 1, 'kind': 'operator_emotion_expression_notes',
            'context': review.context,
            'items': [{'phrase': item.phrase, 'intended_emotion': item.intended_emotion,
                       'verdict': item.verdict, 'note': item.note} for item in review.items],
            'audio_analyzed': False, 'audio_played': False,
            'emotion_generated': False, 'training_authorized': False,
            'broadcast_authorized': False}


def _deserialize(data: object) -> EmotionReview:
    required = {'schema_version', 'kind', 'context', 'items', 'audio_analyzed',
                'audio_played', 'emotion_generated', 'training_authorized', 'broadcast_authorized'}
    if (type(data) is not dict or set(data) != required or type(data['schema_version']) is not int
            or data['schema_version'] != 1 or data['kind'] != 'operator_emotion_expression_notes'
            or type(data['items']) is not list or any(data[k] is not False for k in (
                'audio_analyzed', 'audio_played', 'emotion_generated',
                'training_authorized', 'broadcast_authorized'))):
        raise ValueError('감정 표현 기록 형식이 잘못되었습니다.')
    items = []
    for entry in data['items']:
        if type(entry) is not dict or set(entry) != {'phrase', 'intended_emotion', 'verdict', 'note'}:
            raise ValueError('감정 표현 문장 형식이 잘못되었습니다.')
        items.append(EmotionItem(**entry))
    return EmotionReview(data['context'], tuple(items))


def save_review(path: Path, review: EmotionReview, source: str, profile: dict,
                phrases: tuple[str, ...], *, operator_confirmed: bool = False) -> Path:
    if operator_confirmed is not True:
        raise PermissionError('사용자 확인 없이 감정 표현 기록을 저장하지 않습니다.')
    if type(review) is not EmotionReview or not review.matches(source, profile, phrases):
        raise ValueError('설정이나 문장이 변경되어 기록 저장을 차단합니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일에만 기록을 저장할 수 있습니다.')
    raw = json.dumps(_serialize(review), ensure_ascii=False, indent=2).encode('utf-8')
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('감정 표현 기록이 너무 큽니다.')
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(target)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.emotion-', suffix='.tmp', delete=False) as f:
            tmp = Path(f.name)
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        _assert_safe_path(target)
        os.replace(tmp, target)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    return target


def load_review(path: Path, source: str, profile: dict,
                phrases: tuple[str, ...]) -> EmotionReview | None:
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 읽을 수 있습니다.')
    try:
        with target.open('rb') as f:
            raw = f.read(MAX_FILE_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('감정 표현 파일이 너무 큽니다.')
    try:
        review = _deserialize(json.loads(raw.decode('utf-8')))
    except (ValueError, TypeError, KeyError, UnicodeError) as exc:
        raise ValueError('감정 표현 기록을 읽을 수 없습니다.') from exc
    if not review.matches(source, profile, phrases):
        raise ValueError('목소리 설정 또는 문장이 달라 이전 기록을 사용할 수 없습니다.')
    return review


def delete_review(path: Path, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('사용자 확인 전에는 삭제하지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 삭제할 수 있습니다.')
    try:
        target.unlink()
        return True
    except FileNotFoundError:
        return False
