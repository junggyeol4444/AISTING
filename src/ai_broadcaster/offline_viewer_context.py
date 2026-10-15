"""Original 067: link a viewer's previous *successful* mock turns to 065 replies.

Opt-in and operator-triggered. Same (platform, sender) is a synthetic session
key, not an authenticated viewer ID. No real model, sockets, persistence,
background processing, default filtering or artificial response delays.
"""
from __future__ import annotations

from dataclasses import dataclass

from .core_execution import MAX_CONTEXT_TURNS
from .offline_chat_reactions import OfflineChatReactions
from .offline_chat_receiver import MockReceivedChat


@dataclass(frozen=True)
class ViewerContextReport:
    enabled: bool
    next_event: MockReceivedChat | None
    prior_ordinals: tuple[int, ...]
    prior_inputs: tuple[str, ...]
    replied: int
    pending: int
    blocked: bool
    unsynced: int
    mock_only: bool = True

    def describe(self) -> str:
        lines = [
            '원본 067 · 시청자별 이전 대화 맥락 → 기존 모의 응답 포트 연결',
            f'시청자별 맥락 연결: {"활성" if self.enabled else "비활성 (기존 065 방식 유지)"}',
            f'모의 응답 {self.replied}건 · 동기화 대기 {self.pending}건 · 미동기화 {self.unsynced}건',
            f'오류 중단: {"예" if self.blocked else "아니오"}',
            f'연결 기준: 플랫폼 + 수동 입력 닉네임의 정확한 문자열 일치 · 직전 성공 {MAX_CONTEXT_TURNS}건',
            '모의 닉네임은 실제 계정 인증 ID가 아니며 동일인 식별/장기 기억을 보장하지 않습니다.',
            '모든 채팅 FIFO 유지 · 실패/미응답 채팅은 맥락에 넣지 않음 · 인위적 지연 없음',
            '실제 플랫폼/AI 모델/음성/방송/네트워크/파일 저장 없음',
        ]
        if self.next_event is None:
            lines.append('현재 동기화된 다음 대기 채팅 없음')
        else:
            e = self.next_event
            lines.append(f'다음 채팅 #{e.ordinal} [{e.platform}] {e.sender}: {e.text[:100]}')
            lines.append(f'같은 시청자의 이전 성공 응답 {len(self.prior_ordinals)}건: '
                         + (', '.join('#' + str(x) for x in self.prior_ordinals) or '없음'))
        return '\n'.join(lines)


class OfflineViewerContext:
    """Read-only preview + explicit policy switch for existing 065 session."""

    def __init__(self, reactions: OfflineChatReactions) -> None:
        if not isinstance(reactions, OfflineChatReactions):
            raise ValueError('65단계 기존 모의 응답 세션이 필요합니다.')
        self._reactions = reactions

    def enable(self) -> ViewerContextReport:
        self._reactions.enable_viewer_context()
        return self.snapshot()

    def snapshot(self) -> ViewerContextReport:
        state = self._reactions.snapshot()
        event = state.pending[0] if state.pending else None
        prior = () if event is None else tuple(
            item for item in state.responded
            if item.event.platform == event.platform and item.event.sender == event.sender
            and item.event.ordinal < event.ordinal
        )[-MAX_CONTEXT_TURNS:]
        return ViewerContextReport(
            enabled=self._reactions.viewer_context_enabled,
            next_event=event,
            prior_ordinals=tuple(item.event.ordinal for item in prior),
            prior_inputs=tuple(item.event.text for item in prior),
            replied=len(state.responded), pending=len(state.pending),
            blocked=state.blocked, unsynced=state.unsynced,
        )
