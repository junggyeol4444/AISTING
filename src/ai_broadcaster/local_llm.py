"""선택적 무료 로컬 Ollama AI 텍스트 응답 어댑터.

불러오기/생성은 통신하지 않으며, generate() 호출 때만 이미 실행 중인
127.0.0.1 Ollama로 접속한다. 모델 설치/다운로드/방송 송출은 하지 않는다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import HTTPHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .session import ChatMessage
from .operator_settings import validate_settings
from .conversation_memory import ConversationMemory


class LocalModelError(RuntimeError):
    """로컬 모델 연결 또는 응답 문제."""


class _NoRedirect(HTTPRedirectHandler):
    """외부 URL 등으로 HTTP 리다이렉트하는 것을 금지."""

    def redirect_request(self, req: Request, fp: object, code: int,
                         msg: str, headers: object, newurl: str) -> None:
        return None


@dataclass(frozen=True)
class LocalModelConfig:
    model: str
    port: int = 11434
    timeout_seconds: float = 30.0
    max_reply_chars: int = 6000
    max_context_exchanges: int = 8

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not re.fullmatch(
            r"[a-zA-Z0-9_.:/-]{1,120}", self.model
        ):
            raise ValueError("올바른 로컬 모델 이름이 필요합니다.")
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError("포트 번호가 잘못됐습니다.")
        if (type(self.timeout_seconds) not in (float, int)
                or not 0 < self.timeout_seconds <= 120):
            raise ValueError("응답 제한 시간은 0~120초 범위로 지정합니다.")
        if type(self.max_reply_chars) is not int or not 1 <= self.max_reply_chars <= 20000:
            raise ValueError("응답 길이 제한이 잘못됐습니다.")
        if type(self.max_context_exchanges) is not int or not 0 <= self.max_context_exchanges <= 40:
            raise ValueError("최근 대화 수는 0~40이어야 합니다.")

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}/api/chat"


def persona_prompt(settings: dict[str, Any]) -> str:
    """운영자가 고른 캐릭터의 기초만 반영. 행동 연기는 강제하지 않는다."""
    p = validate_settings(settings)["persona"]
    return (
        f"너는 AI 버추얼 방송인 '{p['name']}'이야.\n"
        f"캐릭터 설정: {p['gender']}\n"
        f"성격: {p['traits']}\n"
        f"말투: {p['speech_style']}\n"
        "한국어로 자연스럽게 답해. 모든 채팅에 기본적으로 반응해.\n"
        "인위적인 응답 지연이나 메시지 선별은 기본으로 적용하지 마.\n"
        "무엇이 자연스러운지는 운영자가 판단하고 조정해."
    )


class LocalOllamaReplyGenerator:
    """ChatPipeline ReplyGenerator 규약을 구현하는 로컬 전용 연결."""

    def __init__(
        self, config: LocalModelConfig, settings: dict[str, Any],
        memory: ConversationMemory | None = None,
    ) -> None:
        if not isinstance(config, LocalModelConfig):
            raise TypeError("LocalModelConfig가 필요합니다.")
        if memory is not None and not isinstance(memory, ConversationMemory):
            raise TypeError("ConversationMemory가 필요합니다.")
        self.config = config
        self.system = persona_prompt(settings)
        self.memory = memory
        # Ollama 서버 자체의 단계별 실측값. 텍스트·계정 정보는 저장하지 않는다.
        self.last_server_timings_seconds: dict[str, float] | None = None
        # 프록시와 리다이렉트 사용을 차단하여 localhost 외 유출을 피함.
        self._opener = build_opener(ProxyHandler({}), HTTPHandler(), _NoRedirect())

    def generate(self, message: ChatMessage) -> str:
        self.last_server_timings_seconds = None
        if not isinstance(message, ChatMessage):
            raise TypeError("ChatMessage가 필요합니다.")
        messages = [{"role": "system", "content": self.system}]
        if self.memory is not None:
            for exchange in self.memory.recent(self.config.max_context_exchanges):
                messages.append({
                    "role": "user", "content": f"{exchange.sender}: {exchange.user_text}",
                })
                messages.append({"role": "assistant", "content": exchange.reply})
        messages.append({"role": "user", "content": f"{message.sender}: {message.text}"})
        payload = {"model": self.config.model, "stream": False, "messages": messages}
        request = Request(
            self.config.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read(1_000_001)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise LocalModelError("로컬 AI 모델이 응답하지 않거나 요청을 거부했습니다.") from exc
        if len(raw) > 1_000_000:
            raise LocalModelError("로컬 AI 응답이 너무 깁니다.")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise LocalModelError("로컬 AI 응답 형식 오류") from exc
        if not isinstance(data, dict) or not isinstance(data.get("message"), dict):
            raise LocalModelError("로컬 AI 응답에 message가 없습니다.")
        reply = data["message"].get("content")
        if not isinstance(reply, str) or not reply.strip():
            raise LocalModelError("로컬 AI 응답 내용이 비어 있습니다.")
        if len(reply) > self.config.max_reply_chars:
            raise LocalModelError("로컬 AI 응답 길이 제한을 넘었습니다.")
        # Ollama는 서버 내부 구간을 나노초로 보고한다. 제공하지 않거나
        # 유효하지 않으면 0으로 추정하지 않는다. 본래 응답은 그대로 유지한다.
        stages = {}
        for key in ("load_duration", "prompt_eval_duration", "eval_duration", "total_duration"):
            duration = data.get(key)
            if type(duration) is int and 0 <= duration <= 10**18:
                stages[key] = round(duration / 1_000_000_000, 6)
        self.last_server_timings_seconds = stages or None
        return reply

    def generate_stream(self, message: ChatMessage,
                        on_chunk: Callable[[str], None]) -> str:
        """Ollama의 실제 NDJSON 생성 청크를 즉시 관찰하되 전체 답변만 확정.

        운영자가 GUI에서 선택한 세션에 한해 사용한다. 중간 청크는
        대화 기억·실제 방송/채팅/음성에 전달하지 않는다.
        응답 스트림이 끝나지 않으면 원래 ChatPipeline은 출력/저장하지 않는다.
        """
        self.last_server_timings_seconds = None
        if not isinstance(message, ChatMessage) or not callable(on_chunk):
            raise TypeError("로컬 AI 스트리밍 입력과 중간 표시 함수 오류")
        messages = [{"role": "system", "content": self.system}]
        if self.memory is not None:
            for exchange in self.memory.recent(self.config.max_context_exchanges):
                messages.append({
                    "role": "user", "content": f"{exchange.sender}: {exchange.user_text}",
                })
                messages.append({"role": "assistant", "content": exchange.reply})
        messages.append({"role": "user", "content": f"{message.sender}: {message.text}"})
        # num_predict, keep_alive 등 사용자 미승인 옵션을 넣지 않는다.
        request = Request(
            self.config.endpoint,
            data=json.dumps({"model": self.config.model, "stream": True,
                             "messages": messages},
                            ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Accept": "application/x-ndjson"},
            method="POST",
        )
        pieces: list[str] = []
        chars = total_bytes = 0
        finished = False
        last_packet = None
        try:
            with self._opener.open(
                    request, timeout=self.config.timeout_seconds) as response:
                while True:
                    line = response.readline(1_000_001)
                    if not line:
                        break
                    total_bytes += len(line)
                    if total_bytes > 1_000_000 or len(line) > 1_000_000:
                        raise LocalModelError("로컬 AI 스트리밍 응답 한도 초과")
                    try:
                        packet = json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError, ValueError) as exc:
                        raise LocalModelError("로컬 AI 스트리밍 조각 형식 오류") from exc
                    if not isinstance(packet, dict) or packet.get("error"):
                        raise LocalModelError("로컬 AI 스트리밍 생성 오류")
                    part = packet.get("message")
                    if not isinstance(part, dict):
                        raise LocalModelError("로컬 AI 스트리밍 응답 내용 형식 오류")
                    delta = part.get("content", "")
                    if not isinstance(delta, str):
                        raise LocalModelError("로컬 AI 스트리밍 텍스트 형식 오류")
                    chars += len(delta)
                    if chars > self.config.max_reply_chars:
                        raise LocalModelError("로컬 AI 응답 길이 제한을 넘었습니다.")
                    if delta:
                        pieces.append(delta)
                        on_chunk(delta)
                    done = packet.get("done")
                    if type(done) is not bool:
                        raise LocalModelError("로컬 AI 스트리밍 완료 플래그 오류")
                    if done:
                        finished = True
                        last_packet = packet
                        break
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise LocalModelError("로컬 AI 스트리밍 연결 또는 수신 시간 초과") from exc
        if not finished:
            raise LocalModelError("로컬 AI 스트리밍 완료 확인 실패 · 중간 답변 저장 금지")
        reply = "".join(pieces)
        if not reply.strip():
            raise LocalModelError("로컬 AI 스트리밍 응답 내용이 비어 있습니다.")
        stages = {}
        for key in ("load_duration", "prompt_eval_duration",
                    "eval_duration", "total_duration"):
            value = last_packet.get(key)
            if type(value) is int and 0 <= value <= 10**18:
                stages[key] = round(value / 1_000_000_000, 6)
        self.last_server_timings_seconds = stages or None
        return reply

    def on_delivered(self, message: ChatMessage, reply: str) -> None:
        """실제로 출력한 뒤에만 SQLite에 대화 내용을 보관한다."""
        if self.memory is not None:
            self.memory.append(message, reply)
