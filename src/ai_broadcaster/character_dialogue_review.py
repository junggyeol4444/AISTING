"""Roadmap 040: operator-led first character dialogue review, strictly offline.

Combines *existing* persona / preferences / optional directions / boundaries
with the stage-035 FIFO mock test.  A simulated response is not evaluated as
natural or policy-compliant; only the operator may record such a judgement.
No file, device, model, platform or network access is performed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .basic_reaction_test import (
    SAMPLE_REACTION_SCRIPT, BasicReactionReport, run_basic_reaction_test,
)
from .core_execution import LocalReplyPort
from .offline_settings import validate_settings
from .operator_boundaries import validate_boundaries
from .reaction_directions import review_reaction_directions

SAMPLE_CHARACTER_SCRIPT = (
    '새봄: 안녕하세요!\n'
    '해솔: ㅋㅋㅋ\n'
    '새봄: 안녕하세요!\n'
    '구름: 요즘 좋아하는 건 뭐예요?\n'
    '달빛: 그건 왜 그런가요?\n'
    '해솔: 다음에 또 만나요!'
)
VERDICTS = ('검토 대기', '자연스러움 확인', '수정 필요')
MAX_NOTE = 500


@dataclass(frozen=True)
class CharacterDialogueReport:
    persona_guidance: str
    mock: BasicReactionReport
    boundary_count: int
    direction_count: int

    @property
    def structure_passed(self) -> bool:
        return self.mock.passed

    def describe(self) -> str:
        return (
            '원본 40단계 · 캐릭터 대화 1차 검증 (운영자 판정 대기)\n'
            f"모의 대화 구조: {'통과' if self.structure_passed else '실패'} "
            f'{self.mock.passed_count}/{self.mock.total}건 · 대기 {self.mock.remaining}건\n'
            f'운영자 직접 입력한 반응 방향 {self.direction_count}개 / 금기 {self.boundary_count}개 (참고용 미리보기만)\n'
            '※ 아래 프롬프트는 모의 답변 생성기에 전달되지 않습니다.\n'
            '※ 답변의 자연스러움·말투 적합성·금기 준수는 자동 판정하지 않습니다.\n'
            '※ 사용자 승인·실제 AI 모델·음성·방송·Windows 실기기 검증과 무관합니다.\n\n'
            '=== 운영자 캐릭터 지침 미리보기 ===\n' + self.persona_guidance
            + '\n\n=== 대화 처리 구조 결과 ===\n' + self.mock.describe()
        )


@dataclass(frozen=True)
class OperatorDialogueAssessment:
    verdicts: tuple[str, ...]
    notes: tuple[str, ...]
    structure_passed: bool

    @property
    def all_reviewed(self) -> bool:
        return bool(self.verdicts) and all(v != '검토 대기' for v in self.verdicts)

    @property
    def operator_accepted(self) -> bool:
        return (self.structure_passed and self.all_reviewed
                and all(v == '자연스러움 확인' for v in self.verdicts))

    def describe(self) -> str:
        lines = ['운영자 수동 평가 · 프로그램 재시작 시 초기화 · 자동 승인/설정 변경 없음',
                 f"구조 검사 {'통과' if self.structure_passed else '실패'} · "
                 f"운영자 판정 {'모두 입력' if self.all_reviewed else '대기 포함'} · "
                 f"{'운영자 긍정 평가 기록' if self.operator_accepted else '최종 판정 대기 또는 수정 필요'}",
                 '※ 모의 응답에 대한 운영자 표시일 뿐 실제 AI 자연스러움/최종 개발 승인이 아닙니다.']
        for n, (verdict, note) in enumerate(zip(self.verdicts, self.notes), 1):
            lines.append(f'[{n}] {verdict}' + (f' — {note}' if note else ''))
        return '\n'.join(lines)


def review_character_dialogue(settings: Mapping[str, object],
                              script: str = SAMPLE_CHARACTER_SCRIPT, *,
                              likes: str = '', dislikes: str = '',
                              directions: Mapping[str, str] | None = None,
                              boundaries: Sequence[str] = (),
                              reply_port: LocalReplyPort | None = None) -> CharacterDialogueReport:
    """Run an isolated mock after validating operator-edited selections.

    Optional fields are supplied explicitly from *visible UI text*, never
    loaded from historical files without a user action.
    """
    validated = validate_settings(dict(settings))
    directions = {} if directions is None else directions
    if not isinstance(directions, dict):
        raise ValueError('반응 방향은 상황별 문자열 사전이어야 합니다.')
    mode, draft = validated['persona_mode'], validated['persona']
    reaction = review_reaction_directions(mode, draft, directions, likes, dislikes)
    explicit_boundaries = validate_boundaries(boundaries)
    appendix = ('\n운영자가 직접 입력한 금기·제한사항 (선택):\n'
                + '\n'.join(f'- {item}' for item in explicit_boundaries)) if explicit_boundaries else ''
    mock = run_basic_reaction_test(validated, script, reply_port=reply_port)
    return CharacterDialogueReport(
        reaction.guidance + appendix, mock, len(explicit_boundaries),
        sum(bool(value) for _, value in reaction.directions),
    )


def assess_character_dialogue(report: CharacterDialogueReport,
                              verdicts: Sequence[str],
                              notes: Sequence[str]) -> OperatorDialogueAssessment:
    """Track operator judgements only; never infer naturalness from mock text."""
    if not isinstance(report, CharacterDialogueReport):
        raise ValueError('먼저 유효한 모의 대화 검사를 실행해야 합니다.')
    if (not isinstance(verdicts, (tuple, list)) or not isinstance(notes, (tuple, list))
            or len(verdicts) != report.mock.total or len(notes) != report.mock.total):
        raise ValueError('모든 대화 순번에 해당하는 평가와 메모가 필요합니다.')
    if (any(type(v) is not str or v not in VERDICTS for v in verdicts)
            or any(type(n) is not str or len(n) > MAX_NOTE
                   or any(ord(c) < 32 and c not in '\n\t' for c in n) for n in notes)):
        raise ValueError('평가값 또는 메모 형식이 올바르지 않습니다.')
    return OperatorDialogueAssessment(tuple(verdicts), tuple(notes), report.structure_passed)
