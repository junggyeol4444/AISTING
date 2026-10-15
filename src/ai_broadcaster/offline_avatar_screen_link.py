"""Stage 072: offline-only avatar-to-scene linkage inspection.

No OBS, capture, device access, persistence, network, or background polling.
"""
from dataclasses import dataclass
from .offline_broadcast_scene import BroadcastSceneDraft, draw_broadcast_scene
from .avatar_renderer import EXPRESSIONS


@dataclass(frozen=True)
class AvatarScreenLinkReport:
    avatar: str
    linked_sample: bool
    expression: str
    detail: str


def inspect_avatar_screen_link(canvas, draft: BroadcastSceneDraft, expression: str = 'neutral') -> AvatarScreenLinkReport:
    """Manually redraw existing offline scene and inspect visible canvas tags."""
    if type(draft) is not BroadcastSceneDraft:
        raise ValueError('검증된 방송 화면 구성안이 필요합니다.')
    if type(expression) is not str or expression not in EXPRESSIONS:
        raise ValueError('기존 2D 표정 선택이 올바르지 않습니다.')
    draw_broadcast_scene(canvas, draft, expression=expression)
    if draft.avatar != '2d':
        return AvatarScreenLinkReport(draft.avatar, False, expression,
            '3D/미정: 실제 아바타 화면 미연결 · 2D 대체 없음 · OBS/송출 없음')
    # Canvas tags are inspected, rather than assuming draw calls succeeded.
    tags = set(canvas.gettags(item) for item in canvas.find_all())
    flat = {tag for group in tags for tag in group}
    linked = 'aisting_sample_2d' in flat
    return AvatarScreenLinkReport('2d', linked, expression,
        ('기존 2D 샘플 화면 연결 표시 확인' if linked else '2D 샘플 표시 태그 미확인')
        + ' · 오프라인 Canvas만 검증 · OBS/송출 없음')
