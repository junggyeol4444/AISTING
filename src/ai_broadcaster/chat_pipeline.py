"""Retry-aware chat → generated reply → output pipeline.

This module uses dependency injection and makes no external service calls.
Real LLM/TTS providers must be separately installed, approved, and connected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from .session import ChatMessage, SessionController


class ReplyGenerator(Protocol):
    def generate(self, message: ChatMessage) -> str: ...


class ReplyOutput(Protocol):
    def deliver(self, reply: str) -> None: ...


@dataclass(frozen=True)
class ProcessedChat:
    original: ChatMessage
    reply: str


class ChatPipeline:
    """FIFO processor that does not silently discard failed messages.

    Reply text is cached while delivery retries. A sender acknowledgement is
    completed only after delivery returns successfully. Exactly-once delivery
    cannot be guaranteed if a future provider emits output then raises.
    """

    def __init__(self, queue: SessionController, generator: ReplyGenerator, output: ReplyOutput) -> None:
        self.queue = queue
        self.generator = generator
        self.output = output
        self._prepared: ProcessedChat | None = None
        self.post_delivery_errors: list[Exception] = []

    def process_next(
            self, *, on_stream_chunk: Callable[[str], None] | None = None,
            should_cancel: Callable[[], bool] | None = None
    ) -> ProcessedChat | None:
        message = self.queue.peek_chat()
        if message is None:
            self._prepared = None
            return None
        if self._prepared is not None and self._prepared.original != message:
            raise RuntimeError("pending prepared reply no longer matches chat head")
        if self._prepared is None:
            if on_stream_chunk is not None:
                streaming = getattr(self.generator, "generate_stream", None)
                if not callable(streaming):
                    raise RuntimeError("선택한 AI 생성기는 실제 스트리밍을 지원하지 않습니다.")
                reply = streaming(message, on_stream_chunk, should_cancel=should_cancel)
            else:
                reply = self.generator.generate(message)
            if should_cancel is not None and should_cancel():
                # Ollama 응답을 받았더라도 운영자 Stop 뒤에는
                # 출력·SQLite 기억·FIFO 완료 처리하지 않는다.
                raise RuntimeError("운영자 중지 · 로컬 AI 답변 출력/기억 확정 금지")
            if not isinstance(reply, str) or not reply.strip():
                raise ValueError("generator must return a nonempty reply")
            self._prepared = ProcessedChat(original=message, reply=reply)
        if should_cancel is not None and should_cancel():
            raise RuntimeError("운영자 중지 · 준비된 답변 출력/기억 확정 금지")
        self.output.deliver(self._prepared.reply)
        self.queue.acknowledge_chat(message)
        result = self._prepared
        self._prepared = None
        # 메모리 저장 실패 때문에 이미 출력한 대답을 다시 출력하지 않는다.
        callback = getattr(self.generator, "on_delivered", None)
        if callable(callback):
            try:
                callback(result.original, result.reply)
            except Exception as error:
                self.post_delivery_errors.append(error)
        return result

    def drain(self) -> list[ProcessedChat]:
        """Process all currently queued chats in order with no intentional delay."""
        results: list[ProcessedChat] = []
        while self.queue.peek_chat() is not None:
            item = self.process_next()
            if item is not None:
                results.append(item)
        return results
