"""운영자 승인형 실제 방송 중 한국어 음성·공식 Cubism 생존 연속 감시.

OBS 송출을 시작하거나 임의 장면을 변경하지 않는다. 기존 방송 예약
작업자가 공급한 실제 모델/창의 로컬 생존 여부만 시간에 따라 누적
판정하고 결과를 반환한다. 상태가 불명확한 동안 정상으로 간주하지 않는다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ApprovedMediaHealth:
    """서버·시청자 최종 음성 수신 성공이 아닌 로컬 매체 생존 관측."""

    state: str
    unhealthy_seconds: float
    expired: bool
    recovered: bool


class ApprovedLiveMediaWatchdog:
    """동일 승인 방송 안에서 일시 실패와 30초 연속 실패를 구분."""

    def __init__(self, *, grace_seconds: float = 30.0):
        if (type(grace_seconds) not in (int, float)
                or not math.isfinite(grace_seconds)
                or not 10.0 <= grace_seconds <= 300.0):
            raise ValueError("한국어 음성·Live2D 복구 유예는 10~300초여야 합니다.")
        self.grace_seconds = float(grace_seconds)
        self.reset()

    def reset(self) -> None:
        """다음 사용자 승인 방송에서 이전 실패 시간을 절대 승계하지 않음."""
        self._last_at: float | None = None
        self._unhealthy_since: float | None = None
        self._was_healthy = False

    def observe(self, *, at: float, healthy: bool) -> ApprovedMediaHealth:
        if (type(at) not in (int, float) or not math.isfinite(at)
                or at < 0 or self._last_at is not None and at < self._last_at):
            raise ValueError("실제 방송 관측의 단조시각이 올바르지 않습니다.")
        if type(healthy) is not bool:
            raise ValueError("공식 한국어 음성·Cubism 생존 여부가 불명확합니다.")
        self._last_at = float(at)
        if healthy:
            recovered = self._unhealthy_since is not None
            self._unhealthy_since = None
            self._was_healthy = True
            return ApprovedMediaHealth(
                "공식 Live2D·권리 한국어 음성 연결 로컬 생존 확인"
                " · 실제 시청자 출력은 미확인",
                0.0, False, recovered)
        if self._unhealthy_since is None:
            self._unhealthy_since = float(at)
        duration = max(0.0, float(at) - self._unhealthy_since)
        expired = duration >= self.grace_seconds
        return ApprovedMediaHealth(
            ("공식 Cubism·한국어 음성 로컬 연결 "
             + (f"{duration:.1f}초 연속 미확인 · 소유 OBS 방송 안전 종료 필요"
                if expired else
                f"{duration:.1f}/{self.grace_seconds:.0f}초 연속 미확인 · 자동 재방송 금지")),
            duration, expired, False)
