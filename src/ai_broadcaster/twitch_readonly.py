"""Read-only connection to publicly available Twitch IRC chat.

No OAuth, account login, chat send, recording, filtering or background startup.
The operator supplies a channel and explicitly starts/stops this observer.
This is NOT a CHZZK/YouTube connector or evidence of audience delivery.
"""
from __future__ import annotations

import math
import re
import secrets
import threading
from dataclasses import dataclass
from typing import Callable

_CHANNEL = re.compile(r"[a-zA-Z0-9_]{3,25}\Z")
# Match IRC protocol replies at their command field, never in viewer text.
_IRC_PREFIX = r"^(?:@\S+\s+)?(?::\S+\s+)?"
_JOIN_ACK = re.compile(_IRC_PREFIX + r"366\s+\S+\s+#([A-Za-z0-9_]+)(?=\s|$)", re.I)
_AUTH_NOTICE = re.compile(_IRC_PREFIX + r"NOTICE(?:\s|$)", re.I)
_WELCOME = re.compile(_IRC_PREFIX + r"001(?:\s|$)", re.I)


class TwitchReadError(RuntimeError):
    pass


@dataclass(frozen=True)
class TwitchChatLine:
    channel: str
    sender: str
    text: str


def parse_irc_chat_line(line: str, channel: str) -> TwitchChatLine | None:
    """Return every PRIVMSG addressed to this channel, including duplicates."""
    if not isinstance(line, str):
        raise TypeError("IRC line must be text")
    # IRCv3 tags may precede the source nickname.
    if line.startswith("@"):
        _, sep, line = line.partition(" ")
        if not sep:
            return None
    match = re.fullmatch(
        r":([^!\s]+)![^\s]*\s+PRIVMSG\s+#([A-Za-z0-9_]+)\s+:(.*)",
        line.rstrip("\r\n"),
    )
    if match is None or match.group(2).lower() != channel.lower():
        return None
    return TwitchChatLine(channel.lower(), match.group(1), match.group(3))


class TwitchReadOnlySession:
    """One explicit user-directed public channel read, with no chat posting."""

    def __init__(self, channel: str, emit: Callable[[str, object], None], *,
                 oauth_token: str = "", oauth_login: str = ""):
        if type(oauth_token) is not str or type(oauth_login) is not str:
            raise ValueError("트위치 채팅 읽기 승인 정보 형식이 올바르지 않습니다.")
        if oauth_token or oauth_login:
            if (not 12 <= len(oauth_token) <= 400
                    or not all(ch.isalnum() for ch in oauth_token)
                    or not _CHANNEL.fullmatch(oauth_login)):
                raise ValueError("트위치 읽기 전용 OAuth 토큰·계정 이름을 확인하세요.")
        if not isinstance(channel, str) or not _CHANNEL.fullmatch(channel):
            raise ValueError("트위치 채널 이름은 영문·숫자·밑줄 3~25자여야 합니다.")
        if not callable(emit):
            raise TypeError("채팅 수신 콜백이 필요합니다.")
        self.channel = channel.lower()
        self._oauth_token = oauth_token
        self._oauth_login = oauth_login.lower()
        self.emit = emit
        self._stop = threading.Event()
        self._socket = None
        self._mutex = threading.Lock()
        self._running = False

    def stop(self) -> None:
        self._stop.set()
        with self._mutex:
            sock = self._socket
        if sock is not None:
            try:
                sock.close()
            except Exception:
                # Stop remains idempotent if a concurrent thread closed it.
                pass

    def run(self, *, max_seconds: float | None = None) -> None:
        """Prevent two receivers from using the same session simultaneously."""
        with self._mutex:
            if self._running:
                raise TwitchReadError("트위치 채팅 수신이 이미 실행 중입니다.")
            self._running = True
        try:
            self._run_once(max_seconds=max_seconds)
        finally:
            with self._mutex:
                self._running = False

    def _run_once(self, *, max_seconds: float | None = None) -> None:
        """Block on public Twitch IRC, passing ALL chat messages to emit.

        Never automatically reconnects or starts on application startup.
        max_seconds is for bounded disposable Windows CI only.
        """
        if max_seconds is not None and (
            type(max_seconds) not in (int, float)
            or not math.isfinite(max_seconds)
            or not 1 <= max_seconds <= 120
        ):
            raise ValueError("검증 제한 시간이 올바르지 않습니다.")
        if self._stop.is_set():
            self.emit("stopped", 0)
            return
        try:
            import websocket
        except ImportError as exc:
            raise TwitchReadError("읽기 전용 WebSocket 지원 패키지가 없습니다.") from exc
        import time
        # stop() may be requested before the background thread starts. Never
        # erase that request or open an unwanted connection afterwards.
        if self._stop.is_set():
            self.emit("stopped", 0)
            return
        try:
            sock = websocket.create_connection(
                "wss://irc-ws.chat.twitch.tv:443", timeout=8,
                enable_multithread=True, origin="https://www.twitch.tv",
            )
        except Exception:
            if self._stop.is_set():
                self.emit("stopped", 0)
                return
            raise
        with self._mutex:
            self._socket = sock
            stopped = self._stop.is_set()
        if stopped:
            try:
                sock.close()
            except Exception:
                pass
            with self._mutex:
                self._socket = None
            self.emit("stopped", 0)
            return
        nick = (self._oauth_login if self._oauth_token
                else "justinfan" + str(secrets.randbelow(90000000) + 10000000))
        ready = False
        received = 0
        deadline = time.monotonic() + max_seconds if max_seconds else None
        try:
            # For real read-only auth Twitch officially requires IRC PASS
            # oauth:<token> and NICK of the token's owner. Anonymous JOIN
            # stays compatible but can no longer prove chat:read access.
            commands = (
                ("PASS oauth:" + self._oauth_token + "\r\n",
                 "NICK " + nick + "\r\n",
                 "CAP REQ :twitch.tv/tags twitch.tv/commands\r\n",
                 "JOIN #" + self.channel + "\r\n")
                if self._oauth_token else (
                    "CAP REQ :twitch.tv/tags twitch.tv/commands\r\n",
                    "NICK " + nick + "\r\n",
                    "JOIN #" + self.channel + "\r\n"))
            for command in commands:
                if self._stop.is_set():
                    return
                try:
                    sock.send(command)
                except Exception:
                    if self._stop.is_set():
                        return
                    raise
            if self._stop.is_set():
                return
            self.emit("connecting", self.channel)
            buffer = ""
            while not self._stop.is_set():
                if deadline is not None and time.monotonic() >= deadline:
                    break
                try:
                    sock.settimeout(1.0)
                    data = sock.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception:
                    if self._stop.is_set():
                        break
                    raise
                if self._stop.is_set():
                    break
                if not isinstance(data, str):
                    raise TwitchReadError("트위치 채팅 응답 형식 오류")
                if not data:
                    raise TwitchReadError("트위치 서버가 연결을 종료했습니다.")
                buffer += data
                # One split per frame avoids quadratic rescanning under load.
                if "\r\n" in buffer:
                    *complete_lines, buffer = buffer.split("\r\n")
                else:
                    complete_lines = ()
                for line in complete_lines:
                    if self._stop.is_set():
                        break
                    if len(line) > 65536:
                        raise TwitchReadError("트위치 채팅 한 줄 크기 한도 초과")
                    if line.startswith("PING "):
                        try:
                            sock.send("PONG " + line[5:] + "\r\n")
                        except Exception:
                            if self._stop.is_set():
                                break
                            raise
                    elif _AUTH_NOTICE.match(line) and (
                        "Login authentication failed" in line or "Improperly formatted auth" in line
                    ):
                        raise TwitchReadError("트위치 IRC 읽기 인증 오류 · chat:read 권한 확인 필요")
                    elif (ack := _JOIN_ACK.match(line)) is not None:
                        if ack.group(1).lower() == self.channel and not ready:
                            ready = True
                            self.emit("ready", self.channel)
                    elif _WELCOME.match(line) and not ready:
                        self.emit("welcome", self.channel)
                    else:
                        chat = parse_irc_chat_line(line, self.channel)
                        if chat is not None:
                            received += 1
                            self.emit("chat", chat)
                if not self._stop.is_set() and len(buffer) > 65536:
                    raise TwitchReadError("트위치 미완성 채팅 줄 크기 한도 초과")
            if not ready and not self._stop.is_set():
                raise TwitchReadError("트위치 채팅방 JOIN 완료를 확인하지 못했습니다.")
        finally:
            with self._mutex:
                self._socket = None
            try:
                sock.close()
            except Exception:
                pass
            self.emit("stopped", received)
