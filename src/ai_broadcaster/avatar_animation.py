"""데스크톱 2D 아바타 말하기 상태 및 미리보기 프레임 제어.

음성 출력 유무를 표시하는 *동작 데모*로, PCM 음소 분석이나 Live2D 립싱크가 아님.
"""
from __future__ import annotations

from threading import Lock


class SpeechActivity:
    """서로 다른 탭의 재생이 중첩돼도 아바타는 실제 재생이 모두 끝나야 쉬는 상태로 돌아감."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._sources: set[str] = set()

    @staticmethod
    def _validate_source(source: str) -> None:
        if not isinstance(source, str) or not 1 <= len(source) <= 80:
            raise ValueError("유효한 음성 이벤트 출처가 필요합니다.")

    def start(self, source: str) -> None:
        self._validate_source(source)
        with self._lock:
            self._sources.add(source)

    def finish(self, source: str) -> None:
        self._validate_source(source)
        with self._lock:
            self._sources.discard(source)

    @property
    def talking(self) -> bool:
        with self._lock:
            return bool(self._sources)

    @property
    def active_sources(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._sources)


def mouth_frame(talking: bool, frame: int) -> int:
    """0=닫힘, 1=작게, 2=보통, 3=크게. 음성 활동 중 애니메이션 데모."""
    if type(talking) is not bool:
        raise TypeError("talking은 bool이어야 합니다.")
    if type(frame) is not int or frame < 0:
        raise ValueError("프레임 번호는 0 이상의 정수여야 합니다.")
    return (1, 2, 3, 2, 1, 2)[frame % 6] if talking else 0


def blink_frame(frame: int) -> bool:
    """눈 깜박이기는 재생 상태와 무관하게 조용히 동작."""
    if type(frame) is not int or frame < 0:
        raise ValueError("프레임 번호는 0 이상의 정수여야 합니다.")
    return frame % 47 in (0, 1)
