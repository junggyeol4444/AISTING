"""운영자가 승인해 이미 송출 중인 OBS의 연결만 재확보하는 24시간 복구 경로.

WebSocket 연결이 끊겨도 OBS 송출을 새로 시작하지 않는다. 기존 프로그램이
시작했다고 확인한 방송과 같은 장면/출력 가동시간인 경우에만 기존
승인 세션의 읽기·종료 제어 연결을 다시 붙인다. 새 방송이나 다른
사용자가 재시작한 방송을 소유했다고 추정하지 않는다.
이 모듈의 모든 OBS 호출은 상태 읽기이며 방송/녹화/장면 변경은 없다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from .original_plan_obs import OfficialObsWebsocket


class ObsStreamIdentityLost(RuntimeError):
    """다른 OBS 방송일 수 있으므로 원래 승인 소유권을 더 이상 주장할 수 없음."""


class ObsReconnectExhausted(RuntimeError):
    """승인된 OBS 연결의 제한된 복구 기회를 모두 사용함."""


@dataclass(frozen=True)
class ObsReconnectSnapshot:
    attempts: int
    recovering: bool
    status: str


class ApprovedObsReconnector:
    """프로세스가 실제 시작 확인한 OBS 송출에만 유효한 연결 복구 관리자."""

    def __init__(
        self, *,
        scene: str,
        started_monotonic: float,
        password: str,
        port: int,
        client_factory: Callable[..., OfficialObsWebsocket],
        retry_seconds: float = 10.0,
        max_attempts: int = 6,
        deadline_seconds: float = 90.0,
    ) -> None:
        if type(scene) is not str or not scene.strip() or len(scene) > 256:
            raise ValueError("원래 승인한 OBS 장면 이름이 없습니다.")
        if (type(started_monotonic) not in (int, float)
                or not math.isfinite(started_monotonic)
                or started_monotonic < 0):
            raise ValueError("OBS 송출 시작 단조 시각이 올바르지 않습니다.")
        if type(password) is not str or not password:
            raise ValueError("기존 OBS 인증 암호가 필요합니다.")
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("OBS 로컬 포트가 잘못되었습니다.")
        if not callable(client_factory):
            raise TypeError("기존 OBS 클라이언트 생성 함수가 필요합니다.")
        if (type(retry_seconds) not in (int, float)
                or not 5 <= retry_seconds <= 60
                or type(max_attempts) is not int or not 1 <= max_attempts <= 10
                or type(deadline_seconds) not in (int, float)
                or not 30 <= deadline_seconds <= 300):
            raise ValueError("승인된 OBS 복구 간격·시도·기한 범위 오류")
        self.scene = scene
        self.started_monotonic = float(started_monotonic)
        self._password = password
        self._port = port
        self._factory = client_factory
        self.retry_seconds = float(retry_seconds)
        self.max_attempts = max_attempts
        self.deadline_seconds = float(deadline_seconds)
        self._since: float | None = None
        self._next_at = 0.0
        self._attempts = 0
        self._status = "OBS 원래 연결 유지"

    def _clock(self, now: float) -> float:
        if (type(now) not in (int, float) or not math.isfinite(now)
                or now < self.started_monotonic):
            raise ValueError("OBS 복구 단조 시각이 잘못되었습니다.")
        return float(now)

    def verify_stream_identity(self, client: OfficialObsWebsocket, now: float) -> None:
        """현재 실제 방송과 원래 시작 시점의 출력 가동시간이 연속적인지 확인.

        OBS GetStreamStatus.outputDuration은 밀리초 단위. 값이 없거나
        재시작/장면 변경/송출 종료이면 새 방송으로 오인하지 않고 중단.
        30초 허용 오차는 상태 질의/Windows 시계 지연만 감안한다.
        시청자에게 영상이 전달됐다는 증거는 아니다.
        """
        now = self._clock(now)
        state = client.status()
        if state.streaming is not True or state.scene != self.scene:
            raise ObsStreamIdentityLost("OBS 송출 종료 또는 다른 장면 감지")
        inner = getattr(client, "_client", None)
        if inner is None:
            raise ObsStreamIdentityLost("OBS 출력 원본 연결을 확인할 수 없음")
        try:
            output = inner.get_stream_status()
        except Exception as exc:
            raise RuntimeError("OBS 출력 가동시간 읽기 실패") from exc
        duration = getattr(output, "output_duration", None)
        if (type(duration) not in (int, float)
                or not math.isfinite(duration) or duration < 0):
            raise ObsStreamIdentityLost("OBS 출력 가동시간을 확인할 수 없음")
        actual = float(duration) / 1000.0
        expected = now - self.started_monotonic
        if abs(actual - expected) > 30.0:
            raise ObsStreamIdentityLost(
                "OBS 출력 가동시간 불연속 · 다른 방송 소유권 가능성")
        if expected > 30.0 and actual < 1.0:
            raise ObsStreamIdentityLost("OBS 출력 재시작 의심")
        self._status = "원래 승인된 OBS 출력 가동시간 연속성 확인"

    def snapshot(self) -> ObsReconnectSnapshot:
        return ObsReconnectSnapshot(
            self._attempts, self._since is not None, self._status)

    def reset(self) -> None:
        """동일 방송 연결 복구 성공 후 다음 연결 단절에 대비."""
        self._since = None
        self._next_at = 0.0
        self._attempts = 0
        self._status = "기존 승인 OBS 연결 복구 완료 · 새 송출 없음"

    def recover(self, now: float) -> OfficialObsWebsocket | None:
        """기존 송출이 계속 유지되는 경우에만 새 읽기 연결 반환.

        None은 재시도 대기 또는 연결 실패를 의미. 다른 송출이거나
        기한 소진 시 예외. 인증 비밀/서버 오류 전문은 기록하지 않는다.
        """
        now = self._clock(now)
        if self._since is None:
            self._since = now
        if now - self._since >= self.deadline_seconds:
            raise ObsReconnectExhausted("OBS 상태를 복구 기한 내 확인하지 못함")
        if self._attempts >= self.max_attempts:
            raise ObsReconnectExhausted("OBS 연결 복구 시도 횟수 소진")
        if now < self._next_at:
            return None
        self._attempts += 1
        self._next_at = now + self.retry_seconds
        candidate = None
        try:
            candidate = self._factory(self._password, port=self._port)
            candidate.connect()
            self.verify_stream_identity(candidate, now)
            return candidate
        except ObsStreamIdentityLost:
            self._close(candidate)
            raise
        except Exception:
            self._status = (
                f"OBS 읽기 연결 재시도 {self._attempts}/{self.max_attempts}"
                " · 기존 송출 변경 없음")
            self._close(candidate)
            return None

    @staticmethod
    def _close(client: OfficialObsWebsocket | None) -> None:
        if client is None:
            return
        inner = getattr(client, "_client", None)
        disconnect = getattr(inner, "disconnect", None)
        if callable(disconnect):
            try:
                disconnect()
            except Exception:
                pass
