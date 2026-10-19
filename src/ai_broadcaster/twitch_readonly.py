"""Read-only connection to publicly available Twitch IRC chat.

No OAuth, account login, chat send, recording, filtering or background startup.
The operator supplies a channel and explicitly starts/stops this observer.
This is NOT a CHZZK/YouTube connector or evidence of audience delivery.
"""
from __future__ import annotations

import re
import secrets
import threading
from dataclasses import dataclass
from typing import Callable

_CHANNEL = re.compile(r"[a-zA-Z0-9_]{3,25}\Z")


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

    def __init__(self, channel: str, emit: Callable[[str, object], None]):
        if not isinstance(channel, str) or not _CHANNEL.fullmatch(channel):
            raise ValueError("트위치 채널 이름은 영문·숫자·밑줄 3~25자여야 합니다.")
        if not callable(emit):
            raise TypeError("채팅 수신 콜백이 필요합니다.")
        self.channel = channel.lower()
        self.emit = emit
        self._stop = threading.Event()
        self._socket = None
        self._mutex = threading.Lock()

    def stop(self) -> None:
        self._stop.set()
        with self._mutex:
            sock = self._socket
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def run(self, *, max_seconds: float | None = None) -> None:
        """Block on public Twitch IRC, passing ALL chat messages to emit.

        Never automatically reconnects or starts on application startup.
        max_seconds is for bounded disposable Windows CI only.
        """
        try:
            import websocket
        except ImportError as exc:
            raise TwitchReadError("읽기 전용 WebSocket 지원 패키지가 없습니다.") from exc
        import time
        if max_seconds is not None and not 1 <= max_seconds <= 120:
            raise ValueError("검증 제한 시간이 올바르지 않습니다.")
        # stop() may be requested before the background thread starts. Never
        # erase that request or open an unwanted connection afterwards.
        if self._stop.is_set():
            self.emit("stopped", 0)
            return
        sock = websocket.create_connection(
            "wss://irc-ws.chat.twitch.tv:443", timeout=8,
            enable_multithread=True, origin="https://www.twitch.tv",
        )
        with self._mutex:
            self._socket = sock
            stopped = self._stop.is_set()
        if stopped:
            sock.close()
            with self._mutex:
                self._socket = None
            self.emit("stopped", 0)
            return
        nick = "justinfan" + str(secrets.randbelow(90000000) + 10000000)
        ready = False
        received = 0
        deadline = time.monotonic() + max_seconds if max_seconds else None
        try:
            sock.send("CAP REQ :twitch.tv/tags twitch.tv/commands\r\n")
            sock.send("NICK " + nick + "\r\n")
            sock.send("JOIN #" + self.channel + "\r\n")
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
                if len(buffer) > 65536:
                    raise TwitchReadError("트위치 채팅 버퍼 한도 초과")
                while "\r\n" in buffer:
                    line, buffer = buffer.split("\r\n", 1)
                    if line.startswith("PING "):
                        sock.send("PONG " + line[5:] + "\r\n")
                    elif " NOTICE " in line and ("Login authentication failed" in line or "Improperly formatted auth" in line):
                        raise TwitchReadError("트위치 익명 읽기 연결 거부")
                    elif " 366 " in line and "#" + self.channel in line.lower():
                        ready = True
                        self.emit("ready", self.channel)
                    elif " 001 " in line and not ready:
                        # Connection welcome alone is NOT proof of JOIN.
                        self.emit("welcome", self.channel)
                    else:
                        chat = parse_irc_chat_line(line, self.channel)
                        if chat is not None:
                            received += 1
                            self.emit("chat", chat)
            if not ready and not self._stop.is_set():
                raise TwitchReadError("트위치 채팅방 JOIN 완료를 확인하지 못했습니다.")
        finally:
            with self._mutex:
                self._socket = None
            sock.close()
            self.emit("stopped", received)
