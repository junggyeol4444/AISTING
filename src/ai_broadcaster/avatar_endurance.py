"""Original stage 059: bounded, accelerated OFFLINE 2D avatar endurance rehearsal.

This is NOT a 24-hour wall-clock run or a memory-leak certification. The full
virtual timeline is evaluated, while only <=12 checkpoint frames are retained.
No sleep, sound, network, OBS, background timer, file writes, or 3D fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import perf_counter

from .avatar_renderer import AvatarFrame, BACKGROUND_COLORS, EXPRESSIONS
from .avatar_layout import AvatarLayout, draw_layout_preview

ALLOWED_HOURS = (1, 6, 24)
CHECKPOINT_LIMIT = 12
RENDER_CYCLES = 240
MAX_CANVAS_ITEMS = 40


@dataclass(frozen=True)
class EnduranceResult:
    hours: int
    virtual_seconds: int
    inspected_frames: int
    speaking_frames: int
    idle_frames: int
    mouth_open_frames: int
    blink_frames: int
    checkpoints: tuple[tuple[int, AvatarFrame], ...]
    fingerprint: str
    wall_seconds: float

    def summary(self) -> str:
        return (f'가상 {self.hours}시간 / {self.inspected_frames:,}개 프레임 검사 · '
                f'발화 {self.speaking_frames:,} / 대기 {self.idle_frames:,} · '
                f'입 열림 {self.mouth_open_frames:,} · 눈 깜빡임 {self.blink_frames:,}\n'
                f'보관 프레임 {len(self.checkpoints)}/{CHECKPOINT_LIMIT}개 · '
                f'계산 실제 경과 {self.wall_seconds:.3f}초 · SHA256 {self.fingerprint[:16]}\n'
                '실제 장시간 실행·메모리 누수·실제 TTS·방송 안정성은 검증하지 않았습니다.')


def run_virtual_endurance(*, avatar: str, name: str, expression: str,
                          background: str = '남색 스튜디오', hours: int = 24) -> EnduranceResult:
    """Evaluate every simulated second; fixed 20s speech/idle rehearsal cycle."""
    if avatar != '2d' or type(avatar) is not str:
        raise ValueError('내장 2D 샘플만 검사합니다. 3D 자동 대체는 금지됩니다.')
    if type(hours) is not int or hours not in ALLOWED_HOURS:
        raise ValueError('모의 시간은 1·6·24시간 중 하나여야 합니다.')
    if type(name) is not str or not name.strip():
        raise ValueError('캐릭터 이름을 확인하세요.')
    if type(expression) is not str or expression not in EXPRESSIONS:
        raise ValueError('지원하지 않는 표정입니다.')
    if type(background) is not str or background not in BACKGROUND_COLORS:
        raise ValueError('지원하지 않는 배경입니다.')
    total = hours * 3600
    checkpoints: list[tuple[int, AvatarFrame]] = []
    selected = {round(i * (total - 1) / (CHECKPOINT_LIMIT - 1))
                for i in range(CHECKPOINT_LIMIT)}
    digest = sha256()
    # Bind the fingerprint to the selected sample identity as well as its timeline.
    for field in (name, expression, background):
        raw = field.encode('utf-8')
        digest.update(len(raw).to_bytes(4, 'big'))
        digest.update(raw)
    speaking_count = idle_count = open_count = blink_count = 0
    start = perf_counter()
    for second in range(total):
        # Synthetic voice: 8 seconds speaking, 12 seconds idle. Never actual TTS.
        speaking = second % 20 < 8
        pose = AvatarFrame(name, speaking, second,
                           background=background, expression=expression)
        speaking_count += speaking
        idle_count += not speaking
        open_count += bool(pose.mouth)
        blink_count += pose.blink
        digest.update(bytes((int(speaking), pose.mouth, int(pose.blink))))
        if second in selected:
            checkpoints.append((second, pose))
    if (speaking_count + idle_count != total or len(checkpoints) != CHECKPOINT_LIMIT
            or any(t1 >= t2 for (t1, _), (t2, _) in zip(checkpoints, checkpoints[1:]))):
        raise RuntimeError('가상 프레임 수/순서 검증 실패')
    return EnduranceResult(hours, total, total, speaking_count, idle_count,
                           open_count, blink_count, tuple(checkpoints),
                           digest.hexdigest(), perf_counter() - start)


def audit_canvas_repetition(canvas, layout: AvatarLayout, result: EnduranceResult,
                            *, cycles: int = RENDER_CYCLES) -> tuple[int, int]:
    """Actually redraw a Tk Canvas repeatedly; bound per-frame object count.

    Restores the initial frame even on error. Checks Canvas item growth, not
    process RSS or actual 24-hour renderer stability.
    """
    if type(layout) is not AvatarLayout or type(result) is not EnduranceResult:
        raise ValueError('2D 배치와 검사 결과가 필요합니다.')
    if type(cycles) is not int or not 1 <= cycles <= RENDER_CYCLES:
        raise ValueError('화면 반복 횟수 초과')
    if layout.background != result.checkpoints[0][1].background:
        raise ValueError('배경이 검사 결과와 다릅니다.')
    sizes: list[int] = []
    try:
        for index in range(cycles):
            _, base = result.checkpoints[index % len(result.checkpoints)]
            # Change frame number to exercise blink and mouth transitions.
            pose = AvatarFrame(base.name, index % 20 < 8, index,
                               background=base.background, expression=base.expression)
            draw_layout_preview(canvas, layout, pose)
            count = len(canvas.find_all())
            if not 1 <= count <= MAX_CANVAS_ITEMS:
                raise RuntimeError(f'Canvas 객체 수 비정상: {count}')
            sizes.append(count)
    finally:
        draw_layout_preview(canvas, layout, result.checkpoints[0][1])
    return min(sizes), max(sizes)
