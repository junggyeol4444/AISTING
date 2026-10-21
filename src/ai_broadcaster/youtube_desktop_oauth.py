"""Opt-in YouTube OWNER read-only OAuth in the existing native Windows EXE.

Uses the OS's real browser for Google's mandatory consent. No embedded web UI,
Chrome profile scraping, password access, Drive access, refresh-token storage,
automatic sign-in, streaming or chat posting. Tokens live in Tk RAM only.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen


YOUTUBE_READ_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


def _client_id(value: str) -> str:
    if (type(value) is not str or len(value) > 300 or not re.fullmatch(
            r"[0-9]+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com", value)):
        raise ValueError("Google 데스크톱 OAuth 클라이언트 ID 형식 오류")
    return value


def _client_secret(value: str) -> str:
    if (type(value) is not str or len(value) > 1024
            or any(ord(ch) < 33 or ord(ch) > 126 for ch in value)):
        raise ValueError("Google 데스크톱 OAuth 클라이언트 secret 형식 오류")
    return value


def new_pkce() -> tuple[str, str, str]:
    verifier = secrets.token_urlsafe(48)
    state = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    return state, verifier, challenge


def authorization_url(client_id: str, redirect_uri: str, state: str,
                      challenge: str) -> str:
    _client_id(client_id)
    if not re.fullmatch(r"http://127\.0\.0\.1:[0-9]{2,5}/oauth2callback", redirect_uri):
        raise ValueError("로컬 전용 OAuth 콜백 주소 오류")
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{30,160}", x)
           for x in (state, challenge)):
        raise ValueError("OAuth 상태 또는 PKCE 검증값 오류")
    return AUTH_ENDPOINT + "?" + urlencode({
        "client_id": client_id, "response_type": "code",
        "redirect_uri": redirect_uri, "scope": YOUTUBE_READ_SCOPE,
        "state": state, "code_challenge": challenge,
        "code_challenge_method": "S256", "access_type": "online",
    })


def verify_callback(target: str, expected_state: str) -> str:
    """Return an authorization CODE only, never a token from callback."""
    parts = urlsplit(target)
    if parts.path != "/oauth2callback" or parts.netloc or parts.fragment:
        raise ValueError("OAuth 콜백 경로 오류")
    query = parse_qs(parts.query, keep_blank_values=True)
    supplied = query.get("state", [])
    if len(supplied) != 1 or not hmac.compare_digest(
            supplied[0], expected_state):
        raise ValueError("OAuth CSRF 상태 불일치")
    if "error" in query:
        raise PermissionError("사용자가 YouTube 읽기 승인을 거부했거나 취소했습니다.")
    codes = query.get("code", [])
    if len(codes) != 1 or not 8 <= len(codes[0]) <= 2048:
        raise ValueError("OAuth 승인 코드 형식 오류")
    if any(ord(ch) <= 32 or ord(ch) > 126 for ch in codes[0]):
        raise ValueError("OAuth 승인 코드 형식 오류")
    return codes[0]


def exchange_code(client_id: str, client_secret: str, redirect_uri: str,
                  verifier: str, authorization_code: str,
                  *, timeout: float = 10.0) -> str:
    """One real Google token exchange only after matching state+PKCE."""
    _client_id(client_id)
    _client_secret(client_secret)
    if not re.fullmatch(r"http://127\.0\.0\.1:[0-9]{2,5}/oauth2callback", redirect_uri):
        raise ValueError("로컬 전용 OAuth 콜백 주소 오류")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", verifier):
        raise ValueError("OAuth PKCE verifier 오류")
    if not 8 <= len(authorization_code) <= 2048:
        raise ValueError("OAuth 승인 코드 오류")
    data = {"client_id": client_id, "code": authorization_code,
            "redirect_uri": redirect_uri, "code_verifier": verifier,
            "grant_type": "authorization_code"}
    if client_secret:
        data["client_secret"] = client_secret
    request = Request(TOKEN_ENDPOINT, data=urlencode(data).encode("ascii"),
                      headers={"Content-Type":"application/x-www-form-urlencoded"},
                      method="POST")
    # Never include a Google response body, private URL or credential in errors.
    try:
        with urlopen(request, timeout=timeout) as response:
            document = json.loads(response.read(32768))
    except Exception:
        raise RuntimeError("YouTube OAuth 승인 코드 교환 실패") from None
    if not isinstance(document, dict):
        raise RuntimeError("YouTube OAuth 토큰 응답 형식 오류")
    token = document.get("access_token")
    if (document.get("token_type", "").lower() != "bearer"
            or type(token) is not str or not 30 <= len(token) <= 4096
            or any(ord(ch) <= 32 or ord(ch) > 126 for ch in token)):
        raise RuntimeError("YouTube OAuth access token 형식 오류")
    scopes = document.get("scope")
    if scopes is not None and (type(scopes) is not str
                              or YOUTUBE_READ_SCOPE not in scopes.split()):
        raise RuntimeError("YouTube 소유 방송 읽기 권한이 부족합니다.")
    return token


def authorize_owner_readonly(client_id: str, client_secret: str = "", *,
                             operator_approved: bool = False,
                             timeout: float = 150.0,
                             browser_opener=None) -> str:
    """Explicit one-shot loopback PKCE consent; no token is stored to disk."""
    if operator_approved is not True:
        raise PermissionError("운영자 승인 없이 YouTube 계정 인증 불가")
    _client_id(client_id)
    _client_secret(client_secret)
    if type(timeout) not in (int, float) or not 10 <= timeout <= 300:
        raise ValueError("YouTube OAuth 인증 제한 시간 오류")
    state, verifier, challenge = new_pkce()
    received: list[str] = []
    failure: list[str] = []

    class CallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            # Do not log authorization codes or query strings to stderr.
            return

        def do_GET(self):
            try:
                code = verify_callback(self.path, state)
            except Exception as exc:
                failure.append(type(exc).__name__)
                code = None
            if code is not None:
                received.append(code)
            self.send_response(200 if code is not None else 400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(
                ("AISTING: Return to your desktop app."
                 if code is not None else "AISTING: Authorization was rejected."
                ).encode("utf-8"))

    with HTTPServer(("127.0.0.1", 0), CallbackHandler) as server:
        server.timeout = 0.5
        redirect = "http://127.0.0.1:" + str(server.server_port) + "/oauth2callback"
        url = authorization_url(client_id, redirect, state, challenge)
        opener = webbrowser.open if browser_opener is None else browser_opener
        try:
            opened = opener(url)
        except Exception:
            raise RuntimeError("Google 동의 브라우저 실행 오류") from None
        if opened is not True:
            raise RuntimeError("Google 동의 브라우저를 열지 못했습니다.")
        deadline = time.monotonic() + timeout
        while not received and time.monotonic() < deadline:
            server.handle_request()
            if len(failure) > 32:
                raise RuntimeError("OAuth 콜백 오류 횟수가 너무 많습니다.")
        if not received:
            raise TimeoutError("YouTube OAuth 동의 시간이 만료되었습니다.")
    return exchange_code(client_id, client_secret, redirect, verifier, received[0])
