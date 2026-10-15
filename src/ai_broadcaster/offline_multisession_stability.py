"""098: sequential, isolated virtual broadcast repetitions (strictly offline).

Calls the existing stage-097 virtual audit with newly constructed mock state each
round. A failed round is NEVER retried automatically. Later independent rounds
may be inspected for contamination; they do not erase the recorded failure.
No live time, user device, OBS, platform, disk, account or network is touched.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_unattended_endurance import (
    CHAT_INTERVAL_SECONDS, run_virtual_unattended_endurance,
)

ALLOWED_ROUNDS = (3, 5, 10)
ALLOWED_HOURS = (1, 3)
MAX_ROUND_REPORTS = 10


@dataclass(frozen=True)
class VirtualRound:
    ordinal: int
    passed: bool
    checked_ticks: int
    accepted: int
    responded: int
    remaining: int
    virtual_ended: bool
    failure: str


@dataclass(frozen=True)
class MultiSessionReport:
    requested_rounds: int
    requested_hours_each: int
    rounds: tuple[VirtualRound, ...]
    total_accepted: int
    total_responded: int
    total_ticks: int
    failed_rounds: tuple[int, ...]
    failure: str
    mock_only: bool = True
    actual_broadcast_tested: bool = False

    @property
    def passed(self) -> bool:
        expected_messages = self.requested_hours_each * 3600 // CHAT_INTERVAL_SECONDS + 1
        return (self.requested_rounds in ALLOWED_ROUNDS
                and self.requested_hours_each in ALLOWED_HOURS
                and not self.failure and not self.failed_rounds
                and self.mock_only and not self.actual_broadcast_tested
                and len(self.rounds) == self.requested_rounds <= MAX_ROUND_REPORTS
                and all(r.ordinal == i and r.passed and r.virtual_ended
                        and not r.failure and r.remaining == 0
                        and r.accepted == r.responded == expected_messages
                        and r.checked_ticks == self.requested_hours_each * 3600 + 1
                        for i, r in enumerate(self.rounds, 1))
                and self.total_ticks == self.requested_rounds * (self.requested_hours_each * 3600 + 1)
                and self.total_accepted == self.total_responded == self.requested_rounds * expected_messages)

    def describe(self) -> str:
        details = '\n'.join(
            f'{r.ordinal}회차 {"통과" if r.passed else "미통과"} · {r.checked_ticks}틱 · '
            f'접수 {r.accepted} / 응답 {r.responded} / 미처리 {r.remaining}'
            + (f' · 오류 {r.failure}' if r.failure else '')
            for r in self.rounds
        )
        return (f'098 여러 회차 오프라인 가속 모의 검증: {"통과" if self.passed else "미통과"}\n'
                f'요청 {self.requested_rounds}회차 × 가상 {self.requested_hours_each}시간; '
                f'검사 {len(self.rounds)}회차; 가상 틱 합 {self.total_ticks}\n'
                f'접수 합 {self.total_accepted} / 응답 합 {self.total_responded}; '
                f'실패 회차 {list(self.failed_rounds)}\n'
                f'{details}\n'
                f'전체 오류: {self.failure or "없음"}\n'
                '실제 연속 방송·Windows·EXE·OBS·AI·TTS·아바타·장기 메모리 누수는 미검증. '
                '각 회차는 독립 가상 세션이며 실제 송출이나 예약·계정 연결 없음.')


def run_virtual_multisession_stability(
    rounds: int, hours_each: int, *,
    fail_round: int | None = None, failure_mode: str = 'reply',
) -> MultiSessionReport:
    """Run bounded sequential mock audits. Faults are test-only and never retry.

    A failed round does not stop later *independent audit rounds*, but the
    summary remains failed. No application settings or sessions are passed in.
    """
    if type(rounds) is not int or rounds not in ALLOWED_ROUNDS:
        raise ValueError('반복 횟수는 3·5·10회 중에서만 선택합니다.')
    if type(hours_each) is not int or hours_each not in ALLOWED_HOURS:
        raise ValueError('회차당 가상 시간은 1·3시간 중 선택합니다.')
    if fail_round is not None and (type(fail_round) is not int or not 1 <= fail_round <= rounds):
        raise ValueError('오류 주입 회차가 실행 범위를 벗어났습니다.')
    if failure_mode not in ('reply', 'corrupt', 'clock', 'closing') or type(failure_mode) is not str:
        raise ValueError('인식할 수 없는 가상 오류 방식입니다.')

    reports: list[VirtualRound] = []
    failed_rounds: list[int] = []
    total_received = total_replied = total_ticks = 0
    failure = ''
    expected = hours_each * 3600 // CHAT_INTERVAL_SECONDS + 1

    for ordinal in range(1, rounds + 1):
        kwargs = {}
        if ordinal == fail_round:
            kwargs = {
                'reply': {'fault_second': 300},
                'corrupt': {'corrupt_second': 60},
                'clock': {'reverse_clock_second': 60},
                'closing': {'fail_closing_display': True},
            }[failure_mode]
        try:
            result = run_virtual_unattended_endurance(hours_each, **kwargs)
            ok = (result.passed and result.requested_hours == hours_each
                  and result.ticks_checked == hours_each * 3600 + 1
                  and result.accepted == result.responded == expected
                  and result.pending == 0 and result.virtual_end
                  and not result.actual_broadcast_tested and result.mock_only)
            reason = '' if ok else (result.failure or '가상 회차 집계/상태 불일치')
            row = VirtualRound(ordinal, ok, result.ticks_checked, result.accepted,
                               result.responded, result.pending, result.virtual_end, reason)
        except Exception as exc:
            # A broken audit function cannot silently mark a cycle successful.
            row = VirtualRound(ordinal, False, 0, 0, 0, 0, False,
                               f'{type(exc).__name__}: {exc}')
        reports.append(row)
        total_received += row.accepted
        total_replied += row.responded
        total_ticks += row.checked_ticks
        if not row.passed:
            failed_rounds.append(ordinal)
    if failed_rounds:
        failure = '실패 회차를 자동 재시도하지 않았습니다. 이후 회차는 독립 가상 시험입니다.'
    return MultiSessionReport(rounds, hours_each, tuple(reports), total_received,
                              total_replied, total_ticks, tuple(failed_rounds), failure)
