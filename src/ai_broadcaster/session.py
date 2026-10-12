"""Platform-neutral chat and broadcast-session simulation.

No OBS, external network, OS controls or automatic broadcasts are accessed.
This module is intentionally a testable core, not a streaming integration.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Deque


class SessionState(str, Enum):
    OFFLINE = "offline"
    LIVE = "live"  # Internal state only: no streaming is performed.
    CLOSING = "closing"


@dataclass(frozen=True)
class ChatMessage:
    message_id: str
    sender: str
    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.message_id, str) or not self.message_id:
            raise ValueError("message_id must be a nonempty string")
        if not isinstance(self.sender, str) or not self.sender:
            raise ValueError("sender must be a nonempty string")
        if not isinstance(self.text, str):
            raise TypeError("chat message text must be a string")


@dataclass(frozen=True)
class SessionPolicy:
    """Rules are disabled until the operator decides their values."""

    minimum_seconds: float = 0.0
    maximum_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.minimum_seconds < 0:
            raise ValueError("minimum_seconds must be >= 0")
        if self.maximum_seconds is not None:
            if self.maximum_seconds <= 0:
                raise ValueError("maximum_seconds must be > 0")
            if self.maximum_seconds < self.minimum_seconds:
                raise ValueError("maximum_seconds cannot be less than minimum_seconds")


@dataclass(frozen=True)
class SessionEvent:
    name: str
    detail: str = ""


class SessionController:
    """Pure in-memory state machine with FIFO chat handling.

    Transitions emit informational events rather than performing I/O.
    A platform adapter may eventually consume them after explicit approval.
    """

    def __init__(self, policy: SessionPolicy | None = None) -> None:
        self.policy = policy if policy is not None else SessionPolicy()
        self.state = SessionState.OFFLINE
        self.started_at: float | None = None
        self._pending_chats: Deque[ChatMessage] = deque()
        self._processed = 0
        self._last_tick: float | None = None

    @property
    def pending_chats(self) -> int:
        return len(self._pending_chats)

    @property
    def processed_chats(self) -> int:
        return self._processed

    def start(self, at_seconds: float) -> SessionEvent:
        """Start a *simulated* session, never an external live broadcast."""
        if self.state != SessionState.OFFLINE:
            raise RuntimeError("session already running")
        if not isinstance(at_seconds, (int, float)):
            raise TypeError("at_seconds must be a number")
        self.state = SessionState.LIVE
        self.started_at = float(at_seconds)
        self._last_tick = float(at_seconds)
        return SessionEvent("simulated_session_started")

    def receive_chat(self, message: ChatMessage) -> None:
        """Accept each incoming message exactly once; no priority/drop/delay."""
        if not isinstance(message, ChatMessage):
            raise TypeError("message must be ChatMessage")
        self._pending_chats.append(message)

    def next_chat(self) -> ChatMessage | None:
        """Return oldest message; caller controls LLM/TTS response delivery."""
        if not self._pending_chats:
            return None
        self._processed += 1
        return self._pending_chats.popleft()

    def tick(self, at_seconds: float) -> SessionEvent | None:
        if self.state == SessionState.OFFLINE:
            return None
        if self.started_at is None:
            raise RuntimeError("missing start timestamp")
        if not isinstance(at_seconds, (int, float)):
            raise TypeError("at_seconds must be a number")
        now = float(at_seconds)
        if self._last_tick is not None and now < self._last_tick:
            raise ValueError("time must not move backwards")
        self._last_tick = now
        if self.state == SessionState.CLOSING:
            return None
        max_seconds = self.policy.maximum_seconds
        elapsed = now - self.started_at
        if max_seconds is not None and elapsed >= max_seconds and elapsed >= self.policy.minimum_seconds:
            return self.request_close()
        return None

    def request_close(self) -> SessionEvent | None:
        """Request an ending line once; does not terminate an external stream."""
        if self.state != SessionState.LIVE:
            return None
        self.state = SessionState.CLOSING
        return SessionEvent("farewell_requested")

    def farewell_finished(self) -> SessionEvent:
        """Transition offline after the caller reports the farewell was spoken."""
        if self.state != SessionState.CLOSING:
            raise RuntimeError("cannot finish farewell unless closing")
        self.state = SessionState.OFFLINE
        return SessionEvent("simulated_session_ended")
