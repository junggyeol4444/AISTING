"""25단계: 실제 모델 접속 없이 한국어 대화의 *구조적* 회귀 시험.

운영자가 실행 버튼을 눌렀을 때만 새 메모리 전용 OfflineCoreSession을 만든다.
한국어 자연스러움·맥락 이해를 채점하지 않으며, 모의 답변의 문자 보존,
입력 순서, 중복, 유효한 응답 여부만 확인한다. 사용자 설정/SQLite/PC 정보에 접근하지 않는다.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Mapping

from .core_execution import LocalReplyPort, OfflineCoreSession
from .offline_chat import parse_script

SAMPLE_KOREAN_SCRIPT = (
    "하늘: 안녕하세요!\n"
    "바다: 오늘 방송은 어떤 내용인가요?\n"
    "하늘: 안녕하세요!\n"
    "별: 게임도 하시나요? 🎮\n"
    "초롱: AI와 한국어로 이야기하고 싶어요.\n"
    "나래: 반가워요 :) hello 123\n"
    "해솔: 띄어쓰기와 쉼표, 물음표는 괜찮나요?"
)
MAX_KOREAN_TURNS = 30
MAX_KOREAN_SCRIPT = 10000


def _has_hangul(text: str) -> bool:
    return any("\uac00" <= char <= "\ud7a3" for char in unicodedata.normalize("NFC", text))


def _valid_reply(text: object) -> bool:
    return (
        type(text) is str and bool(text.strip()) and _has_hangul(text)
        and "\ufffd" not in text
        and not any(unicodedata.category(char) == "Cc" and char not in "\n\t" for char in text)
    )


@dataclass(frozen=True)
class KoreanTurnCheck:
    sender: str
    input_text: str
    response: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class KoreanDialogueReport:
    turns: tuple[KoreanTurnCheck, ...]
    total: int
    remaining: int
    error: str = ""

    @property
    def passed(self) -> bool:
        return (self.total > 0 and not self.error and self.remaining == 0
                and len(self.turns) == self.total and all(turn.passed for turn in self.turns))

    @property
    def passed_count(self) -> int:
        return sum(turn.passed for turn in self.turns)

    def describe(self) -> str:
        lines = [
            "25단계 · 한국어 대화 구조 시험 (오프라인 모의 답변)",
            f"판정: {'구조 시험 통과' if self.passed else '구조 시험 실패'} · {self.passed_count}/{self.total}건 통과 · 남은 입력 {self.remaining}건",
            "검사: FIFO/중복/원문 보존, 한글 포함 응답, 빈 답변·문자 깨짐 방지",
            "주의: 모의 답변은 원문을 인용합니다. 한국어 문장 자연스러움·의미 이해·대화 맥락·실제 AI 품질을 검증하지 않습니다.",
            "사용자 설정·SQLite 기억·파일·네트워크·Ollama·OBS·방송·PC 사양 조회 없음",
            "Windows 실기기 및 실제 로컬 모델 한국어 생성은 사용자 승인 후 별도 검증 필요 · 공식 9/100",
        ]
        if self.error:
            lines.append("중단 원인: " + self.error)
        for i, turn in enumerate(self.turns, 1):
            lines.append(
                f"[{i}] {'통과' if turn.passed else '실패'} · {turn.sender}: {turn.input_text[:200]}\n"
                f"AI(모의): {turn.response[:300]}" + ("\n원인: " + turn.reason if turn.reason else "")
            )
        return "\n\n".join(lines)


def run_korean_dialogue_test(
    settings: Mapping[str, object], script: str = SAMPLE_KOREAN_SCRIPT,
    *, reply_port: LocalReplyPort | None = None,
) -> KoreanDialogueReport:
    """독립 세션을 생성하여 구조 검사만 수행. 입력 오류 시 외부 부작용 없음.

    reply_port는 네트워크 없는 가짜 포트 주입용이며 기본값은 기존 모의 응답기.
    실제 Ollama/로컬 음성/방송 포트는 여기서 절대 선택하지 않는다.
    """
    if type(script) is not str or len(script) > MAX_KOREAN_SCRIPT:
        raise ValueError(f"시험 대본은 문자열 {MAX_KOREAN_SCRIPT}자 이하이어야 합니다.")
    parsed = parse_script(script)
    if len(parsed) > MAX_KOREAN_TURNS:
        raise ValueError(f"한 번의 한국어 시험은 최대 {MAX_KOREAN_TURNS}건입니다.")
    if not any(_has_hangul(item.text) for item in parsed):
        raise ValueError("한국어 시험에는 한글이 포함된 채팅이 적어도 하나 필요합니다.")

    # settings는 검증만 수행하며 저장/수정하지 않는다. 별도 세션을 매 호출 생성한다.
    session = OfflineCoreSession(dict(settings), reply_port=reply_port)
    session.enqueue(script)
    turns: list[KoreanTurnCheck] = []
    error = ""
    for expected in parsed:
        try:
            reply = session.process_one()
        except Exception as exc:
            error_kind = "ValueError" if isinstance(exc, ValueError) else "RuntimeError" if isinstance(exc, RuntimeError) else type(exc).__name__
            error = f"모의 응답 생성 실패 ({error_kind}): {exc}"
            break
        if reply is None:
            error = "입력 대기열이 예정보다 먼저 비었습니다."
            break
        same_input = reply.input.sender == expected.sender and reply.input.text == expected.text
        valid_text = _valid_reply(reply.text)
        ok = same_input and valid_text
        reason = "" if ok else ("입력 순서/원문이 다릅니다." if not same_input else "한글 없는/비어 있는/깨진 응답입니다.")
        turns.append(KoreanTurnCheck(expected.sender, expected.text, reply.text, ok, reason))
    return KoreanDialogueReport(tuple(turns), len(parsed), session.pending_count, error)
