"""기존 공식 WAV PCM 음량과 Live2D 렌더러 RMS의 시간 정렬 후보 분석.

동일 공식 관찰에서 이미 취득한 비식별 수치만 사용한다.
실제 음원 파일·채팅 본문·사용자 계정·개인 식별정보를 저장하지 않는다.
PCM과 렌더러 RMS의 상관은 동일 발화/음원 권리/OBS 송출/시청자 수신의
인과관계 증명이 아니다. 관찰하지 않은 표본은 합성하지 않는다.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Iterable


@dataclass(frozen=True)
class PcmCubismAlignmentCandidate:
    """실제 공식 세션의 첫 WAV 후보와 렌더러 RMS 후보의 상관 정보."""
    status: str
    sample_count: int = 0
    lag_seconds: float | None = None
    correlation: float | None = None
    # 렌더러 Cubism 입 움직임·RMS 동시 관찰 여부. 음원 인과성은 아님.
    cubism_mouth_observed: bool = False


def _pearson(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 8:
        return None
    count = len(pairs)
    ax = sum(a for a, _ in pairs) / count
    by = sum(b for _, b in pairs) / count
    va = sum((a - ax) ** 2 for a, _ in pairs)
    vb = sum((b - by) ** 2 for _, b in pairs)
    if va <= 1e-8 or vb <= 1e-8:
        return None
    cov = sum((a - ax) * (b - by) for a, b in pairs)
    return max(-1.0, min(1.0, cov / sqrt(va * vb)))


def analyze_pcm_cubism_alignment(
    pcm_envelope: Iterable[float],
    renderer_rms_samples: Iterable[tuple[float, float]],
    *,
    mouth_observed: bool,
) -> PcmCubismAlignmentCandidate:
    """이미 측정된 첫 WAV 50ms RMS와 수신 후 렌더러 RMS를 대조한다.

    렌더러 시각은 WAV 수신 후 상대초, PCM 음량은 50ms 구간이다.
    0~1초 지연 후보를 50ms 단위로 대조하며 각 후보에 최소 8개
    관찰값과 실제 양측 음량 변화가 있어야만 상관을 반환한다.
    최대 상관만 골라내는 탐색이므로 값이 높아도 동일 발화 증명은 아니다.
    """
    if type(mouth_observed) is not bool:
        return PcmCubismAlignmentCandidate("관찰값오류")
    try:
        pcm = tuple(pcm_envelope)
        renderer = tuple(renderer_rms_samples)
    except (TypeError, ValueError):
        return PcmCubismAlignmentCandidate("관찰값오류")
    if (not 8 <= len(pcm) <= 160 or not 8 <= len(renderer) <= 100):
        return PcmCubismAlignmentCandidate("표본부족",
                                           cubism_mouth_observed=mouth_observed)
    if any(type(x) not in (float, int) or not isfinite(x)
           or not 0 <= x <= 1 for x in pcm):
        return PcmCubismAlignmentCandidate("관찰값오류",
                                           cubism_mouth_observed=mouth_observed)
    last = -1.0
    for item in renderer:
        if (not isinstance(item, (list, tuple)) or len(item) != 2
                or any(type(x) not in (int, float) or not isfinite(x)
                       for x in item)
                or not 0 <= item[0] <= 12
                or not 0 <= item[1] <= 10
                or item[0] <= last):
            return PcmCubismAlignmentCandidate("관찰값오류",
                                               cubism_mouth_observed=mouth_observed)
        last = float(item[0])
    best: tuple[float, float, int] | None = None
    for lag_index in range(21):
        lag = lag_index * 0.05
        pairs = []
        for t, rms in renderer:
            position = (float(t) - lag) / 0.05
            if position < 0 or position >= len(pcm):
                continue
            # nearest 50ms bin, do not extrapolate beyond observed PCM.
            index = min(len(pcm) - 1, int(position + 0.5))
            pairs.append((float(pcm[index]), float(rms)))
        corr = _pearson(pairs)
        if corr is None:
            continue
        # Prefer more independent observed samples when correlation ties.
        if best is None or (corr, len(pairs), -lag) > (best[0], best[2], -best[1]):
            best = (corr, lag, len(pairs))
    if best is None:
        return PcmCubismAlignmentCandidate("변화·중첩표본부족",
                                           cubism_mouth_observed=mouth_observed)
    return PcmCubismAlignmentCandidate(
        "입·음량동시후보" if mouth_observed else "렌더러음량후보",
        sample_count=best[2], lag_seconds=round(best[1], 3),
        correlation=round(best[0], 4),
        cubism_mouth_observed=mouth_observed,
    )


class LivePcmCubismAlignmentMetrics:
    """4플랫폼별 실제 공식 관찰 후보 통계. 텍스트·음성·신원 저장 금지."""

    def __init__(self, *, capacity: int = 512):
        if type(capacity) is not int or not 1 <= capacity <= 10000:
            raise ValueError("실측 후보 보관 한도가 올바르지 않습니다.")
        self._values: deque[float] = deque(maxlen=capacity)
        self.observations = 0
        self.candidates = 0
        self.missing = 0
        self.mouth_candidates = 0
        self.last_lag_seconds: float | None = None

    def observe(self, result: PcmCubismAlignmentCandidate) -> None:
        self.observations += 1
        if result.correlation is None:
            self.missing += 1
            return
        self.candidates += 1
        self.mouth_candidates += int(result.cubism_mouth_observed)
        self._values.append(result.correlation)
        self.last_lag_seconds = result.lag_seconds

    def snapshot(self) -> dict[str, int | float | None]:
        return {
            "관찰시도": self.observations,
            "상관후보": self.candidates,
            "후보미충족": self.missing,
            "Cubism입동시후보": self.mouth_candidates,
            "최근후보": len(self._values),
            "최신지연후보초": self.last_lag_seconds,
            "최근최고상관후보": max(self._values) if self._values else None,
        }
