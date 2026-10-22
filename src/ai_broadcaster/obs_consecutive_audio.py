# -*- coding: utf-8 -*-
"""연속 OBS 관찰 구간에서 실제 측정된 선택 오디오 시각을 안전하게 결합.

사용자 채팅/음성 본문을 저장하지 않는다. OBS 송출/녹화 동작도 없다.
"""
from __future__ import annotations
import math
from typing import Iterable

def _valid_time(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value > 0

def collect_obs_audio_times(
    observations: Iterable[tuple[float, float, object]],
    mouth_first: float,
    mouth_last: float,
    *,
    near_seconds: float = 0.2,
) -> tuple[tuple[float, ...], int]:
    """실제 RMS/입 움직임 구간 근접 표본만 순서대로 결합한다.

    간격을 임의 보간하지 않는다. 선택된 경로와 OBS 장면 후보가
    확인되지 않은 구간, 시간 역행/중복 표본은 포함하지 않는다.
    """
    if not (_valid_time(mouth_first) and _valid_time(mouth_last)
            and mouth_first < mouth_last
            and type(near_seconds) in (int, float)
            and math.isfinite(near_seconds) and 0 <= near_seconds <= 1.0):
        return (), 0
    collected: list[float] = []
    window_count = 0
    for began, ended, sample in observations:
        if not (_valid_time(began) and _valid_time(ended) and began < ended
                and bool(getattr(sample, "coherent_media_candidate", False))):
            continue
        audio = getattr(sample, "audio", None)
        first = getattr(audio, "first_selected_signal_monotonic", None)
        last = getattr(audio, "last_selected_signal_monotonic", None)
        times = getattr(audio, "selected_signal_sample_times", ())
        if not (_valid_time(first) and _valid_time(last)
                and began <= first < last <= ended
                and first < mouth_last and last > mouth_first
                and isinstance(times, tuple) and times
                and all(_valid_time(v) for v in times)
                and all(x < y for x, y in zip(times, times[1:]))
                and first <= times[0] <= times[-1] <= last):
            continue
        near = [t for t in times if mouth_first - near_seconds <= t <= mouth_last + near_seconds]
        if not near:
            continue
        if collected and near[0] <= collected[-1]:
            continue
        collected.extend(near)
        window_count += 1
    return tuple(collected), window_count
