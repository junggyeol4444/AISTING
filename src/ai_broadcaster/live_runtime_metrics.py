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

class LiveParseReplyMetrics:
    """실제 4플랫폼 파싱→로컬 AI 작업 종결의 시간차만 메모리에 보존.

    실패한 작업도 종결로 기록하며 성공·시청자 전달·WAV/OBS 증거로 보지 않는다.
    """
    def __init__(self, *, capacity: int = 512):
        if type(capacity) is not int or not 1 <= capacity <= 10000:
            raise ValueError("파싱→AI 종결 표본 한도가 올바르지 않습니다.")
        self._samples: deque[tuple[float, float, float]] = deque(maxlen=capacity)
        self.completed = self.failed = self.missing = self.invalid = 0
        self.over_three_seconds = 0
        self.longest_seconds = 0.0

    def terminal(self, parsed_at, accepted_at, model_started_at, ended_at,
                 failed: bool = False) -> bool:
        if parsed_at is None:
            self.missing += 1
            return False
        stamps = (parsed_at, accepted_at, model_started_at, ended_at)
        if (type(failed) is not bool or any(
                type(x) not in (int, float) or not isfinite(x) for x in stamps)):
            self.invalid += 1
            return False
        parsed, accepted, started, ended = (float(x) for x in stamps)
        if not 0 < parsed <= accepted <= started <= ended:
            self.invalid += 1
            return False
        wait, inference, total = started-parsed, ended-started, ended-parsed
        self.completed += 1
        self.failed += int(failed)
        self.over_three_seconds += int(total > 3.0)
        self.longest_seconds = max(self.longest_seconds, total)
        self._samples.append((wait, inference, total))
        return True

    def snapshot(self) -> dict[str, int | float | None]:
        return {
            "종결": self.completed, "실패": self.failed,
            "파싱시각누락": self.missing, "시각오류": self.invalid,
            "3초초과": self.over_three_seconds, "최근표본": len(self._samples),
            "최근p95초": _p95([x[2] for x in self._samples]),
            "대기p95초": _p95([x[0] for x in self._samples]),
            "AIp95초": _p95([x[1] for x in self._samples]),
            "최장초": self.longest_seconds,
        }


class LiveFirstWavLatencyMetrics:
    """실제 공식 WebSocket의 첫 WAV 수신 *후보*까지 로컬 지연을 기록.

    공식 서버에 채팅별 응답 식별자가 없으므로 이전 발화의 WAV일 수 있다.
    같은 채팅의 합성·Cubism·OBS·시청자 출력 성공으로 절대 계수하지 않는다.
    채팅 본문·닉네임·음성·인증정보는 기록하지 않는다.
    """

    def __init__(self, *, capacity: int = 512):
        if type(capacity) is not int or not 1 <= capacity <= 10000:
            raise ValueError("첫 WAV 후보 표본 한도가 올바르지 않습니다.")
        self._samples: deque[tuple[float, float, float]] = deque(maxlen=capacity)
        self.attempts = 0
        self.observed_candidates = 0
        self.not_observed = 0
        self.errors = 0
        self.missing_parse_time = 0
        self.invalid = 0
        self.over_three_seconds = 0
        self.longest_seconds = 0.0

    def error(self) -> None:
        """실제 공식 전송/관찰 예외는 WAV 미관측과 구분한다."""
        self.attempts += 1
        self.errors += 1

    def observe(self, parsed_at, accepted_at, request_started_at,
                first_wav_seconds, wav_received) -> bool:
        self.attempts += 1
        if type(wav_received) is not bool:
            self.invalid += 1
            return False
        if not wav_received:
            if first_wav_seconds is not None:
                self.invalid += 1
            else:
                self.not_observed += 1
            return False
        if parsed_at is None:
            self.missing_parse_time += 1
            return False
        stamps = (parsed_at, accepted_at, request_started_at, first_wav_seconds)
        if any(type(value) not in (int, float) or not isfinite(value)
               for value in stamps):
            self.invalid += 1
            return False
        parsed, accepted, started, delay = (float(v) for v in stamps)
        if not (0 < parsed <= accepted <= started and 0 <= delay <= 20):
            self.invalid += 1
            return False
        queue_wait = started - parsed
        total = queue_wait + delay
        self.observed_candidates += 1
        self.over_three_seconds += int(total > 3)
        self.longest_seconds = max(self.longest_seconds, total)
        self._samples.append((queue_wait, delay, total))
        return True

    def snapshot(self) -> dict[str, int | float | None]:
        return {
            "관찰시도": self.attempts,
            "WAV수신후보": self.observed_candidates,
            "WAV미관측": self.not_observed,
            "전송관찰오류": self.errors,
            "파싱시각누락": self.missing_parse_time,
            "시각오류": self.invalid,
            "3초초과후보": self.over_three_seconds,
            "최근표본": len(self._samples),
            "파싱부터후보p95초": _p95([v[2] for v in self._samples]),
            "파싱부터전송대기p95초": _p95([v[0] for v in self._samples]),
            "전송부터WAV후보p95초": _p95([v[1] for v in self._samples]),
            "최장후보초": self.longest_seconds,
        }


class LiveFirstMouthLatencyMetrics:
    """실제 공식 Cubism 첫 입 움직임 후보까지의 로컬 단계 지연.

    플랫폼 채팅 파싱→공식 단일 질문 요청→Cubism RMS·입 움직임 표본만 측정한다.
    첫 WAV→입 표본은 같은 공식 관찰 안의 순서 후보로만 간주한다.
    공식 서버 응답과 원본 채팅의 명시적 ID가 없으므로 인과성·실제 출력,
    OBS 인코딩·시청자 수신 지연을 입증하지 않는다.
    본문·닉네임·음성·인증 정보나 표본별 개인 식별자는 저장하지 않는다.
    """

    def __init__(self, *, capacity: int = 512):
        if type(capacity) is not int or not 1 <= capacity <= 10000:
            raise ValueError("첫 Cubism 입 표본 저장 한도가 올바르지 않습니다.")
        self._samples: deque[tuple[float, float, float]] = deque(maxlen=capacity)
        self._wav_to_mouth_samples: deque[float] = deque(maxlen=capacity)
        self.attempts = 0
        self.mouth_candidates = 0
        self.mouth_not_observed = 0
        self.request_errors = 0
        self.missing_parse_time = 0
        self.invalid = 0
        self.wav_mouth_candidates = 0
        self.wav_mouth_missing = 0
        self.wav_mouth_invalid = 0
        self.over_three_seconds = 0
        self.longest_seconds = 0.0

    def error(self) -> None:
        """기존 공식 질문 또는 입 관찰 예외를 미관측과 구분한다."""
        self.attempts += 1
        self.request_errors += 1

    def observe(self, parsed_at, accepted_at, request_started_at,
                observed_finished_at, first_mouth_at, verified_mouth,
                wav_received_at=None) -> bool:
        """실제 동일 프로세스 monotonic 시각만 접수.

        WAV 시각이 없어도 입 후보는 따로 집계하되 WAV→입 동일성
        근거로 세지 않는다. WAV가 입보다 늦거나 현재 관찰 밖이면
        오류 통계로 남기고 WAV→입 후보 계산에서 제외한다.
        """
        self.attempts += 1
        if type(verified_mouth) is not bool:
            self.invalid += 1
            return False
        if not verified_mouth:
            self.mouth_not_observed += 1
            return False
        if parsed_at is None:
            self.missing_parse_time += 1
            return False
        stamps = (parsed_at, accepted_at, request_started_at,
                  observed_finished_at, first_mouth_at)
        if any(type(v) not in (int, float) or not isfinite(v)
               for v in stamps):
            self.invalid += 1
            return False
        parsed, accepted, started, finished, first = map(float, stamps)
        if not (0 < parsed <= accepted <= started <= first <= finished):
            self.invalid += 1
            return False
        request_wait = started - parsed
        first_mouth_wait = first - started
        total = first - parsed
        self.mouth_candidates += 1
        self.over_three_seconds += int(total > 3.0)
        self.longest_seconds = max(self.longest_seconds, total)
        self._samples.append((request_wait, first_mouth_wait, total))
        if wav_received_at is None or wav_received_at == 0:
            self.wav_mouth_missing += 1
        elif (type(wav_received_at) not in (int, float)
              or not isfinite(wav_received_at)
              or not started <= wav_received_at <= first):
            self.wav_mouth_invalid += 1
        else:
            self.wav_mouth_candidates += 1
            self._wav_to_mouth_samples.append(first - float(wav_received_at))
        return True

    def snapshot(self) -> dict[str, int | float | None]:
        return {
            "관찰시도": self.attempts,
            "입표본후보": self.mouth_candidates,
            "입미관측": self.mouth_not_observed,
            "공식관찰오류": self.request_errors,
            "파싱시각누락": self.missing_parse_time,
            "시각오류": self.invalid,
            "3초초과후보": self.over_three_seconds,
            "최근표본": len(self._samples),
            "파싱부터입후보p95초": _p95([v[2] for v in self._samples]),
            "파싱부터전송대기p95초": _p95([v[0] for v in self._samples]),
            "전송부터입후보p95초": _p95([v[1] for v in self._samples]),
            "최장후보초": self.longest_seconds,
            "WAV입시각후보": self.wav_mouth_candidates,
            "WAV시각누락": self.wav_mouth_missing,
            "WAV시각오류": self.wav_mouth_invalid,
            "WAV부터입후보p95초": _p95(self._wav_to_mouth_samples),
        }
