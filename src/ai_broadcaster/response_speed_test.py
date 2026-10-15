"""Roadmap 036: opt-in timing for isolated mock replies, not human-likeness grading.

No OS/hardware inventory, networking, filesystem, TTS, artificial waits or streaming.
Only the synchronous, in-memory core processing segment is timed per message.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from statistics import median
from time import perf_counter_ns
from typing import Callable, Mapping

from .basic_reaction_test import SAMPLE_REACTION_SCRIPT, MAX_REACTION_SCRIPT, MAX_REACTION_TURNS
from .core_execution import LocalReplyPort, MockCoreReplyPort, OfflineCoreSession
from .offline_chat import parse_script

SAMPLE_SPEED_SCRIPT = SAMPLE_REACTION_SCRIPT


@dataclass(frozen=True)
class TimedTurn:
    sequence: int
    sender: str
    text: str
    elapsed_ns: int

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed_ns / 1_000_000


@dataclass(frozen=True)
class SpeedReport:
    turns: tuple[TimedTurn, ...]
    total: int
    remaining: int
    attempts: int
    stopped_reason: str = ""

    @property
    def completed(self) -> bool:
        return (self.total > 0 and self.remaining == 0 and not self.stopped_reason
                and self.attempts == self.total and len(self.turns) == self.total)

    @property
    def median_ms(self) -> float | None:
        return median(t.elapsed_ms for t in self.turns) if self.turns else None

    @property
    def p95_ms(self) -> float | None:
        if not self.turns:
            return None
        ordered = sorted(t.elapsed_ms for t in self.turns)
        return ordered[ceil(0.95 * len(ordered)) - 1]

    @property
    def total_measured_ms(self) -> float:
        return sum(t.elapsed_ns for t in self.turns) / 1_000_000

    def describe(self) -> str:
        lines = [
            "원본 계획 36단계 · 응답 시간 관찰 (오프라인 모의 전용)",
            f"{'모의 처리 완료' if self.completed else '모의 처리 미완료'} · 완료 {len(self.turns)}/{self.total}건 · 미처리 {self.remaining}건 · 시도 {self.attempts}회",
            "측정 범위: 각 채팅의 메모리 내 코어 처리 1회 (입력 대기/화면 표시/TTS/모델 생성/방송 시간 제외)",
            "인위적 대기 시간·자동 재시도·채팅 선별 없음 / 속도 합격 기준 없음",
            "모의 실행 시간은 Windows PC나 실제 AI의 응답 성능을 나타내지 않습니다.",
            "자연스러움·말투 적합성의 최종 판단은 운영자가 합니다.",
            "자동 파일 기록·설정 변경·PC 사양 조회·네트워크·OBS 접근 없음",
        ]
        if self.turns:
            lines.append(f"측정 합계 {self.total_measured_ms:.3f} ms · 중앙값 {self.median_ms:.3f} ms · "
                         f"최소 {min(x.elapsed_ms for x in self.turns):.3f} ms · "
                         f"최대 {max(x.elapsed_ms for x in self.turns):.3f} ms · "
                         f"P95(최근접 순위) {self.p95_ms:.3f} ms")
        else:
            lines.append("완료된 응답의 유효한 시간 표본이 없습니다.")
        if self.stopped_reason:
            lines.append("중단: " + self.stopped_reason)
        for turn in self.turns:
            lines.append(f"[{turn.sequence}] {turn.sender}: {turn.text[:120]} → {turn.elapsed_ms:.3f} ms")
        return "\n\n".join(lines)


def run_response_speed_test(
    settings: Mapping[str, object],
    script: str = SAMPLE_SPEED_SCRIPT,
    *,
    reply_port: LocalReplyPort | None = None,
    clock_ns: Callable[[], int] | None = None,
) -> SpeedReport:
    """Operator-triggered, at-most-30-turn isolated run; never grade speed/naturalness.

    ``clock_ns`` and ``reply_port`` are injectable for offline deterministic tests.
    A failure stops immediately and keeps the rest of the private queue untouched.
    Clock readings are validated; malformed/nonmonotonic readings cannot be reported as success.
    """
    if type(script) is not str or len(script) > MAX_REACTION_SCRIPT:
        raise ValueError(f"시험 대본은 {MAX_REACTION_SCRIPT}자 이하의 문자열이어야 합니다.")
    messages = parse_script(script)
    if len(messages) > MAX_REACTION_TURNS:
        raise ValueError(f"최대 {MAX_REACTION_TURNS}건의 채팅만 측정할 수 있습니다.")
    session = OfflineCoreSession(dict(settings), reply_port=reply_port if reply_port is not None else MockCoreReplyPort())
    session.enqueue(script)
    clock = perf_counter_ns if clock_ns is None else clock_ns
    turns: list[TimedTurn] = []
    attempts = 0
    failure = ""
    for index, item in enumerate(messages, 1):
        try:
            start = clock()
            if type(start) is not int or start < 0:
                raise ValueError("invalid clock")
        except Exception:
            failure = f"{index}번째 측정 시작 시계 오류 (PC 정보는 조회하지 않음)"
            break
        attempts += 1
        try:
            answer = session.process_one()
        except Exception:
            failure = f"{index}번째 모의 응답 실패 · 실패 입력과 이후 채팅은 대기 상태 (자동 재시도 없음)"
            break
        try:
            end = clock()
            if type(end) is not int or end < start:
                raise ValueError("invalid clock")
        except Exception:
            failure = f"{index}번째 측정 종료 시계 오류 · 실제 응답 성공은 시간 검사 완료로 간주하지 않음"
            break
        if answer is None or answer.input.sender != item.sender or answer.input.text != item.text:
            failure = f"{index}번째 채팅 응답 순서 불일치"
            break
        turns.append(TimedTurn(index, item.sender, item.text, end - start))
    return SpeedReport(tuple(turns), len(messages), session.pending_count, attempts, failure)
