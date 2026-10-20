"""Read-only multi-platform live-chat coordinator for the existing AISTING GUI.

No platform login, posting, streaming, automatic startup or text filtering.
Every accepted viewer event enters the existing one-worker AI FIFO.
"""
from __future__ import annotations

import math
import threading
import time

from .multiplatform_readonly import (
    PlatformChat, ChzzkReadOnlySession, SoopReadOnlySession,
    YouTubeReadOnlySession,
)
from .twitch_readonly import TwitchChatLine, TwitchReadOnlySession

SUPPORTED = ("twitch", "chzzk", "soop", "youtube")


class MultiPlatformReadOnlySession:
    """Run selected read-only transports concurrently, preserving each FIFO."""

    def __init__(self, channels: dict[str, str], emit, *, youtube_api_key: str = ""):
        if (type(channels) is not dict or not channels or len(channels) > 4
                or not callable(emit)):
            raise ValueError("동시 채팅 플랫폼과 채널을 확인하세요.")
        if any(code not in SUPPORTED or not isinstance(value, str)
               or not value.strip() for code, value in channels.items()):
            raise ValueError("지원하지 않는 플랫폼 또는 비어 있는 채널입니다.")
        self.channel = "전체"
        self._stop = threading.Event()
        self._run_lock = threading.Lock()
        self._emit_lock = threading.Lock()
        self._started_once = False
        self._running = False
        self._emit = emit
        self._readers = {}

        def callback_for(code):
            def callback(kind, item):
                with self._emit_lock:
                    if self._stop.is_set():
                        return
                    if kind == "chat":
                        if code == "twitch" and isinstance(item, TwitchChatLine):
                            item = PlatformChat(item.channel, item.sender, item.text, code)
                        if not isinstance(item, PlatformChat) or item.platform != code:
                            raise ValueError("채팅 플랫폼 식별자가 올바르지 않습니다.")
                        self._emit("chat", item)
                    elif kind in ("ready", "connected"):
                        # Never expose reader-provided URLs, tokens or secrets.
                        self._emit(kind, code + " 공개 채팅 연결")
                    elif kind == "error":
                        self._emit("error", code + " 공개 채팅 연결 오류")
            return callback

        factories = {
            "twitch": lambda channel, cb: TwitchReadOnlySession(channel, cb),
            "chzzk": lambda channel, cb: ChzzkReadOnlySession(channel, cb),
            "soop": lambda channel, cb: SoopReadOnlySession(channel, cb),
            "youtube": lambda channel, cb: YouTubeReadOnlySession(
                channel, cb, youtube_api_key),
        }
        # Construct and validate every reader before starting any network I/O.
        for code, channel in channels.items():
            self._readers[code] = factories[code](channel.strip(), callback_for(code))

    def stop(self) -> None:
        with self._run_lock:
            self._stop.set()
        for reader in self._readers.values():
            try:
                reader.stop()
            except Exception:
                # One broken reader cannot prevent the other readers stopping.
                pass

    def run(self, *, max_seconds=None) -> None:
        if max_seconds is not None and (
                type(max_seconds) not in (int, float)
                or not math.isfinite(max_seconds) or max_seconds < 0):
            raise ValueError("동시 채팅 검사 제한 시간이 올바르지 않습니다.")
        if max_seconds == 0:
            return
        with self._run_lock:
            if self._running or self._started_once:
                raise RuntimeError("동시 채팅 수신이 이미 실행 중이거나 종료됐습니다.")
            if self._stop.is_set():
                return
            self._running = True
            self._started_once = True
        try:
            def read_one(code, reader):
                try:
                    reader.run(max_seconds=max_seconds)
                except Exception as exc:
                    if not self._stop.is_set():
                        with self._emit_lock:
                            if not self._stop.is_set():
                                # No exception messages: they may contain credentials.
                                self._emit("error", code + " 읽기 실패 (" +
                                           type(exc).__name__ + ")")

            workers = [
                threading.Thread(target=read_one, args=(code, reader),
                                 name="aisting-public-" + code, daemon=True)
                for code, reader in self._readers.items()
            ]
            started = []
            for worker in workers:
                with self._run_lock:
                    if self._stop.is_set():
                        break
                    worker.start()
                    started.append(worker)
            for worker in started:
                deadline = None
                while worker.is_alive():
                    worker.join(timeout=0.2)
                    if self._stop.is_set():
                        if deadline is None:
                            deadline = time.monotonic() + 3
                        if time.monotonic() >= deadline:
                            break
        finally:
            with self._run_lock:
                self._running = False
