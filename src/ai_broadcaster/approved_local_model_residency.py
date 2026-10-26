"""사용자가 고른 기존 로컬 Ollama 모델의 승인형 선행 적재.

공개 채팅이 쏟아지는 첫 순간 모델을 디스크에서 로드하는 비용을 줄일
목적으로, 운영자가 선택한 한 모델을 localhost /api/generate의
빈 프롬프트/keep_alive=10m로 로드한다. 임의 모델 다운로드/설치,
요금 서버 전송, 방송/채팅 게시, 합성·훈련을 실행하지 않는다.

서버가 성공을 반환해도 1~3초 답변이나 GPU 모델 상주를 장시간
보증하지 않으며, 추론성능·완료 시청자 전송을 주장하지 않는다.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import HTTPHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .local_llm import LocalModelConfig


class ModelResidencyError(RuntimeError):
    """기존 로컬 모델의 선행 적재 실패."""


class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class ModelResidencyReceipt:
    model: str
    request_seconds: float
    server_load_seconds: float | None
    keep_alive: str = "10m"
    inference_verified: bool = False


class ApprovedLocalModelResidency:
    """수동 선택·명시 승인된 기존 로컬 모델만 준비."""

    def __init__(self, config: LocalModelConfig):
        if not isinstance(config, LocalModelConfig):
            raise TypeError("기존 Ollama 모델 설정을 지정해야 합니다.")
        self._config = config
        self._opener = build_opener(ProxyHandler({}), HTTPHandler(), _RejectRedirect())

    def warm_once(self, *, operator_approved: bool = False,
                  timeout_seconds: float = 60.0) -> ModelResidencyReceipt:
        if operator_approved is not True:
            raise PermissionError("로컬 모델 선행 준비는 운영자 명시 승인이 필요합니다.")
        if (type(timeout_seconds) not in (float, int)
                or not math.isfinite(timeout_seconds)
                or not 1 <= timeout_seconds <= 120):
            raise ValueError("로컬 모델 준비 제한 시간은 1~120초입니다.")
        config = self._config
        # LocalModelConfig.endpoint derives ONLY http://127.0.0.1:<port>/api/chat
        # and model is validated by the existing strict model-name validator.
        url = "http://127.0.0.1:" + str(config.port) + "/api/generate"
        # prompt를 제공하지 않으면 Ollama는 기존 모델만 메모리에 로드.
        # 기존 응답 num_predict=96이나 캐릭터/말투/대화 기억을 변경하지 않음.
        request = Request(
            url,
            data=json.dumps({
                "model": config.model, "stream": False,
                "keep_alive": "10m"
            }, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json",
                     "Accept": "application/json"},
        )
        started = time.monotonic()
        try:
            with self._opener.open(
                    request, timeout=float(timeout_seconds)) as response:
                if response.status != 200:
                    raise ModelResidencyError("로컬 Ollama 모델 적재 승인 응답이 없습니다.")
                raw = response.read(65537)
        except (HTTPError, URLError, TimeoutError, OSError):
            # 로컬 오류 원문에는 사용자 설정 경로나 환경 정보가 있을 수 있음.
            raise ModelResidencyError(
                "기존 로컬 Ollama 모델 준비 실패 · 모델 설치/다운로드 미시도") from None
        if len(raw) > 65536:
            raise ModelResidencyError("로컬 모델 적재 확인 응답 크기 초과")
        try:
            result = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError):
            raise ModelResidencyError("로컬 Ollama 준비 응답 형식을 알 수 없습니다.") from None
        if (not isinstance(result, dict)
                or result.get("model") != config.model
                or result.get("done") is not True
                or result.get("error")):
            raise ModelResidencyError("선택한 기존 Ollama 모델 준비를 확인하지 못했습니다.")
        nanoseconds = result.get("load_duration")
        server_load = (
            round(nanoseconds / 1_000_000_000, 6)
            if type(nanoseconds) is int and 0 <= nanoseconds <= 10**18
            else None)
        return ModelResidencyReceipt(
            model=config.model,
            request_seconds=round(time.monotonic() - started, 6),
            server_load_seconds=server_load)
