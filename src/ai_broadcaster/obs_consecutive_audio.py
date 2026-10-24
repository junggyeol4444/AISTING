# -*- coding: utf-8 -*-
"""연속 OBS 관찰 구간에서 실제 측정된 선택 오디오 시각을 안전하게 결합.

사용자 채팅/음성 본문을 저장하지 않는다. OBS 송출/녹화 동작도 없다.
"""
from __future__ import annotations
import math
from typing import Iterable

def _valid_time(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value > 0

def _관찰창_경로(sample: object) -> tuple[bool, object | None]:
    """OBS 선택 입력/장면/트랙의 전후 경로가 같은지 확인한다.

    과거 가상 검사에는 경로 객체가 없으므로 두 값 모두 없는 경우만
    동일한 미지정 경로로 취급한다. 실제 OBS 객체는 경로를 제공한다.
    """
    # 과거 가상 객체는 두 경로 속성이 모두 없을 때만 호환한다.
    # 실제 OBS 관찰 객체에 속성은 있으나 값이 None이면 경로를 확인하지
    # 못한 상태다. 이를 '경로 미지정'으로 합쳐 동일 발화로 오판하지 않는다.
    before_exists = hasattr(sample, "before_audio_route")
    after_exists = hasattr(sample, "after_audio_route")
    if not before_exists and not after_exists:
        return True, None
    if not (before_exists and after_exists):
        return False, None
    before = getattr(sample, "before_audio_route")
    after = getattr(sample, "after_audio_route")
    if (before is None or after is None
            or (isinstance(before, str) and not before.strip())
            or (isinstance(after, str) and not after.strip())
            or before != after):
        return False, None
    return True, before

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
    경로확정 = False
    선택경로 = None
    마지막_관찰창_시작 = None
    마지막_관찰창_종료 = None
    for began, ended, sample in observations:
        if not (_valid_time(began) and _valid_time(ended) and began < ended):
            # 한 번 근거를 채택한 뒤의 불명확한 창을 건너뛰고
            # 뒤의 표본을 같은 발화로 이어 붙이지 않는다.
            if 경로확정:
                break
            continue
        경로정상, 현재경로 = _관찰창_경로(sample)
        if not 경로정상 or not bool(getattr(sample, "coherent_media_candidate", False)):
            if 경로확정:
                break
            continue
        # 소리가 없는 중간 창도 실제 경로 연속성 검사에 포함한다.
        # 다른 경로로 갔다가 돌아온 경우 역시 동일 발화로 결합하지 않는다.
        if 경로확정 and 현재경로 != 선택경로:
            break
        # 동일 경로라도 관찰창 자체가 과거 시각으로 역행하면
        # 뒤쪽 표본을 같은 발화의 시간순 증거로 합치지 않는다.
        # 겹치는 창은 시작 시각이 역행하지 않는 한 허용한다.
        if 경로확정 and began < 마지막_관찰창_시작:
            break
        # 이전 정상 관찰창이 끝난 뒤 관측되지 않은 시간이 있으면
        # 그 공백 사이에 OBS 입력/장면/트랙이 바뀌지 않았음을 보장할 수 없다.
        # 겹침과 경계가 맞닿은 창은 유지하지만 실제 관찰 공백을 건너뛰지 않는다.
        if 경로확정 and began > 마지막_관찰창_종료:
            break
        # 무음 창도 순서 검증에 포함하여 뒤의 창이 거슬러 올라가지 못하게 한다.
        if 경로확정:
            마지막_관찰창_시작 = began
            # 겹친 창이 더 일찍 끝나더라도 이미 확인한 관찰 범위는 보존.
            마지막_관찰창_종료 = max(마지막_관찰창_종료, ended)
        audio = getattr(sample, "audio", None)
        if audio is None:
            # 이미 채택한 실제 표본 뒤의 오디오 관측 객체 누락은
            # 무음이 아니라 관찰 실패다. 이후 표본을 이어 붙이지 않는다.
            if 경로확정:
                break
            continue
        first = getattr(audio, "first_selected_signal_monotonic", None)
        last = getattr(audio, "last_selected_signal_monotonic", None)
        times = getattr(audio, "selected_signal_sample_times", None)
        # 실제로 선택 입력 신호가 없었던 정상 무음 관찰창만 통과시킨다.
        if first is None and last is None and times == ():
            continue
        # 일부 메타데이터만 있거나 시각·순서가 깨진 관찰창은
        # 같은 발화의 연속 증거를 보장할 수 없다.
        if not (_valid_time(first) and _valid_time(last)
                and began <= first < last <= ended
                and isinstance(times, tuple) and times
                and all(_valid_time(v) for v in times)
                and all(x < y for x, y in zip(times, times[1:]))
                and first <= times[0] <= times[-1] <= last):
            if 경로확정:
                break
            continue
        # 메타데이터는 정상이지만 이번 입 움직임 밖의 실제 소리는
        # 손상으로 취급하지 않고 증거 후보에서만 제외한다.
        if not (first < mouth_last and last > mouth_first):
            continue
        near = [t for t in times if mouth_first - near_seconds <= t <= mouth_last + near_seconds]
        if not near:
            continue
        # 연속 관찰창이 겹치더라도 뒤쪽의 새로운 실측 표본은 보존한다.
        # 이미 수집한 시각 이하만 제외하며 가상 표본을 만들지 않는다.
        if collected:
            near = [t for t in near if t > collected[-1]]
        if not near:
            continue
        collected.extend(near)
        window_count += 1
        if not 경로확정:
            선택경로, 경로확정 = 현재경로, True
            마지막_관찰창_시작 = began
            마지막_관찰창_종료 = ended
    return tuple(collected), window_count

def collect_obs_input_meter_levels(
    observations: Iterable[tuple[float, float, object]],
    *,
    since: float,
    until: float,
) -> tuple[tuple[float, float], ...]:
    """같은 OBS 입력/프로그램 장면이 확인된 실제 레벨 콜백만 수집.

    무음 샘플을 만들거나 보간하지 않는다. 연속 관찰창 경계의
    시간 중복·역행도 후보에서 제외한다.
    """
    if not (_valid_time(since) and _valid_time(until) and since < until):
        return ()
    merged: list[tuple[float, float]] = []
    경로확정 = False
    선택경로 = None
    마지막_관찰창_시작 = None
    마지막_관찰창_종료 = None
    for began, ended, sample in observations:
        if not (_valid_time(began) and _valid_time(ended) and began < ended):
            if 경로확정:
                break
            continue
        경로정상, 현재경로 = _관찰창_경로(sample)
        if not 경로정상 or not bool(getattr(sample, "coherent_media_candidate", False)):
            if 경로확정:
                break
            continue
        # 레벨 0개인 중간 창도 입력/장면/트랙이 바뀌었는지 검사한다.
        if 경로확정 and 현재경로 != 선택경로:
            break
        # 동일 경로라도 관찰창 자체가 과거 시각으로 역행하면
        # 뒤쪽 표본을 같은 발화의 시간순 증거로 합치지 않는다.
        # 겹치는 창은 시작 시각이 역행하지 않는 한 허용한다.
        if 경로확정 and began < 마지막_관찰창_시작:
            break
        # 이전 정상 관찰창이 끝난 뒤 관측되지 않은 시간이 있으면
        # 그 공백 사이에 OBS 입력/장면/트랙이 바뀌지 않았음을 보장할 수 없다.
        # 겹침과 경계가 맞닿은 창은 유지하지만 실제 관찰 공백을 건너뛰지 않는다.
        if 경로확정 and began > 마지막_관찰창_종료:
            break
        # 무음 창도 순서 검증에 포함하여 뒤의 창이 거슬러 올라가지 못하게 한다.
        if 경로확정:
            마지막_관찰창_시작 = began
            # 겹친 창이 더 일찍 끝나더라도 이미 확인한 관찰 범위는 보존.
            마지막_관찰창_종료 = max(마지막_관찰창_종료, ended)
        audio = getattr(sample, "audio", None)
        if audio is None:
            if 경로확정:
                break
            continue
        levels = getattr(audio, "selected_all_meter_level_samples", None)
        # 빈 튜플은 정상 무음이지만, 속성 누락·형식 오류·시간 역행은
        # 관찰 연속성 불확정이다. 기존 실측 표본 뒤라면 즉시 중단한다.
        if (not isinstance(levels, tuple)
                or any(not isinstance(p, tuple) or len(p) != 2
                       or not _valid_time(p[0])
                       or type(p[1]) not in (int, float)
                       or not math.isfinite(p[1]) or not 0 <= p[1] <= 20
                       for p in levels)
                or any(not (began <= when <= ended) for when, _ in levels)
                or any(x[0] >= y[0] for x, y in zip(levels, levels[1:]))):
            if 경로확정:
                break
            continue
        for when, level in levels:
            if began <= when <= ended and since <= when <= until:
                if not merged or when > merged[-1][0]:
                    merged.append((when, level))
                    if not 경로확정:
                        선택경로, 경로확정 = 현재경로, True
                        마지막_관찰창_시작 = began
                        마지막_관찰창_종료 = ended
    return tuple(merged)
