"""PC의 무료 한국어 Windows TTS로 로컬 AI 답변을 읽어주는 조립 계층.

방송 외부 송출 없음. 사용자 UI 선택 전에는 재생하지 않음.
WindowsSpeechPreview의 600글자 제한을 보존하고 긴 AI 답변을 여러 문장으로 나눔.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

from .windows_tts import Voice, SpeechError, WindowsSpeechPreview


def split_reply(text: str, max_chars: int = 600) -> list[str]:
    """원래 답변을 생략하지 않고 최대 600자씩 음성 합성용으로 분할."""
    if not isinstance(text, str) or not text.strip() or len(text) > 6000:
        raise ValueError("AI 답변은 1~6000자 사이여야 합니다.")
    if type(max_chars) is not int or not 1 <= max_chars <= 600:
        raise ValueError("음성 구간은 1~600자여야 합니다.")
    remaining = text.strip()
    chunks: list[str] = []
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        segment = remaining[:max_chars]
        # 가능하다면 문장 끝에서 분할, 그렇지 않으면 최대 길이로 자름.
        candidate = max(
            (i + 1 for i, ch in enumerate(segment) if ch in ".!?。！？\n"),
            default=0,
        )
        boundary = candidate if candidate >= max_chars // 2 else max_chars
        part = remaining[:boundary].strip()
        if part:
            chunks.append(part)
        remaining = remaining[boundary:].lstrip()
    return chunks


def should_auto_read(enabled: object, voice: Voice | None, reply: object) -> bool:
    """명시적으로 켠 토글과 설치된 한국어 음성이 있을 때만 자동 미리 듣기."""
    return (
        enabled is True and isinstance(voice, Voice)
        and isinstance(reply, str) and bool(reply.strip())
    )


@dataclass(frozen=True)
class ReadingResult:
    total_chunks: int
    spoken_chunks: int
    stopped: bool


class ReplyVoicePlayer:
    """별도 UI 스레드에서 읽고 언제든 중지 가능.

    응답 생성/기억 저장과 분리: TTS 실패해도 채팅이 재송신되거나 기억이 바뀌지 않음.
    """

    def __init__(self, backend: WindowsSpeechPreview | None = None) -> None:
        self.backend = backend if backend is not None else WindowsSpeechPreview()
        self._lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._speaking = False

    @property
    def speaking(self) -> bool:
        with self._lock:
            return self._speaking

    def read(self, reply: str, voice: Voice) -> ReadingResult:
        if not isinstance(voice, Voice):
            raise TypeError("한국어 음성 선택이 필요합니다.")
        chunks = split_reply(reply)
        with self._lock:
            if self._speaking:
                raise SpeechError("이미 AI 답변을 읽고 있습니다.")
            self._speaking = True
            self._stop_requested.clear()
        count = 0
        try:
            for part in chunks:
                if self._stop_requested.is_set():
                    break
                try:
                    self.backend.speak(part, voice)
                except SpeechError:
                    if self._stop_requested.is_set():
                        break
                    raise
                count += 1
            return ReadingResult(
                total_chunks=len(chunks),
                spoken_chunks=count,
                stopped=self._stop_requested.is_set(),
            )
        finally:
            with self._lock:
                self._speaking = False

    def stop(self) -> bool:
        with self._lock:
            if not self._speaking:
                return False
            self._stop_requested.set()
        self.backend.stop()
        return True
