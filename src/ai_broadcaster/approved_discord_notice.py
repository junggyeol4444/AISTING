"""운영자 명시 승인 후에만 사용하는 실제 Discord 시작·종료 공지 전송.

기존 오프라인 공지 모의 파일을 교체하지 않는다. 새 서버나 브라우저를
띄우지 않고 Windows EXE 프로세스의 HTTPS 클라이언트만 사용한다.
Webhook URL/응답 본문/계정·채팅 비밀정보를 파일이나 로그로 남기지 않는다.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlsplit
from urllib.request import (
    HTTPHandler, HTTPSHandler, HTTPRedirectHandler,
    ProxyHandler, Request, build_opener)
from urllib.error import HTTPError, URLError


class _DenyRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_ALLOWED_HOSTS = frozenset(("discord.com", "discordapp.com"))
_WEBHOOK_PATH = re.compile(r"/api/webhooks/[0-9]{10,30}/[A-Za-z0-9_-]{20,200}\Z")


class ApprovedDiscordNoticeSender:
    """운영자가 넣은 1개 공식 Discord 웹훅으로만 지정 문구 전송."""

    def __init__(self, webhook: str, *, operator_approved: bool = False):
        if operator_approved is not True:
            raise PermissionError("실제 디스코드 외부 공지 전송 승인이 필요합니다.")
        if type(webhook) is not str or len(webhook) > 360:
            raise ValueError("디스코드 웹훅 주소 형식 오류")
        parsed = urlsplit(webhook)
        if (parsed.scheme != "https" or parsed.hostname not in _ALLOWED_HOSTS
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443)
                or parsed.query or parsed.fragment
                or _WEBHOOK_PATH.fullmatch(parsed.path) is None):
            raise ValueError("공식 Discord HTTPS 웹훅 주소만 사용 가능합니다.")
        self._webhook = webhook
        self._opener = build_opener(ProxyHandler({}), HTTPSHandler(), HTTPHandler(), _DenyRedirect())

    def send(self, text: str, *, operator_approved: bool = False) -> bool:
        """실제 HTTP 204 응답만 게시 완료로 인정, 재시도·중복 발신 없음."""
        if operator_approved is not True:
            raise PermissionError("실제 공지 게시를 운영자가 승인해야 합니다.")
        if (type(text) is not str or not 1 <= len(text.strip()) <= 2000
                or any(ord(ch) < 32 and ch not in "\n\t" for ch in text)
                or "@everyone" in text.lower() or "@here" in text.lower()):
            raise ValueError("공지 글자수·대량 멘션 제한을 확인하세요.")
        data = json.dumps({
            "content": text.strip(),
            "allowed_mentions": {"parse": []}
        }, ensure_ascii=False).encode("utf-8")
        if len(data) > 16_000:
            raise ValueError("공지 전송 데이터가 너무 큽니다.")
        request = Request(self._webhook, data=data, method="POST",
                          headers={"Content-Type": "application/json",
                                   "Accept": "application/json"})
        try:
            with self._opener.open(request, timeout=7.0) as response:
                status = response.status
        except (HTTPError, URLError, TimeoutError, OSError):
            # Server exceptions can include webhook URL. Never include them.
            raise RuntimeError("실제 Discord 공지 전송 실패 · 중복 전송하지 않음") from None
        if status != 204:
            raise RuntimeError("디스코드 공지 완료 상태 미확인 · 중복 전송하지 않음")
        return True
