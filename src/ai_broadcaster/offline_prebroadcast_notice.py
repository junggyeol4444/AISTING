"""Original step 084: deterministic, review-only pre-broadcast notice drafts.

No LLM, posting, links, clipboard, scheduler, credentials, file or network I/O.
An operator explicitly supplies the announced time and optional topic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .offline_broadcast_schedule import KST
from .offline_settings import CONTENTS, PLATFORMS, active_persona, validate_settings

CONTENT_LABELS = {code: label for label, code in CONTENTS.items()}
PLATFORM_LABELS = {code: label for label, code in PLATFORMS.items()}


def _safe_line(value: str, *, title: str, limit: int, optional: bool = False) -> str:
    if type(value) is not str:
        raise ValueError(f'{title}은(는) 문자열이어야 합니다.')
    text = value.strip()
    if not optional and not text:
        raise ValueError(f'{title}을(를) 입력해야 합니다.')
    if len(text) > limit or any(ord(ch) < 32 or ord(ch) == 127 for ch in text):
        raise ValueError(f'{title}은(는) {limit}자 이내의 한 줄이어야 합니다.')
    # A local preview must never silently become a mass-mention or a URL.
    if any(word in text.lower() for word in ('@everyone', '@here', 'http://', 'https://', 'www.')):
        raise ValueError('대량 멘션 및 링크는 수동 검토 이후 직접 작성해야 합니다.')
    return text


@dataclass(frozen=True)
class PrebroadcastNoticeDraft:
    text: str
    announcement_time: str
    platforms: tuple[str, ...]
    content: str
    persona_name: str
    topic: str
    review_only: bool = True
    ai_generated: bool = False
    published: bool = False
    scheduled: bool = False

    def describe(self) -> str:
        return ('084 사전 공지 검토 초안 · 규칙 기반 생성(실제 AI 생성 아님) · '
                '미게시 · 외부 송신/자동 예약 없음 · 실제 방송 시작 미확인')


def make_prebroadcast_notice(settings: dict, when: datetime, topic: str = '') -> PrebroadcastNoticeDraft:
    """Create a local TEXT draft; the stated time is operator supplied, not checked against a live clock."""
    selected = validate_settings(settings)
    if type(when) is not datetime or when.tzinfo is None or when.utcoffset() != timedelta(hours=9):
        raise ValueError('공지 예정 시각은 운영자가 입력한 KST 기준이어야 합니다.')
    # Avoid subtle wrong timezone conversion by explicitly using the approved KST offset.
    local = when.astimezone(KST)
    topic = _safe_line(topic, title='방송 주제', limit=100, optional=True)
    persona = active_persona(selected)
    name = _safe_line(persona['name'], title='캐릭터 이름', limit=200)
    labels = tuple(PLATFORM_LABELS[p] for p in selected['platforms'])
    content = CONTENT_LABELS[selected['content']]
    time_text = local.strftime('%Y-%m-%d %H:%M KST')
    lines = [f'[{name}] 방송 시작 예정 안내',
             f'예정 시각(운영자 입력): {time_text}',
             f'방송 내용: {content}']
    if topic:
        lines.append(f'오늘의 주제: {topic}')
    lines.append('방송 플랫폼: ' + (', '.join(labels) if labels else '미선택 (게시 전 확인 필요)'))
    lines.append('방송 링크: 미설정 (실제 링크를 임의로 만들지 않음)')
    lines.append('※ 검토용 초안 / 실제 방송 시작·공지 게시 아님')
    return PrebroadcastNoticeDraft('\n'.join(lines), time_text, labels, content, name, topic)
