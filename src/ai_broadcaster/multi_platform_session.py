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
    YouTubeReadOnlySession, YouTubeChatResumeState,
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
        # 장시간 수신에서 플랫폼별 재연결 횟수와 관측된 공백을
        # 네트워크 시간으로만 기록한다. 놓친 채팅 건수는 추정하지 않는다.
        self._disconnect_started: dict[str, float] = {}
        self._reconnect_count = {code: 0 for code in channels}
        self._observed_gap_seconds = {code: 0.0 for code in channels}
        # 수신기 콜백·GUI 전달·예외를 플랫폼별로 구분한다.
        # 실제 서버 게시 건수나 시청자 수를 추정하지 않는다.
        self._callback_chat_count = {code: 0 for code in channels}
        self._forwarded_chat_count = {code: 0 for code in channels}
        self._callback_error_count = {code: 0 for code in channels}

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
                        self._callback_chat_count[code] += 1
                        try:
                            self._emit("chat", item)
                        except Exception:
                            self._callback_error_count[code] += 1
                            raise
                        else:
                            self._forwarded_chat_count[code] += 1
                    elif kind in ("ready", "connected"):
                        # 실제 채팅방 준비(ready) 이전의 소켓 연결(connected)은
                        # 공백 종료로 계산하지 않는다. 소스/API 토큰은 출력 금지.
                        reconnect_started = (
                            self._disconnect_started.pop(code, None)
                            if kind == "ready" else None
                        )
                        if reconnect_started is None:
                            self._emit(kind, code + " 공개 채팅 연결")
                        else:
                            gap = max(0.0, time.monotonic() - reconnect_started)
                            self._reconnect_count[code] += 1
                            self._observed_gap_seconds[code] += gap
                            self._emit(
                                "ready", code + " 공개 채팅 재연결 완료 · 관측된 수신 공백 "
                                + f"{gap:.2f}초 · 누락 여부는 실증 불가"
                            )
                    elif kind == "error":
                        self._emit("error", code + " 공개 채팅 연결 오류")
            return callback

        # 한 운영자 수신 세션의 실제 YouTube 채팅 ID·페이지 위치만 공유한다.
        # 실패 뒤 새 리더 객체를 만들더라도 기존 4플랫폼 FIFO 내용과
        # 이미 전달한 이벤트 ID가 사라지지 않는다.
        self._youtube_resume = (
            YouTubeChatResumeState() if "youtube" in channels else None
        )
        factories = {
            "twitch": lambda channel, cb: TwitchReadOnlySession(
                channel, cb, oauth_token=twitch_oauth_token,
                oauth_login=twitch_oauth_login) if twitch_oauth_token else
                TwitchReadOnlySession(channel, cb),
            "chzzk": lambda channel, cb: ChzzkReadOnlySession(channel, cb),
            "soop": lambda channel, cb: SoopReadOnlySession(channel, cb),
            "youtube": lambda channel, cb: YouTubeReadOnlySession(
                channel, cb, youtube_api_key,
                oauth_access_token=youtube_oauth_token,
                resume_state=self._youtube_resume)
                if youtube_oauth_token else YouTubeReadOnlySession(
                    channel, cb, youtube_api_key,
                    resume_state=self._youtube_resume),
        }
        # Only an explicitly running session may reconnect after a failure.
        self._factories = factories
        self._channels = {code: channel.strip() for code, channel in channels.items()}
        self._callbacks = {code: callback_for(code) for code in channels}
        # Construct and validate every reader before starting any network I/O.
        for code, channel in channels.items():
            self._readers[code] = factories[code](channel.strip(), self._callbacks[code])

    def reconnect_snapshot(self) -> dict[str, dict[str, float | int | bool]]:
        """실제 재연결 준비 완료 횟수·관측 공백만 메모리에서 조회한다.

        24시간 송출 성공 또는 무누락 수신으로 해석하지 않는다.
        토큰/채널명/채팅 본문은 결과에 넣지 않는다.
        """
        with self._emit_lock:
            now = time.monotonic()
            return {
                code: {
                    "재연결완료": self._reconnect_count[code],
                    "관측공백초": round(
                        self._observed_gap_seconds[code]
                        + max(0.0, now - self._disconnect_started[code])
                        if code in self._disconnect_started
                        else self._observed_gap_seconds[code], 6),
                    "현재공백": code in self._disconnect_started,
                    "콜백수신": self._callback_chat_count[code],
                    "콜백전달완료": self._forwarded_chat_count[code],
                    "콜백전달오류": self._callback_error_count[code],
                }
                for code in self._channels
            }

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
                    failures = 0
                    while not self._stop.is_set():
                        connected_at = time.monotonic()
                        try:
                            reader.run(max_seconds=max_seconds)
                            # 무기한 수신기가 Stop 없이 끝나면 연결 공백으로 처리한다.
                            if (max_seconds is None and not self._stop.is_set()
                                    and not getattr(reader, "_terminal_chat_end", False)):
                                raise ConnectionError("공개 채팅 읽기가 예기치 않게 종료됐습니다.")
                            break
                        except Exception as exc:
                            if self._stop.is_set():
                                break
                            # 전송 오류 뒤 다음 수신기를 만들기 전에 실패한
                            # 소켓/네트워크 세션을 해제한다. 사용자 전체 Stop과
                            # 달리 다른 3개 수신기의 처리는 계속된다.
                            try:
                                reader.stop()
                            except Exception:
                                # 토큰·연결 URL 등 원본 예외 본문을 노출하지 않는다.
                                pass
                            with self._emit_lock:
                                if not self._stop.is_set():
                                    self._disconnect_started.setdefault(
                                        code, time.monotonic())
                                    # Do not reveal transport credentials.
                                    self._emit("error", code + " 읽기 실패 (" +
                                               type(exc).__name__ + ")")
                            # Finite Windows probes must not retry after failure.
                            if max_seconds is not None:
                                break
                            if time.monotonic() - connected_at >= 30:
                                failures = 0
                            failures += 1
                            # 장시간 장애 중에도 운영자가 Stop할 때까지 재연결한다.
                            if failures == 4 or failures % 30 == 0:
                                with self._emit_lock:
                                    if not self._stop.is_set():
                                        self._emit("error", code +
                                                   " 재연결 3회 이상 실패 · 수신 공백 지속 · 재시도 중")
                            with self._emit_lock:
                                if not self._stop.is_set():
                                    self._emit("error", code +
                                               " 수신 연결 끊김 · 재연결 대기 중 (공백 가능)")
                            # 재연결 횟수가 커져도 거대한 정수 계산을 피한다.
                            if self._stop.wait(min(2 ** min(failures - 1, 2), 4)):
                                break
                            # 실패한 옛 수신기는 재사용하지 않고 새 수신기만 재생성한다.
                            replacement = None
                            while replacement is None and not self._stop.is_set():
                                try:
                                    replacement = self._factories[code](
                                        self._channels[code], self._callbacks[code])
                                except Exception as reconnect_error:
                                    with self._emit_lock:
                                        if not self._stop.is_set():
                                            self._emit("error", code + " 재연결 준비 실패 (" +
                                                       type(reconnect_error).__name__ + ")")
                                    if self._stop.wait(min(2 ** min(failures - 1, 2), 4)):
                                        break
                            if replacement is None:
                                break
                            with self._run_lock:
                                stopped = self._stop.is_set()
                                if not stopped:
                                    self._readers[code] = replacement
                            if stopped:
                                replacement.stop()
                                break
                            reader = replacement
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
