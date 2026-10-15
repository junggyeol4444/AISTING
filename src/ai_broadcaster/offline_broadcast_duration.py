"""Original stage 078: local-only broadcast duration decision core.

No scheduler, IO, OBS control, waiting, automatic stream launch or stop.
The pure evaluator accepts explicit elapsed time. A session can be queried with
an injected monotonic clock by future approved local runtime integrations.
"""
from dataclasses import dataclass
from math import isfinite


DEFAULT_MINIMUM_MINUTES = 60
DEFAULT_MAXIMUM_MINUTES = 180
MAX_CONFIG_MINUTES = 1440


def _whole_minutes(value, name: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{name}: 정수 분 단위를 입력하세요.')
    if value < (0 if allow_zero else 1) or value > MAX_CONFIG_MINUTES:
        raise ValueError(f'{name}: {0 if allow_zero else 1}~{MAX_CONFIG_MINUTES}분이어야 합니다.')
    return value


@dataclass(frozen=True)
class BroadcastDurationRules:
    minimum_minutes: int = DEFAULT_MINIMUM_MINUTES
    maximum_minutes: int = DEFAULT_MAXIMUM_MINUTES

    def __post_init__(self):
        _whole_minutes(self.minimum_minutes, '최소 방송 시간')
        _whole_minutes(self.maximum_minutes, '최대 방송 시간')
        if self.minimum_minutes > self.maximum_minutes:
            raise ValueError('최소 방송 시간은 최대 방송 시간보다 길 수 없습니다.')

    def evaluate(self, elapsed_seconds: int | float) -> 'DurationDecision':
        if isinstance(elapsed_seconds, bool) or not isinstance(elapsed_seconds, (float, int)):
            raise ValueError('경과 시간은 유한한 초 단위 숫자여야 합니다.')
        if not isfinite(elapsed_seconds) or elapsed_seconds < 0:
            raise ValueError('경과 시간은 음수가 아닌 유한한 값이어야 합니다.')
        minimum = self.minimum_minutes * 60
        maximum = self.maximum_minutes * 60
        return DurationDecision(
            minimum_minutes=self.minimum_minutes,
            maximum_minutes=self.maximum_minutes,
            elapsed_seconds=float(elapsed_seconds),
            minimum_satisfied=elapsed_seconds >= minimum,
            maximum_reached=elapsed_seconds >= maximum,
        )


@dataclass(frozen=True)
class DurationDecision:
    minimum_minutes: int
    maximum_minutes: int
    elapsed_seconds: float
    minimum_satisfied: bool
    maximum_reached: bool

    @property
    def action(self) -> str:
        if self.maximum_reached:
            return 'wrap_up_requested'  # Never performs end or announcement itself.
        return 'continue'

    @property
    def can_consider_ending(self) -> bool:
        return self.minimum_satisfied

    @property
    def description(self) -> str:
        elapsed = self.elapsed_seconds / 60
        if not self.minimum_satisfied:
            verdict = '최소 시간 미달 · 종료 판단 차단'
        elif self.maximum_reached:
            verdict = '최대 시간 도달 · 마무리 판단 필요 (실제 종료하지 않음)'
        else:
            verdict = '최소 시간 충족 · 방송 계속 (자동 종료 없음)'
        return (f'가상 경과 {elapsed:.2f}분 / 최소 {self.minimum_minutes}분 / '
                f'최대 {self.maximum_minutes}분 · {verdict} · '
                '시뮬레이션 전용 / OBS·실제 방송 제어 없음 / 사용자 승인 대기')


class BroadcastDurationSession:
    """Monotonic clock contract. No background timers or automatic callbacks."""

    def __init__(self, rules: BroadcastDurationRules, started_at: int | float):
        if not isinstance(rules, BroadcastDurationRules):
            raise ValueError('검증된 방송 시간 설정이 필요합니다.')
        self.rules = rules
        self.started_at = self._timestamp(started_at)
        self._last_seen = self.started_at

    @staticmethod
    def _timestamp(value):
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value):
            raise ValueError('시간 값은 유한한 초 단위 숫자여야 합니다.')
        return float(value)

    def check(self, monotonic_now: int | float) -> DurationDecision:
        now = self._timestamp(monotonic_now)
        if now < self._last_seen:
            raise ValueError('단조 시계 역행 감지 · 기존 판단 유지')
        decision = self.rules.evaluate(now - self.started_at)
        self._last_seen = now
        return decision
