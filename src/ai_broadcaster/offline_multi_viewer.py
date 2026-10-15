"""Original 068: manual multi-viewer FIFO conversation exercise, offline only.

Reuses the existing 062 receiver, 063 queue, 065 reply session, and 067
per-(platform, nickname) successful-turn context. It neither selects viewers
nor runs a background worker; the operator starts every processing batch.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_chat_reactions import OfflineChatReactions, MockReaction, MAX_REACTION_BATCH
from .offline_chat_receiver import MockReceivedChat


@dataclass(frozen=True)
class ViewerLane:
    platform: str
    sender: str
    accepted_ordinals: tuple[int, ...]
    staged_ordinals: tuple[int, ...]
    replied_ordinals: tuple[int, ...]
    pending_ordinals: tuple[int, ...]
    unsynced_ordinals: tuple[int, ...]

    @property
    def next_pending(self) -> int | None:
        return self.pending_ordinals[0] if self.pending_ordinals else None


@dataclass(frozen=True)
class MultiViewerReport:
    active: bool
    viewers: tuple[ViewerLane, ...]
    accepted: int
    staged: int
    replied: int
    pending: int
    unsynced: int
    head: MockReceivedChat | None
    blocked: bool
    order_paused: bool
    source_consistent: bool
    mock_only: bool = True

    @property
    def complete(self) -> bool:
        return (self.active and self.accepted > 0 and self.replied == self.accepted
                and not self.pending and not self.unsynced and not self.blocked
                and not self.order_paused and self.source_consistent)

    def describe(self) -> str:
        lines = [
            '원본 068 · 여러 시청자 대화 처리 · 운영자 수동 오프라인 모의',
            f'시청자별 맥락: {"활성" if self.active else "비활성 · 첫 응답 전 활성화 필요"}',
            f'가상 시청자 {len(self.viewers)}명 / 수동 접수 {self.accepted}건 / '
            f'동기화 {self.staged}건 / 모의 응답 {self.replied}건 / '
            f'대기 {self.pending}건 / 미동기화 {self.unsynced}건',
            f'응답 중단 {"예" if self.blocked else "아니오"} / '
            f'순서 중단 {"예" if self.order_paused else "아니오"} / '
            f'원본 일치 {"예" if self.source_consistent else "아니오 · 처리 차단"}',
            '모든 시청자 채팅을 수신 순번 FIFO로 1회씩 처리 · 중복 내용도 보존 · '
            '시청자별 우선순위/선별/고의 지연/자동 재시도 없음',
            '시청자 구분은 플랫폼+직접 입력 닉네임(실제 계정 ID 아님) · '
            '이전 성공 응답만 해당 시청자에게 전달',
            '실제 플랫폼/AI 모델/음성/아바타/방송 연결 없음 · 파일 저장/네트워크 없음',
        ]
        if self.head is not None:
            lines.append(f'다음 전체 FIFO 선두 #{self.head.ordinal} '
                         f'[{self.head.platform}] {self.head.sender}')
        for lane in self.viewers[:15]:
            lines.append(f'[{lane.platform}] {lane.sender}: 접수 {len(lane.accepted_ordinals)} / '
                         f'응답 {len(lane.replied_ordinals)} / 대기 {len(lane.pending_ordinals)} / '
                         f'미동기화 {len(lane.unsynced_ordinals)} / '
                         f'다음 #{lane.next_pending if lane.next_pending is not None else "없음"}')
        if len(self.viewers) > 15:
            lines.append(f'화면에는 앞 15명만 표시 · 나머지 {len(self.viewers)-15}명도 '
                         '원본 수신/처리 기록에서 제외하지 않음')
        if self.complete:
            lines.append('현재 수동 접수된 다중 시청자 모의 채팅 모두 처리 (실방송 검증 아님)')
        return '\n'.join(lines)


class OfflineMultiViewerDialogue:
    """Manual processing of all interleaved viewers in a single existing FIFO.

    No per-viewer worker/queue or scheduling: per-viewer lanes are *read-only*
    projections of the single source, not independently reordered streams.
    """

    def __init__(self, reactions: OfflineChatReactions) -> None:
        if not isinstance(reactions, OfflineChatReactions):
            raise ValueError('65단계 기존 모의 응답 세션이 필요합니다.')
        self._reactions = reactions

    def snapshot(self) -> MultiViewerReport:
        state = self._reactions.snapshot()
        received = self._reactions._receiver.snapshot().buffered
        order = self._reactions._order.snapshot()
        try:
            self._reactions._validate_source()
            consistent = (all(type(e.ordinal) is int and e.ordinal == i
                              for i, e in enumerate(received, start=1))
                          and len(state.responded) <= len(state.staged)
                          and all(item.event == state.staged[i]
                                  for i, item in enumerate(state.responded)))
        except ValueError:
            consistent = False

        lanes: dict[tuple[str, str], dict[str, list[int]]] = {}

        def record(event: MockReceivedChat, column: str) -> None:
            key = (event.platform, event.sender)
            if key not in lanes:
                lanes[key] = dict(accepted=[], staged=[], replied=[], pending=[], unsynced=[])
            lanes[key][column].append(event.ordinal)

        # Build lanes in first-acceptance order; never sort or discard events.
        for event in received:
            record(event, 'accepted')
        for event in state.staged:
            record(event, 'staged')
        for item in state.responded:
            record(item.event, 'replied')
        for event in state.pending:
            record(event, 'pending')
        for event in received[len(state.staged):]:
            record(event, 'unsynced')

        viewers = tuple(ViewerLane(platform, sender,
                                  tuple(data['accepted']), tuple(data['staged']),
                                  tuple(data['replied']), tuple(data['pending']),
                                  tuple(data['unsynced']))
                        for (platform, sender), data in lanes.items())
        return MultiViewerReport(
            active=self._reactions.viewer_context_enabled, viewers=viewers,
            accepted=len(received), staged=len(state.staged), replied=len(state.responded),
            pending=len(state.pending), unsynced=len(received) - len(state.staged),
            head=state.pending[0] if state.pending else None,
            blocked=state.blocked, order_paused=order.paused,
            source_consistent=consistent,
        )

    def activate(self) -> MultiViewerReport:
        """Explicitly select per-viewer context before the first reply."""
        if not self._reactions.viewer_context_enabled:
            self._reactions.enable_viewer_context()
        return self.snapshot()

    def sync(self) -> MultiViewerReport:
        """Operator-triggered 062 -> 063 -> 065 append-only sync, no reply."""
        self._reactions._order.sync()
        self._reactions.sync()
        return self.snapshot()

    def _require_active(self) -> None:
        if not self._reactions.viewer_context_enabled:
            raise ValueError('여러 시청자 맥락을 먼저 수동 활성화하세요 (첫 응답 전).')

    def reply_next(self, *, simulate_failure: bool = False) -> MockReaction:
        self._require_active()
        return self._reactions.reply_next(simulate_failure=simulate_failure)

    def reply_batch(self, count: int = MAX_REACTION_BATCH) -> MultiViewerReport:
        self._require_active()
        self._reactions.reply_batch(count)
        return self.snapshot()

    def resume(self) -> MultiViewerReport:
        """Manual resume after a reply-port failure; never auto-retry head."""
        self._reactions.resume()
        return self.snapshot()
