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

    def __init__(self, channels: dict[str, str], emit, *, youtube_api_key: str = "",
                 youtube_oauth_token: str = "",
                 twitch_oauth_token: str = "", twitch_oauth_login: str = ""):
        if (type(channels) is not dict or not channels or len(channels) > 4
                or not callable(emit)):
            raise ValueError("동시 채팅 플랫폼과 채널을 확인하세요.")
        if any(code not in SUPPORTED or not isinstance(value, str)
               or not value.strip() for code, value in channels.items()):
            raise ValueError("지원하지 않는 플랫폼 또는 비어 있는 채널입니다.")
        self.channel = "전체"
        self._stop = threading.Event()
        self._stop_started_at = None
        self._run_lock = threading.Lock()
        self._emit_lock = threading.Lock()
        self._started_once = False
        self._running = False
        self._emit = emit
        self._readers = {}
        self._finished_readers = set()

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
            "twitch": lambda channel, cb: TwitchReadOnlySession(
                channel, cb, oauth_token=twitch_oauth_token,
                oauth_login=twitch_oauth_login) if twitch_oauth_token else
                TwitchReadOnlySession(channel, cb),
            "chzzk": lambda channel, cb: ChzzkReadOnlySession(channel, cb),
            "soop": lambda channel, cb: SoopReadOnlySession(channel, cb),
            "youtube": lambda channel, cb: YouTubeReadOnlySession(
                channel, cb, youtube_api_key, oauth_access_token=youtube_oauth_token)
                if youtube_oauth_token else YouTubeReadOnlySession(
                    channel, cb, youtube_api_key),
        }
        # Construct and validate every reader before starting any network I/O.
        for code, channel in channels.items():
            self._readers[code] = factories[code](channel.strip(), callback_for(code))

    def stop(self) -> None:
        """Close every transport without blocking Tk on a broken reader."""
        with self._run_lock:
            if self._stop.is_set():
                return
            self._stop_started_at = time.monotonic()
            self._stop.set()
        def close_one(reader):
            try:
                reader.stop()
            except Exception:
                # Do not expose transport URLs, credentials or internals.
                pass
        closers = [
            threading.Thread(target=close_one, args=(reader,), daemon=True)
            for reader in self._readers.values()
        ]
        for closer in closers:
            try:
                closer.start()
            except RuntimeError:
                # Failure to launch a closer cannot block other Stop requests.
                continue
        deadline = time.monotonic() + 0.5
        for closer in closers:
            if closer.ident is not None:
                closer.join(timeout=max(0, deadline - time.monotonic()))

    def run(self, *, max_seconds=None) -> None:
        """One finite inspection deadline and a shared operator Stop deadline."""
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
        started_at = time.monotonic()
        run_deadline = (started_at + max_seconds
                        if max_seconds is not None else None)
        try:
            def read_one(code, reader):
                try:
                    reader.run(max_seconds=max_seconds)
                except Exception as exc:
                    if not self._stop.is_set():
                        with self._emit_lock:
                            if not self._stop.is_set():
                                # Exception text may contain an API key.
                                self._emit("error", code + " 읽기 실패 (" +
                                           type(exc).__name__ + ")")
                finally:
                    # A single transport may end while other reader threads
                    # continue. Never silently imply all four remain online.
                    if not self._stop.is_set():
                        with self._emit_lock:
                            if not self._stop.is_set():
                                self._finished_readers.add(code)
                                remaining = len(self._readers) - len(self._finished_readers)
                                # Do not claim continued chat reception merely
                                # because a reader was selected at startup.
                                if remaining:
                                    detail = (" · 나머지 " + str(remaining)
                                              + "개 채널은 상태 개별 확인")
                                else:
                                    detail = " · 선택한 모든 채널의 읽기 작업 종료"
                                self._emit("reader_stopped",
                                           code + " 채팅 수신 종료" + detail)
            workers = [
                threading.Thread(target=read_one, args=(code, reader),
                                 name="aisting-public-" + code, daemon=True)
                for code, reader in self._readers.items()
            ]
            started = []
            startup_failed = False
            for worker in workers:
                with self._run_lock:
                    if self._stop.is_set():
                        break
                    try:
                        worker.start()
                    except Exception:
                        startup_failed = True
                        break
                    started.append(worker)
            if startup_failed:
                self.stop()
                raise RuntimeError("공개 채팅 수신 작업을 시작할 수 없습니다.")
            for worker in started:
                while worker.is_alive():
                    if (run_deadline is not None
                            and time.monotonic() >= run_deadline
                            and not self._stop.is_set()):
                        self.stop()
                    if self._stop.is_set():
                        # The three seconds start when Stop was requested,
                        # not when this particular worker is joined.
                        remaining = self._stop_started_at + 3 - time.monotonic()
                        if remaining <= 0:
                            break
                        worker.join(timeout=min(0.2, remaining))
                    else:
                        remaining = (run_deadline - time.monotonic()
                                     if run_deadline is not None else 0.2)
                        worker.join(timeout=max(0.001, min(0.2, remaining)))
        finally:
            with self._run_lock:
                self._running = False
