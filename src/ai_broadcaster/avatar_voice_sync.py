"""Roadmap 056: operator-driven virtual voice / 2D-mouth timing alignment.

A deterministic synthetic clock aligns the successful virtual voice segments from
stage 055 with a silent on-screen mouth pose. No audio is rendered or measured;
character-based duration is a test fixture, not a TTS timing estimate.
"""
from __future__ import annotations

from dataclasses import dataclass

from .avatar_renderer import AvatarFrame
from .avatar_voice_mouth import VoiceMouthRehearsal
from .dialogue_voice_link import LinkStatus


@dataclass(frozen=True)
class VirtualVoiceWindow:
    chat_number: int
    segment_index: int
    text: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class SyncFrame:
    clock_ms: int
    window: VirtualVoiceWindow | None
    frame: AvatarFrame
    phase: str


class VirtualVoiceMouthSync:
    """Explicit mock dispatch + inspectable virtual clock (no timers, no devices)."""

    def __init__(self, script: str, *, avatar: str, name: str, expression: str,
                 voice_source: str, voice_name: str, rate: int, volume: int,
                 fail_second_once: bool = False, milliseconds_per_character: int = 80):
        if type(milliseconds_per_character) is not int or not (20 <= milliseconds_per_character <= 500):
            raise ValueError('모의 문자별 길이는 20~500ms 정수여야 합니다.')
        self.rehearsal = VoiceMouthRehearsal(
            script, avatar=avatar, name=name, expression=expression,
            voice_source=voice_source, voice_name=voice_name, rate=rate, volume=volume,
            fail_second_once=fail_second_once)
        self.ms_per_character = milliseconds_per_character
        self.windows: list[VirtualVoiceWindow] = []
        self._recorded = 0
        self.clock_ms = 0

    @property
    def duration_ms(self) -> int:
        return self.windows[-1].end_ms if self.windows else 0

    def step(self) -> LinkStatus:
        """Only a user action dispatches one chat; no automatic retry."""
        result = self.rehearsal.step()
        for event in self.rehearsal.delivered[self._recorded:]:
            start = self.duration_ms
            # At least 240ms per event; pauses outside virtual windows are silent.
            duration = max(240, len(event.text) * self.ms_per_character)
            self.windows.append(VirtualVoiceWindow(
                event.chat_number, event.segment_index, event.text,
                start, start + duration))
        self._recorded = len(self.rehearsal.delivered)
        return result

    def seek(self, clock_ms: int) -> SyncFrame:
        """Scrub without dispatching more audio/chat; end bound is always closed."""
        if type(clock_ms) is not int or not 0 <= clock_ms <= self.duration_ms:
            raise ValueError('가상 시각이 생성된 구간 범위를 벗어났습니다.')
        self.clock_ms = clock_ms
        return self._frame_at(clock_ms)

    def _frame_at(self, clock_ms: int) -> SyncFrame:
        for window in self.windows:
            if window.start_ms <= clock_ms < window.end_ms:
                delta = clock_ms - window.start_ms
                length = window.end_ms - window.start_ms
                # 0..40% open, 40..80% open, 80..100% closed.
                phase_idx = (delta * 5) // length
                if phase_idx < 2:
                    frame_id, phase = 1, '가상 재생 · 입 열림'
                elif phase_idx < 4:
                    frame_id, phase = 2, '가상 재생 · 입 열림'
                else:
                    frame_id, phase = 4, '가상 마무리 · 입 닫힘'
                return SyncFrame(clock_ms, window, AvatarFrame(
                    self.rehearsal.name, frame_id != 4, frame_id,
                    expression=self.rehearsal.expression), phase)
        return SyncFrame(clock_ms, None, AvatarFrame(
            self.rehearsal.name, False, 4,
            expression=self.rehearsal.expression), '가상 구간 밖 · 입 닫힘')

    def advance(self, milliseconds: int) -> SyncFrame:
        if type(milliseconds) is not int or milliseconds <= 0 or milliseconds > 10000:
            raise ValueError('가상 시간 이동은 1~10000ms 정수여야 합니다.')
        return self.seek(min(self.duration_ms, self.clock_ms + milliseconds))

    def audit(self) -> tuple[bool, str]:
        """Check timeline/voice attribution without claiming physical synchronization."""
        pos = 0
        if len(self.windows) != len(self.rehearsal.delivered):
            return False, '전달된 음성 구간과 타임라인의 수가 다릅니다.'
        for window, event in zip(self.windows, self.rehearsal.delivered):
            if (window.start_ms != pos or window.end_ms <= pos or
                (window.chat_number, window.segment_index, window.text) !=
                (event.chat_number, event.segment_index, event.text)):
                return False, '가상 구간 시간 또는 출처가 불일치합니다.'
            pos = window.end_ms
            if self._frame_at(window.start_ms).frame.mouth == 0:
                return False, '가상 시작 시 입이 닫혀 있습니다.'
            if self._frame_at(window.end_ms - 1).frame.mouth != 0:
                return False, '가상 종료 직전 입이 닫히지 않았습니다.'
        if self._frame_at(pos).frame.mouth != 0:
            return False, '마지막 가상 음성 종료 뒤 입이 열려 있습니다.'
        return True, '생성된 가상 음성 구간과 2D 입 프레임의 시각·순서가 일치합니다.'

    def describe(self) -> str:
        result = self.rehearsal.status()
        ok, reason = self.audit()
        lines = ['원본 056 · 무음 가상 음성/입 시각 정렬 시험',
                 f'모의 시간표 {len(self.windows)}구간 · 총 {self.duration_ms}ms · '
                 f'검사 {"통과" if ok else "실패"}',
                 f'처리 {len(result.completed)} / 대기 {len(result.pending)} · '
                 f'최근 가상 전달 상태 {result.state}', reason]
        for w in self.windows[:90]:
            lines.append(f'채팅 {w.chat_number} / 구간 {w.segment_index}: '
                         f'{w.start_ms}~{w.end_ms}ms · {len(w.text)}자')
        lines.append('문자 수 기반 가상 시간이며 실제 TTS 음향·음소·파형 립싱크 및 Windows 재생 미검증')
        return '\n'.join(lines)
