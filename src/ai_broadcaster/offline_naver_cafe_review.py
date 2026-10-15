"""Stage 087 — offline Naver Cafe publication feasibility review, NOT API integration.

Deliberately no HTTP, OAuth, browser automation, token, cafe identifier,
login or upload implementation. An operator must verify current official API
capabilities/terms and permissions separately before an actual integration.
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from .offline_prebroadcast_notice import PrebroadcastNoticeDraft

MAX_LOCAL_TITLE = 100
MAX_LOCAL_BODY = 5000  # LOCAL preview safety bound, not an API limit.
BLOCKED_FRAGMENTS = ('@everyone', '@here', 'http://', 'https://', 'www.', '<@', '<#')


def _checked(value: object, label: str, limit: int, *, multiline: bool) -> str:
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise ValueError(f'{label}은(는) 로컬 검토 제한 {limit}자 이내의 비어 있지 않은 문자열이어야 합니다.')
    if any((ord(ch) < 32 and (not multiline or ch != '\n')) or ord(ch) == 127 for ch in value):
        raise ValueError(f'{label}에 제어 문자가 포함되어 있습니다.')
    lowered = value.lower()
    if any(fragment in lowered for fragment in BLOCKED_FRAGMENTS):
        raise ValueError('멘션·링크를 포함한 공지는 자동 처리 대상이 아닙니다.')
    return value


@dataclass(frozen=True)
class CafeOfficialApiReview:
    title: str
    body: str
    source_time: str

    def to_report_dict(self) -> dict:
        """Local *review report*, not a compatible API request/payload."""
        return {
            'mode': 'offline_feasibility_review_only',
            'provider': 'naver_cafe',
            'title_preview': self.title,
            'body_preview': self.body,
            'source_time': self.source_time,
            'official_api_capability': 'unverified',
            'current_terms_and_scope': 'unverified',
            'cafe_write_permission': 'unverified',
            'cafe_target': None,
            'credentials': None,
            'network_enabled': False,
            'browser_automation_enabled': False,
            'api_payload_ready': False,
            'published': False,
            'operator_approval': 'pending',
            'operator_checklist': [
                '운영자가 네이버 개발자 공식 문서의 현재 지원 범위·약관을 직접 확인',
                '본인 카페 글쓰기 권한과 공식 인증 절차 확인 (현재 입력·연결 금지)',
                '운영자가 제목/본문/공개 범위/개인정보 및 저작권 검토',
                '명시적 승인 후 별도 Windows 환경에서 실제 글쓰기 및 오류·중복 검사',
            ],
        }

    def to_report_json(self) -> str:
        return json.dumps(self.to_report_dict(), ensure_ascii=False, indent=2)

    def describe(self) -> str:
        return '087 네이버 카페 공식 연동 사전 검토 · API 지원/권한 미확인 · 인증/전송/게시 없음'


def review_naver_cafe_official_link(draft: PrebroadcastNoticeDraft) -> CafeOfficialApiReview:
    """Validate only a previous local draft; never infer café/account from streams."""
    if type(draft) is not PrebroadcastNoticeDraft:
        raise ValueError('084 방송 전 공지 초안을 먼저 만들어야 합니다.')
    if not draft.review_only or draft.ai_generated or draft.published or draft.scheduled:
        raise ValueError('이미 게시/예약되거나 승인 없는 AI 작성 초안은 검토하지 않습니다.')
    if type(draft.announcement_time) is not str or not draft.announcement_time.endswith(' KST'):
        raise ValueError('공지의 KST 예정 시각을 확인할 수 없습니다.')
    _checked(draft.persona_name, '캐릭터 이름', 200, multiline=False)
    title = _checked(f'[{draft.persona_name}] 방송 시작 예정 안내', '제목', MAX_LOCAL_TITLE, multiline=False)
    body = _checked(draft.text, '본문', MAX_LOCAL_BODY, multiline=True)
    if draft.announcement_time not in body:
        raise ValueError('공지 본문의 방송 예정 시각이 원본과 일치하지 않습니다.')
    return CafeOfficialApiReview(title, body, draft.announcement_time)
