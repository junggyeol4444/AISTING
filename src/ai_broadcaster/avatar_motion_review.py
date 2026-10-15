"""Original roadmap 057: deterministic expression and motion regression rehearsal.

Uses only the bundled Tk 2D sample; no audio, models, cameras, networks, or timers.
An audit checks Canvas structure, NOT visual appeal or actual lip synchronization.
"""
from __future__ import annotations

from dataclasses import dataclass

from .avatar_renderer import AvatarFrame, BACKGROUND_COLORS, EXPRESSIONS, draw_avatar

# Frame boundaries cover speaking/idle, three mouth openings, and blink onset/end.
MOTION_STEPS = (
    ('대기 · 눈 깜빡임', 0, False),
    ('발화 · 눈 깜빡임', 1, True),
    ('발화 · 입 변화 1', 2, True),
    ('발화 · 입 변화 2', 3, True),
    ('발화 종료 · 입 닫힘', 4, False),
    ('대기 · 눈 열림', 44, False),
    ('발화 · 눈 깜빡임 재시작', 45, True),
    ('대기 · 눈 깜빡임 지속', 46, False),
    ('대기 · 눈 열림 복귀', 47, False),
)


@dataclass(frozen=True)
class MotionInspection:
    passed: bool
    checks: tuple[str, ...]
    failures: tuple[str, ...]

    def describe(self) -> str:
        header = '모의 2D 구조 검사: ' + ('통과' if self.passed else '실패')
        return '\n'.join((header, *self.checks, *('실패: ' + x for x in self.failures),
                          '실제 음성 립싱크·움직임 자연스러움·외부 모델 품질은 미검증 (운영자 평가 대기)'))


def inspect_motion_canvas(canvas, pose: AvatarFrame) -> tuple[str, ...]:
    """Check actual Canvas tags and displayed metadata, without reading pixels."""
    failures: list[str] = []
    if not canvas.find_withtag('aisting_sample_2d') or canvas.find_withtag('aisting_3d_unavailable'):
        failures.append('내장 2D 샘플 상태가 아닙니다.')
    if canvas.cget('bg') != BACKGROUND_COLORS[pose.background]:
        failures.append('배경이 선택값과 다릅니다.')
    expected = 'aisting_expression_' + pose.expression
    if len(canvas.find_withtag(expected)) < 2 or any(
        canvas.find_withtag('aisting_expression_' + item)
        for item in EXPRESSIONS if item != pose.expression
    ):
        failures.append('표정 표시가 선택값과 다릅니다.')
    open_mouth = bool(canvas.find_withtag('aisting_mouth_open'))
    closed_mouth = bool(canvas.find_withtag('aisting_mouth_closed'))
    if open_mouth != bool(pose.mouth) or closed_mouth != (not bool(pose.mouth)):
        failures.append('입 열림/닫힘이 프레임과 다릅니다.')
    blink = bool(canvas.find_withtag('aisting_eyes_blink'))
    eyes_open = bool(canvas.find_withtag('aisting_eyes_open'))
    if blink != pose.blink or eyes_open != (not pose.blink):
        failures.append('눈 깜빡임 상태가 프레임과 다릅니다.')
    names = canvas.find_withtag('aisting_display_name')
    if len(names) != 1 or canvas.itemcget(names[0], 'text') != pose.display_name:
        failures.append('화면 캐릭터 이름이 선택값과 다릅니다.')
    return tuple(failures)


class AvatarMotionReview:
    """All motion is advanced by an explicit operator action, not by a timer."""

    def __init__(self, *, avatar: str, name: str, expression: str,
                 background: str = '남색 스튜디오'):
        if avatar != '2d':
            raise ValueError('2D 샘플을 선택해야 합니다. 3D·미정에서 2D 자동 대체는 금지됩니다.')
        if type(expression) is not str or expression not in EXPRESSIONS:
            raise ValueError('선택할 수 없는 2D 표정입니다.')
        if type(name) is not str or not name.strip():
            raise ValueError('캐릭터 이름을 확인하세요.')
        if type(background) is not str or background not in BACKGROUND_COLORS:
            raise ValueError('배경 선택이 올바르지 않습니다.')
        self.name = name
        self.expression = expression
        self.background = background
        self.index = 0

    @property
    def count(self) -> int:
        return len(MOTION_STEPS)

    @property
    def current(self) -> tuple[str, AvatarFrame]:
        label, frame, speaking = MOTION_STEPS[self.index]
        return label, AvatarFrame(self.name, speaking, frame,
                                  background=self.background, expression=self.expression)

    def seek(self, index: int) -> tuple[str, AvatarFrame]:
        if type(index) is not int or not 0 <= index < self.count:
            raise ValueError('모의 움직임 단계가 범위를 벗어났습니다.')
        self.index = index
        return self.current

    def next(self) -> tuple[str, AvatarFrame]:
        return self.seek(min(self.count - 1, self.index + 1))

    def previous(self) -> tuple[str, AvatarFrame]:
        return self.seek(max(0, self.index - 1))

    def audit(self, canvas) -> MotionInspection:
        """Render and audit each frame, restoring the selected preview afterward."""
        original = self.index
        checks: list[str] = []
        failures: list[str] = []
        try:
            for index, (label, _, _) in enumerate(MOTION_STEPS):
                _, pose = self.seek(index)
                draw_avatar(canvas, pose)
                found = inspect_motion_canvas(canvas, pose)
                if found:
                    failures.extend(f'{index + 1}단계 {label}: {err}' for err in found)
                else:
                    checks.append(f'{index + 1}/{self.count} {label}: 구조 일치')
        finally:
            self.seek(original)
            draw_avatar(canvas, self.current[1])
        return MotionInspection(not failures, tuple(checks), tuple(failures))
