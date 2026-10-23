# -*- coding: utf-8 -*-
"""동일 공식 WebSocket 수신 PCM16 WAV와 실제 OBS 미터의 음량 후보 비교.

승인받은 기존 단일 질문/관찰 경로에서만 호출된다. WAV 본문·채팅,
음성 파형·OBS 미터 원본을 로그나 파일에 저장하지 않는다.
상관값은 실제 OBS 출력 또는 음성/영상 동일성의 증명이 아니다.
"""
from __future__ import annotations

import math


def compare_official_pcm_obs_levels(
    envelope: tuple[float, ...],
    received_monotonic: float,
    meter_levels: tuple[tuple[float, float], ...],
) -> tuple[float | None, int, float | None]:
    """50ms WAV RMS의 실제 음량 변화와 OBS 입력 레벨 변화를 대조.

    공식 WebSocket 수신 시점 이후 OBS 레벨만 허용한다.
    임의의 가상 OBS 프레임·무음·WAV 재생 상태는 생성하지 않는다.
    실제 OS 단조시계 한 종류의 관측값만 사용하고 0~3초 재생
    지연 후보만 비교한다. 결과는 (최대 상관, 표본수, 후보 지연).
    """
    if (not isinstance(envelope, tuple) or not 12 <= len(envelope) <= 160
            or type(received_monotonic) not in (int, float)
            or not math.isfinite(received_monotonic)
            or received_monotonic <= 0
            or not isinstance(meter_levels, tuple)
            or len(meter_levels) < 12 or len(meter_levels) > 4096):
        return None, 0, None
    if (any(type(x) not in (int, float) or not math.isfinite(x)
            or x < 0 or x > 1 for x in envelope)
            or any(not isinstance(p, tuple) or len(p) != 2
                   or type(p[0]) not in (int, float)
                   or type(p[1]) not in (int, float)
                   or not math.isfinite(p[0]) or not math.isfinite(p[1])
                   or p[0] <= 0 or not 0 <= p[1] <= 20
                   for p in meter_levels)
            or any(a[0] >= b[0] for a, b in zip(meter_levels, meter_levels[1:]))):
        return None, 0, None
    samples = [(float(t) - received_monotonic, float(v)) for t, v in meter_levels
               if received_monotonic <= t <= received_monotonic + 12.0]
    if len(samples) < 12 or samples[-1][0] - samples[0][0] < 0.55:
        return None, 0, None
    best_score: float | None = None
    best_n = 0
    best_lag: float | None = None
    # 재생 지연 0..3초까지 50ms 후보만 계산. 높은 상관을 찾았다고
    # 실제 지연(또는 파형 동일성)을 확정하지 않는다.
    for ticks in range(61):
        lag = ticks * 0.05
        used: set[int] = set()
        paired = []
        for elapsed, observed_peak in samples:
            relative = elapsed - lag
            if relative < 0:
                continue
            wav_index = int(relative / 0.05)
            if wav_index < len(envelope) and wav_index not in used:
                used.add(wav_index)
                paired.append((float(envelope[wav_index]), observed_peak))
        if len(paired) < 12:
            continue
        # 상관을 계산하려면 발화와 쉼에 따른 실제 변화가 있어야 한다.
        mean_wav = sum(x for x, _ in paired) / len(paired)
        mean_obs = sum(y for _, y in paired) / len(paired)
        wav_delta = [x-mean_wav for x, _ in paired]
        obs_delta = [y-mean_obs for _, y in paired]
        var_wav = sum(d*d for d in wav_delta)
        var_obs = sum(d*d for d in obs_delta)
        if var_wav < 1e-7 or var_obs < 1e-7:
            continue
        corr = sum(x*y for x, y in zip(wav_delta, obs_delta)) / math.sqrt(
            var_wav * var_obs)
        if best_score is None or corr > best_score:
            best_score = corr
            best_n = len(paired)
            best_lag = lag
    if best_score is None:
        return None, 0, None
    return round(max(-1.0, min(1.0, best_score)), 4), best_n, round(best_lag, 3)
