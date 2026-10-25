"""실제 OBS WebSocket 방송의 프레임·혼잡도 읽기 전용 운용 관찰.

사용자가 이미 승인해 시작한 OBS 세션의 기존 연결만 사용한다.
방송/녹화 시작·종료, 설정 변경, 사용자 계정 연결을 수행하지 않는다.
이 관찰은 수신자 화면 전달, 최종 음성·영상 E2E, 24시간 성공 증거가 아니다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


def _finite_float(value, *, minimum=0.0, maximum=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        return None
    out = float(value)
    return out if out >= minimum and (maximum is None or out <= maximum) else None


def _nonnegative_int(value):
    if type(value) is not int or value < 0:
        return None
    return value


def _get(object_, field: str):
    if isinstance(object_, dict):
        return object_.get(field)
    return getattr(object_, field, None)


@dataclass(frozen=True)
class ObsHealthSnapshot:
    actual_samples: int
    actual_streaming: bool | None
    reconnecting: bool | None
    congestion: float | None
    skipped_frames: int | None
    total_frames: int | None
    active_fps: float | None
    render_skipped_frames: int | None
    render_total_frames: int | None
    reconnect_observations: int
    first_sample_monotonic: float | None
    last_sample_monotonic: float | None
    read_errors: int
    frame_counter_resets: int

    @property
    def description(self) -> str:
        if self.actual_samples == 0:
            return "OBS 출력 상태 실측 없음 · 시청자 E2E 미확인"
        state = ("진행" if self.actual_streaming is True else
                 "비활성" if self.actual_streaming is False else "미확인")
        congestion = (f"{self.congestion * 100:.1f}%"
                      if self.congestion is not None else "미관측")
        fps = f"{self.active_fps:.1f}" if self.active_fps is not None else "미관측"
        total = (f"{self.skipped_frames}/{self.total_frames}"
                 if self.skipped_frames is not None and self.total_frames is not None
                 else "미관측")
        return (f"OBS 실제 송출 {state} · 혼잡 {congestion} · FPS {fps} "
                f"· 누적 전송 누락 프레임 {total} · 재연결 관측 "
                f"{self.reconnect_observations}회 · 관찰 {self.actual_samples}회 "
                f"· 읽기 실패 {self.read_errors}회 · 수신자 E2E 미확인")


class ObsStreamHealthMonitor:
    """5초 등 호출자가 선택한 간격의 서버 실제 GetStreamStatus/GetStats 조회.

    누락·FPS는 OBS가 반환한 실제 값을 그대로 보존한다.
    서버 재시작으로 프레임 카운터가 감소한 경우 증가량을 추정하지 않는다.
    """
    def __init__(self) -> None:
        self._samples = 0
        self._errors = 0
        self._reconnect = 0
        self._first = None
        self._last = None
        self._last_reconnecting = None
        self._active = None
        self._reconnecting = None
        self._congestion = None
        self._skipped = None
        self._total = None
        self._fps = None
        self._render_skipped = None
        self._render_total = None
        self._frame_resets = 0

    def observe(self, official_obs, *, monotonic_now: float) -> ObsHealthSnapshot:
        if _finite_float(monotonic_now, minimum=0.0) is None:
            raise ValueError("OBS 관측 시각 형식이 올바르지 않습니다.")
        if self._last is not None and monotonic_now < self._last:
            raise ValueError("OBS 관측 단조시계가 역행했습니다.")
        inner = getattr(official_obs, "_client", None)
        if inner is None:
            self._errors += 1
            return self.snapshot()
        try:
            stream = inner.get_stream_status()
            stats = inner.get_stats()
            active = _get(stream, "output_active")
            reconnect = _get(stream, "output_reconnecting")
            if type(active) is not bool or type(reconnect) is not bool:
                raise ValueError("OBS 공식 출력 상태가 누락되었습니다.")
            skipped = _nonnegative_int(_get(stream, "output_skipped_frames"))
            total = _nonnegative_int(_get(stream, "output_total_frames"))
            if (skipped is not None and total is not None and skipped > total):
                raise ValueError("OBS 전송 프레임 통계가 일치하지 않습니다.")
            if self._total is not None and total is not None and total < self._total:
                self._frame_resets += 1
            if reconnect and self._last_reconnecting is not True:
                self._reconnect += 1
            self._active = active
            self._reconnecting = reconnect
            self._last_reconnecting = reconnect
            self._congestion = _finite_float(
                _get(stream, "output_congestion"), maximum=1.0)
            self._skipped, self._total = skipped, total
            self._fps = _finite_float(_get(stats, "active_fps"), maximum=300)
            self._render_skipped = _nonnegative_int(
                _get(stats, "render_skipped_frames"))
            self._render_total = _nonnegative_int(
                _get(stats, "render_total_frames"))
            if self._first is None:
                self._first = float(monotonic_now)
            self._last = float(monotonic_now)
            self._samples += 1
        except Exception:
            # 예외의 네트워크/암호/OBS 내부 응답 내용은 저장/출력하지 않음.
            self._errors += 1
        return self.snapshot()

    def snapshot(self) -> ObsHealthSnapshot:
        return ObsHealthSnapshot(
            self._samples, self._active, self._reconnecting,
            self._congestion, self._skipped, self._total, self._fps,
            self._render_skipped, self._render_total, self._reconnect,
            self._first, self._last, self._errors, self._frame_resets)
