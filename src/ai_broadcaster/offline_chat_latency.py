"""Original stage 066: time *existing* 065 FIFO mock replies, without added waits.

Operator-triggered only. This is a measurement of synchronous in-memory mock
reply calls, NOT message-arrival-to-reply latency or real model/network speed.
No timer, sleep, worker, network, persistence, threshold, or automatic retry.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from statistics import median
from time import perf_counter_ns
from typing import Callable

from .offline_chat_reactions import MAX_REACTION_BATCH, MockReaction, OfflineChatReactions


@dataclass(frozen=True)
class TimedMockReaction:
    reaction: MockReaction
    elapsed_ns: int

    @property
    def ordinal(self) -> int:
        return self.reaction.event.ordinal

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed_ns / 1_000_000


@dataclass(frozen=True)
class ChatLatencyReport:
    received: int
    responded: int
    pending: int
    unsynced: int
    blocked: bool
    samples: tuple[TimedMockReaction, ...]
    unmeasured_ordinals: tuple[int, ...]
    invalid_samples: tuple[int, ...]
    failed_attempts: int
    clock_faults: int
    mock_only: bool = True

    @property
    def completed(self) -> bool:
        return (self.received > 0 and self.responded == self.received and
                not self.pending and not self.unsynced and not self.blocked and
                not self.unmeasured_ordinals and not self.invalid_samples and
                len(self.samples) == self.received)

    @property
    def median_ms(self) -> float | None:
        return median(sample.elapsed_ms for sample in self.samples) if self.samples else None

    @property
    def p95_ms(self) -> float | None:
        if not self.samples:
            return None
        times = sorted(sample.elapsed_ms for sample in self.samples)
        return times[ceil(len(times) * 0.95) - 1]

    def describe(self) -> str:
        lines = [
            '원본 066 · 인위적 응답 지연 없는 수동 모의 처리 시간 관찰',
            f'접수 {self.received}건 · 응답 {self.responded}건 · 측정 {len(self.samples)}건 · '
            f'응답 대기 {self.pending}건 · 미동기화 {self.unsynced}건',
            f'실패 시도 {self.failed_attempts}회 · 측정 시계 오류 {self.clock_faults}회 · '
            f'{"모의 측정 완료" if self.completed else "모의 측정 미완료"}',
            '측정 범위: 운영자 버튼 클릭 후 기존 065 모의 응답 포트의 동기 호출 시간만.',
            '채팅 도착~응답/GUI 표시/TTS/실제 LLM/네트워크/방송 지연은 측정하지 않습니다.',
            '고의 대기·타이머·자동 재시도·채팅 선별·속도 합격 기준 없음.',
            '실제 플랫폼 메시지/AI 모델 0건 · 자연스러움·속도 적합성은 운영자가 판단.',
            '설정·기존 수신함·순서 기록·SQLite·사용자 파일 수정 없음.',
        ]
        if self.samples:
            elapsed = [item.elapsed_ms for item in self.samples]
            lines.append(f'모의 응답 시간: 중앙값 {self.median_ms:.3f}ms · '
                         f'P95(최근접 순위) {self.p95_ms:.3f}ms · '
                         f'최소 {min(elapsed):.3f}ms · 최대 {max(elapsed):.3f}ms')
        else:
            lines.append('성공적으로 측정된 모의 응답이 없습니다.')
        if self.unmeasured_ordinals:
            lines.append('응답은 했지만 시간을 측정하지 못한 순번: '
                         + ', '.join(map(str, self.unmeasured_ordinals[:30])))
        if self.invalid_samples:
            lines.append('기존 응답 기록과 일치하지 않는 측정 순번: '
                         + ', '.join(map(str, self.invalid_samples[:30])))
        if self.blocked:
            lines.append('모의 응답 오류 중단 · 기존 065 화면에서 운영자 수동 재개 필요')
        lines.extend(f'#{item.ordinal} [{item.reaction.event.platform}] {item.elapsed_ms:.3f}ms'
                     for item in self.samples[-15:])
        return '\n'.join(lines)


class OfflineChatLatencyAudit:
    """Non-destructive timer around *one* already staged mock reply at a time.

    If the clock fails *after* a reply, that reply remains consumed and is
    explicitly reported as unmeasured; never replay it to obtain a time.
    """

    def __init__(self, reactions: OfflineChatReactions,
                 *, clock_ns: Callable[[], int] | None = None) -> None:
        if not isinstance(reactions, OfflineChatReactions):
            raise ValueError('65단계 기존 모의 응답 세션이 필요합니다.')
        self._reactions = reactions
        self._clock = perf_counter_ns if clock_ns is None else clock_ns
        self._samples: list[TimedMockReaction] = []
        self._failed_attempts = 0
        self._clock_faults = 0

    def snapshot(self) -> ChatLatencyReport:
        current = self._reactions.snapshot()
        responses = {item.event.ordinal: item for item in current.responded}
        valid_samples = tuple(sample for sample in self._samples
                              if responses.get(sample.ordinal) == sample.reaction)
        valid_ordinals = {sample.ordinal for sample in valid_samples}
        invalid_ordinals = tuple(sample.ordinal for sample in self._samples
                                 if responses.get(sample.ordinal) != sample.reaction)
        unmeasured = tuple(item.event.ordinal for item in current.responded
                           if item.event.ordinal not in valid_ordinals)
        return ChatLatencyReport(current.received, len(current.responded), len(current.pending),
                                 current.unsynced, current.blocked, valid_samples,
                                 unmeasured, invalid_ordinals,
                                 self._failed_attempts, self._clock_faults)

    def measure_next(self) -> TimedMockReaction:
        try:
            start = self._clock()
            if type(start) is not int or start < 0:
                raise ValueError('invalid start')
        except Exception:
            self._clock_faults += 1
            raise ValueError('측정 시작 시계 오류 · 채팅을 처리하지 않았습니다.') from None
        try:
            reply = self._reactions.reply_next()
        except ValueError:
            self._failed_attempts += 1
            raise
        try:
            end = self._clock()
            if type(end) is not int or end < start:
                raise ValueError('invalid end')
        except Exception:
            self._clock_faults += 1
            raise ValueError('측정 종료 시계 오류 · 모의 응답은 이미 처리됨 · 자동 재처리 금지') from None
        timed = TimedMockReaction(reply, end - start)
        self._samples.append(timed)
        return timed

    def measure_batch(self, count: int = MAX_REACTION_BATCH) -> ChatLatencyReport:
        if type(count) is not int or not 1 <= count <= MAX_REACTION_BATCH:
            raise ValueError(f'한 번에 1~{MAX_REACTION_BATCH}건만 수동 측정할 수 있습니다.')
        pending = len(self._reactions.snapshot().pending)
        if not pending:
            raise ValueError('측정할 동기화 채팅이 없습니다. 먼저 수동 동기화하세요.')
        for _ in range(min(count, pending)):
            self.measure_next()  # fail fast; do not retry or skip a chat
        return self.snapshot()
