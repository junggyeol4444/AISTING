"""Original roadmap 038: consent-gated offline idle speech rehearsal.

Purely simulated clock.  No timers, actual AI, audio, PC inspection, storage,
networking or broadcasting. Chat reception always takes priority; there is no
artificial delay for chat responses.  The operator owns idle threshold and text.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .all_chat_policy import AllChatPolicySession, PolicyAudit
from .core_execution import LocalReplyPort

MAX_IDLE_SECONDS = 86400
MAX_IDLE_THRESHOLD = 3600
MAX_UTTERANCE_LENGTH = 240


@dataclass(frozen=True)
class IdleSpeechAudit:
    enabled: bool
    threshold_seconds: int | None
    quiet_seconds: int
    chat: PolicyAudit
    suggestions: tuple[str, ...]
    reason: str

    def describe(self) -> str:
        lines = [
            '원본 038단계 · 무채팅 시 자발적 발화 모의 (수동 가상 시계)',
            f'사용자 활성화: {"켜짐" if self.enabled else "꺼짐"} · '
            f'가상 무채팅 시간: {self.quiet_seconds}초 · '
            f'운영자 지정 기준: {self.threshold_seconds if self.threshold_seconds is not None else "미설정"}초',
            f'채팅 접수 {self.chat.accepted}건 / 응답 {len(self.chat.replied)}건 / 대기 {len(self.chat.pending)}건',
            f'모의 발화 후보 {len(self.suggestions)}건 · 상태: {self.reason}',
            '채팅 우선: 대기/실패 채팅이 있으면 자발 발화 후보를 만들지 않습니다.',
            '이 화면은 사용자 입력 텍스트를 후보로만 표시하며 실제 AI 생성·음성·방송 출력은 하지 않습니다.',
            '설정/기억 저장, 네트워크, PC 정보 조회, 자동 타이머/지연 없음',
        ]
        for seq, sender, text in self.chat.pending:
            lines.append(f'대기 채팅 #{seq} {sender}: {text[:70]}')
        for index, message in enumerate(self.suggestions, 1):
            lines.append(f'모의 발화 후보 #{index}: {message}')
        return '\n'.join(lines)


class IdleSpeechSession:
    """Isolated mock; explicit enable, simulated clock and evaluation.

    Each idle period yields at most one preview. A successfully received chat
    rearms it, but queued/failed chats cannot be bypassed by idle output.
    """

    def __init__(self, settings: Mapping[str, object], *, reply_port: LocalReplyPort | None = None):
        self._chat = AllChatPolicySession(settings, reply_port=reply_port)
        self._enabled = False
        self._threshold: int | None = None
        self._utterance = ''
        self._quiet = 0
        self._produced_in_period = False
        self._suggestions: list[str] = []

    def configure(self, *, enabled: bool, threshold_seconds: int, utterance: str) -> IdleSpeechAudit:
        # All-or-nothing validation: rejected settings cannot arm the system.
        if type(enabled) is not bool:
            raise ValueError('활성화 값은 참/거짓이어야 합니다.')
        if type(threshold_seconds) is not int or not 1 <= threshold_seconds <= MAX_IDLE_THRESHOLD:
            raise ValueError(f'무채팅 기준은 1~{MAX_IDLE_THRESHOLD}초 정수여야 합니다.')
        if type(utterance) is not str or not utterance.strip() or len(utterance) > MAX_UTTERANCE_LENGTH:
            raise ValueError(f'발화 예시 문구는 1~{MAX_UTTERANCE_LENGTH}자로 입력해야 합니다.')
        if any(ord(ch) < 32 for ch in utterance):
            raise ValueError('발화 문구에 개행·제어 문자를 넣을 수 없습니다.')
        changed = (self._threshold != threshold_seconds or self._utterance != utterance.strip())
        self._enabled = enabled
        self._threshold = threshold_seconds
        self._utterance = utterance.strip()
        # Reconfiguring does not silently enable a second utterance in same quiet period.
        if changed:
            self._quiet = 0
            self._produced_in_period = False
        return self.audit()

    def receive_chat(self, script: str) -> IdleSpeechAudit:
        self._chat.append(script)
        self._quiet = 0
        self._produced_in_period = False
        return self.audit()

    def process_chat(self, *, manual_retry: bool = False) -> IdleSpeechAudit:
        self._chat.run_next(manual_retry=manual_retry)
        # Do not consider time spent handling chat as idle; no throttling.
        self._quiet = 0
        return self.audit()

    def process_batch(self, count: int = 50) -> IdleSpeechAudit:
        self._chat.run_batch(count)
        self._quiet = 0
        return self.audit()

    def advance(self, seconds: int) -> IdleSpeechAudit:
        if type(seconds) is not int or not 1 <= seconds <= MAX_IDLE_SECONDS:
            raise ValueError(f'가상 시간 이동은 1~{MAX_IDLE_SECONDS}초 정수여야 합니다.')
        self._quiet += seconds
        return self.audit()

    def preview_if_idle(self) -> IdleSpeechAudit:
        report = self._chat.audit()
        if (self._enabled and self._threshold is not None
                and self._quiet >= self._threshold and not report.pending
                and report.failed_sequence is None and not report.stopped_reason
                and not self._produced_in_period):
            self._suggestions.append(self._utterance)
            self._produced_in_period = True
        return self.audit()

    def audit(self) -> IdleSpeechAudit:
        report = self._chat.audit()
        if not self._enabled:
            reason = '운영자 비활성 · 모의 발화 없음'
        elif report.pending or report.failed_sequence is not None or report.stopped_reason:
            reason = '채팅 처리 우선 · 모의 발화 차단'
        elif self._produced_in_period:
            reason = '이번 무채팅 구간 후보 생성 완료 · 반복 없음'
        elif self._threshold is None:
            reason = '무채팅 기준 미설정'
        elif self._quiet < self._threshold:
            reason = '무채팅 기준 미도달'
        else:
            reason = '발화 후보 확인 버튼을 누르면 모의 생성 가능'
        return IdleSpeechAudit(self._enabled, self._threshold, self._quiet,
                               report, tuple(self._suggestions), reason)
