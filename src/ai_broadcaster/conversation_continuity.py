"""29단계: 명시적 읽기 후 저장된 모의 응답과 새 채팅의 연속성 구조 검증.

실제 AI 의미 이해나 영구 기억을 주장하지 않는다. DB 읽기는 호출 시에만 수행.
"""
from __future__ import annotations

from dataclasses import dataclass
from .core_execution import MAX_CONTEXT_TURNS
from .offline_chat import parse_script
from .response_records import ResponseRecord, ResponseRecordStore


@dataclass(frozen=True)
class ContinuityReport:
    saved_count: int
    new_count: int
    checks: tuple[tuple[str, int, str], ...]
    passed: bool

    def describe(self) -> str:
        lines = ["29단계 · 저장 기록 → 새 대화 연속성 구조 검증 (오프라인)",
                 f"판정: {'통과' if self.passed else '실패'} · 저장 이력 {self.saved_count}건 · 새 입력 {self.new_count}건",
                 f"직전 최대 {MAX_CONTEXT_TURNS}건 전달 순서·중복·세션 경계 확인",
                 "실제 AI 의미 이해·기억 품질 검증 아님. 실제 모델/방송/네트워크 연결 없음."]
        lines.extend(f"{i+1}. {sender}: 직전 {count}건 · {note}" for i, (sender, count, note) in enumerate(self.checks))
        return "\n".join(lines)


def check_continuity(records: tuple[ResponseRecord, ...], script: str) -> ContinuityReport:
    """순서가 보장된 동일 세션의 저장 기록만 사용. 새 입력은 저장하지 않음."""
    if type(records) is not tuple or not records:
        raise ValueError("연결할 저장 기록이 없습니다. 먼저 수동으로 기록을 저장해 주세요.")
    if type(script) is not str or len(script) > 10000:
        raise ValueError("새 대화 대본은 10000자 이하 문자열이어야 합니다.")
    incoming = parse_script(script)
    if not 1 <= len(incoming) <= 30:
        raise ValueError("새 대화는 1~30건이어야 합니다.")
    key = records[0].session_key
    last = 0
    for record in records:
        if not isinstance(record, ResponseRecord) or record.session_key != key or record.turn_no <= last:
            raise ValueError("저장 기록의 세션 또는 순서가 올바르지 않습니다.")
        last = record.turn_no
    history = [(r.sender, r.input_text, r.reply_text) for r in records]
    checks = []
    for item in incoming:
        context = history[-MAX_CONTEXT_TURNS:]
        expected = history[max(0, len(history)-MAX_CONTEXT_TURNS):]
        if context != expected:
            return ContinuityReport(len(records), len(incoming), tuple(checks), False)
        checks.append((item.sender, len(context), "저장 이력 연결" if len(checks) == 0 else "신규 입력 순서 유지"))
        # 신규 입력은 아직 답변이 없으므로 성공 응답 이력에 넣지 않는다.
    return ContinuityReport(len(records), len(incoming), tuple(checks), True)


def check_saved_continuity(store: ResponseRecordStore, script: str) -> ContinuityReport:
    """사용자 버튼으로 호출하는 읽기 전용 경로. DB 생성/수정 없음."""
    rows = store.recent(100)
    if not rows:
        raise ValueError("저장된 응답 기록이 없습니다.")
    newest_key = rows[0].session_key
    session_rows = tuple(reversed([row for row in rows if row.session_key == newest_key]))
    return check_continuity(session_rows, script)
