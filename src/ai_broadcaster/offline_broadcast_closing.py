"""Original stage 079: deterministic, *offline-only* closing conversation.

This is an inspectable simulation contract: no TTS, OBS, subprocess, network,
clock, persistence, scheduler, background worker, or real stream control.
"""
from dataclasses import dataclass

from .offline_broadcast_duration import DurationDecision


@dataclass(frozen=True)
class ClosingSnapshot:
    phase: str
    next_line: str | None
    delivered_lines: tuple[str, ...]
    virtual_stream_ended: bool
    details: str


def _safe_display_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError('캐릭터 이름은 문자열이어야 합니다.')
    value = ' '.join(value.split())
    if not value or len(value) > 40 or any(ord(char) < 32 for char in value):
        raise ValueError('캐릭터 이름은 공백 제외 1~40자로 지정하세요.')
    return value


class OfflineBroadcastClosing:
    """Single-run closing protocol with explicit delivery acknowledgement.

    initialize() requires a validated max-duration decision. Each advance()
    passes the next text to a caller-supplied *local* display function and
    advances only after that function completes successfully. No external
    action is possible through this class; its terminal bit is mock-only.
    """

    def __init__(self, decision: DurationDecision, persona_name: str):
        if not isinstance(decision, DurationDecision) or not decision.maximum_reached:
            raise ValueError('최대 방송 시간 도달 판정 후에만 종료 절차 모의를 시작할 수 있습니다.')
        if not decision.minimum_satisfied or decision.action != 'wrap_up_requested':
            raise ValueError('종료 규칙 판정이 일치하지 않습니다.')
        name = _safe_display_name(persona_name)
        self._lines = (
            f'{name}: 오늘도 함께해 주셔서 고마워요. 이제 슬슬 마무리할게요.',
            f'{name}: 오늘 방송은 여기까지 할게요. 다음에 또 만나요!',
        )
        self._phase = 'notice_pending'
        self._delivered: list[str] = []
        self._in_flight = False

    def snapshot(self) -> ClosingSnapshot:
        next_line = self._lines[len(self._delivered)] if len(self._delivered) < 2 else None
        ended = self._phase == 'virtual_ended'
        return ClosingSnapshot(
            phase=self._phase, next_line=next_line,
            delivered_lines=tuple(self._delivered), virtual_stream_ended=ended,
            details=('079 오프라인 모의 종료 완료 · 실제 OBS/방송 종료 0건 · 사용자 승인 대기'
                     if ended else '079 모의 종료 순서 점검 중 · 실제 송출/음성 출력 없음'),
        )

    def advance(self, display_text) -> ClosingSnapshot:
        """Display pending mock text; after two acknowledgements set virtual end.

        A failing display callback leaves the pending message available to
        retry manually. This method never retries automatically.
        """
        if self._in_flight:
            raise RuntimeError('마무리 단계 중복 진행 차단')
        if self._phase == 'virtual_ended':
            raise ValueError('가상 종료 후에는 다시 진행할 수 없습니다.')
        if not callable(display_text):
            raise ValueError('문구를 표시할 로컬 콜백이 필요합니다.')
        self._in_flight = True
        try:
            text = self._lines[len(self._delivered)]
            display_text(text)
            self._delivered.append(text)
            if len(self._delivered) == 1:
                self._phase = 'farewell_pending'
            else:
                # 'Automatic' termination is only a local state transition.
                self._phase = 'virtual_ended'
            return self.snapshot()
        finally:
            self._in_flight = False
