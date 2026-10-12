"""Retry-aware chat → generated reply → output pipeline.

This module uses dependency injection and makes no external service calls.
Real LLM/TTS providers must be separately installed, approved, and connected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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

    def process_next(self) -> ProcessedChat | None:
        message = self.queue.peek_chat()
        if message is None:
            self._prepared = None
            return None
        if self._prepared is not None and self._prepared.original != message:
            raise RuntimeError("pending prepared reply no longer matches chat head")
        if self._prepared is None:
            reply = self.generator.generate(message)
            if not isinstance(reply, str) or not reply.strip():
                raise ValueError("generator must return a nonempty reply")
            self._prepared = ProcessedChat(original=message, reply=reply)
        self.output.deliver(self._prepared.reply)
        self.queue.acknowledge_chat(message)
        result = self._prepared
        self._prepared = None
        return result

    def drain(self) -> list[ProcessedChat]:
        """Process all currently queued chats in order with no intentional delay."""
        results: list[ProcessedChat] = []
        while self.queue.peek_chat() is not None:
            item = self.process_next()
            if item is not None:
                results.append(item)
        return results
