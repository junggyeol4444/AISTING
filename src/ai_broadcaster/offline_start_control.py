"""082: fail-closed *manual* rehearsal of schedule-triggered broadcast starts.

Never registers a timer, reads the system clock, runs an executable, sends audio,
connects to OBS/platforms or actually starts a stream. All times are supplied by
an operator/test in modern Korean wall time, without automatic clock polling.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Mapping

from .offline_broadcast_schedule import BroadcastScheduleDraft, KST

PROHIBITED_FLAGS = ('scheduled_execution', 'streaming_enabled', 'external_publish_enabled')


@dataclass(frozen=True)
class StartDecision:
    code: str
    explanation: str
    occurrence: str | None = None

    @property
    def can_mock_start(self) -> bool:
        return self.code == 'mock_ready'


class OfflineStartController:
    """In-memory rehearsal control; NO real broadcast-capable start action."""

    def __init__(self, draft: BroadcastScheduleDraft):
        if type(draft) is not BroadcastScheduleDraft:
            raise TypeError('검증된 로컬 일정 초안만 허용됩니다.')
        self._draft = draft
        self._seen: set[str] = set()
        self._active: str | None = None

    @property
    def active(self) -> bool:
        return self._active is not None

    @property
    def active_occurrence(self) -> str | None:
        """Current *virtual* start timestamp, never real broadcast state."""
        return self._active

    @property
    def simulated_count(self) -> int:
        return len(self._seen)

    def inspect(self, when: datetime, settings: Mapping[str, object]) -> StartDecision:
        if not isinstance(settings, dict) or any(settings.get(k) is not False for k in PROHIBITED_FLAGS):
            return StartDecision('blocked', '자동 시작·실제 송출·외부 게시 설정이 비활성임을 확인할 수 없습니다.')
        if (not isinstance(when, datetime) or when.tzinfo is None or when.utcoffset() != timedelta(hours=9)):
            raise ValueError('운영자가 입력한 KST 날짜·시간만 사용할 수 있습니다.')
        if when.second or when.microsecond:
            return StartDecision('not_due', '정확한 HH:MM 경계가 아니므로 시작 대상이 아닙니다.')
        when = when.astimezone(KST)
        matches = [slot for slot in self._draft.slots
                   if slot.weekday == when.weekday() and slot.start_time == when.strftime('%H:%M')]
        if not matches:
            return StartDecision('not_due', '현재 수동 입력 시간과 일치하는 등록 일정이 없습니다.')
        occurrence = when.strftime('%Y-%m-%d %H:%M KST')
        if self._active is not None:
            return StartDecision('mock_active', '이미 가상 방송 중이므로 추가 시작을 차단했습니다.', occurrence)
        if occurrence in self._seen:
            return StartDecision('duplicate', '같은 일정 발생 시각은 이미 가상 시작 처리됐습니다.', occurrence)
        return StartDecision('mock_ready', '가상 시작만 가능 · 실제 자동 시작은 비활성입니다.', occurrence)

    def simulate_start(self, when: datetime, settings: Mapping[str, object],
                       *, show_mock_start: Callable[[str], None] | None = None) -> StartDecision:
        """Explicit operator call only. Failure to show status does NOT consume slot."""
        decision = self.inspect(when, settings)
        if not decision.can_mock_start:
            return decision
        if show_mock_start is not None:
            try:
                show_mock_start(decision.occurrence)
            except Exception as exc:
                return StartDecision('display_failed', '가상 표시 실패, 일정 미소비 · 수동 재시도 필요: '
                                     + type(exc).__name__, decision.occurrence)
        self._seen.add(decision.occurrence)
        self._active = decision.occurrence
        return StartDecision('mock_started', '메모리 가상 시작만 기록했습니다. 실제 방송은 시작하지 않았습니다.',
                             decision.occurrence)

    def simulate_finish(self) -> StartDecision:
        if self._active is None:
            return StartDecision('not_active', '종료할 가상 세션이 없습니다. 실제 방송 제어 없음.')
        occurrence = self._active
        self._active = None
        return StartDecision('mock_finished', '메모리 가상 세션 종료 · 실제 방송 제어 없음.', occurrence)
