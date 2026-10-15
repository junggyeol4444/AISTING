"""Original 088: operator-selected, deterministic, review-only notice variations.

No LLM, random timer, posting, credentials, persistent preferences, IO, or network.
The 084 base notice is never mutated; later posting reviews keep their base contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from .offline_broadcast_schedule import parse_reference
from .offline_prebroadcast_notice import (
    PrebroadcastNoticeDraft, _safe_line, make_prebroadcast_notice,
)
from .offline_settings import active_persona, validate_settings

STYLES = ('친근', '차분', '활기')
LENGTHS = ('짧게', '기본', '자세히')
OPENINGS = {
    '친근': ('안녕! 같이 놀러 와줘~', '오늘도 같이 수다 떨어요!', '반가워요, 오늘 방송도 함께해요!'),
    '차분': ('방송 일정을 안내합니다.', '오늘 방송 예정 안내입니다.', '편안한 시간에 함께해 주세요.'),
    '활기': ('오늘도 출발!', '다 같이 신나게 시작해요!', '오늘 방송, 기대해 주세요!'),
}


@dataclass(frozen=True)
class NoticeVariationOptions:
    style: str = '친근'
    length: str = '기본'
    emoji: bool = False
    variant_number: int = 1  # 1–3; operator selects it, no random background work
    context: str = ''
    lead_minutes: int = 0  # 0=disabled; optional suggested pre-notice time, not a scheduler


@dataclass(frozen=True)
class NoticeVariationPreview:
    text: str
    planned_start: str
    suggested_notice_time: str | None
    options: NoticeVariationOptions
    review_only: bool = True
    ai_generated: bool = False
    published: bool = False
    scheduled: bool = False

    def describe(self) -> str:
        return '088 운영자 선택형 규칙 기반 변주 · 실제 AI 생성/게시/예약 없음 · 검토용'


def make_notice_variation(base: PrebroadcastNoticeDraft, settings: dict,
                          options: NoticeVariationOptions) -> NoticeVariationPreview:
    """Only accept a current 084 base whose text still matches the selected settings."""
    if type(options) is not NoticeVariationOptions:
        raise ValueError('운영자 변주 설정 형식이 올바르지 않습니다.')
    if options.style not in STYLES or options.length not in LENGTHS:
        raise ValueError('지원하지 않는 문구 스타일·길이입니다.')
    if type(options.emoji) is not bool:
        raise ValueError('이모지 사용 여부는 참/거짓이어야 합니다.')
    if type(options.variant_number) is not int or not 1 <= options.variant_number <= 3:
        raise ValueError('변주 번호는 1~3 사이에서 직접 선택해야 합니다.')
    if type(options.lead_minutes) is not int or options.lead_minutes not in (0, *range(10, 41)):
        raise ValueError('공지 시간 변주는 사용 안 함 또는 시작 10~40분 전만 가능합니다.')
    context = _safe_line(options.context, title='당일 맥락', limit=100, optional=True)
    checked = validate_settings(settings)
    if type(base) is not PrebroadcastNoticeDraft or not base.review_only or base.ai_generated or base.published or base.scheduled:
        raise ValueError('미게시 084 검토 초안이 필요합니다.')
    when = parse_reference(base.announcement_time.removesuffix(' KST'))
    original = make_prebroadcast_notice(checked, when, base.topic)
    if original != base:
        raise ValueError('084 원본 공지 또는 운영자 설정이 변경됐습니다. 새 초안을 생성하세요.')
    persona = active_persona(checked)
    persona_style = _safe_line(persona['style'], title='캐릭터 말투', limit=200)
    name, platform_text = base.persona_name, ', '.join(base.platforms) if base.platforms else '미선택 (확인 필요)'
    opening = OPENINGS[options.style][options.variant_number - 1]
    if options.emoji:
        opening = '✨ ' + opening
    time_line = f'방송 시작 예정(운영자 입력): {base.announcement_time}'
    if options.length == '짧게':
        lines = [f'[{name}] {opening}', time_line]
        if base.topic:
            lines.append(f'주제: {base.topic}')
        if context:
            lines.append(f'오늘의 맥락: {context}')
        lines.append(f'방송: {base.content} / {platform_text}')
    else:
        lines = [f'[{name}] {opening}', time_line,
                 f'방송 내용: {base.content}', f'방송 플랫폼: {platform_text}']
        if base.topic:
            lines.append(f'오늘의 주제: {base.topic}')
        if context:
            lines.append(f'오늘의 맥락(운영자 입력): {context}')
        if options.length == '자세히':
            lines.append(f'캐릭터 말투 설정(운영자 지정): {persona_style}')
            lines.append('방송 링크는 확정되지 않았습니다. 방송 시각 및 공지는 직접 확인해 주세요.')
    suggested = None
    if options.lead_minutes:
        suggested = (when - timedelta(minutes=options.lead_minutes)).strftime('%Y-%m-%d %H:%M KST')
        lines.append(f'공지 작성 권장 시각(예약 아님): {suggested}')
    lines.append('※ 문구 변주 검토용 / 실제 AI 작성·게시·자동 예약·방송 시작 아님')
    result = '\n'.join(lines)
    if len(result) > 2000:
        raise ValueError('변주 문구가 2,000자를 초과합니다.')
    return NoticeVariationPreview(result, base.announcement_time, suggested, options)
