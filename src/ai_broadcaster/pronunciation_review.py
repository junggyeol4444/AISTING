"""Original roadmap 047: operator-entered pronunciation / intonation observations.

No sound is played, recorded, opened or analyzed; even positive entries never
constitute a technical pronunciation or speech-quality pass. No background I/O.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import VOICES, data_dir, validate_voice_profile
from .runtime_profile import _assert_safe_path

FILE_NAME = 'pronunciation_intonation_operator_notes.json'
MAX_FILE_BYTES = 16000
MAX_LINES = 12
MAX_PHRASE = 160
MAX_NOTE = 160
STATES = ('unreviewed', 'operator_ok', 'needs_adjustment')
LABELS = {'unreviewed': '미평가', 'operator_ok': '운영자가 적절하다고 기재',
          'needs_adjustment': '수정 필요'}


def _safe_line(text: str, length: int) -> str:
    if (type(text) is not str or not 1 <= len(text.strip()) <= length
            or any(ord(c) < 32 or ord(c) == 127 for c in text)
            or any(token in text for token in ('://', '@', '\\', '|', '..'))
            or '/' in text):
        raise ValueError('문장/메모는 한 줄의 일반 텍스트로 입력하세요. 경로·URL·연락처는 제외하세요.')
    return text.strip()


def context_digest(source: str, profile: dict) -> str:
    if source not in VOICES.values() or source == 'undecided':
        raise ValueError('목소리 확보 방식을 먼저 선택하세요.')
    p = validate_voice_profile(profile)
    # OS enumeration is never performed. The saved/manual name may be empty;
    # an empty Windows voice means the operator has not selected one yet.
    if source == 'windows_system' and not p['installed_voice_name']:
        raise ValueError('Windows 목소리 이름을 먼저 직접 선택하세요. 자동 조회하지 않습니다.')
    data = {'source': source,
            'voice': p['installed_voice_name'] if source == 'windows_system' else '(미연결 음성)',
            'rate': p['rate'] if source == 'windows_system' else None,
            'volume': p['volume'] if source == 'windows_system' else None}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class PronunciationItem:
    phrase: str
    pronunciation: str = 'unreviewed'
    intonation: str = 'unreviewed'
    note: str = ''

    def __post_init__(self):
        _safe_line(self.phrase, MAX_PHRASE)
        if self.pronunciation not in STATES or self.intonation not in STATES:
            raise ValueError('발음·억양 평가는 지정된 선택지만 허용합니다.')
        if self.note:
            _safe_line(self.note, MAX_NOTE)
        elif type(self.note) is not str:
            raise ValueError('메모 형식이 올바르지 않습니다.')


@dataclass(frozen=True)
class PronunciationReview:
    context: str
    items: tuple[PronunciationItem, ...]

    def __post_init__(self):
        if type(self.context) is not str or len(self.context) != 64 or any(c not in '0123456789abcdef' for c in self.context):
            raise ValueError('목소리 연결 정보가 올바르지 않습니다.')
        if type(self.items) is not tuple or not 1 <= len(self.items) <= MAX_LINES or any(type(i) is not PronunciationItem for i in self.items):
            raise ValueError('평가표는 1~12문장이 필요합니다.')

    def matches(self, source: str, profile: dict, phrases: tuple[str, ...]) -> bool:
        return self.context == context_digest(source, profile) and tuple(i.phrase for i in self.items) == phrases

    def describe(self) -> str:
        lines = ['원본 047단계 · 발음/억양 수동 관찰표 · 실제 음성 재생/분석 없음',
                 f'문장 {len(self.items)}건 · 운영자 메모 초안',
                 '※ 운영자 양호 기재는 실제 음성 품질 보증/승인/재생 테스트 합격이 아닙니다.']
        for i, item in enumerate(self.items, 1):
            lines += [f'{i}. {item.phrase}', f'   발음: {LABELS[item.pronunciation]} / 억양: {LABELS[item.intonation]}']
            if item.note:
                lines.append(f'   메모: {item.note}')
        lines.append('※ 사용자 확인 없는 자동 저장·음성 수집·실제 학습·송출 없음')
        return '\n'.join(lines)


def parse_phrases(text: str) -> tuple[str, ...]:
    if type(text) is not str or len(text) > 2400:
        raise ValueError('시험 문장이 너무 깁니다.')
    lines = text.splitlines()
    if not 1 <= len(lines) <= MAX_LINES:
        raise ValueError('한 줄에 문장 1개씩, 최대 12개를 입력하세요.')
    return tuple(_safe_line(line, MAX_PHRASE) for line in lines)


def blank_review(source: str, profile: dict, phrases: tuple[str, ...]) -> PronunciationReview:
    validated = parse_phrases('\n'.join(phrases))
    return PronunciationReview(context_digest(source, profile), tuple(PronunciationItem(v) for v in validated))


def update_item(review: PronunciationReview, index: int, pronunciation: str, intonation: str,
                note: str = '') -> PronunciationReview:
    if type(review) is not PronunciationReview or type(index) is not int or not 0 <= index < len(review.items):
        raise ValueError('평가 문장 번호가 올바르지 않습니다.')
    updated = PronunciationItem(review.items[index].phrase, pronunciation, intonation, note)
    return PronunciationReview(review.context,
                               tuple(updated if j == index else v for j, v in enumerate(review.items)))


def review_path(directory: Path | None = None) -> Path:
    return (Path(directory) if directory is not None else data_dir()) / FILE_NAME


def _serialize(review: PronunciationReview) -> dict:
    return {'schema_version': 1, 'kind': 'operator_pronunciation_intonation_notes',
            'context': review.context,
            'items': [dict(phrase=i.phrase, pronunciation=i.pronunciation,
                           intonation=i.intonation, note=i.note) for i in review.items],
            'audio_analyzed': False, 'audio_played': False,
            'training_authorized': False, 'broadcast_authorized': False}


def _deserialize(data: object) -> PronunciationReview:
    if (type(data) is not dict or set(data) != set(_serialize(blank_review(
            'own_recording', {'installed_voice_name': '', 'rate': 0, 'volume': 85}, ('예시',))))
            or type(data.get('schema_version')) is not int or data['schema_version'] != 1
            or data['kind'] != 'operator_pronunciation_intonation_notes'
            or any(data[name] is not False for name in ('audio_analyzed', 'audio_played', 'training_authorized', 'broadcast_authorized'))
            or type(data['items']) is not list):
        raise ValueError('발음·억양 기록 형식이 잘못되었습니다.')
    items = []
    for item in data['items']:
        if type(item) is not dict or set(item) != {'phrase', 'pronunciation', 'intonation', 'note'}:
            raise ValueError('발음·억양 문장 형식이 잘못되었습니다.')
        items.append(PronunciationItem(**item))
    return PronunciationReview(data['context'], tuple(items))


def save_review(path: Path, review: PronunciationReview, source: str, profile: dict,
                phrases: tuple[str, ...], *, operator_confirmed: bool = False) -> Path:
    if operator_confirmed is not True:
        raise PermissionError('사용자가 확인하기 전에는 평가표를 저장하지 않습니다.')
    if type(review) is not PronunciationReview or not review.matches(source, profile, phrases):
        raise ValueError('음성 설정이나 시험 문장이 변경되어 이전 평가를 저장하지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 저장할 수 있습니다.')
    raw = json.dumps(_serialize(review), ensure_ascii=False, indent=2).encode('utf-8')
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('평가표가 너무 큽니다.')
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(target)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.pronunciation-', suffix='.tmp', delete=False) as file:
            tmp = Path(file.name)
            file.write(raw)
            file.flush()
            os.fsync(file.fileno())
        _assert_safe_path(target)
        os.replace(tmp, target)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    return target


def load_review(path: Path, source: str, profile: dict, phrases: tuple[str, ...]) -> PronunciationReview | None:
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 읽을 수 있습니다.')
    try:
        with target.open('rb') as file:
            raw = file.read(MAX_FILE_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('평가 파일이 너무 큽니다.')
    try:
        parsed = _deserialize(json.loads(raw.decode('utf-8')))
    except (ValueError, UnicodeError, TypeError, KeyError) as exc:
        raise ValueError('발음·억양 기록을 읽을 수 없습니다.') from exc
    if not parsed.matches(source, profile, phrases):
        raise ValueError('목소리 설정·문장이 변경되어 저장 기록을 불러오지 않습니다.')
    return parsed


def delete_review(path: Path, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('사용자가 확인하기 전에는 삭제하지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 삭제할 수 있습니다.')
    try:
        target.unlink()
        return True
    except FileNotFoundError:
        return False
