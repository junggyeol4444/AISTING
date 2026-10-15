"""Stage 064: read-only, operator-triggered audit of synthetic chat ingress.

An ordinal is a *local manual-acceptance* counter, not a platform message ID.
Equal sender/text is never sufficient evidence to discard or reject a chat.
This audit performs no I/O, retries, synchronization or message processing.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .offline_chat_receiver import OfflineChatReceiveBuffer, MockReceivedChat
from .offline_chat_order import OfflineChatOrder


@dataclass(frozen=True)
class IntegrityReport:
    received: int
    synced: int
    checked: int
    pending: int
    unsynced: int
    repeated_content_groups: int
    repeated_content_extra: int
    issues: tuple[str, ...]
    paused: bool
    mock_only: bool = True

    @property
    def structurally_consistent(self) -> bool:
        return not self.issues

    def describe(self) -> str:
        state = '구조 오류 발견' if self.issues else '현재 관찰 범위에서 구조 오류 없음'
        lines = [
            '원본 064 · 중복·누락 구조 점검 · 수동 오프라인 모의',
            state,
            f'수신 {self.received}건 / 063 동기화 {self.synced}건 / 순서 확인 {self.checked}건 / 대기 {self.pending}건',
            f'아직 수동 동기화하지 않은 접수 {self.unsynced}건 (누락 판정 아님)',
            f'동일 플랫폼·닉네임·내용 반복 그룹 {self.repeated_content_groups}개 / 추가 건수 {self.repeated_content_extra}건 (정상 중복 가능, 삭제·차단 없음)',
            f'순서 관리 중단 상태: {"예" if self.paused else "아니오"}',
        ]
        lines.extend('오류: ' + issue for issue in self.issues)
        lines.extend((
            '같은 내용의 채팅은 서로 다른 정상 메시지일 수 있으므로 자동 중복 제거하지 않습니다.',
            '마지막 수신 이후의 미도착 메시지, 플랫폼 고유 ID, 서버 재전송, 실제 네트워크 누락은 판정할 수 없습니다.',
            '실제 플랫폼 수신 0건 · 실제 AI 응답 0건 · 방송 송출 없음 · 이번 검사 결과는 검사 시점의 메모리 스냅샷입니다.',
        ))
        return '\n'.join(lines)


class OfflineChatIntegrity:
    """Read-only consistency check across existing 062 receiver and 063 queue."""

    def __init__(self, receiver: OfflineChatReceiveBuffer, order: OfflineChatOrder) -> None:
        if not isinstance(receiver, OfflineChatReceiveBuffer):
            raise ValueError('62단계 모의 수신함이 필요합니다.')
        if not isinstance(order, OfflineChatOrder) or order._receiver is not receiver:
            raise ValueError('같은 62단계 수신함을 참조하는 63단계 순서 관리가 필요합니다.')
        self._receiver = receiver
        self._order = order

    def inspect(self) -> IntegrityReport:
        """Never mutate either source, even when a corrupted buffer is found."""
        received = self._receiver.snapshot().buffered
        ordered = self._order.snapshot()
        issues: list[str] = []
        valid = [event for event in received if isinstance(event, MockReceivedChat)]
        if len(valid) != len(received):
            issues.append('수신함에 잘못된 메시지 형식이 있습니다.')
        malformed_content = [event for event in valid if any(type(field) is not str for field in
                             (event.platform, event.sender, event.text))]
        if malformed_content:
            issues.append('수신 메시지의 플랫폼·닉네임·내용 형식이 올바르지 않습니다.')
        ordinals = [event.ordinal for event in valid]
        valid_ordinals = [n for n in ordinals if type(n) is int and n > 0]
        if len(valid_ordinals) != len(ordinals):
            issues.append('수신 순번에 올바르지 않은 값이 있습니다.')
        counts = Counter(valid_ordinals)
        collisions = sorted(n for n, count in counts.items() if count > 1)
        if collisions:
            issues.append('수신 순번 중복: ' + ', '.join(f'#{n}' for n in collisions[:12]))
        # Detect holes only inside the *observed* 1..max range. An absent tail
        # cannot be detected without a server-side sequence/watermark.
        if valid_ordinals:
            missing: list[int] = []
            previous = 0
            for current in sorted(set(valid_ordinals)):
                if current > previous + 1:
                    missing.extend(range(previous + 1, min(current, previous + 13)))
                if len(missing) >= 12:
                    break
                previous = current
            if missing:
                issues.append('관찰된 순번 범위의 누락: ' + ', '.join(f'#{n}' for n in missing[:12]))
        if ordinals != list(range(1, len(received) + 1)):
            issues.append('수신 순번이 1부터 연속된 접수 순서와 다릅니다.')
        if ordered.queued != ordered.processed + ordered.pending:
            issues.append('순서 관리의 확인/대기 구분이 일치하지 않습니다.')
        if len(ordered.queued) > len(received) or received[:len(ordered.queued)] != ordered.queued:
            issues.append('63단계 동기화 기록과 62단계 수신함의 접두 기록이 다릅니다.')
            unsynced = 0  # do not misreport corrupt history as unsynced arrivals
        else:
            unsynced = len(received) - len(ordered.queued)
        content = Counter((event.platform, event.sender, event.text) for event in valid
                          if event not in malformed_content)
        repeated = [count for count in content.values() if count > 1]
        return IntegrityReport(
            received=len(received), synced=len(ordered.queued),
            checked=len(ordered.processed), pending=len(ordered.pending),
            unsynced=unsynced, repeated_content_groups=len(repeated),
            repeated_content_extra=sum(count - 1 for count in repeated),
            issues=tuple(issues), paused=ordered.paused,
        )
