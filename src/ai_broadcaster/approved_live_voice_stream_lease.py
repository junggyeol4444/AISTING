"""승인된 한 번의 한국어 음성 방송을 원래 OBS 출력에만 묶는 소유권 경계.

OBS 연결/상태는 읽기만 한다. 다른 송출로 전환되거나 가동시간이
불연속이면 이미 대기 중인 음성을 새 방송으로 자동 옮기지 않는다.
시청자 수신·립싱크 성공을 판정하지 않는다.
"""
from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass

from .original_plan_obs import OfficialObsWebsocket


class VoiceStreamLeaseLost(RuntimeError):
    """처음 승인한 OBS 출력과 현재 송출의 동일성이 사라짐."""


@dataclass(frozen=True)
class VoiceStreamLeaseSnapshot:
    scene: str
    elapsed_seconds: float
    last_output_seconds: float
    checks: int


class ApprovedVoiceStreamLease:
    """첫 실제 발화 때 출력 uptime을 고정하고 모든 구간마다 연속성 확인."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._scene: str | None = None
        self._baseline_monotonic: float | None = None
        self._baseline_duration: float | None = None
        self._last_monotonic: float | None = None
        self._last_duration: float | None = None
        self._checks = 0
        self._lost = False

    @staticmethod
    def _observation(obs: OfficialObsWebsocket) -> tuple[str, float]:
        state = obs.status()
        if state.streaming is not True or not state.scene:
            raise VoiceStreamLeaseLost("실제 OBS 송출이 중지되었거나 장면이 없습니다.")
        client = getattr(obs, "_client", None)
        if client is None:
            raise VoiceStreamLeaseLost("실제 OBS 출력 소유권을 확인할 수 없습니다.")
        try:
            status = client.get_stream_status()
        except Exception as exc:
            raise VoiceStreamLeaseLost("OBS 송출 가동시간 조회 실패") from exc
        duration = getattr(status, "output_duration", None)
        if (type(duration) not in (int, float)
                or not math.isfinite(duration) or duration < 0):
            raise VoiceStreamLeaseLost("OBS 송출 가동시간이 확인되지 않습니다.")
        return state.scene, float(duration) / 1000.0

    def check(self, obs: OfficialObsWebsocket) -> VoiceStreamLeaseSnapshot:
        """현재 실제 방송의 장면·출력 uptime을 검증하며 첫 호출에만 고정.

        원래 승인한 한 출력에 대한 첫 호출이므로 앱 재시작 후에는
        새로운 운영자 승인을 받아 새 Lease를 만들어야 한다.
        """
        with self._lock:
            if self._lost:
                raise VoiceStreamLeaseLost("이전 방송의 음성 소유권이 상실되었습니다.")
            try:
                scene, duration = self._observation(obs)
                now = time.monotonic()
                if self._scene is None:
                    self._scene = scene
                    self._baseline_monotonic = now
                    self._baseline_duration = duration
                else:
                    if scene != self._scene:
                        raise VoiceStreamLeaseLost("승인된 OBS 방송 장면이 변경되었습니다.")
                    elapsed = now - self._baseline_monotonic
                    expected = self._baseline_duration + elapsed
                    # 스트림이 잠깐 중단·재시작하면 elapsed에 비해 uptime이
                    # 줄어들므로 다른 방송으로 자동 발화하지 않는다.
                    if abs(duration - expected) > 3.0:
                        raise VoiceStreamLeaseLost(
                            "OBS 출력 가동시간 불연속 · 새 송출에 음성 전송 차단")
                    if self._last_duration is not None:
                        delta = duration - self._last_duration
                        clock_delta = now - self._last_monotonic
                        if delta < -0.5 or abs(delta - clock_delta) > 3.0:
                            raise VoiceStreamLeaseLost(
                                "OBS 출력 재시작 또는 일시정지 가능성")
                self._last_monotonic = now
                self._last_duration = duration
                self._checks += 1
                return VoiceStreamLeaseSnapshot(
                    self._scene, now - self._baseline_monotonic,
                    duration, self._checks)
            except Exception:
                # 상태 조회 실패 뒤에도 새 방송에 재승인 없이 재연결 금지.
                self._lost = True
                raise

    @property
    def lost(self) -> bool:
        with self._lock:
            return self._lost
