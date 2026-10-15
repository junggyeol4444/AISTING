"""Original stage 073: *silent* virtual speech-to-broadcast-scene output port.

This is not an audio transport. No speaker, microphone, OS voice enumeration,
OBS, streaming, network or persistence is touched. A human must request each
segment. Existing text splitting and immutable scene intent are reused.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_broadcast_scene import BroadcastSceneDraft
from .offline_tts import speech_chunks


@dataclass(frozen=True)
class BroadcastVoiceStatus:
    state: str
    delivered: tuple[str, ...]
    remaining: tuple[str, ...]
    detail: str


class OfflineBroadcastVoiceLink:
    """Non-playing, explicit one-chunk-at-a-time output preview.

    The route is bound to one scene draft. A failed draw or injected virtual
    interruption cannot consume a chunk. Scene/user selection changes require
    making a new link; no TTS engine can be reached from this class.
    """

    def __init__(self, draft: BroadcastSceneDraft, text: str, *, maximum: int = 120):
        if type(draft) is not BroadcastSceneDraft:
            raise ValueError('기존 방송 화면 구성안이 필요합니다.')
        if draft.voice != 'windows_system':
            raise ValueError('현재 선택한 목소리 출력 경로는 미연결입니다. 다른 목소리로 대체하지 않습니다.')
        self.draft = draft
        self.chunks = tuple(speech_chunks(text, maximum=maximum))
        self.cursor = 0
        self.state = 'ready'

    def status(self) -> BroadcastVoiceStatus:
        return BroadcastVoiceStatus(
            self.state, self.chunks[:self.cursor], self.chunks[self.cursor:],
            f'무음 가상 경로 · {self.cursor}/{len(self.chunks)}구간 · 실제 음성/OBS 송출 0건',
        )

    def step(self, canvas, current_draft: BroadcastSceneDraft, *, interrupt: bool = False) -> BroadcastVoiceStatus:
        if type(current_draft) is not BroadcastSceneDraft or current_draft != self.draft:
            raise ValueError('방송 화면 선택이 변경되어 가상 음성 연결이 무효화되었습니다.')
        if type(interrupt) is not bool:
            raise ValueError('가상 중단 상태가 올바르지 않습니다.')
        if self.cursor >= len(self.chunks):
            self.state = 'simulated_complete'
            return self.status()
        if interrupt:
            self.state = 'simulated_interrupted'
            return self.status()
        index = self.cursor + 1
        part = self.chunks[self.cursor]
        # This is an explicit *text marker*, not a call to an audio renderer.
        # Commit cursor only after the visible overlay is successfully drawn.
        try:
            canvas.delete('aisting_scene_voice')
            canvas.create_rectangle(18, 295, 615, 322, fill='#253d57', outline='#9dc7d9',
                                    tags=('aisting_scene_voice',))
            canvas.create_text(315, 308, text=f'무음 가상 출력 {index}/{len(self.chunks)} · {part[:44]}',
                               fill='#ffffff', width=560, tags=('aisting_scene_voice',))
        except Exception:
            self.state = 'simulated_error'
            # This is an isolated overlay and cannot roll back an external effect;
            # the cursor is deliberately not advanced, requiring manual retry.
            raise
        self.cursor += 1
        self.state = 'simulated_complete' if self.cursor == len(self.chunks) else 'simulated_partial'
        return self.status()
