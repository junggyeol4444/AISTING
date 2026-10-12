"""선택적 무료 로컬 Ollama AI 텍스트 응답 어댑터.

불러오기/생성은 통신하지 않으며, generate() 호출 때만 이미 실행 중인
127.0.0.1 Ollama로 접속한다. 모델 설치/다운로드/방송 송출은 하지 않는다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .session import ChatMessage
from .operator_settings import validate_settings


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

    def __init__(self, config: LocalModelConfig, settings: dict[str, Any]) -> None:
        if not isinstance(config, LocalModelConfig):
            raise TypeError("LocalModelConfig가 필요합니다.")
        self.config = config
        self.system = persona_prompt(settings)
        # 프록시와 리다이렉트 사용을 차단하여 localhost 외 유출을 피함.
        self._opener = build_opener(ProxyHandler({}), HTTPHandler(), _NoRedirect())

    def generate(self, message: ChatMessage) -> str:
        if not isinstance(message, ChatMessage):
            raise TypeError("ChatMessage가 필요합니다.")
        payload = {
            "model": self.config.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": self.system},
                {"role": "user", "content": f"{message.sender}: {message.text}"},
            ],
        }
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
        return reply
