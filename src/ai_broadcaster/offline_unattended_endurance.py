"""097: bounded, accelerated 1/3-hour mock-only unattended integration audit.

This never waits for real time, reads device usage, starts a schedule, opens a
socket, plays audio, persists data or touches OBS. Every run builds an isolated
in-memory 062/063/065/078/079/095 session. Passing is NOT evidence of real
unattended broadcasting, memory-leak freedom or Windows stability.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_broadcast_duration import BroadcastDurationRules, BroadcastDurationSession
from .offline_broadcast_closing import OfflineBroadcastClosing
from .platform_chat_connector import OfflinePlatformChatConnector
from .offline_chat_receiver import OfflineChatReceiveBuffer
from .offline_chat_order import OfflineChatOrder
from .offline_chat_reactions import OfflineChatReactions
from .offline_broadcast_safety import OfflineBroadcastSafetyGate

ALLOWED_HOURS = (1, 3)
CHAT_INTERVAL_SECONDS = 300
MAX_SAMPLES = 12


@dataclass(frozen=True)
class EnduranceSample:
    virtual_second: int
    accepted: int
    responded: int
    pending: int


@dataclass(frozen=True)
class EnduranceReport:
    requested_hours: int
    virtual_seconds_checked: int
    ticks_checked: int
    accepted: int
    responded: int
    pending: int
    peak_pending: int
    samples: tuple[EnduranceSample, ...]
    delivered_closing_lines: int
    virtual_end: bool
    failure: str
    mock_only: bool = True
    actual_broadcast_tested: bool = False
    real_elapsed_hours: int = 0

    @property
    def passed(self) -> bool:
        total = self.requested_hours * 3600
        expected = total // CHAT_INTERVAL_SECONDS + 1
        return (not self.failure and self.mock_only and not self.actual_broadcast_tested
                and self.virtual_end and self.delivered_closing_lines == 2
                and self.virtual_seconds_checked == total and self.ticks_checked == total + 1
                and self.accepted == self.responded == expected and self.pending == 0
                and 0 < len(self.samples) <= MAX_SAMPLES and self.peak_pending <= 1)

    def describe(self) -> str:
        return ('097 가속 오프라인 장시간 모의 검증 ' + ('통과' if self.passed else '미통과') + '\n'
                f'요청 가상 {self.requested_hours}시간 / 검사 {self.virtual_seconds_checked}초·{self.ticks_checked}틱\n'
                f'가상 채팅 접수 {self.accepted} / 가상 응답 {self.responded} / 잔여 {self.pending} / 최대 대기 {self.peak_pending}\n'
                f'고정 상한 감사 표본 {len(self.samples)}/{MAX_SAMPLES} / 가상 종료 문구 {self.delivered_closing_lines}건\n'
                f'오류: {self.failure or "없음"}\n'
                '실제 경과시간/장기 메모리 누수/Windows·OBS·AI·TTS·아바타·실방송: 미검증. '
                '사용자 최종 승인 대기. 네트워크·장치·예약·파일 I/O 없음.')


def run_virtual_unattended_endurance(
    hours: int, *, fault_second: int | None = None,
    corrupt_second: int | None = None,
    reverse_clock_second: int | None = None,
    fail_closing_display: bool = False,
) -> EnduranceReport:
    """Run 3601/10801 virtual ticks immediately, never in the background.

    Fault switches are deterministic *test injection* only. A fault halts the
    audit; there is NO automatic retry. No actual operator state is passed in.
    """
    if type(hours) is not int or hours not in ALLOWED_HOURS:
        raise ValueError('가상 실행 길이는 1시간 또는 3시간만 허용합니다.')
    total = hours * 3600
    for value in (fault_second, corrupt_second, reverse_clock_second):
        if value is not None and (type(value) is not int or value < 0 or value > total):
            raise ValueError('가상 오류 발생 시점은 실행 범위 내 정수 초여야 합니다.')
    if fault_second is not None and fault_second % CHAT_INTERVAL_SECONDS:
        raise ValueError('가상 응답 실패는 채팅 접수 시점에서만 발생할 수 있습니다.')
    if type(fail_closing_display) is not bool:
        raise ValueError('가상 문구 오류 선택값은 참/거짓이어야 합니다.')

    # All new instances: no reference to the application's mutable user session.
    connector = OfflinePlatformChatConnector(['chzzk'])
    connector.connect()
    receiver = OfflineChatReceiveBuffer()
    receiver.attach(connector)
    order = OfflineChatOrder(receiver)
    reactions = OfflineChatReactions(receiver, order)
    safety = OfflineBroadcastSafetyGate(receiver, order, reactions)
    duration = BroadcastDurationSession(BroadcastDurationRules(60, hours * 60), 0)
    sample_every = max(600, ((total // 10 + 299) // 300) * 300)
    samples: list[EnduranceSample] = []
    last_second = -1
    ticks = 0
    peak_pending = 0
    delivered = 0
    virtual_end = False
    failure = ''

    try:
        for second in range(total + 1):
            decision = duration.check(second)
            if second < 3600 and decision.minimum_satisfied:
                raise RuntimeError('최소 시간 전 마무리 판정')
            if second < total and decision.maximum_reached:
                raise RuntimeError('최대 시간 이전 종료 판정')
            if second == total and not decision.maximum_reached:
                raise RuntimeError('최대 시간 종료 판정 누락')

            if second % CHAT_INTERVAL_SECONDS == 0:
                # Deliberately identical texts to prove distinct ordinals survive.
                msg = receiver.inject('chzzk', 'synthetic-viewer', 'virtual synthetic chat')
                order.sync()
                order.acknowledge_next()
                reactions.sync()
                peak_pending = max(peak_pending, len(reactions.snapshot().pending))
                if fault_second == second:
                    try:
                        reactions.reply_next(simulate_failure=True)
                    except ValueError:
                        pass
                    if not reactions.snapshot().blocked or msg not in reactions.snapshot().pending:
                        raise RuntimeError('실패 후 미처리 메시지 보존 실패')
                    raise RuntimeError('주입된 모의 응답 실패 · 자동 재시도 없이 중단')
                result = reactions.reply_next()
                if result.event != msg:
                    raise RuntimeError('가상 응답 FIFO 불일치')
            if corrupt_second == second:
                # Corruption only in this newly constructed disposable mock object.
                order._cursor = len(order.snapshot().queued) + 1
            if reverse_clock_second == second:
                duration.check(second - 1)

            check = safety.inspect(second)
            if check.held or check.issues:
                raise RuntimeError('가상 이상 감지 보류: ' + ', '.join(check.issues))
            if check.pending != 0 or check.received != check.replied:
                raise RuntimeError('가상 채팅 누락/응답 잔여')
            ticks += 1
            last_second = second
            if second % sample_every == 0 or second == total:
                if len(samples) >= MAX_SAMPLES:
                    raise RuntimeError('감사 표본 제한 초과')
                samples.append(EnduranceSample(second, check.received, check.replied, check.pending))

        state = reactions.snapshot()
        if not state.all_responded or len(order.snapshot().processed) != state.received:
            raise RuntimeError('마지막 가상 채팅 미처리')
        closing = OfflineBroadcastClosing(decision, '아이스팅')

        def show_line(line: str) -> None:
            nonlocal delivered
            if fail_closing_display:
                raise RuntimeError('주입된 마무리 화면 표시 실패')
            if not isinstance(line, str) or not line.strip():
                raise RuntimeError('빈 가상 마무리 멘트')
            delivered += 1

        closing.advance(show_line)
        end_state = closing.advance(show_line)
        virtual_end = (end_state.phase == 'virtual_ended' and end_state.virtual_stream_ended
                       and len(end_state.delivered_lines) == 2 and delivered == 2)
        if not virtual_end:
            raise RuntimeError('가상 종료 상태 불일치')
    except Exception as exc:
        # An unexpected mock-port failure is an audit failure, never success.
        failure = f'{type(exc).__name__}: {exc}'

    final = reactions.snapshot()
    return EnduranceReport(hours, max(0, last_second), ticks,
                           final.received, len(final.responded),
                           len(final.pending) + final.unsynced, peak_pending,
                           tuple(samples), delivered, virtual_end, failure)
