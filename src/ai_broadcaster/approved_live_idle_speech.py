"""기존 실제 공식 AI 방송 세션의 명시 승인형 무채팅 발화 조정기.

로컬 단조시계와 현재 공개 채팅 FIFO의 실제 미처리 건수만 판단한다.
이 모듈은 OBS·WebSocket·채팅·음성에 직접 접근하지 않으며, 운영자가
입력해 승인한 텍스트만 기존 공식 Live2D 단일 작업자에게 전달한다.
한 무채팅 구간에는 단 한 번만 후보를 반환하고, 새 채팅이 접수돼야
다음 구간을 시작한다. 모델·음성·캐릭터 설정은 변경하지 않는다.
"""
from __future__ import annotations

import math
import time
from typing import Callable


class ApprovedLiveIdleSpeech:
    """운영자 승인한 공식 Live2D 방송에서만 한 번씩 발화하도록 제어."""

    def __init__(
        self, *, threshold_seconds: int, utterance: str,
        operator_approved: bool = False,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if operator_approved is not True:
            raise PermissionError("공식 AI의 자발 발화는 운영자 별도 승인이 필요합니다.")
        if type(threshold_seconds) is not int or not 30 <= threshold_seconds <= 3600:
            raise ValueError("무채팅 발화 기준은 30~3600초 정수여야 합니다.")
        if type(utterance) is not str or not 1 <= len(utterance.strip()) <= 240:
            raise ValueError("운영자 자발 발화 문구는 1~240자여야 합니다.")
        if any(ord(char) < 32 or ord(char) == 127 for char in utterance):
            raise ValueError("자발 발화 문구에는 줄바꿈·제어 문자가 허용되지 않습니다.")
        if not callable(clock):
            raise TypeError("무채팅 시계 함수가 올바르지 않습니다.")
        self.threshold_seconds = threshold_seconds
        self.utterance = utterance.strip()
        self._clock = clock
        self._last_activity = self._checked_time()
        self._used = False
        self._attempted = 0

    def _checked_time(self) -> float:
        now = self._clock()
        if type(now) not in (float, int) or not math.isfinite(now) or now < 0:
            raise ValueError("무채팅 관찰 시계 값이 올바르지 않습니다.")
        return float(now)

    def note_chat(self) -> None:
        """새로 처리할 실제 메시지가 도착했으므로 무채팅 시계 초기화."""
        now = self._checked_time()
        if now < self._last_activity:
            raise RuntimeError("무채팅 단조시계가 역행했습니다.")
        self._last_activity = now
        self._used = False

    def next_if_quiet(self, *, pending_count: int, sending: bool = False) -> str | None:
        """실제 FIFO/SQLite에 보류 메시지가 없어야만 발화 문구를 반환.

        호출자만 음성 발화를 전송할 수 있으며, 반환 직전 _used를
        먼저 True로 바꿔 네트워크 불확실 응답에도 중복 발화하지 않는다.
        """
        if type(pending_count) is not int or pending_count < 0:
            raise ValueError("실제 미처리 공개 채팅 건수가 올바르지 않습니다.")
        if type(sending) is not bool:
            raise ValueError("공식 AI 전송 중 여부가 올바르지 않습니다.")
        now = self._checked_time()
        if now < self._last_activity:
            raise RuntimeError("무채팅 단조시계가 역행했습니다.")
        if (pending_count or sending or self._used
                or now - self._last_activity < self.threshold_seconds):
            return None
        self._used = True
        self._attempted += 1
        return self.utterance

    @property
    def attempted(self) -> int:
        """출력 성공이 아닌, 공식 Live2D 요청을 허가한 횟수."""
        return self._attempted
