"""Stage 085: offline Discord message-shape review, NEVER a network connector.

No channel identifiers, credentials, webhook, token, HTTP client, sender, or
scheduled job is accepted or retained here. A preview cannot be published.
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from .offline_prebroadcast_notice import PrebroadcastNoticeDraft

MAX_DISCORD_CONTENT = 2000


@dataclass(frozen=True)
class DiscordNoticeDryRun:
    content: str
    source_time: str
    platform: str = 'discord'
    destination_configured: bool = False
    credentials_configured: bool = False
    transport_enabled: bool = False
    send_ready: bool = False
    published: bool = False

    def to_preview_dict(self) -> dict:
        """Describe the *unroutable* payload without exposing any send method.

        `allowed_mentions` is explicitly empty. This object is not a request
        ready for Discord's REST API (the destination is deliberately absent).
        """
        return {
            'mode': 'offline_review_only',
            'platform': self.platform,
            'destination': None,
            'send_ready': False,
            'message': {
                'content': self.content,
                'tts': False,
                'allowed_mentions': {'parse': [], 'users': [], 'roles': [], 'replied_user': False},
            },
            'connection': 'disabled',
            'published': False,
        }

    def to_preview_json(self) -> str:
        return json.dumps(self.to_preview_dict(), ensure_ascii=False, indent=2)

    def describe(self) -> str:
        return ('085 디스코드 메시지 형식 확인 · 채널/토큰 없음 · 접속/전송/예약 불가 · 미게시')


def prepare_discord_notice_dry_run(draft: PrebroadcastNoticeDraft) -> DiscordNoticeDryRun:
    """Check a previously generated local notice before viewing its format.

    Do not infer Discord server/channel from the streaming platform selection.
    """
    if type(draft) is not PrebroadcastNoticeDraft:
        raise ValueError('084 공지 초안 객체를 먼저 생성해야 합니다.')
    if not draft.review_only or draft.ai_generated or draft.published or draft.scheduled:
        raise ValueError('전송/예약/AI 작성 상태의 공지는 이 오프라인 시험에서 허용하지 않습니다.')
    content = draft.text
    if type(content) is not str or not content or len(content) > MAX_DISCORD_CONTENT:
        raise ValueError('디스코드 메시지 검토 내용은 1~2000자여야 합니다.')
    if any((ord(ch) < 32 and ch != '\n') or ord(ch) == 127 for ch in content):
        raise ValueError('메시지 내용에 제어 문자가 있습니다.')
    # Defence in depth: even a fabricated/altered draft cannot inject a
    # mass mention, target mention or external destination into the preview.
    lower = content.lower()
    if any(part in lower for part in ('@everyone', '@here', '<@', '<#', 'http://', 'https://', 'www.')):
        raise ValueError('멘션과 외부 링크가 포함된 공지는 검토 대상에서 제외됩니다.')
    if type(draft.announcement_time) is not str or not draft.announcement_time.endswith(' KST'):
        raise ValueError('원본 공지의 KST 시작 시각이 확인되지 않습니다.')
    return DiscordNoticeDryRun(content=content, source_time=draft.announcement_time)
