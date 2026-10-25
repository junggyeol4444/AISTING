"""운영자가 승인한 방송의 네이버 카페 시작/종료 공지: 공식 Open API만 사용.

로그인/권한 취득·토큰 갱신·브라우저 자동화는 수행하지 않는다.
운영자가 별도로 발급받은 카페 글쓰기 권한 OAuth 토큰을 현재 GUI
메모리에서만 받는다. 호출 대상은 네이버 공식 글쓰기 API 단 하나.
실제 게시 전 독립 SQLite 시도 장부에서 슬롯·종류를 원자적으로
청구해야 한다. 응답 분실/오류 때 무단 재게시하지 않는다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlsplit
from urllib.request import (
    Request, build_opener, HTTPSHandler, HTTPRedirectHandler, ProxyHandler,
)

_ID = re.compile(r"[1-9][0-9]{0,15}\Z")
_TOKEN = re.compile(r"[A-Za-z0-9+/_=.-]{20,4096}\Z")
_HOST = "openapi.naver.com"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class CafeNoticeReceipt:
    """실제 서버 성공 응답만 표시하며 시청자 노출은 확인하지 않음."""
    article_id: int
    article_url: str


def _validate_text(value: str, *, label: str, maximum: int) -> str:
    if (type(value) is not str or not 1 <= len(value.strip()) <= maximum
            or any((ord(ch) < 32 and ch not in "\r\n\t")
                   or ord(ch) == 127 for ch in value)):
        raise ValueError(label + "은(는) 비어 있거나 길이/제어 문자가 잘못되었습니다.")
    return value.strip()


class ApprovedNaverCafeNoticeSender:
    """공식 POST /v1/cafe/{clubid}/menu/{menuid}/articles 전용."""

    def __init__(
        self, club_id: str, menu_id: str, access_token: str, *,
        operator_approved: bool = False,
    ) -> None:
        if operator_approved is not True:
            raise PermissionError("네이버 카페 실제 공지 별도 운영자 승인이 필요합니다.")
        if (type(club_id) is not str or _ID.fullmatch(club_id) is None
                or type(menu_id) is not str or _ID.fullmatch(menu_id) is None):
            raise ValueError("네이버 카페 번호와 일반 게시판 번호를 확인하세요.")
        if type(access_token) is not str or _TOKEN.fullmatch(access_token) is None:
            raise ValueError("운영자 본인 카페 글쓰기 권한의 OAuth 토큰을 확인하세요.")
        self.club_id = club_id
        self.menu_id = menu_id
        self._token = access_token
        self._opener = build_opener(
            ProxyHandler({}), HTTPSHandler(), _NoRedirect())

    def post(
        self, subject: str, content: str, *,
        operator_approved: bool = False,
    ) -> CafeNoticeReceipt:
        """외부 글쓰기 단 한 번. 실패/타임아웃 때 자동 재시도 없음."""
        if operator_approved is not True:
            raise PermissionError("이 공지의 실제 발송 승인 없이 게시하지 않습니다.")
        subject = _validate_text(subject, label="카페 공지 제목", maximum=150)
        content = _validate_text(content, label="카페 공지 본문", maximum=4000)
        # 네이버 공식 Java 글쓰기 샘플: UTF-8 URL 인코딩 후
        # MS949 URL 재인코딩. 첫 결과는 ASCII 퍼센트 문자열이므로
        # 두 번째 인코딩은 quote_plus로 동등하게 표현된다.
        data = ("subject=" + quote_plus(quote_plus(subject, encoding="utf-8"),
                                      encoding="ms949")
                + "&content=" + quote_plus(quote_plus(content, encoding="utf-8"),
                                           encoding="ms949")).encode("ascii")
        url = (
            f"https://{_HOST}/v1/cafe/{self.club_id}/menu/"
            f"{self.menu_id}/articles")
        req = Request(
            url, data=data, method="POST",
            headers={
                "Authorization": "Bearer " + self._token,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        try:
            with self._opener.open(req, timeout=12) as response:
                if response.status != 200:
                    raise RuntimeError("네이버 카페 글쓰기 서버 성공 미확인")
                raw = response.read(16385)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            # 토큰, 오류 응답 본문, HTTP 헤더, URL을 로그/GUI로 유출 금지.
            raise RuntimeError("네이버 카페 글쓰기 전송 결과 불명") from None
        if len(raw) > 16384:
            raise RuntimeError("네이버 카페 응답 크기 초과 · 게시 결과 불명")
        try:
            doc = json.loads(raw.decode("utf-8"))
            message = doc["message"]
            result = message["result"]
            if (str(message["status"]) != "200"
                    or type(result["articleId"]) is not int
                    or result["articleId"] <= 0):
                raise ValueError("서버 성공 응답 형식 오류")
            article_url = result.get("articleUrl", "")
            if type(article_url) is not str:
                raise ValueError("게시글 주소 형식 오류")
            if article_url:
                parsed = urlsplit(article_url)
                if (parsed.scheme != "https"
                        or parsed.hostname != "cafe.naver.com"
                        or parsed.username is not None
                        or parsed.password is not None
                        or parsed.port not in (None, 443)):
                    raise ValueError("게시글 주소가 공식 카페 도메인이 아닙니다.")
            return CafeNoticeReceipt(
                article_id=result["articleId"], article_url=article_url)
        except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError):
            raise RuntimeError("네이버 카페 응답을 확인하지 못했습니다 · 자동 재게시 금지") from None
