"""Original stage 060: operator-triggered, OFFLINE integrated 2D avatar rehearsal.

Combines existing renderer, layout, virtual voice timing and endurance checks.
A passing report only certifies the built-in mock Canvas paths, never a real
voice, Live2D/VRM model, Windows PC, OBS or a natural-looking avatar.
"""
from __future__ import annotations

from dataclasses import dataclass

from .avatar_renderer import AvatarFrame, EXPRESSIONS
from .avatar_layout import AvatarLayout, draw_layout_preview
from .avatar_motion_review import inspect_motion_canvas
from .avatar_voice_sync import VirtualVoiceMouthSync
from .avatar_endurance import run_virtual_endurance, audit_canvas_repetition

SAMPLE_SCRIPT = '시청자A: 안녕하세요\n시청자B: 오늘도 반가워요'
TEST_VOICE_NAME = 'AISTING_무음_시험_음성'


@dataclass(frozen=True)
class AvatarIntegrationReport:
    passed: bool
    checks: tuple[str, ...]
    failures: tuple[str, ...]
    virtual_segments: int
    virtual_frames: int
    canvas_cycles: int

    def describe(self) -> str:
        return '\n'.join((
            '원본 060 · 내장 2D 캐릭터 통합 모의 검사: ' + ('통과' if self.passed else '실패'),
            *(f'통과: {item}' for item in self.checks),
            *(f'실패: {item}' for item in self.failures),
            f'가상 음성 구간 {self.virtual_segments} · 가상 프레임 {self.virtual_frames:,} · Tk 반복 {self.canvas_cycles}회',
            '실제 Windows/EXE·24시간 연속 실행·음성 파형 립싱크·외부 모델·OBS·자연스러움은 미검증. 운영자 승인 대기.',
        ))


def audit_avatar_integration(canvas, *, avatar: str, name: str, expression: str,
                             layout: AvatarLayout, voice_source: str,
                             rate: int = 0, volume: int = 85) -> AvatarIntegrationReport:
    """Run a bounded integration test and always restore the chosen idle preview.

    Fails closed for 3D/undecided/unsupported voice source. No implicit choice
    changes, disk I/O, network access, OS speech or background activity.
    """
    if type(avatar) is not str or avatar != '2d':
        raise ValueError('내장 2D를 선택하세요. 3D/미정에서 2D 자동 대체는 금지됩니다.')
    if type(layout) is not AvatarLayout or layout.avatar != avatar:
        raise ValueError('유효한 내장 2D 배치가 필요합니다.')
    if type(name) is not str or not name.strip():
        raise ValueError('캐릭터 이름을 확인하세요.')
    if type(expression) is not str or expression not in EXPRESSIONS:
        raise ValueError('표정 선택이 유효하지 않습니다.')
    if voice_source != 'windows_system' or type(voice_source) is not str:
        raise ValueError('무음 음성 연결 시험은 Windows 무료 음성 방식을 선택해야 합니다. 실제 음성 조회는 하지 않습니다.')
    # Delegate rate/volume validation to the existing virtual voice route.
    session = VirtualVoiceMouthSync(
        SAMPLE_SCRIPT, avatar=avatar, name=name, expression=expression,
        voice_source=voice_source, voice_name=TEST_VOICE_NAME,
        rate=rate, volume=volume, fail_second_once=True,
    )
    initial = AvatarFrame(name, False, 4, background=layout.background, expression=expression)
    checks: list[str] = []
    failures: list[str] = []
    segments = virtual_frames = cycles = 0

    def inspect(label: str, pose: AvatarFrame) -> None:
        draw_layout_preview(canvas, layout, pose)
        issues = inspect_motion_canvas(canvas, pose)
        if issues:
            failures.append(label + ': ' + '; '.join(issues))
        else:
            checks.append(label)

    try:
        # Verify four built-in expressions and speaking/idle + blink transitions.
        for face in EXPRESSIONS:
            for speaking, frame in ((False, 4), (True, 1), (True, 45), (False, 46)):
                inspect(f'표정 {face} / {"발화" if speaking else "대기"} / 프레임 {frame}',
                        AvatarFrame(name, speaking, frame, background=layout.background,
                                    expression=face))
        # Synthetic voice dispatch: first chat succeeds, second fails once,
        # remains pending without any extra voice window, then manual retry.
        first = session.step()
        if len(first.completed) != 1 or len(first.pending) != 1 or not session.windows:
            failures.append('첫 채팅/가상 음성 전달 상태 불일치')
        else:
            checks.append('첫 채팅 가상 음성 전달')
        before = len(session.windows)
        interrupted = session.step()
        if (interrupted.state == 'simulated_complete' or len(interrupted.pending) != 1
                or len(session.windows) != before):
            failures.append('가상 전달 실패 시 중단/미처리 보존 위반')
        else:
            checks.append('가상 음성 중단·미처리 보존')
        resumed = session.step()
        if len(resumed.completed) != 2 or resumed.pending:
            failures.append('사용자 수동 재개 후 채팅 완료 실패')
        else:
            checks.append('수동 재개 후 모든 채팅 완료')
        ok, reason = session.audit()
        if not ok or not session.windows:
            failures.append('가상 입 시각 정렬: ' + reason)
        else:
            checks.append('가상 음성 구간/입 시각 정렬')
        segments = len(session.windows)
        for index, window in enumerate(session.windows, 1):
            for phase, ms in (('시작', window.start_ms), ('종료 직전', window.end_ms - 1)):
                synced = session.seek(ms)
                pose = AvatarFrame(name, synced.frame.speaking, synced.frame.frame,
                                   background=layout.background, expression=expression)
                inspect(f'가상 구간 {index} {phase} / 입·표정·배치', pose)
        ended = session.seek(session.duration_ms)
        if ended.frame.mouth != 0 or ended.window is not None:
            failures.append('가상 음성 종료 후 입 닫힘 위반')
        else:
            checks.append('가상 음성 종료 후 입 닫힘')
        inspect('가상 음성 종료 화면', AvatarFrame(
            name, False, 4, background=layout.background, expression=expression))
        # Reuse the existing endurance implementation; do not claim real time.
        endurance = run_virtual_endurance(
            avatar=avatar, name=name, expression=expression,
            background=layout.background, hours=1)
        virtual_frames = endurance.inspected_frames
        if virtual_frames != 3600 or len(endurance.checkpoints) != 12:
            failures.append('가속 모의 장시간 프레임 수/보관 한도 위반')
        else:
            checks.append('가속 1시간 모의 프레임·보관 한도')
        low, high = audit_canvas_repetition(canvas, layout, endurance, cycles=60)
        cycles = 60
        if not 1 <= low <= high <= 40:
            failures.append('Tk Canvas 반복 객체 수 제한 위반')
        else:
            checks.append('Tk Canvas 60회 반복 렌더링 객체 수 제한')
    finally:
        # Restore even if any downstream stage raises (no partial preview left).
        draw_layout_preview(canvas, layout, initial)
    return AvatarIntegrationReport(not failures, tuple(checks), tuple(failures),
                                   segments, virtual_frames, cycles)
