"""Roadmap 046: operator-selected local Korean voice routing, simulated only.

Caller supplies an explicit list of *virtual* or manually queried voices. This module
never enumerates OS voices, opens speakers, scans PC, or sends data anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .offline_settings import validate_voice_profile
from .offline_tts import KoreanVoice, speech_chunks
from .voice_choices import preferred_installed_voice


@dataclass(frozen=True)
class VoiceRouteReport:
    source: str
    voice_name: str
    rate: int
    volume: int
    segments: tuple[str, ...]
    delivered: tuple[str, ...]
    pending: tuple[str, ...]
    state: str
    reason: str

    def describe(self) -> str:
        lines = [
            '원본 046 · 운영자 선택 목소리 전달 모의 (실제 출력 없음)',
            f'음성 방식: {self.source} / 선택 목소리: {self.voice_name}',
            f'속도: {self.rate} / 음량: {self.volume}',
            f'결과: {self.state} / 전체 {len(self.segments)} · 전달 {len(self.delivered)} · 대기 {len(self.pending)}',
            'Windows 설치/재생 여부 및 실제 목소리 일치는 사용자 직접 검증 대기',
        ]
        lines += [f'{i}. [{"모의 전달" if i <= len(self.delivered) else "미처리"}] {segment}'
                  for i, segment in enumerate(self.segments, 1)]
        if self.reason:
            lines.append('사유: ' + self.reason)
        return '\n'.join(lines)


def rehearse_selected_voice(
    text: str, *, source: str, selected_name: str,
    available_voices: Iterable[KoreanVoice], profile: dict,
    virtual_speak: Callable[[str, KoreanVoice, int, int, int], bool] | None = None,
) -> VoiceRouteReport:
    """Verify exact chosen ko-KR voice & rate/volume reach each virtual output.

    No fallback, no actual speaker or system voice query. A failure/stop retains the
    failed segment and all subsequent segments. No automatic retry.
    """
    if source != 'windows_system':
        raise ValueError('Windows 무료 음성을 선택한 경우에만 시험 가능 · 다른 음성 방식 미구성')
    checked = validate_voice_profile(profile)
    if not isinstance(selected_name, str) or not selected_name or len(selected_name) > 160:
        raise ValueError('운영자가 한국어 목소리를 직접 선택해야 합니다.')
    voices = tuple(available_voices)
    if len(voices) > 100 or len({v.name for v in voices if isinstance(v, KoreanVoice)}) != len(voices):
        raise ValueError('한국어 목소리 목록이 중복되거나 잘못됐습니다.')
    voice = preferred_installed_voice(selected_name, voices)
    if voice is None:
        raise ValueError('선택한 한국어 목소리가 목록에 없습니다. 자동 대체하지 않습니다.')
    if checked['installed_voice_name'] != selected_name:
        raise ValueError('목소리 프로필과 실제 선택값이 다릅니다. 자동 대체하지 않습니다.')
    segments = tuple(speech_chunks(text))
    delivered: list[str] = []
    state, reason = 'simulated_complete', ''
    for index, part in enumerate(segments, 1):
        try:
            result = True if virtual_speak is None else virtual_speak(
                part, voice, checked['rate'], checked['volume'], index)
            if type(result) is not bool:
                raise ValueError('가상 출력 결과 형식 오류')
            if not result:
                state = 'simulated_interrupted'
                reason = f'{index}번째 구간에서 중단 · 자동 재시도 없음'
                break
        except Exception as exc:
            state = 'simulated_error'
            # Do not expose arbitrary exception texts (e.g. file paths, secrets).
            reason = f'{index}번째 구간에서 오류 ({type(exc).__name__}) · 자동 재시도 없음'
            break
        delivered.append(part)
    return VoiceRouteReport(source, voice.name, checked['rate'], checked['volume'],
                            segments, tuple(delivered), segments[len(delivered):], state, reason)
