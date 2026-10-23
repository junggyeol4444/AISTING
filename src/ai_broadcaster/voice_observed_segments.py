# -*- coding: utf-8 -*-
"""실제 GPT-SoVITS PCM WAV 발화/쉼과 OBS 입력 레벨 관측의 시간 대응.

입력 WAV와 미터 샘플은 메모리에서만 사용한다. 이 값은 파형 복제,
인코더 출력, 시청자 전달, 발화자의 권리를 증명하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .voice_waveform_meter_match import _rms_pcm16_windows


@dataclass(frozen=True)
class VoiceObsSegmentEvidence:
    score: float | None = None
    samples: int = 0
    voiced_samples: int = 0
    silent_samples: int = 0
    lag_seconds: float | None = None
    candidate: bool = False


def compare_wav_obs_active_silence(
    raw_wav: bytes,
    meter_levels: tuple[tuple[float, float], ...],
    restart_monotonic: float | None,
) -> VoiceObsSegmentEvidence:
    """실제 양성·무음 이벤트를 50ms PCM 구간과 보수적으로 비교한다.

    OBS의 시간 정렬은 0~1초의 후보 지연만 허용한다. 무음 표본이
    수집되지 않았거나 WAV 내부 쉼이 없다면 판단하지 않는다.
    한 발화 전체가 관측됐다는 뜻도 아니며 누락 구간은 보간하지 않는다.
    """
    blank = VoiceObsSegmentEvidence()
    if (type(restart_monotonic) not in (int, float)
            or not math.isfinite(restart_monotonic) or restart_monotonic <= 0
            or not isinstance(meter_levels, tuple)
            or len(meter_levels) < 12 or len(meter_levels) > 256):
        return blank
    envelope = _rms_pcm16_windows(raw_wav)
    if len(envelope) < 16:
        return blank
    if (any(not isinstance(pair, tuple) or len(pair) != 2
            or any(type(x) not in (int, float) or not math.isfinite(x)
                   for x in pair)
            for pair in meter_levels)
            or any(a[0] >= b[0] for a, b in zip(meter_levels, meter_levels[1:]))
            or any(level < 0 or level > 20 for _, level in meter_levels)):
        return blank
    selected = tuple((t - restart_monotonic, level)
                     for t, level in meter_levels if t >= restart_monotonic)
    if (len(selected) < 12 or selected[-1][0] - selected[0][0] < 0.6
            or max(level for _, level in selected) <= 0.002):
        return blank
    wav_threshold = max(0.005, max(envelope) * 0.18)
    obs_threshold = max(0.001, max(level for _, level in selected) * 0.18)
    voice = [value >= wav_threshold for value in envelope]
    if sum(voice) < 4 or len(voice) - sum(voice) < 4:
        return blank
    best: VoiceObsSegmentEvidence | None = None
    for lag_tick in range(21):
        lag = lag_tick * 0.05
        visited = set()
        matched_voice = matched_silence = 0
        count_voice = count_silence = count = 0
        for seconds, level in selected:
            # PCM의 프레임별 RMS는 고정 50ms 간격이고,
            # 실제 OBS 미터 콜백 도착시각만 여기에 연결한다.
            offset = seconds - lag
            if offset < 0:
                continue
            index = int(offset / 0.05)
            if index >= len(voice) or index in visited:
                continue
            visited.add(index)
            count += 1
            expected_voice = voice[index]
            observed_voice = level >= obs_threshold
            if expected_voice:
                count_voice += 1
                matched_voice += int(observed_voice)
            else:
                count_silence += 1
                matched_silence += int(not observed_voice)
        # 말하는 동안 계속 높은 소리만 있거나, 모든 구간이 침묵이면
        # 잡음/다른 오디오에 의해 높은 점수가 만들어질 수 있다.
        if count < 12 or count_voice < 4 or count_silence < 4:
            continue
        voiced_rate = matched_voice / count_voice
        silent_rate = matched_silence / count_silence
        score = (voiced_rate + silent_rate) / 2.0
        evidence = VoiceObsSegmentEvidence(
            score=round(score, 4), samples=count,
            voiced_samples=count_voice, silent_samples=count_silence,
            lag_seconds=round(lag, 3),
            candidate=bool(score >= 0.8 and voiced_rate >= 0.7
                           and silent_rate >= 0.7),
        )
        if (best is None or score > best.score or
                (score == best.score and count > best.samples)):
            best = evidence
    return best if best is not None else blank
