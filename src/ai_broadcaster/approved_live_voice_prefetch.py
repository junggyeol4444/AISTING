"""승인된 한국어 실제 방송에서 다음 음성 구간 한 건만 선행 합성.

현재 구간의 OBS·공식 Cubism 재생을 시작한 뒤에만 다음 구간을
같은 권리 확인된 GPT-SoVITS 모델로 합성한다. 합성 완료 순서가
아니라 원문 구간 순서대로 WAV를 소비한다. 실패/중지 시 다음
구간을 임의로 건너뛰거나 다른 목소리로 대체하지 않는다.
시청자에게 1~3초 내 도착한다는 보장은 아니다.
"""
from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable


class ApprovedVoiceSegmentPrefetch:
    """메모리에 최대 한 구간의 선행 합성 결과만 유지하는 작업자."""

    def __init__(self, synthesize: Callable[[str], object],
                 stop: threading.Event) -> None:
        if not callable(synthesize) or not isinstance(stop, threading.Event):
            raise TypeError("한국어 선행 합성 작업자 인자가 올바르지 않습니다.")
        self._synthesize = synthesize
        self._stop = stop
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="AISTING-다음음성합성")
        self._next_text: str | None = None
        self._future: Future | None = None
        self._closed = False

    def start_next(self, text: str) -> None:
        """현재 WAV 방송 시작 직전에 다음 한 문장만 미리 합성."""
        if self._closed or self._stop.is_set():
            raise RuntimeError("중지된 실제 음성 세션에서 선행 합성을 시작하지 않습니다.")
        if self._future is not None:
            raise RuntimeError("한국어 음성 선행 합성 슬롯은 한 건만 허용합니다.")
        if type(text) is not str or not text.strip():
            raise ValueError("다음 실제 한국어 음성 구간이 비어 있습니다.")
        self._next_text = text
        try:
            self._future = self._executor.submit(self._synthesize, text)
        except BaseException:
            self._next_text = None
            raise

    def take(self, text: str) -> object | None:
        """원래 순번의 WAV만 반환. 첫 구간은 기존 직접 합성 경로 사용."""
        if self._closed or self._stop.is_set():
            raise RuntimeError("중지된 실제 음성 세션의 합성 결과를 재생하지 않습니다.")
        future = self._future
        if future is None:
            return None
        if self._next_text != text:
            raise RuntimeError("실제 음성 구간 FIFO 순서가 일치하지 않습니다.")
        try:
            actual = future.result()
        finally:
            self._future = None
            self._next_text = None
        if self._stop.is_set():
            raise RuntimeError("한국어 음성 선행 합성 도중 중지되었습니다.")
        return actual

    def close(self) -> None:
        """대기 작업 취소. 이미 실행 중인 합성은 송출에 사용하지 않음."""
        if self._closed:
            return
        self._closed = True
        future = self._future
        if future is not None:
            future.cancel()
        self._future = None
        self._next_text = None
        self._executor.shutdown(wait=False, cancel_futures=True)
