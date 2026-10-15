"""21단계: 방송 코어 연결 계약. 정의만 있으며 외부 장치/네트워크를 실행하지 않음.

22단계 이후에서 구현할 포트를 명시한다. 21단계에서는 실제 방송 코어를
구동하지 않으며, 기존 ChatRehearsal/ReplyGenerator 구현을 변경하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class CoreInput:
    """단일 입력. 21단계에서는 플랫폼/계정 채팅을 읽지 않는다."""
    sender: str
    text: str


@dataclass(frozen=True)
class CoreReply:
    """단일 답변. 실제 음성·방송 송출과 무관한 텍스트 자료형."""
    input: CoreInput
    text: str


class InputPort(Protocol):
    def receive(self) -> CoreInput | None: ...


class ReplyPort(Protocol):
    def generate(self, item: CoreInput, history: Sequence[CoreReply]) -> str: ...


class MemoryPort(Protocol):
    def append(self, item: CoreReply) -> None: ...


class VoicePort(Protocol):
    def speak(self, text: str) -> None: ...


class AvatarPort(Protocol):
    def display(self, item: CoreReply) -> None: ...


class BroadcastPort(Protocol):
    def publish(self, item: CoreReply) -> None: ...
