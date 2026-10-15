"""운영자가 런타임에 선택하는 무료 음성 확보 계획과 설치된 PC 음성 복원."""
from __future__ import annotations

from collections.abc import Iterable

from .offline_settings import VOICES
from .offline_tts import KoreanVoice

_SOURCE_DESCRIPTIONS = {
    "undecided": "아직 목소리를 확정하지 않아도 돼. 언제든 선택해.",
    "windows_system": "이미 설치된 Windows 한국어 음성을 선택해 PC에서만 재생해.",
    "own_recording": "본인 녹음 계획만 기록. 자동 녹음·복제·학습은 하지 않아.",
    "consented_recording": "음성 제공자의 명시적 동의를 별도로 확인하기 전에는 학습하지 않아.",
    "licensed_recording": "사용 권한과 라이선스를 별도로 확인하기 전에는 학습하지 않아.",
}


def describe_voice_source(code: str) -> str:
    if code not in VOICES.values():
        raise ValueError("선택하지 않은 목소리 확보 방식입니다.")
    return _SOURCE_DESCRIPTIONS[code]


def preferred_installed_voice(name: str, installed: Iterable[KoreanVoice]) -> KoreanVoice | None:
    """이전에 고른 목소리가 설치됐으면 그 음성을 복원; 없으면 자동 대체하지 않음."""
    if not isinstance(name, str):
        raise TypeError("목소리 이름이 올바르지 않습니다.")
    if not name:
        return None
    for voice in installed:
        if not isinstance(voice, KoreanVoice):
            raise TypeError("Windows 한국어 음성 객체가 필요합니다.")
        if voice.name == name:
            return voice
    return None
