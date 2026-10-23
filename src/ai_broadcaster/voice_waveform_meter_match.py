# -*- coding: utf-8 -*-
"""권리 확인된 실제 PCM WAV의 음량 윤곽과 OBS 선택 미터의 관측 비교.

원본 음성, 개인 식별자, OBS 미터 레벨을 영구 기록하지 않는다.
소스 파형의 동일성/시청자 전달 성공 증빙은 아니다.
"""
from __future__ import annotations

import io
import math
import struct
import wave

def _rms_pcm16_windows(raw: bytes, *, window_seconds: float = 0.05) -> tuple[float, ...]:
    """16비트 PCM WAV(1~2ch) 50ms 단위 RMS. 압축/float는 미지원."""
    if type(raw) is not bytes or not 44 <= len(raw) <= 20_000_000:
        return ()
    try:
        with wave.open(io.BytesIO(raw), "rb") as f:
            if (f.getcomptype() != "NONE" or f.getsampwidth() != 2
                    or f.getnchannels() not in (1, 2)
                    or not 8000 <= f.getframerate() <= 192000):
                return ()
            frame_size = max(1, round(f.getframerate() * window_seconds))
            if f.getnframes() < frame_size * 2:
                return ()
            rms = []
            # 8초 관찰 구간 이외에는 길이를 늘려 비교하지 않는다.
            for _ in range(min(200, math.ceil(f.getnframes() / frame_size))):
                block = f.readframes(frame_size)
                if len(block) < 4 or len(block) % 2:
                    break
                count = len(block) // 2
                sum_sq = sum(float(v) * v for (v,) in struct.iter_unpack("<h", block))
                rms.append(math.sqrt(sum_sq / count) / 32768.0)
            return tuple(rms)
    except (EOFError, OSError, ValueError, wave.Error, struct.error):
        return ()

def compare_voice_meter_envelope(
    raw_wav: bytes,
    meter_samples: tuple[tuple[float, float], ...],
    restart_monotonic: float | None,
) -> tuple[float | None, int]:
    """관측 이벤트의 강도 변화를 실제 PCM WAV의 상대 시간과 비교.

    추정 재생 지연은 0~1초 범위에 한정하고, 그중 가장 비슷한
    값만 보고한다. 녹화/전송이나 출력의 검증으로 격상하지 않는다.
    """
    if (type(restart_monotonic) not in (int, float)
            or not math.isfinite(restart_monotonic)
            or restart_monotonic <= 0
            or not isinstance(meter_samples, tuple)
            or len(meter_samples) < 8
            or len(meter_samples) > 128):
        return None, 0
    envelope = _rms_pcm16_windows(raw_wav)
    if len(envelope) < 12:
        return None, 0
    if any(not isinstance(pair, tuple) or len(pair) != 2
           or any(type(v) not in (int, float) or not math.isfinite(v) for v in pair)
           for pair in meter_samples):
        return None, 0
    ordered = [(float(t), float(level)) for t, level in meter_samples
               if t >= restart_monotonic and 0.001 < level <= 20]
    if (len(ordered) < 8 or ordered[-1][0] - ordered[0][0] < 0.5
            or any(a[0] >= b[0] for a, b in zip(ordered, ordered[1:]))):
        return None, 0
    best = None
    best_count = 0
    for lag_ticks in range(0, 21):  # 0~1초, 50ms 분해능
        lag = lag_ticks * 0.05
        pairs = []
        used_bins = set()
        for t, level in ordered:
            index = int((t - restart_monotonic - lag) / 0.05)
            if 0 <= index < len(envelope) and index not in used_bins:
                used_bins.add(index)
                pairs.append((envelope[index], level))
        if len(pairs) < 8:
            continue
        x_bar = sum(p[0] for p in pairs) / len(pairs)
        y_bar = sum(p[1] for p in pairs) / len(pairs)
        x_dev = [p[0] - x_bar for p in pairs]
        y_dev = [p[1] - y_bar for p in pairs]
        xx = sum(v*v for v in x_dev)
        yy = sum(v*v for v in y_dev)
        if xx < 1e-7 or yy < 1e-7:
            continue
        corr = sum(x*y for x, y in zip(x_dev, y_dev)) / math.sqrt(xx*yy)
        if best is None or corr > best:
            best, best_count = corr, len(pairs)
    return (round(max(-1.0, min(1.0, best)), 4), best_count) if best is not None else (None, 0)
