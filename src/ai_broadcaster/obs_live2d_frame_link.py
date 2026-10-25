"""실제 OBS 현재 장면의 공식 Live2D 창 캡처와 오디오 구간 영상 관측 후보.

OBS 설정의 임의 화면 캡처·게임 캡처·타인 창을 공식 Live2D로 간주하지
않는다. 프로그램 장면 PNG의 변화는 Cubism 입 변화의 인과성 증명이
아니며, 실제 시청자에게 송출되었다는 뜻도 아니다.
"""
from __future__ import annotations

import math

OFFICIAL_WINDOW_TITLE = "AISTING | 공식 Live2D 및 AI 대화"


def active_official_window_capture(captures: tuple[str, ...]) -> bool:
    """실제 OBS가 보고한 활성 창 캡처의 대상 창 제목을 확인한다.

    기존 OBS 장면/소스 이름을 변경하지 않고, OBS WebSocket이 반환한
    읽기 전용 입력 설정의 창 제목을 엄격히 대조한다.
    """
    if not isinstance(captures, tuple):
        return False
    return any(
        isinstance(item, str)
        and "(window_capture, 활성)" in item
        and " / 선택된 창 " + OFFICIAL_WINDOW_TITLE in item
        and ": 비활성" not in item
        for item in captures
    )


def program_motion_near_audio(
    frames: tuple[tuple[float, str, str], ...],
    positive_audio_times: tuple[float, ...],
    *,
    restart_at: float,
    wav_seconds: float,
) -> bool:
    """실제 WAV 구간의 OBS 프레임 변화와 양성 오디오 시각 근접 후보.

    frames: (실제 프레임 취득 완료 단조시각, 장면 이름, PNG SHA256).
    PNG 데이터 자체를 저장하거나 외부로 보내지 않는다. PNG 해시
    차이는 화면 변화의 약한 후보이지 입술 움직임 판별이 아니다.
    """
    if (len(frames) < 3 or not isinstance(restart_at, (int, float))
            or not math.isfinite(restart_at) or restart_at <= 0
            or not isinstance(wav_seconds, (int, float))
            or not math.isfinite(wav_seconds) or not 0 < wav_seconds <= 8):
        return False
    if any(
        not isinstance(sample, tuple) or len(sample) != 3
        or type(sample[0]) not in (int, float)
        or not math.isfinite(sample[0])
        or not isinstance(sample[1], str) or not sample[1]
        or not isinstance(sample[2], str) or len(sample[2]) != 64
        for sample in frames
    ):
        return False
    if len({sample[1] for sample in frames}) != 1:
        return False
    if any(frames[i][0] >= frames[i + 1][0]
           for i in range(len(frames) - 1)):
        return False
    baseline = frames[0][2]
    if frames[0][0] >= restart_at:
        return False
    upper = restart_at + wav_seconds
    valid_audio = tuple(
        moment for moment in positive_audio_times
        if type(moment) in (float, int) and math.isfinite(moment)
        and restart_at <= moment <= upper + 0.5
    )
    if not valid_audio:
        return False
    return any(
        restart_at < when <= upper
        and digest != baseline
        and any(abs(when - audio_when) <= 0.6
                for audio_when in valid_audio)
        for when, _scene, digest in frames[1:-1]
    )
