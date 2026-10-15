"""Roadmap 044: non-executing Korean speech synthesis configuration draft.

No TTS model installation, PC probing, audio/file input, model inference, or
speech playback. The plan documents choices; it is NOT readiness certification.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import VOICES, data_dir, validate_voice_profile
from .runtime_profile import _assert_safe_path

FILE_NAME = 'korean_synthesis_environment_draft.json'
SCHEMA = 1
MAX_BYTES = 4096
ENGINES = {'windows_system': 'windows_system_speech',
           'undecided': 'not_selected',
           'own_recording': 'future_local_tts_unconfigured',
           'consented_recording': 'future_local_tts_unconfigured',
           'licensed_recording': 'future_local_tts_unconfigured'}


@dataclass(frozen=True)
class SynthesisEnvironmentDraft:
    source: str
    engine: str
    language: str
    voice_name: str
    rate: int
    volume: int

    def __post_init__(self) -> None:
        if type(self.source) is not str or self.source not in VOICES.values():
            raise ValueError('프로그램에서 선택한 목소리 확보 방식이 올바르지 않습니다.')
        if type(self.engine) is not str or self.engine != ENGINES[self.source]:
            raise ValueError('외부/미승인 음성 합성 엔진을 설정할 수 없습니다.')
        if self.language != 'ko-KR':
            raise ValueError('한국어(ko-KR) 환경 초안만 준비합니다.')
        validate_voice_profile({'installed_voice_name': self.voice_name,
                                'rate': self.rate, 'volume': self.volume})
        if self.engine != 'windows_system_speech' and self.voice_name:
            raise ValueError('Windows 이외의 미구성 음성 모델에 설치된 음성 이름을 적용할 수 없습니다.')

    def matches(self, source: str, profile: dict) -> bool:
        return self == build_synthesis_environment(source, profile)

    def describe(self) -> str:
        lines = ['원본 044단계 · 한국어 음성 합성 환경 설정 초안',
                 f'사용자 선택 음성 확보 방식: {self.source}',
                 '대상 언어: ko-KR',
                 f'구성 후보: {self.engine}',
                 'PC·설치된 음성·마이크·음성파일 자동 조사 없음',
                 '외부 서비스·프로그램 설치·음성 복제/학습·재생·방송 없음']
        if self.engine == 'windows_system_speech':
            lines.extend([f'저장된 Windows 음성 이름: {self.voice_name or "미선택"}',
                          f'속도: {self.rate} / 음량: {self.volume}',
                          '동봉된 Windows System.Speech 코드는 이미 존재하지만,',
                          '실제 설치 음성·한국어 재생·OS 호환성은 사용자 PC에서 수동 확인 대기.'])
            if not self.voice_name:
                lines.append('※ Windows 한국어 음성 이름이 선택되지 않았습니다. 실행 가능 판정 불가.')
        elif self.engine == 'not_selected':
            lines.append('※ 음성 방식 미정. 사용자가 프로그램에서 나중에 선택할 수 있습니다.')
        else:
            lines.append('※ 별도 로컬 한국어 TTS 엔진 미설치·미연결. 후보 구성만 기록했습니다.')
            lines.append('※ 41~43단계의 권리/자료/품질은 사용자 확인 대기이며 자동 승인되지 않습니다.')
        lines.append('상태: 구성 초안만 작성 · 실제 실행 가능/사용권/품질/학습/방송 승인 아님')
        return '\n'.join(lines)


def build_synthesis_environment(source: str, profile: dict) -> SynthesisEnvironmentDraft:
    if type(source) is not str or source not in ENGINES:
        raise ValueError('음성 확보 방식이 잘못되었습니다.')
    p = validate_voice_profile(profile)
    return SynthesisEnvironmentDraft(
        source, ENGINES[source], 'ko-KR',
        p['installed_voice_name'] if source == 'windows_system' else '',
        p['rate'], p['volume'])


def synthesis_environment_path(directory: Path | None = None) -> Path:
    return (Path(directory) if directory is not None else data_dir()) / FILE_NAME


def _record(draft: SynthesisEnvironmentDraft) -> dict:
    return {'schema_version': SCHEMA, 'kind': 'offline_synthesis_environment_draft',
            'source': draft.source, 'engine': draft.engine, 'language': draft.language,
            'voice_name': draft.voice_name, 'rate': draft.rate, 'volume': draft.volume,
            'pc_probed': False, 'audio_accessed': False, 'model_installed': False,
            'training_authorized': False, 'broadcast_authorized': False,
            'environment_verified': False}


def validate_synthesis_record(payload: object) -> SynthesisEnvironmentDraft:
    allowed = set(_record(build_synthesis_environment('undecided',
                   {'installed_voice_name': '', 'rate': 0, 'volume': 85})))
    if type(payload) is not dict or set(payload) != allowed:
        raise ValueError('합성 환경 기록 구조가 올바르지 않습니다.')
    if type(payload['schema_version']) is not int or payload['schema_version'] != SCHEMA or \
       payload['kind'] != 'offline_synthesis_environment_draft' or any(
            payload[k] is not False for k in ('pc_probed', 'audio_accessed', 'model_installed',
                                            'training_authorized', 'broadcast_authorized',
                                            'environment_verified')):
        raise ValueError('합성 환경 승인/조사 기록을 임의로 변경할 수 없습니다.')
    return SynthesisEnvironmentDraft(payload['source'], payload['engine'],
                                      payload['language'], payload['voice_name'],
                                      payload['rate'], payload['volume'])


def save_synthesis_environment(path: Path, draft: SynthesisEnvironmentDraft, *,
                               operator_confirmed: bool = False) -> Path:
    if operator_confirmed is not True:
        raise PermissionError('운영자 확인 없이 음성 합성 구성 초안을 저장하지 않습니다.')
    if type(draft) is not SynthesisEnvironmentDraft:
        raise ValueError('음성 환경 초안이 필요합니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 저장할 수 있습니다.')
    raw = json.dumps(_record(draft), ensure_ascii=False, indent=2).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValueError('합성 환경 기록이 너무 큽니다.')
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(target)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent, prefix='.tts-env-',
                                         suffix='.tmp', delete=False) as stream:
            temp = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _assert_safe_path(target)
        os.replace(temp, target)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return target


def load_synthesis_environment(path: Path, source: str, profile: dict) -> SynthesisEnvironmentDraft | None:
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 읽을 수 있습니다.')
    try:
        with target.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(raw) > MAX_BYTES:
        raise ValueError('합성 환경 기록이 너무 큽니다.')
    try:
        draft = validate_synthesis_record(json.loads(raw.decode('utf-8')))
    except (UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise ValueError('음성 합성 기록을 읽을 수 없습니다.') from exc
    if not draft.matches(source, profile):
        raise ValueError('현재 선택한 음성 확보 방식·Windows 음성/속도/음량과 다른 기록입니다.')
    return draft


def delete_synthesis_environment(path: Path, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('운영자 확인 없이 합성 구성 기록을 삭제하지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 삭제할 수 있습니다.')
    try:
        target.unlink()
        return True
    except FileNotFoundError:
        return False
