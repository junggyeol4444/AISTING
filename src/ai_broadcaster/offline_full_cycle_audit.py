"""Stage 083: deterministic, operator-triggered offline start-to-finish audit.

Reuses the actual stage 081/082 schedule/start controllers and 078/079
elapsed-duration/closing contracts. Every instant is injected: NO time reads,
background scheduler, audio, OBS, external connection or broadcasting.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from .offline_broadcast_schedule import BroadcastScheduleDraft
from .offline_start_control import OfflineStartController
from .offline_broadcast_duration import BroadcastDurationRules, BroadcastDurationSession
from .offline_broadcast_closing import OfflineBroadcastClosing


@dataclass(frozen=True)
class CycleAuditCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CycleAuditReport:
    checks: tuple[CycleAuditCheck, ...]
    events: tuple[str, ...]
    simulated_only: bool = True

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks) \
            and bool(self.events) and self.events[-1] == '가상 종료 기록'

    def describe(self) -> str:
        failed = next((c.name for c in self.checks if not c.passed), None)
        verdict = '통과' if self.passed else '미통과'
        text = f'083 시작→종료 오프라인 감사 {verdict} · {sum(c.passed for c in self.checks)}/{len(self.checks)} 항목'
        if failed:
            text += f' · 첫 실패: {failed}'
        return text + ' · 실제 자동 방송·OBS·TTS·Windows 동작 미검증 / 사용자 승인 대기'


class _AuditStopped(Exception):
    pass


def run_offline_full_cycle_audit(
    draft: BroadcastScheduleDraft, when: datetime, settings: Mapping[str, object],
    persona_name: str, minimum_minutes: int = 60, maximum_minutes: int = 180,
    *, start_factory=OfflineStartController, closing_factory=OfflineBroadcastClosing,
) -> CycleAuditReport:
    """Manually run a *virtual* full broadcast scenario; always fail closed.

    Optional factories are used solely to prove faulty dependency detection in
    unit tests. Nothing is persisted or run outside this function.
    """
    if type(draft) is not BroadcastScheduleDraft:
        raise ValueError('검증된 로컬 방송 일정 초안만 사용할 수 있습니다.')
    if not isinstance(settings, dict):
        raise ValueError('검증된 설정 사전이 필요합니다.')
    rules = BroadcastDurationRules(minimum_minutes, maximum_minutes)
    if not callable(start_factory) or not callable(closing_factory):
        raise ValueError('검증 가능한 로컬 상태 기계가 필요합니다.')

    checks: list[CycleAuditCheck] = []
    events: list[str] = []

    def require(name: str, operation) -> None:
        try:
            if operation() is not True:
                raise AssertionError('상태 또는 순서 불일치')
            checks.append(CycleAuditCheck(name, True, '메모리 가상 상태 확인'))
        except Exception as exc:
            checks.append(CycleAuditCheck(name, False, f'{type(exc).__name__}: {exc}'))
            raise _AuditStopped from exc

    try:
        controller = start_factory(draft)
        require('등록 일정·보안 설정에서 가상 시작 준비',
                lambda: controller.inspect(when, settings).code == 'mock_ready')

        displayed_start: list[str] = []
        def start():
            decision = controller.simulate_start(when, settings, show_mock_start=displayed_start.append)
            if decision.code == 'mock_started':
                events.append('가상 시작 기록')
            return (decision.code == 'mock_started' and controller.active
                    and displayed_start == [decision.occurrence] and controller.simulated_count == 1)
        require('가상 시작 표시 확인 후 단일 시작', start)
        require('진행 중 같은 일정 재진입 차단',
                lambda: controller.simulate_start(when, settings).code == 'mock_active')

        session = BroadcastDurationSession(rules, 0)
        require('초기 경과 시간에서 종료 차단',
                lambda: not session.check(0).minimum_satisfied)
        require('최소 시간 직전 종료 차단',
                lambda: not session.check(rules.minimum_minutes * 60 - 0.01).can_consider_ending)
        require('최소 시간부터 종료 고려만 가능',
                lambda: session.check(rules.minimum_minutes * 60).can_consider_ending)
        require('최대 시간 이전에 가상 종료 없음',
                lambda: not rules.evaluate(rules.maximum_minutes * 60 - 0.01).maximum_reached
                        and controller.active)
        decision = session.check(rules.maximum_minutes * 60)
        require('최대 시간에서 종료 절차 준비',
                lambda: decision.maximum_reached and decision.action == 'wrap_up_requested'
                        and controller.active)

        closing = closing_factory(decision, persona_name)
        require('예고 대기 초기 상태',
                lambda: closing.snapshot().phase == 'notice_pending'
                        and closing.snapshot().delivered_lines == ())
        displayed_lines: list[str] = []
        def notice():
            state = closing.advance(displayed_lines.append)
            events.append('마무리 예고 표시')
            return (state.phase == 'farewell_pending' and not state.virtual_stream_ended
                    and tuple(displayed_lines) == state.delivered_lines
                    and len(displayed_lines) == 1 and '마무리' in displayed_lines[0])
        require('예고 표시 확인 후 인사 대기', notice)

        def farewell():
            state = closing.advance(displayed_lines.append)
            events.append('작별 인사 표시')
            return (state.phase == 'virtual_ended' and state.virtual_stream_ended
                    and state.next_line is None and len(displayed_lines) == 2
                    and tuple(displayed_lines) == state.delivered_lines
                    and '다음에' in displayed_lines[1])
        require('작별 인사 확인 후 가상 종료 판정', farewell)

        def finish():
            result = controller.simulate_finish()
            if result.code == 'mock_finished':
                events.append('가상 종료 기록')
            return result.code == 'mock_finished' and not controller.active
        require('가상 시작 세션 안전하게 마무리', finish)
        require('가상 종료 중복 실행 차단',
                lambda: controller.simulate_finish().code == 'not_active')
        require('같은 일정 두 번째 가상 시작 차단',
                lambda: controller.simulate_start(when, settings).code == 'duplicate')
    except _AuditStopped:
        pass
    except Exception as exc:
        checks.append(CycleAuditCheck('예상하지 못한 통합 실행 오류', False,
                                      f'{type(exc).__name__}: {exc}'))
    return CycleAuditReport(tuple(checks), tuple(events))
