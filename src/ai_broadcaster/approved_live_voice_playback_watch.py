"""실제 발화가 재생되는 동안 OBS 출력·공식 Cubism 창을 지속 감시.

GPT-SoVITS 동일 WAV가 재생 중일 때 기존 코드는 끝에서만 OBS 상태를
확인했다. 이 작업자는 이미 승인된 음성 한 구간의 재생 도중에도
실제 OBS 출력 uptime/장면·현재 임시 음성 소스 UUID·공식 Live2D
창 생존을 주기적으로 읽는다. 새 송출 시작/다른 소스 수정/재발화 없음.
중단 또는 관측 불명 시 현재 발화를 불명으로 남기고 후속 발화를 차단.
이 감시는 OBS 프로그램 출력의 시청자 최종 수신을 증명하지 않는다.
"""
from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from typing import Callable

from .approved_live_voice_stream_lease import ApprovedVoiceStreamLease
from .original_plan_obs import OfficialObsWebsocket


@dataclass(frozen=True)
class LivePlaybackObservation:
    """읽기 전용 감시 완료 시각과 상태. 시청자 수신 증거는 아님."""

    samples: int
    observed_seconds: float
    scene: str
    source_owned: bool
    cubism_alive: bool


class ApprovedLiveVoicePlaybackWatch:
    """이미 승인한 실제 OBS 음성 재생 중 동일 출력의 연속성 감시."""

    def __init__(self, *, interval_seconds: float = 0.4) -> None:
        if (type(interval_seconds) not in (int, float)
                or not math.isfinite(interval_seconds)
                or not 0.1 <= interval_seconds <= 2.0):
            raise ValueError("방송 음성 재생 관찰 간격은 0.1~2초여야 합니다.")
        self.interval_seconds = float(interval_seconds)

    def wait_for_current_wav(
        self, *, seconds: float, stop: threading.Event,
        obs: OfficialObsWebsocket, lease: ApprovedVoiceStreamLease,
        expected_scene: str, source_is_owned: Callable[[], bool],
        cubism_is_alive: Callable[[], bool],
    ) -> LivePlaybackObservation:
        """기존 WAV 시간만 기다리며 주기적으로 실제 출력 소유권을 확인.

        관찰 호출이 실패하면 성공을 추정하지 않는다. 자동 재생/재연결/
        OBS 송출 시작/종료/녹화 변경은 이 함수에서 수행하지 않는다.
        """
        if (type(seconds) not in (float, int)
                or not math.isfinite(seconds) or not 0.4 <= seconds <= 8.0):
            raise ValueError("실제 한국어 WAV 재생 시간이 올바르지 않습니다.")
        if (not isinstance(stop, threading.Event)
                or not isinstance(lease, ApprovedVoiceStreamLease)
                or not isinstance(obs, OfficialObsWebsocket)
                or not callable(source_is_owned)
                or not callable(cubism_is_alive)
                or type(expected_scene) is not str or not expected_scene):
            raise TypeError("기존 승인된 OBS·Cubism·음성 출력 관찰 대상 오류")
        started = time.monotonic()
        deadline = started + float(seconds) + 0.2
        samples = 0
        while True:
            if stop.is_set():
                raise RuntimeError("운영자가 한국어 실제 음성 출력을 중지했습니다.")
            current = time.monotonic()
            remaining = deadline - current
            if remaining <= 0:
                break
            if stop.wait(min(self.interval_seconds, remaining)):
                raise RuntimeError("운영자가 실제 방송 음성 재생을 중지했습니다.")
            # 읽기 전용 조회만 하며 예전 방송과 동일 출력인지 판정.
            snapshot = lease.check(obs)
            if snapshot.scene != expected_scene:
                raise RuntimeError("승인된 OBS 장면과 현재 장면이 다릅니다.")
            if cubism_is_alive() is not True:
                raise RuntimeError("동일 WAV 재생 중 공식 Cubism 창이 종료됐습니다.")
            if source_is_owned() is not True:
                raise RuntimeError("동일 WAV 재생 중 OBS 전용 음성 소스 소유권 상실")
            samples += 1
        return LivePlaybackObservation(
            samples=samples,
            observed_seconds=max(0.0, time.monotonic() - started),
            scene=expected_scene,
            source_owned=True,
            cubism_alive=True)
