"""Windows EXE의 수동 로컬 AI 대화 테스트 실행부.

사용자가 '전송'을 눌러야만 PC에 이미 설치된 Ollama와 연결한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from uuid import uuid4

from .chat_pipeline import ChatPipeline
from .conversation_memory import ConversationMemory, DEFAULT_MEMORY_FILE
from .local_llm import LocalModelConfig, LocalOllamaReplyGenerator
from .operator_settings import load_settings, DEFAULT_FILE
from .offline_settings import active_persona, load_settings as load_gui_settings
from .session import ChatMessage, SessionController


@dataclass(frozen=True)
class ChatResult:
    reply: str
    remembered_count: int
    warning: str = ""
    # Ollama가 실제 제공한 서버 구간(초)만 선택적으로 전달한다.
    ollama_server_timings_seconds: dict[str, float] | None = None


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
    use_committed_gui_character: bool = False,
    relevant_memory: bool = False,
) -> ChatResult:
    if not isinstance(text, str) or not text.strip() or len(text) > 4000:
        raise ValueError("내용은 공백이 아닌 1~4000글자로 입력해 주세요.")
    if not isinstance(sender, str) or not sender.strip() or len(sender) > 160:
        raise ValueError("채팅 작성자 정보가 올바르지 않습니다.")
    if type(relevant_memory) is not bool:
        raise ValueError("과거 관련 기억 선택값이 올바르지 않습니다.")
    cfg = LocalModelConfig(
        model=model, port=port,
        max_relevant_exchanges=2 if relevant_memory else 0)
    memory = ConversationMemory(path=memory_path)
    model_settings = load_settings(settings_path)
    if use_committed_gui_character:
        # The real AISTING operator GUI persists the chosen character in
        # offline_settings.json. The older standalone local-chat settings
        # file is NOT authoritative for the operator's confirmed identity.
        confirmed = active_persona(load_gui_settings())
        model_settings["persona"]["name"] = confirmed["name"]
        model_settings["persona"]["traits"] = confirmed["character"]
        model_settings["persona"]["speech_style"] = confirmed["style"]
    generator = LocalOllamaReplyGenerator(cfg, model_settings, memory=memory)
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
    return ChatResult(
        reply=result.reply, remembered_count=memory.count(), warning=warning,
        ollama_server_timings_seconds=getattr(
            generator, "last_server_timings_seconds", None))


class LocalChatRunner:
    """한 번 승인된 Windows 수신 세션에서 기존 Ollama 클라이언트 재사용.

    요청마다 모델 설정·캐릭터를 다시 파싱하고 HTTP 연결 객체를
    재생성하는 비용을 줄인다. FIFO 처리 순서, SQLite 기록 시점,
    각 채팅 메시지의 개별 ID와 원래 답변 길이 설정은 유지한다.
    모델 병렬 실행·출력 생략·토큰 상한/keep_alive 강제 변경 없음.
    """

    def __init__(
        self, model: str, *, port: int = 11434,
        settings_path: Path = DEFAULT_FILE,
        memory_path: Path = DEFAULT_MEMORY_FILE,
        use_committed_gui_character: bool = True,
        broadcast_facts: str = "",
        relevant_memory: bool = False,
    ) -> None:
        if type(relevant_memory) is not bool:
            raise ValueError("과거 관련 기억 선택값이 올바르지 않습니다.")
        config = LocalModelConfig(
            model=model, port=port,
            max_relevant_exchanges=2 if relevant_memory else 0)
        self.memory = ConversationMemory(path=memory_path)
        settings = load_settings(settings_path)
        if use_committed_gui_character:
            confirmed = active_persona(load_gui_settings())
            settings["persona"]["name"] = confirmed["name"]
            settings["persona"]["traits"] = confirmed["character"]
            settings["persona"]["speech_style"] = confirmed["style"]
        self.generator = LocalOllamaReplyGenerator(
            config, settings, memory=self.memory,
            broadcast_facts=broadcast_facts)

    def reply(self, text: str, *, sender: str,
              on_stream_chunk: Callable[[str], None] | None = None,
              should_cancel: Callable[[], bool] | None = None) -> ChatResult:
        if should_cancel is not None and not callable(should_cancel):
            raise TypeError("로컬 AI 처리 중지 확인 함수 오류")
        if on_stream_chunk is not None and not callable(on_stream_chunk):
            raise TypeError("로컬 생성 진행 표시 함수 오류")
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            raise ValueError("내용은 공백이 아닌 1~4000글자로 입력해 주세요.")
        if not isinstance(sender, str) or not sender.strip() or len(sender) > 160:
            raise ValueError("채팅 작성자 정보가 올바르지 않습니다.")
        # 원래의 요청별 임시 FIFO/발화 객체와 SQLite 저장 의미를
        # 그대로 지켜, 한 채팅의 추론 실패가 다음 채팅의 답변을
        # 잘못 대신하게 하거나 이전 출력을 재전송하지 않는다.
        fifo = SessionController()
        fifo.receive_chat(ChatMessage(str(uuid4()), sender.strip(), text.strip()))
        output = _TextOutput()
        pipeline = ChatPipeline(fifo, self.generator, output)
        outcome = (pipeline.process_next(
            on_stream_chunk=on_stream_chunk, should_cancel=should_cancel)
            if on_stream_chunk is not None else
            (pipeline.process_next(should_cancel=should_cancel)
             if should_cancel is not None else pipeline.process_next()))
        if outcome is None:
            raise RuntimeError("로컬 AI 응답 처리 결과가 없습니다.")
        return ChatResult(
            reply=outcome.reply, remembered_count=self.memory.count(),
            warning=("대화는 출력했지만 기억 저장에 실패했습니다. 저장 경로를 확인해 주세요."
                     if pipeline.post_delivery_errors else ""),
            ollama_server_timings_seconds=getattr(
                self.generator, "last_server_timings_seconds", None),
        )
