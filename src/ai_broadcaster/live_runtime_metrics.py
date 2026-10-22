"""Measured *local* live chat FIFO health; never viewer end-to-end proof.

Data is in memory only, bounded, contains no usernames, chat text, tokens,
audio, URLs or persisted traces. For the existing real native Tk receiver.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import ceil, isfinite


def _seconds(value: float, name: str) -> float:
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError(name + "은 0 이상의 유한한 시간이어야 합니다.")
    return float(value)


def _p95(values) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[ceil(len(ordered) * 0.95) - 1]


@dataclass(frozen=True)
class LiveLatencySnapshot:
    accepted: int
    completed: int
    failed: int
    invalid: int
    over_three_seconds: int
    sampled: int
    total_p95: float | None
    wait_p95: float | None
    inference_p95: float | None
    local_running_seconds: float
    reader_faults: int
    stopped: bool

    @property
    def unterminated(self) -> int:
        # 완료/실패 종료는 모두 completed로 계산된다. 시간 자체가 잘못된
        # 종료 사건은 invalid로 따로 계수해 남은 작업과 구분한다.
        return max(0, self.accepted - self.completed - self.invalid)

    @property
    def bottleneck_ko(self) -> str:
        # 실제 로컬 표본 p95의 상대 비중만 표시하며 시청자 지연을 뜻하지 않는다.
        if self.total_p95 is None or self.wait_p95 is None or self.inference_p95 is None:
            return '로컬 병목 미측정'
        if self.total_p95 <= 3:
            return '최근 로컬 p95 3초 이내 · 시청자 E2E 미검증'
        return ('로컬 p95 병목 추정: FIFO 대기' if self.wait_p95 >= self.inference_p95
                else '로컬 p95 병목 추정: AI 처리')

    def describe(self) -> str:
        p95 = ("측정 없음" if self.total_p95 is None
               else f"{self.total_p95:.2f}초")
        wait = ("-" if self.wait_p95 is None else f"{self.wait_p95:.2f}초")
        infer = ("-" if self.inference_p95 is None
                 else f"{self.inference_p95:.2f}초")
        return (f"로컬 실제 수신 {self.accepted}건 · 종결 측정 {self.completed}건 "
                f"· 실패 {self.failed}건 · 시간 오류 {self.invalid}건 "
                f"· 3초 초과 {self.over_three_seconds}건 "
                f"· 미종결 {self.unterminated}건 · 최근 {self.sampled}건 p95 총 {p95} "
                f"(대기 {wait} / AI {infer}) · {self.bottleneck_ko} · 로컬 연결 경과 "
                f"{self.local_running_seconds / 3600:.2f}시간 "
                f"· 수신기 오류 {self.reader_faults}건"
                " · 시청자 전달·방송 24시간 정상 송출은 미검증")


class LiveLatencyMetrics:
    """Session-scoped local timing. No thread/socket ownership or I/O.

    A measured local 3-second violation is meaningful, but a success does
    NOT establish chat transport-to-viewer or an OBS encoder delay.
    """

    def __init__(self, started_at: float, *, capacity: int = 1024):
        self.started_at = _seconds(started_at, "수신 시작 시각")
        if type(capacity) is not int or not 1 <= capacity <= 10000:
            raise ValueError("최근 측정 샘플 저장 한도를 확인하세요.")
        self._samples: deque[tuple[float, float, float]] = deque(maxlen=capacity)
        self.accepted = 0
        self.completed = 0
        self.failed = 0
        self.invalid = 0
        self.over_three_seconds = 0
        self.reader_faults = 0
        self.stopped_at: float | None = None

    def accept(self) -> None:
        if self.stopped_at is None:
            self.accepted += 1

    def reader_fault(self) -> None:
        if self.stopped_at is None:
            self.reader_faults += 1

    def stop(self, now: float) -> None:
        now = _seconds(now, "수신 중지 시각")
        if now < self.started_at:
            raise ValueError("수신 중지 시간 역행")
        if self.stopped_at is None:
            self.stopped_at = now

    def terminal(self, queue_wait: float, inference: float, total: float,
                 failed: bool = False) -> bool:
        if self.stopped_at is not None:
            return False
        try:
            wait = _seconds(queue_wait, "AI 대기")
            model = _seconds(inference, "AI 처리")
            elapsed = _seconds(total, "전체 처리")
            if type(failed) is not bool or abs(wait + model - elapsed) > 0.05:
                raise ValueError("시간 측정값이 일치하지 않습니다.")
        except ValueError:
            self.invalid += 1
            return False
        self.completed += 1
        self.failed += int(failed)
        self.over_three_seconds += int(elapsed > 3)
        self._samples.append((wait, model, elapsed))
        return True

    def snapshot(self, now: float) -> LiveLatencySnapshot:
        now = _seconds(now, "현재 시각")
        if now < self.started_at:
            raise ValueError("현재 시간 역행")
        observed_until = min(now, self.stopped_at) if self.stopped_at is not None else now
        return LiveLatencySnapshot(
            accepted=self.accepted, completed=self.completed,
            failed=self.failed, invalid=self.invalid,
            over_three_seconds=self.over_three_seconds,
            sampled=len(self._samples),
            total_p95=_p95([x[2] for x in self._samples]),
            wait_p95=_p95([x[0] for x in self._samples]),
            inference_p95=_p95([x[1] for x in self._samples]),
            local_running_seconds=max(0, observed_until - self.started_at),
            reader_faults=self.reader_faults, stopped=self.stopped_at is not None,
        )
