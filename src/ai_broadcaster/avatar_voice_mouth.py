"""Original roadmap 055: manual, silent mock voice-to-2D-mouth rehearsal.

A successful virtual voice segment emits deterministic OPEN/OPEN/CLOSED frames for
preview. Rejected/failed segments emit no mouth movement; the existing FIFO
DialogueVoiceLink retains unfinished work for a later operator click.
Never touches hardware, audio, network, memory, files, real models or OBS.
"""
from __future__ import annotations

from dataclasses import dataclass

from .avatar_renderer import AvatarFrame
from .dialogue_voice_link import DialogueVoiceLink, LinkStatus
from .offline_tts import KoreanVoice


@dataclass(frozen=True)
class DeliveredVoiceSegment:
    chat_number: int
    segment_index: int
    text: str


@dataclass(frozen=True)
class MouthCue:
    chat_number: int
    segment_index: int
    frame: AvatarFrame


class VoiceMouthRehearsal:
    """Each step is explicit; only confirmed virtual dispatch creates cues."""

    def __init__(self, script: str, *, avatar: str, name: str, expression: str,
                 voice_source: str, voice_name: str, rate: int, volume: int,
                 fail_second_once: bool = False):
        if avatar != '2d':
            raise ValueError('내장 2D 선택에서만 입 움직임을 미리볼 수 있습니다. 3D를 2D로 대체하지 않습니다.')
        # Validate pose and shape before accepting the script; no fallback to neutral.
        AvatarFrame(name, False, 0, expression=expression)
        self.name = name
        self.expression = expression
        self.cues: list[MouthCue] = []
        self.delivered: list[DeliveredVoiceSegment] = []
        self._fail_second_once = bool(fail_second_once)
        self._failed_once = False
        self._frame_id = 0
        self._link = DialogueVoiceLink(
            script, source=voice_source, selected_name=voice_name,
            available_voices=[KoreanVoice(voice_name)],
            profile={'installed_voice_name': voice_name, 'rate': rate, 'volume': volume},
            virtual_speak=self._virtual_dispatch,
        )

    def _virtual_dispatch(self, _text: str, _voice: KoreanVoice,
                          _rate: int, _volume: int, segment_index: int) -> bool:
        chat_index = len(self._link.completed) + 1
        if self._fail_second_once and chat_index == 2 and not self._failed_once:
            self._failed_once = True
            return False
        # Every delivered segment gets a recognizable silent open/open/close cycle.
        # Frame indices 1/2 are open in the existing AvatarFrame; 4 is closed.
        for offset in (1, 2, 4):
            self.cues.append(MouthCue(chat_index, segment_index,
                AvatarFrame(self.name, offset != 4, self._frame_id + offset,
                            expression=self.expression)))
        self._frame_id += 4
        self.delivered.append(DeliveredVoiceSegment(chat_index, segment_index, _text))
        return True

    def step(self) -> LinkStatus:
        return self._link.step()

    def status(self) -> LinkStatus:
        return self._link.status()

    def describe(self) -> str:
        s = self.status()
        return ('원본 055 · 채팅→모의 대사→가상 음성→내장 2D 입 모션 (무음)\n'
                f'접수 {s.accepted} / 완료 {len(s.completed)} / 대기 {len(s.pending)}'
                f' · 가상 전달 {s.state}\n'
                f'미리보기 입 프레임 {len(self.cues)}개 · 실패 구간은 입 모션 미기록\n'
                + (f'중단 사유: {s.reason}\n' if s.reason else '')
                + '실제 음향 파형·음소 립싱크, Windows 음성 재생·Live2D/VRM 미검증')
