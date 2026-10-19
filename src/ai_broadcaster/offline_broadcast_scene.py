"""Original stage 071: read-only, local 16:9 *composition* preview.

No video capture, audio routing, OBS, streaming, device discovery, account
access, persistence, or background execution. Existing operator selections and
stage 058's 2D layout are used as-is; 3D is never silently replaced by 2D.
"""
from __future__ import annotations

from dataclasses import dataclass

from .avatar_layout import AvatarLayout, PREVIEW_WIDTH, PREVIEW_HEIGHT, draw_layout_preview
from .avatar_renderer import AvatarFrame, BACKGROUND_COLORS, EXPRESSIONS
from .offline_settings import PLATFORMS, CONTENTS, AVATARS, VOICES

CONTENT_LABELS = {
    'undecided': '콘텐츠 미정 · 화면 영역 자리표시자',
    'chat': '수다 콘텐츠 · 가상 화면 영역',
    'game': '게임 화면 자리표시자 · 캡처 없음',
    'both': '수다 + 게임 · 가상 분할 영역',
}


@dataclass(frozen=True)
class BroadcastSceneDraft:
    """Immutable screen-layout intent, not an executable broadcast profile."""
    platforms: tuple[str, ...]
    content: str
    avatar: str
    voice: str
    persona_name: str
    layout: AvatarLayout | None = None
    show_title: bool = True
    show_chat: bool = True

    def __post_init__(self) -> None:
        if (type(self.platforms) is not tuple or len(self.platforms) > 4
                or any(type(code) is not str or code not in PLATFORMS.values()
                       for code in self.platforms)
                or len(set(self.platforms)) != len(self.platforms)):
            raise ValueError('방송 플랫폼은 미선택 또는 중복 없는 치지직·유튜브·트위치·SOOP 선택만 허용합니다.')
        if type(self.content) is not str or self.content not in CONTENTS.values():
            raise ValueError('수다·게임·둘 다·미정 중 콘텐츠를 선택하세요.')
        if type(self.avatar) is not str or self.avatar not in AVATARS.values():
            raise ValueError('아바타 선택이 올바르지 않습니다.')
        if type(self.voice) is not str or self.voice not in VOICES.values():
            raise ValueError('목소리 선택이 올바르지 않습니다.')
        if (type(self.persona_name) is not str or not 1 <= len(self.persona_name.strip()) <= 200
                or any(ord(c) < 32 or ord(c) == 127 for c in self.persona_name)):
            raise ValueError('캐릭터 이름은 1~200자의 일반 문자열이어야 합니다.')
        if type(self.show_title) is not bool or type(self.show_chat) is not bool:
            raise ValueError('화면 오버레이 선택은 참/거짓만 허용합니다.')
        if self.avatar == '2d':
            if type(self.layout) is not AvatarLayout or self.layout.avatar != '2d':
                raise ValueError('2D 미리보기는 기존 058단계 2D 배치가 필요합니다.')
        elif self.layout is not None:
            raise ValueError('3D/미정 아바타를 2D 배치로 자동 대체하지 않습니다.')

    @property
    def warnings(self) -> tuple[str, ...]:
        warnings = []
        if not self.platforms:
            warnings.append('플랫폼 미선택 (허용 · 실제 연결 없음)')
        if self.content == 'undecided':
            warnings.append('콘텐츠 미정 (자리표시자만 표시)')
        if self.avatar != '2d':
            warnings.append('3D/미정 아바타 미연결 · 2D 자동 대체 없음')
        else:
            assert self.layout is not None
            scale, x, y = self.layout.geometry()
            # The mock content panel occupies x=12..405, y=58..308.
            if x < 405 and x + 370 * scale > 12 and y < 308 and y + 460 * scale > 58:
                warnings.append('현재 아바타 배치가 콘텐츠 영역과 겹칠 수 있음 (운영자 확인)')
        return tuple(warnings)

    def describe(self) -> str:
        labels = [label for label, code in PLATFORMS.items() if code in self.platforms]
        return ('원본 071 · 640×360 (16:9) 로컬 방송 화면 구성안\n'
                f'선택 플랫폼: {", ".join(labels) if labels else "미선택"} (연결 안 됨)\n'
                f'콘텐츠: {CONTENT_LABELS[self.content]}\n'
                f'아바타: {self.avatar} · 캐릭터: {self.persona_name.strip()}\n'
                f'목소리 방식: {self.voice} (음성 출력/믹싱 미연결)\n'
                f'제목 표시: {self.show_title} · 채팅 UI 자리표시자: {self.show_chat}\n'
                + ('검토 안내: ' + ' / '.join(self.warnings) + '\n' if self.warnings else '')
                + '오프라인 Canvas 구성만 확인 · 실제 영상 캡처/OBS/송출/실방송/Windows 검증 없음.\n'
                '사용자 최종 승인 및 실기기 검증은 별도 대기.')


def draw_broadcast_scene(canvas, draft: BroadcastSceneDraft, *, expression: str = 'neutral') -> None:
    """Draw only local static placeholders and the existing 2D sample, if selected."""
    if type(draft) is not BroadcastSceneDraft:
        raise ValueError('검증된 화면 구성안이 필요합니다.')
    if type(expression) is not str or expression not in EXPRESSIONS:
        raise ValueError('기존 2D 샘플의 표정만 허용합니다.')

    if draft.avatar == '2d':
        assert draft.layout is not None
        draw_layout_preview(canvas, draft.layout, AvatarFrame(
            draft.persona_name, False, 4, background=draft.layout.background,
            expression=expression))
    else:
        canvas.configure(bg=BACKGROUND_COLORS['남색 스튜디오'])
        canvas.delete('all')

    # Panel is deliberately lowered below the existing avatar sample: no second
    # renderer, capture API, video frames, or external scene source is introduced.
    canvas.create_rectangle(12, 58, 405, 308, fill='#101a31', outline='#8b9bbb',
                            width=2, tags=('aisting_scene_content',))
    if draft.content == 'both':
        canvas.create_rectangle(22, 91, 395, 191, fill='#253a57', outline='#6981a5',
                                tags=('aisting_scene_content',))
        canvas.create_text(208, 141, text='게임 화면 자리표시자 · 캡처 없음',
                           fill='#ffffff', tags=('aisting_scene_content',))
        canvas.create_rectangle(22, 201, 395, 295, fill='#1b2c45', outline='#6981a5',
                                tags=('aisting_scene_content',))
        canvas.create_text(208, 244, text=('모의 채팅 UI (메시지 없음)' if draft.show_chat
                                          else '수다 영역 (채팅 UI 숨김)'),
                           fill='#ffffff', tags=('aisting_scene_content',))
    else:
        canvas.create_text(208, 174, text=(
            '수다 화면 자리표시자 · 채팅 UI 숨김'
            if draft.content == 'chat' and not draft.show_chat
            else CONTENT_LABELS[draft.content]), fill='#ffffff',
            font=('Malgun Gothic', 12), tags=('aisting_scene_content',))
        if draft.content == 'chat' and draft.show_chat:
            for y in (213, 234, 255):
                canvas.create_rectangle(56, y, 345, y + 9, fill='#425978', outline='',
                                        tags=('aisting_scene_content',))
    canvas.tag_lower('aisting_scene_content')

    if draft.avatar != '2d':
        canvas.create_rectangle(416, 91, 627, 290, outline='#8b9bbb',
                                fill='#22334e', tags=('aisting_scene_avatar_placeholder',))
        canvas.create_text(521, 180,
                           text=('3D 선택 · 렌더러 미연결' if draft.avatar == '3d'
                                 else '아바타 미정 · 미연결'),
                           fill='#ffffff', width=195,
                           tags=('aisting_scene_avatar_placeholder',))
    if draft.show_title:
        canvas.create_rectangle(12, 10, 405, 48, fill='#283d60', outline='',
                                tags=('aisting_scene_title',))
        canvas.create_text(208, 29, text=draft.persona_name.strip()[:24] + ' · 화면 구성안',
                           fill='#ffffff', font=('Malgun Gothic', 13, 'bold'),
                           tags=('aisting_scene_title',))
    canvas.create_rectangle(0, 326, PREVIEW_WIDTH, PREVIEW_HEIGHT,
                            fill='#142039', outline='', tags=('aisting_scene_watermark',))
    canvas.create_text(320, 342, text='오프라인 미리보기 · 영상/음성 송출 불가 · OBS 미연결',
                       fill='#ffffff', font=('Malgun Gothic', 10),
                       tags=('aisting_scene_watermark',))
