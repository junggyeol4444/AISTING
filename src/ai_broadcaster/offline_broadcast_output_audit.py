"""Official 074: read-only nominal volume and local Canvas composition audit.

This inspects *settings and drawing tags*, not speaker loudness, audio samples,
OBS mixer meters, capture fidelity, real visibility to viewers or broadcasting.
No device discovery, GUI redraw, side effects or external connection.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_broadcast_scene import BroadcastSceneDraft
from .offline_broadcast_voice_link import OfflineBroadcastVoiceLink


@dataclass(frozen=True)
class BroadcastOutputAudit:
    screen_ok: bool
    volume_setting: int
    silent_by_setting: bool
    issues: tuple[str, ...]
    cautions: tuple[str, ...]
    description: str
    voice_route_prepared: bool = False
    voice_delivered_segments: int = 0


def audit_broadcast_output(
    canvas, draft: BroadcastSceneDraft, current_draft: BroadcastSceneDraft,
    volume: int, voice_link: OfflineBroadcastVoiceLink | None = None,
) -> BroadcastOutputAudit:
    """Check the rendered draft and the configured (NOT measured) volume.

    ``current_draft`` must still match the draft captured by the GUI preview.
    Canvas contains a placeholder scene, not pixels/video frames from OBS.
    """
    if type(draft) is not BroadcastSceneDraft or type(current_draft) is not BroadcastSceneDraft:
        raise ValueError('이전에 수동으로 갱신한 방송 화면 미리보기가 필요합니다.')
    if draft != current_draft:
        raise ValueError('현재 선택이 미리보기와 달라 다시 그린 후 점검해야 합니다.')
    if type(volume) is not int or not 0 <= volume <= 100:
        raise ValueError('설정 음량은 0~100의 정수여야 합니다. 실제 음량 측정값이 아닙니다.')
    if voice_link is not None and (
        type(voice_link) is not OfflineBroadcastVoiceLink or voice_link.draft != draft
    ):
        raise ValueError('무음 가상 음성 경로가 현재 미리보기와 일치하지 않습니다.')
    if not callable(getattr(canvas, 'find_withtag', None)) or not callable(getattr(canvas, 'cget', None)):
        raise ValueError('방송 화면 Canvas 검사가 불가능합니다.')
    try:
        width, height = int(canvas.cget('width')), int(canvas.cget('height'))
        present = lambda tag: bool(canvas.find_withtag(tag))
        # Store the result of all canvas queries before returning; a damaged
        # canvas or unsupported implementation must not be mistaken for PASS.
        tags = {tag: present(tag) for tag in (
            'aisting_scene_content', 'aisting_scene_watermark',
            'aisting_scene_title', 'aisting_sample_2d',
            'aisting_scene_avatar_placeholder', 'aisting_scene_voice',
            'aisting_scene_stale', 'aisting_scene_error',
        )}
    except (ValueError, TypeError, AttributeError, RuntimeError) as exc:
        raise ValueError('Canvas의 실제 구성 정보를 읽지 못했습니다.') from exc
    issues: list[str] = []
    cautions: list[str] = []
    if (width, height) != (640, 360):
        issues.append(f'Canvas 설정 크기 불일치: {width}×{height}, 예상 640×360')
    if tags['aisting_scene_stale'] or tags['aisting_scene_error']:
        issues.append('화면 미리보기가 무효 또는 오류 상태입니다.')
    for tag, label in (('aisting_scene_content', '콘텐츠 자리표시자'),
                       ('aisting_scene_watermark', '오프라인 미송출 워터마크')):
        if not tags[tag]:
            issues.append(f'{label}가 Canvas에 없습니다.')
    if tags['aisting_scene_title'] != draft.show_title:
        issues.append('제목 표시 선택과 실제 Canvas 구성 태그가 다릅니다.')
    if draft.avatar == '2d':
        if not tags['aisting_sample_2d'] or tags['aisting_scene_avatar_placeholder']:
            issues.append('선택한 2D 샘플 또는 아바타 자리표시자 구성이 일치하지 않습니다.')
    else:
        if tags['aisting_sample_2d'] or not tags['aisting_scene_avatar_placeholder']:
            issues.append('3D/미정은 자리표시자여야 하며 2D로 자동 대체할 수 없습니다.')
        cautions.append('선택한 3D/미정 아바타는 실제 렌더링되지 않았습니다.')
    # The virtual voice overlay is a text marker, NOT a sound meter.
    expected_overlay = voice_link is not None and voice_link.cursor > 0
    if tags['aisting_scene_voice'] != expected_overlay:
        issues.append('가상 음성 표시와 수동으로 처리한 구간 상태가 일치하지 않습니다.')
    if volume == 0:
        cautions.append('설정 음량이 0입니다 (음소거 설정). 실제 출력은 시험하지 않았습니다.')
    if draft.voice != 'windows_system':
        cautions.append('선택 목소리는 방송 출력 미연결 · 다른 음성으로 대체하지 않습니다.')
    else:
        cautions.append('Windows 음성 선택은 실제 음성 설치·권리·재생·음질을 보증하지 않습니다.')
    cautions.extend(draft.warnings)
    ok = not issues
    description = (
        '74단계 오프라인 음량·방송 화면 점검 · ' + ('Canvas 구성 일치' if ok else 'Canvas 구성 불일치') + '\n'
        f'현재 UI 목표 음량 {volume}/100 (설정값만 확인, 측정 음압·dB 아님) · '
        f'음소거 설정 {"예" if volume == 0 else "아니오"}\n'
        f'가상 화면 {width}×{height} · 실제 영상/음성/OBS 송출 0건\n'
        + ('오류: ' + ' / '.join(issues) + '\n' if issues else '')
        + ('주의: ' + ' / '.join(cautions) + '\n' if cautions else '')
        + '실제 소리 크기·믹싱·장치 상태·시청 화면·Windows 실기기 및 사용자 승인은 미검증.'
    )
    return BroadcastOutputAudit(ok, volume, volume == 0, tuple(issues), tuple(cautions),
                                description, voice_link is not None,
                                voice_link.cursor if voice_link is not None else 0)
