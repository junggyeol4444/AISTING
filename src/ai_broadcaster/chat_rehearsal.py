"""Windows EXE용 오프라인 다중 시청자 채팅 연습.

입력은 운영자가 직접 넣은 테스트 대본으로만 취급한다.
플랫폼 수신, 네트워크 접속, TTS 재생, 실제 OBS 방송은 이 모듈에서 하지 않는다.
동일한 내용의 메시지도 각각 답한다. 실패한 메시지는 FIFO 큐에 남는다.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from .chat_pipeline import ChatPipeline, ProcessedChat, ReplyGenerator
from .session import ChatMessage, SessionController

MAX_MESSAGES_PER_BATCH = 500
MAX_SCRIPT_CHARS = 100_000


class ChatScriptError(ValueError):
    """모든 입력을 처리할 수 없을 때 대본 전체를 거부한다."""


def parse_chat_script(script: str) -> list[ChatMessage]:
    """'닉네임: 메시지' 형식. 빈 줄만 무시, 잘못된 줄은 전체 오류."""
    if not isinstance(script, str) or not script.strip():
        raise ChatScriptError("시청자 채팅을 한 줄 이상 입력해 주세요.")
    if len(script) > MAX_SCRIPT_CHARS:
        raise ChatScriptError("대본이 너무 깁니다 (최대 100,000글자).")
    result: list[ChatMessage] = []
    for line_number, line in enumerate(script.splitlines(), 1):
        if not line.strip():
            continue
        if ":" not in line:
            raise ChatScriptError(f"{line_number}번째 줄: '닉네임: 메시지' 형식으로 입력해 주세요.")
        sender, message = line.split(":", 1)
        sender, message = sender.strip(), message.strip()
        if not 1 <= len(sender) <= 100 or not 1 <= len(message) <= 4000:
            raise ChatScriptError(f"{line_number}번째 줄: 닉네임은 1~100자, 내용은 1~4000자여야 합니다.")
        result.append(ChatMessage(str(uuid4()), sender, message))
        if len(result) > MAX_MESSAGES_PER_BATCH:
            raise ChatScriptError("한 번에 최대 500개까지 입력할 수 있습니다. 나눠서 입력해 주세요.")
    if not result:
        raise ChatScriptError("빈 줄 이외의 채팅을 입력해 주세요.")
    return result


class MockKoreanReplyGenerator:
    """연결이 필요 없는 단순 시험 응답. LLM 응답이 아님."""

    def generate(self, message: ChatMessage) -> str:
        return f"{message.sender}님, '{message.text[:300]}'에 대한 모의 응답입니다."


@dataclass(frozen=True)
class RehearsalStatus:
    total: int
    processed: int
    pending: int


class _CaptureOutput:
    def __init__(self) -> None:
        self.last: str | None = None

    def deliver(self, reply: str) -> None:
        self.last = reply


class ChatRehearsal:
    """순서대로 각 메시지에 응답. 재시도 시 이미 생성한 답변은 재사용."""

    def __init__(self, generator: ReplyGenerator | None = None) -> None:
        self.queue = SessionController()
        self.output = _CaptureOutput()
        self.generator = generator if generator is not None else MockKoreanReplyGenerator()
        self.pipeline = ChatPipeline(self.queue, self.generator, self.output)
        self._total = 0

    def add_script(self, script: str) -> int:
        messages = parse_chat_script(script)
        # 전부 검증한 뒤에만 넣으므로 중간까지 수신되는 일이 없다.
        for message in messages:
            self.queue.receive_chat(message)
        self._total += len(messages)
        return len(messages)

    @property
    def status(self) -> RehearsalStatus:
        return RehearsalStatus(
            total=self._total,
            processed=self.queue.processed_chats,
            pending=self.queue.pending_chats,
        )

    def process_next(self) -> ProcessedChat | None:
        return self.pipeline.process_next()
