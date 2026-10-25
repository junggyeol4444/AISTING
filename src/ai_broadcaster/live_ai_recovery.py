"""4플랫폼 단일 AI FIFO의 일시적인 로컬 Ollama 실패 복구.

사용자가 선택한 원래 모델/설정/페르소나/대화 SQLite는 변경하지 않는다.
한 메시지가 처리에 성공하기 전 다음 메시지를 생성하지 않으며,
재시도 한도를 넘으면 호출자가 세션을 중지해 SQLite 원본을 보존한다.
공식 WebSocket 전송이나 GPT-SoVITS에는 중복 발화 위험 때문에 적용 금지.
"""
from __future__ import annotations

from threading import Event
from typing import Callable, TypeVar

from .local_llm import LocalModelError


Reply = TypeVar("Reply")


class LiveAiRetryExhausted(RuntimeError):
    """원래 채팅이 저장된 상태에서 로컬 모델 복구 시도 종료."""


def run_local_fifo_with_recovery(
    invoke: Callable[[], Reply], *,
    stop: Event | None = None,
    on_retry: Callable[[int, float], None] | None = None,
    max_attempts: int = 6,
) -> Reply:
    """기존 단일 FIFO의 동일 채팅만 제한 횟수 재생성.

    전체 답변 확정/대화 기억 저장은 invoke의 기존 ChatPipeline이
    수행한다. 아직 답변을 확정하지 않은 LocalModelError에 한해 재시도.
    포트/모델/토큰 상한/keep_alive 및 원래 요청에 새 옵션을 넣지 않는다.
    지연은 모델 실패 뒤에만 존재하며 성공 경로에 의도적인 대기 없음.
    """
    if not callable(invoke):
        raise TypeError("기존 로컬 AI 호출 함수가 없습니다.")
    if stop is not None and not isinstance(stop, Event):
        raise TypeError("운영자 Stop 이벤트가 올바르지 않습니다.")
    if on_retry is not None and not callable(on_retry):
        raise TypeError("재시도 현황 알림 함수가 올바르지 않습니다.")
    if type(max_attempts) is not int or not 1 <= max_attempts <= 12:
        raise ValueError("모델 복구 최대 재시도 횟수가 올바르지 않습니다.")
    for attempt in range(1, max_attempts + 1):
        if stop is not None and stop.is_set():
            raise RuntimeError("운영자 중지 · 로컬 AI 재시도 금지")
        try:
            return invoke()
        except LocalModelError as error:
            if stop is not None and stop.is_set():
                raise RuntimeError("운영자 중지 · 로컬 AI 재시도 금지") from error
            if attempt == max_attempts:
                raise LiveAiRetryExhausted(
                    "기존 단일 AI FIFO 처리가 연속 실패하여 다음 채팅을 진행하지 않습니다."
                ) from error
            wait_seconds = min(2 ** (attempt - 1) * 0.5, 8.0)
            if on_retry is not None:
                on_retry(attempt, wait_seconds)
            if stop is not None:
                if stop.wait(wait_seconds):
                    raise RuntimeError("운영자 중지 · 로컬 AI 재시도 금지") from error
            else:
                # 실제 GUI 경로는 반드시 session._stop를 제공한다.
                raise RuntimeError(
                    "운영자 중지 이벤트 없는 로컬 AI 자동 재시도는 불가합니다."
                ) from error
    raise RuntimeError("로컬 AI 재시도 상태가 올바르지 않습니다.")
