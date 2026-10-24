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
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

_CHANNEL = re.compile(r"[a-zA-Z0-9_]{3,25}\Z")
# Match IRC protocol replies at their command field, never in viewer text.
_IRC_PREFIX = r"^(?:@\S+\s+)?(?::\S+\s+)?"
_JOIN_ACK = re.compile(_IRC_PREFIX + r"366\s+\S+\s+#([A-Za-z0-9_]+)(?=\s|$)", re.I)
_AUTH_NOTICE = re.compile(_IRC_PREFIX + r"NOTICE(?:\s|$)", re.I)
_WELCOME = re.compile(_IRC_PREFIX + r"001(?:\s|$)", re.I)
_SERVER_RECONNECT = re.compile(_IRC_PREFIX + r"RECONNECT(?:\s|$)", re.I)
# 대상 채팅방의 실제 PRIVMSG 명령만 확인한다. 파서가 실패한
# 손상 채팅을 정상 제어 명령처럼 조용히 버리지 않기 위한 구분이다.
_TARGET_PRIVMSG = re.compile(
    _IRC_PREFIX + r"PRIVMSG\s+#([A-Za-z0-9_]+)(?=\s|$)", re.I)



class TwitchReadError(RuntimeError):
    pass


class TwitchServerReconnect(TwitchReadError):
    """트위치 서버가 명시적으로 요청한 재연결(일반 통신 장애와 구분)."""
    pass


@dataclass(frozen=True)
class TwitchChatLine:
    channel: str
    sender: str
    text: str
    event_id: str | None = field(default=None, compare=False, repr=False)


def parse_irc_chat_line(line: str, channel: str) -> TwitchChatLine | None:
    """Return every PRIVMSG addressed to this channel, including duplicates."""
    if not isinstance(line, str):
        raise TypeError("IRC line must be text")
    # IRCv3 tags may precede the source nickname. Only the real id tag
    # can identify a retransmitted server event; do not dedupe chat text.
    event_id = None
    if line.startswith("@"):
        tags, sep, line = line.partition(" ")
        if not sep:
            return None
        for tag in tags[1:].split(";"):
            if tag.startswith("id="):
                candidate = tag[3:]
                if re.fullmatch(r"[A-Za-z0-9_-]{1,256}", candidate):
                    event_id = candidate
                break
    match = re.fullmatch(
        r":([^!\s]+)![^\s]*\s+PRIVMSG\s+#([A-Za-z0-9_]+)\s+:(.*)",
        line.rstrip("\r\n"),
    )
    if match is None or match.group(2).lower() != channel.lower():
        return None
    return TwitchChatLine(channel.lower(), match.group(1), match.group(3), event_id)


class TwitchReadOnlySession:
    """One explicit user-directed public channel read, with no chat posting."""

    def __init__(self, channel: str, emit: Callable[[str, object], None], *,
                 oauth_token: str = "", oauth_login: str = ""):
        if type(oauth_token) is not str or type(oauth_login) is not str:
            raise ValueError("트위치 채팅 읽기 승인 정보 형식이 올바르지 않습니다.")
        if oauth_token or oauth_login:
            if (not 12 <= len(oauth_token) <= 400
                    or not oauth_token.isascii()
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
        # 같은 수신 세션에서 이미 파싱한 IRC 채팅은 AI FIFO 수용까지
        # 유지한다. 상위 조정기가 재연결 수신기와 이 deque를 공유한다.
        self._pending_chats = deque()

    def _flush_pending_chats(self) -> int:
        """JOIN 승인 뒤 이미 파싱한 채팅만 순서대로 전달한다.

        콜백 False/예외 시 선두와 뒤쪽 사건을 보존한다. Stop 이후
        재전달하지 않으며, 수신 프레임 이전 서버 사건은 복원하지 못한다.
        """
        accepted = 0
        while self._pending_chats and not self._stop.is_set():
            if self.emit("chat", self._pending_chats[0]) is False:
                raise TwitchReadError("트위치 채팅이 AI 수신 큐에 수용되지 않았습니다.")
            self._pending_chats.popleft()
            accepted += 1
        return accepted

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
            # IRC JOIN 승인 전 채팅과 재연결 뒤 미수용 채팅 모두
            # self._pending_chats에서 처리한다. 임의 폐기하지 않는다.
            # IRC의 PING/서버 알림도 실제 통신 활동이다. 무채팅을
            # 장애로 오판하지 않으며 15분간 무프레임이면 재접속한다.
            last_received_at = time.monotonic()
            while not self._stop.is_set():
                if deadline is not None and time.monotonic() >= deadline:
                    break
                try:
                    sock.settimeout(1.0)
                    data = sock.recv()
                except websocket.WebSocketTimeoutException:
                    if (deadline is None and not self._stop.is_set()
                            and time.monotonic() - last_received_at >= 900):
                        self.emit("transport_stalled", None)
                        raise TwitchReadError("트위치 소켓 서버 응답이 15분간 없어 재연결합니다.")
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
                last_received_at = time.monotonic()
                self.emit("transport_activity", None)
                buffer += data
                # One split per frame avoids quadratic rescanning under load.
                if "\r\n" in buffer:
                    *complete_lines, buffer = buffer.split("\r\n")
                else:
                    complete_lines = ()
                # 같은 프레임의 중간 콜백이 실패해도 뒤쪽 채팅이
                # 소실되지 않도록, 전달 시도 전에 프레임 전체를 파싱한다.
                # 중복 서버 ID는 상위 조정기에서 수용 완료 건만 차단한다.
                # 손상된 PRIVMSG가 프레임 중간에 있더라도 뒤쪽의
                # 정상 채팅까지 먼저 추출·보관한 뒤 오류로 재연결한다.
                # 파서가 인식하지 못한 대상 채팅은 정상 제어 명령으로
                # 오인해 무음 폐기하지 않는다. 서버가 미전송한 사건이나
                # 손상 본문 자체는 복구할 수 없음을 별도 구분한다.
                parsed_chats = []
                malformed_target_chat = False
                oversized_line = False
                for line in complete_lines:
                    if self._stop.is_set():
                        break
                    if len(line) > 65536:
                        oversized_line = True
                        continue
                    parsed = parse_irc_chat_line(line, self.channel)
                    if parsed is not None:
                        parsed_chats.append(parsed)
                    else:
                        command = _TARGET_PRIVMSG.match(line)
                        if (command is not None
                                and command.group(1).lower() == self.channel):
                            malformed_target_chat = True
                if self._stop.is_set():
                    break
                self._pending_chats.extend(parsed_chats)
                if oversized_line:
                    raise TwitchReadError(
                        "트위치 채팅 한 줄 크기 한도 초과 · 정상 채팅은 보류")
                if malformed_target_chat:
                    raise TwitchReadError(
                        "트위치 대상 채팅 PRIVMSG 형식 손상 · 정상 채팅은 보류")
                if not ready and len(self._pending_chats) > 4096:
                    raise TwitchReadError(
                        "트위치 JOIN 확인 전 임시 채팅 한도 초과 · 누락 위험")
                server_requested_reconnect = False
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
                    elif _SERVER_RECONNECT.match(line):
                        # 동일 프레임 뒤쪽의 채팅도 먼저 수용한 뒤 상위 재연결기로 알린다.
                        server_requested_reconnect = True
                    elif _AUTH_NOTICE.match(line) and (
                        "Login authentication failed" in line or "Improperly formatted auth" in line
                    ):
                        raise TwitchReadError("트위치 IRC 읽기 인증 오류 · chat:read 권한 확인 필요")
                    elif (ack := _JOIN_ACK.match(line)) is not None:
                        if ack.group(1).lower() == self.channel and not ready:
                            ready = True
                            self.emit("ready", self.channel)
                            received += self._flush_pending_chats()
                    elif _WELCOME.match(line) and not ready:
                        self.emit("welcome", self.channel)
                # JOIN 확인 뒤에는 현재 프레임의 모든 채팅을 먼저
                # 보존한 상태에서, 미수용 선두부터 다시 전달한다.
                if ready and not self._stop.is_set():
                    received += self._flush_pending_chats()
                if server_requested_reconnect and not self._stop.is_set():
                    raise TwitchServerReconnect("트위치 서버 RECONNECT 요청 · 재연결 필요")
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
