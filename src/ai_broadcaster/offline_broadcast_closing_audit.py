"""080: isolated deterministic audit of the existing local closing protocol.

No real timer, background execution, microphone, TTS, OBS, process, file or
network interface. Each check uses a separate in-memory closing session.
"""
from dataclasses import dataclass

from .offline_broadcast_closing import OfflineBroadcastClosing
from .offline_broadcast_duration import BroadcastDurationRules


@dataclass(frozen=True)
class ClosingAuditItem:
    name: str
    passed: bool
    explanation: str


@dataclass(frozen=True)
class ClosingAuditReport:
    checks: tuple[ClosingAuditItem, ...]
    simulated_only: bool = True

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(item.passed for item in self.checks)

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def passed_count(self) -> int:
        return sum(item.passed for item in self.checks)

    def describe(self) -> str:
        result = '통과' if self.passed else '미통과'
        failures = '; '.join(item.name for item in self.checks if not item.passed)
        suffix = f' · 실패 검사: {failures}' if failures else ''
        return (f'080 종료 절차 오프라인 통합 감사 {result}: {self.passed_count}/{self.total}'
                f'{suffix} · 실제 음성·OBS·방송 자동 종료 미검증 / 사용자 승인 대기')


def run_offline_closing_audit(minimum_minutes=60, maximum_minutes=180,
                              persona_name='아이스팅', *, session_factory=None) -> ClosingAuditReport:
    """Audit independent scenarios; report failures, never certify a real stop.

    ``session_factory`` is an optional local test seam to prove failure
    reporting is fail-closed; it is not used for any external integration.
    """
    rules = BroadcastDurationRules(minimum_minutes, maximum_minutes)
    factory = session_factory if session_factory is not None else OfflineBroadcastClosing
    if not callable(factory):
        raise ValueError('로컬 검증 세션 생성자가 필요합니다.')
    # Validate the supplied persona before evaluating scenarios, including names
    # which would otherwise only be used inside a negative test.
    ready_decision = rules.evaluate(maximum_minutes * 60)
    factory(ready_decision, persona_name)
    checks: list[ClosingAuditItem] = []

    def check(name, run):
        try:
            outcome = run()
            if outcome is not True:
                raise AssertionError('상태/순서 불일치')
            checks.append(ClosingAuditItem(name, True, '가상 메모리 절차 확인'))
        except Exception as exc:
            checks.append(ClosingAuditItem(name, False, f'{type(exc).__name__}: {exc}'))

    def fresh():
        return factory(ready_decision, persona_name)

    def blocked(seconds):
        try:
            factory(rules.evaluate(seconds), persona_name)
        except ValueError:
            return True
        return False

    check('최소시간 미달 시작 차단', lambda: blocked(0))
    check('최대시간 직전 시작 차단', lambda: blocked(maximum_minutes * 60 - 0.01))

    def verify_ready():
        snapshot = fresh().snapshot()
        return (snapshot.phase == 'notice_pending' and not snapshot.virtual_stream_ended
                and snapshot.delivered_lines == () and snapshot.next_line is not None)
    check('최대시간 도달 시 대기 상태', verify_ready)

    def verify_notice():
        session = fresh()
        shown = []
        result = session.advance(shown.append)
        return (len(shown) == 1 and shown == list(result.delivered_lines)
                and '마무리' in shown[0] and result.phase == 'farewell_pending'
                and not result.virtual_stream_ended and result.next_line is not None)
    check('예고 문구 확인 후 인사 대기', verify_notice)

    def verify_finish():
        session = fresh()
        shown = []
        session.advance(shown.append)
        result = session.advance(shown.append)
        return (result.phase == 'virtual_ended' and result.virtual_stream_ended
                and len(shown) == 2 and shown == list(result.delivered_lines)
                and '다음에' in shown[-1] and result.next_line is None
                and '실제 OBS/방송 종료 0건' in result.details)
    check('예고→인사→가상 종료 순서', verify_finish)

    def verify_notice_failure():
        session = fresh()
        before = session.snapshot()
        calls = []
        def fail(text):
            calls.append(text)
            raise RuntimeError('offline display failure')
        try:
            session.advance(fail)
        except RuntimeError:
            pass
        after = session.snapshot()
        return (len(calls) == 1 and after == before and not after.virtual_stream_ended)
    check('예고 표시 실패 시 대기 상태 보존', verify_notice_failure)

    def verify_farewell_failure():
        session = fresh()
        session.advance(lambda _: None)
        before = session.snapshot()
        calls = []
        def fail(text):
            calls.append(text)
            raise RuntimeError('offline display failure')
        try:
            session.advance(fail)
        except RuntimeError:
            pass
        after = session.snapshot()
        return (len(calls) == 1 and after == before and not after.virtual_stream_ended)
    check('인사 표시 실패 시 가상 종료 차단', verify_farewell_failure)

    def verify_manual_retry():
        session = fresh()
        calls = []
        def sometimes_fail(text):
            calls.append(text)
            if len(calls) == 1:
                raise RuntimeError('first display failed')
        try:
            session.advance(sometimes_fail)
        except RuntimeError:
            pass
        not_retried = len(calls) == 1 and session.snapshot().phase == 'notice_pending'
        session.advance(sometimes_fail)  # Explicit manual retry only.
        return (not_retried and len(calls) == 2 and calls[0] == calls[1]
                and session.snapshot().phase == 'farewell_pending')
    check('자동 재시도 없음·수동 재개', verify_manual_retry)

    def verify_duplicate():
        session = fresh()
        session.advance(lambda _: None)
        session.advance(lambda _: None)
        before = session.snapshot()
        calls = []
        try:
            session.advance(calls.append)
        except ValueError:
            pass
        return not calls and before == session.snapshot()
    check('중복 종료 호출 차단', verify_duplicate)

    def verify_reentry():
        session = fresh()
        reentered = []
        def display(_):
            try:
                session.advance(lambda value: None)
            except RuntimeError:
                reentered.append(True)
        result = session.advance(display)
        return reentered == [True] and result.phase == 'farewell_pending'
    check('표시 중 재진입 차단', verify_reentry)

    def verify_isolation():
        first, second = fresh(), fresh()
        first.advance(lambda _: None)
        return (second.snapshot().phase == 'notice_pending'
                and second.snapshot().delivered_lines == ())
    check('독립 세션 간 상태 격리', verify_isolation)

    def verify_snapshot():
        session = fresh()
        before = session.snapshot()
        try:
            before.phase = 'virtual_ended'
        except (AttributeError, TypeError):
            return session.snapshot().phase == 'notice_pending'
        return False
    check('스냅샷 외부 변조 방지', verify_snapshot)

    return ClosingAuditReport(tuple(checks))
