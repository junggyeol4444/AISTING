"""Windows EXE의 수동 로컬 AI 대화 테스트 실행부.

사용자가 '전송'을 눌러야만 PC에 이미 설치된 Ollama와 연결한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .chat_pipeline import ChatPipeline
from .conversation_memory import ConversationMemory, DEFAULT_MEMORY_FILE
from .local_llm import LocalModelConfig, LocalOllamaReplyGenerator
from .operator_settings import load_settings, DEFAULT_FILE
from .session import ChatMessage, SessionController


@dataclass(frozen=True)
class ChatResult:
    reply: str
    remembered_count: int
    warning: str = ""


class _TextOutput:
    def __init__(self) -> None:
        self.reply: str | None = None

    def deliver(self, reply: str) -> None:
        self.reply = reply


def run_local_chat(
    model: str, text: str, *,
    port: int = 11434,
    settings_path: Path = DEFAULT_FILE,
    memory_path: Path = DEFAULT_MEMORY_FILE,
    sender: str = "운영자",
) -> ChatResult:
    if not isinstance(text, str) or not text.strip() or len(text) > 4000:
        raise ValueError("내용은 공백이 아닌 1~4000글자로 입력해 주세요.")
    if not isinstance(sender, str) or not sender.strip() or len(sender) > 160:
        raise ValueError("채팅 작성자 정보가 올바르지 않습니다.")
    cfg = LocalModelConfig(model=model, port=port)
    memory = ConversationMemory(path=memory_path)
    generator = LocalOllamaReplyGenerator(cfg, load_settings(settings_path), memory=memory)
    queue = SessionController()
    output = _TextOutput()
    queue.receive_chat(ChatMessage(str(uuid4()), sender.strip(), text.strip()))
    pipeline = ChatPipeline(queue, generator, output)
    result = pipeline.process_next()
    if result is None:
        raise RuntimeError("응답 처리 결과가 없습니다.")
    warning = (
        "대화는 출력했지만 기억 저장에 실패했습니다. 저장 경로를 확인해 주세요."
        if pipeline.post_delivery_errors else ""
    )
    return ChatResult(reply=result.reply, remembered_count=memory.count(), warning=warning)
