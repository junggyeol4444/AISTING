# -*- coding: utf-8 -*-
"""실제 공개 채팅 수신 큐의 진행 중·중단된 대기 관측.

채팅 본문·사용자 식별자·토큰·계정 정보는 저장하지 않는다.
이 계측은 수신기 콜백 이후의 로컬 큐 상태만 설명하며,
플랫폼 서버 누락·시청자 종단간 지연을 증명하지 않는다.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Callable


class LiveQueueWaitTracker:
    """수신 콜백마다 독립된 토큰으로 중첩 대기를 정확히 추적한다."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._active: dict[object, tuple[str, float]] = {}
        self._interrupted: dict[str, tuple[int, float]] = {}

    def begin(self, platform: str) -> object:
        """실제 로컬 수신 큐 적체가 시작된 순간에만 호출한다."""
        if not isinstance(platform, str) or not platform:
            platform = "미분류"
        token = object()
        now = self._clock()
        with self._lock:
            self._active[token] = (platform, now)
        return token

    def finish(self, token: object | None, *, accepted: bool) -> None:
        """큐 수용과 중지·종료를 구분한다. 중단은 성공으로 집계하지 않는다."""
        if token is None:
            return
        now = self._clock()
        with self._lock:
            entry = self._active.pop(token, None)
            if entry is None or accepted:
                return
            platform, began = entry
            elapsed = max(0.0, now - began)
            count, total = self._interrupted.get(platform, (0, 0.0))
            self._interrupted[platform] = (count + 1, total + elapsed)

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        """현재 대기와 중단 대기를 원본 채팅 없이 플랫폼별로 복사한다."""
        now = self._clock()
        with self._lock:
            result: dict[str, dict[str, float | int]] = defaultdict(
                lambda: {"진행중": 0, "진행최장초": 0.0,
                         "중단": 0, "중단누적초": 0.0})
            for platform, (count, total) in self._interrupted.items():
                result[platform]["중단"] = count
                result[platform]["중단누적초"] = total
            for platform, began in self._active.values():
                elapsed = max(0.0, now - began)
                result[platform]["진행중"] += 1
                result[platform]["진행최장초"] = max(
                    result[platform]["진행최장초"], elapsed)
            return {platform: dict(value) for platform, value in result.items()}
