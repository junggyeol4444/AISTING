"""Original 086: *manual*, in-memory broadcast-start announcement rehearsal.

There is intentionally NO network transport, publisher, scheduler, timer,
Discord authentication, file persistence, or claim that anything was posted.
A simulated start from stage 082 is a prerequisite, never a real stream.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .offline_broadcast_schedule import parse_reference
from .offline_discord_notice_link import prepare_discord_notice_dry_run
from .offline_prebroadcast_notice import PrebroadcastNoticeDraft
from .offline_start_control import OfflineStartController


@dataclass(frozen=True)
class NoticePostingRehearsalResult:
    code: str
    explanation: str
    occurrence: str | None = None
    published: bool = False
    scheduled: bool = False
    transport_used: bool = False

    def describe(self) -> str:
        return f'086 {self.code} · {self.explanation} · 실제 게시/예약/전송 없음'


class OfflineNoticePostingRehearsal:
    """Per-process duplicate suppression for simulated announcement displays.

    Records are NOT persisted across program restarts and thus cannot protect
    against real-world duplicate posts; no posts can be made by this class.
    """

    def __init__(self):
        self._displayed: set[str] = set()

    @property
    def simulated_count(self) -> int:
        return len(self._displayed)

    def inspect(self, draft: PrebroadcastNoticeDraft,
                controller: OfflineStartController,
                settings: Mapping[str, object]) -> NoticePostingRehearsalResult:
        # Reuse stage 085 structural and safety validation instead of
        # duplicating Discord validation or accepting a raw payload.
        preview = prepare_discord_notice_dry_run(draft)
        if type(controller) is not OfflineStartController:
            raise ValueError('082 가상 시작 제어기가 필요합니다.')
        if type(draft.announcement_time) is not str:
            raise ValueError('공지 시각이 유효하지 않습니다.')
        try:
            when = parse_reference(draft.announcement_time.removesuffix(' KST'))
        except (ValueError, TypeError) as exc:
            raise ValueError('운영자가 입력한 공지 KST 시각이 올바르지 않습니다.') from exc
        occurrence = when.strftime('%Y-%m-%d %H:%M KST')
        if draft.announcement_time != occurrence:
            raise ValueError('공지 시각 형식이 정확하지 않습니다.')
        # inspect() enforces safe, explicitly disabled execution/publish flags
        # even if a caller uses a forged object or modifies settings directly.
        start = controller.inspect(when, settings)
        if start.code == 'blocked':
            return NoticePostingRehearsalResult('blocked', start.explanation, occurrence)
        if not controller.active or controller.active_occurrence != occurrence:
            return NoticePostingRehearsalResult(
                'not_started', '동일한 시각의 082 가상 방송 시작이 확인되지 않았습니다.', occurrence)
        if start.code != 'mock_active' or start.occurrence != occurrence:
            return NoticePostingRehearsalResult(
                'blocked', '시작 제어 상태가 일치하지 않습니다.', occurrence)
        if occurrence in self._displayed:
            return NoticePostingRehearsalResult('duplicate', '같은 시작 시각은 이미 가상 표시했습니다.', occurrence)
        if preview.to_preview_dict()['send_ready'] is not False:
            return NoticePostingRehearsalResult('blocked', '전송 가능한 메시지는 사용하지 않습니다.', occurrence)
        return NoticePostingRehearsalResult('mock_ready', '검토용 공지를 화면에 가상 표시할 수 있습니다.', occurrence)

    def simulate_display(self, draft: PrebroadcastNoticeDraft,
                         controller: OfflineStartController,
                         settings: Mapping[str, object],
                         *, show_local: Callable[[str], None]) -> NoticePostingRehearsalResult:
        """Explicit user action; a failed GUI display does not consume the slot."""
        decision = self.inspect(draft, controller, settings)
        if decision.code != 'mock_ready':
            return decision
        if not callable(show_local):
            raise ValueError('검토용 문구를 표시할 화면 콜백이 필요합니다.')
        try:
            show_local(draft.text)
        except Exception as exc:
            return NoticePostingRehearsalResult(
                'display_failed', f'화면 표시 실패로 기록 미소비 · 수동 재시도 가능: {type(exc).__name__}',
                decision.occurrence)
        self._displayed.add(decision.occurrence)
        return NoticePostingRehearsalResult(
            'mock_displayed', '화면에만 가상 공지 표시 · 서버 게시 기록 아님', decision.occurrence)
