"""Roadmap 049: connect mock AI answers to virtual local voice output, safely.

No OS voice probing, speaker playback, model call, account, network, DB or files.
Every processing attempt must be initiated explicitly by the operator. Failed or
interrupted segments remain queued; a later click resumes without replaying them.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Iterable

from .offline_chat import Answer, ChatMessage, MockReplyGenerator, parse_script
from .offline_tts import KoreanVoice, speech_chunks
from .offline_settings import validate_voice_profile
from .voice_choices import preferred_installed_voice
from .selected_voice_routing import rehearse_selected_voice


@dataclass(frozen=True)
class LinkStatus:
    accepted: int
    completed: tuple[Answer, ...]
    pending: tuple[ChatMessage, ...]
    current: Answer | None
    delivered_segments: tuple[str, ...]
    remaining_segments: tuple[str, ...]
    state: str
    reason: str
    voice_name: str
    rate: int
    volume: int

    def describe(self) -> str:
        lines = [
            '원본 049 · 모의 AI 대사 → 가상 한국어 음성 전달 (실제 음성 출력 없음)',
            f'목소리 식별자: {self.voice_name} · 속도 {self.rate} · 음량 {self.volume}',
            f'상태: {self.state} · 접수 {self.accepted} · 완료 {len(self.completed)} · 대기 {len(self.pending)}',
            '동일 채팅도 개별 처리 · 실패 구간은 수동 재시도 시 이어서 처리',
        ]
        for idx, answer in enumerate(self.completed, 1):
            lines.append(f'{idx}. [{answer.original.sender}] {answer.reply}')
        if self.current is not None:
            lines.append(f'진행 중: [{self.current.original.sender}] {self.current.reply}')
            lines.append(f'가상 전달 구간 {len(self.delivered_segments)} / 미처리 {len(self.remaining_segments)}')
        if self.reason:
            lines.append('사유: ' + self.reason)
        lines.append('실제 LLM/Windows 음성·스피커/음질/방송 연결은 별도 사용자 검증 대기')
        return '\n'.join(lines)


class DialogueVoiceLink:
    """Explicitly driven per-chat FIFO rehearsal using only the mock text generator.

    A partially dispatched answer stays prepared at queue head; pressing step()
    again manually resumes the first un-delivered chunk, never silently replaying
    the already delivered portion or re-generating its text.
    """

    def __init__(self, script: str, *, source: str, selected_name: str,
                 available_voices: Iterable[KoreanVoice], profile: dict,
                 virtual_speak: Callable[[str, KoreanVoice, int, int, int], bool] | None = None):
        messages = parse_script(script)
        if len(messages) > 30:
            raise ValueError('모의 음성 연결 시험은 최대 30건까지 가능합니다.')
        if source != 'windows_system':
            raise ValueError('Windows 무료 음성 방식에서만 가상 경로 검증 가능 (다른 로컬 음성 엔진 미구성)')
        checked = validate_voice_profile(profile)
        # selected_voice_routing supplies the strict no-fallback contract.
        rehearsal = rehearse_selected_voice(
            '구성 확인', source=source, selected_name=selected_name,
            available_voices=available_voices, profile=checked)
        self.voice = KoreanVoice(rehearsal.voice_name)
        self.rate = rehearsal.rate
        self.volume = rehearsal.volume
        self.accepted = len(messages)
        self.pending: deque[ChatMessage] = deque(messages)
        self.completed: list[Answer] = []
        self.current: Answer | None = None
        self.chunks: tuple[str, ...] = ()
        self.cursor = 0
        self.state = 'ready'
        self.reason = ''
        self._generator = MockReplyGenerator()
        self._speak = virtual_speak

    def status(self) -> LinkStatus:
        return LinkStatus(
            self.accepted, tuple(self.completed), tuple(self.pending), self.current,
            self.chunks[:self.cursor], self.chunks[self.cursor:], self.state,
            self.reason, self.voice.name, self.rate, self.volume,
        )

    def step(self) -> LinkStatus:
        if not self.pending:
            self.state, self.reason = 'simulated_complete', ''
            return self.status()
        if self.current is None:
            head = self.pending[0]
            # Fail closed before touching pending; never call an external model.
            reply = self._generator.generate(head, self.completed[-8:])
            if not isinstance(reply, str) or not reply.strip() or len(reply) > 6000:
                self.state, self.reason = 'simulated_error', '모의 AI 대사 형식 오류'
                return self.status()
            self.current = Answer(head, reply)
            self.chunks = tuple(speech_chunks(reply))
            self.cursor = 0
        self.state, self.reason = 'simulated_complete', ''
        while self.cursor < len(self.chunks):
            index = self.cursor + 1
            part = self.chunks[self.cursor]
            # Reuse the already-tested per-voice routing guard for each chunk.
            # A manually provided virtual backend never activates a real speaker.
            def dispatch(segment: str, voice: KoreanVoice, rate: int, volume: int, _index: int) -> bool:
                if self._speak is None:
                    return True
                return self._speak(segment, voice, rate, volume, index)
            result = rehearse_selected_voice(
                part, source='windows_system', selected_name=self.voice.name,
                available_voices=(self.voice,),
                profile={'installed_voice_name': self.voice.name,
                         'rate': self.rate, 'volume': self.volume},
                virtual_speak=dispatch)
            if result.state != 'simulated_complete':
                self.state = result.state
                self.reason = f'{index}번째 음성 구간 미전달 · 자동 재시도 없음'
                return self.status()
            self.cursor += 1
        self.completed.append(self.current)
        self.pending.popleft()
        self.current = None
        self.chunks = ()
        self.cursor = 0
        return self.status()

    def run_manual_batch(self) -> LinkStatus:
        """Operator button: process up to 30 accepted chats, stop on first failure."""
        for _ in range(len(self.pending)):
            result = self.step()
            if result.state != 'simulated_complete':
                return result
        return self.status()
