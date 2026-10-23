"""Read-only multi-platform live-chat coordinator for the existing AISTING GUI.

No platform login, posting, streaming, automatic startup or text filtering.
Every accepted viewer event enters the existing one-worker AI FIFO.
"""
from __future__ import annotations

import math
import threading
import time
from collections import deque

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
        # GUI 상태 스냅샷은 동일 스레드 재진입을 허용한다.
        self._emit_lock = threading.RLock()
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
        self._callback_locks = {code: threading.Lock() for code in channels}
        self._callback_emit_total_seconds = {code: 0.0 for code in channels}
        self._callback_emit_max_seconds = {code: 0.0 for code in channels}
        self._callback_aborted_count = {code: 0 for code in channels}
        # 실제 서버 이벤트 ID가 재연결 뒤 다시 온 경우만 중복 전송 차단.
        # 본문/닉네임으로는 절대 합치지 않으며 ID 없는 사건은 모두 전달.
        # 수신기 콜백이 AI FIFO 수용에 성공한 ID만 최근 5만 개 유지한다.
        self._replayed_event_id_count = {code: 0 for code in channels}
        self._recent_event_ids = {code: deque() for code in channels}
        self._seen_event_ids = {code: set() for code in channels}
        # 읽기 루프가 실제 시도/예외를 관측한 횟수만 기록한다.
        # 채팅이 조용하다는 이유로 끊김이나 무누락을 추정하지 않는다.
        self._reader_attempts = {code: 0 for code in channels}
        self._reader_failures = {code: 0 for code in channels}
        self._last_reader_failure_at: dict[str, float] = {}
        self._room_ready = {code: False for code in channels}
        self._last_ready_at = {}
        self._last_chat_at = {}
        # 실제 WebSocket 수신 프레임(트위치/치지직/SOOP) 또는
        # 정상이 확인된 YouTube API 응답. 채팅 개수와 절대 혼동하지 않는다.
        self._transport_activity_count = {code: 0 for code in channels}
        self._last_transport_activity_at: dict[str, float] = {}
        # 반열림 소켓 감지에 의한 복구와 네트워크 예외를 혼동하지 않는다.
        self._transport_stalled_count = {code: 0 for code in channels}
        # 실제 ready 신호가 확인된 기간만 누적한다. 실제 네트워크
        # 무누락 또는 24시간 송출 성공과는 다른 읽기 전용 지표다.
        self._ready_interval_started: dict[str, float] = {}
        self._ready_observed_seconds = {code: 0.0 for code in channels}
        self._max_ready_streak_seconds = {code: 0.0 for code in channels}
        self._ended_ready_streak_24h_count = {code: 0 for code in channels}
        # 실제 재연결 완료 공백의 최근 512개 표본만 보존한다.
        # 채팅 본문, 닉네임, 토큰 및 소켓 내용은 저장하지 않는다.
        self._completed_gap_samples = {
            code: deque(maxlen=512) for code in channels
        }
        self._completed_gap_max_seconds = {code: 0.0 for code in channels}
        self._completed_gap_over_three = {code: 0 for code in channels}
        self._session_started_at: float | None = None

        def callback_for(code):
            def callback(kind, item):
                # 동일 플랫폼 이벤트 순서만 직렬화하고, 다른 플랫폼의
                # GUI 전달 대기까지 공유 상태 잠금으로 묶지 않는다.
                with self._callback_locks[code]:
                    if self._stop.is_set():
                        return False
                    if kind == "chat":
                        if code == "twitch" and isinstance(item, TwitchChatLine):
                            item = PlatformChat(
                                item.channel, item.sender, item.text, code,
                                item.event_id)
                        if not isinstance(item, PlatformChat) or item.platform != code:
                            raise ValueError("채팅 플랫폼 식별자가 올바르지 않습니다.")
                        event_id = item.event_id
                        if event_id is not None and event_id in self._seen_event_ids[code]:
                            # 같은 플랫폼·같은 세션에서 이미 AI FIFO에 넣은
                            # 서버 사건의 재전달만 막는다. 별개 채팅은 보존.
                            with self._emit_lock:
                                self._replayed_event_id_count[code] += 1
                            return True
                        with self._emit_lock:
                            self._callback_chat_count[code] += 1
                            self._last_chat_at[code] = time.monotonic()
                        started = time.monotonic()
                        try:
                            accepted = self._emit("chat", item)
                        except Exception:
                            with self._emit_lock:
                                self._callback_error_count[code] += 1
                            raise
                        else:
                            with self._emit_lock:
                                if accepted is False:
                                    self._callback_aborted_count[code] += 1
                                else:
                                    self._forwarded_chat_count[code] += 1
                                    if event_id is not None:
                                        recent = self._recent_event_ids[code]
                                        recent.append(event_id)
                                        self._seen_event_ids[code].add(event_id)
                                        if len(recent) > 50_000:
                                            self._seen_event_ids[code].discard(
                                                recent.popleft())
                        finally:
                            elapsed = max(0.0, time.monotonic() - started)
                            with self._emit_lock:
                                self._callback_emit_total_seconds[code] += elapsed
                                self._callback_emit_max_seconds[code] = max(
                                    self._callback_emit_max_seconds[code], elapsed)
                    elif kind == "transport_stalled":
                        with self._emit_lock:
                            self._transport_stalled_count[code] += 1
                    elif kind == "transport_activity":
                        with self._emit_lock:
                            self._transport_activity_count[code] += 1
                            self._last_transport_activity_at[code] = time.monotonic()
                        # 프레임마다 GUI 큐에 상태 이벤트를 올리지 않는다.
                        # 채팅 수신·단일 AI FIFO를 밀어내지 않도록 카운터만 유지.
                    elif kind in ("ready", "connected"):
                        with self._emit_lock:
                            if kind == "ready":
                                ready_at = time.monotonic()
                                self._room_ready[code] = True
                                self._last_ready_at[code] = ready_at
                                self._ready_interval_started.setdefault(code, ready_at)
                                disconnected_at = self._disconnect_started.pop(code, None)
                            else:
                                disconnected_at = None
                            if disconnected_at is not None:
                                gap = max(0.0, time.monotonic() - disconnected_at)
                                self._reconnect_count[code] += 1
                                self._observed_gap_seconds[code] += gap
                                self._completed_gap_samples[code].append(gap)
                                self._completed_gap_max_seconds[code] = max(
                                    self._completed_gap_max_seconds[code], gap)
                                self._completed_gap_over_three[code] += int(gap > 3)
                            else:
                                gap = None
                        if gap is None:
                            self._emit(kind, code + " 공개 채팅 연결")
                        else:
                            self._emit(
                                "ready", code + " 공개 채팅 재연결 완료 · 관측된 수신 공백 "
                                + f"{gap:.2f}초 · 누락 여부는 실증 불가")
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
                    "완료공백최근표본": len(self._completed_gap_samples[code]),
                    "완료공백최장초": round(self._completed_gap_max_seconds[code], 3),
                    "완료공백3초초과": self._completed_gap_over_three[code],
                    "완료공백최근p95초": (
                        round(sorted(self._completed_gap_samples[code])[
                            math.ceil(len(self._completed_gap_samples[code]) * 0.95) - 1
                        ], 3) if self._completed_gap_samples[code] else None
                    ),
                    "관측입장시간비율": (
                        round(min(1.0, max(0.0, (
                            self._ready_observed_seconds[code]
                            + (max(0.0, min(now, self._stop_started_at
                                           if self._stop_started_at is not None else now)
                                   - self._ready_interval_started[code])
                               if code in self._ready_interval_started else 0.0)
                        ) / max(0.001, (
                            min(now, self._stop_started_at
                                if self._stop_started_at is not None else now)
                            - self._session_started_at
                        )))), 5)
                        if self._session_started_at is not None else None
                    ),
                    "관측공백초": round(
                        self._observed_gap_seconds[code]
                        + max(0.0, now - self._disconnect_started[code])
                        if code in self._disconnect_started
                        else self._observed_gap_seconds[code], 6),
                    "현재공백": code in self._disconnect_started,
                    "콜백수신": self._callback_chat_count[code],
                    "콜백전달완료": self._forwarded_chat_count[code],
                    "콜백전달오류": self._callback_error_count[code],
                    "콜백전달중단": self._callback_aborted_count[code],
                    "서버이벤트ID재수신차단": self._replayed_event_id_count[code],
                    "콜백전달누적초": round(self._callback_emit_total_seconds[code], 6),
                    "콜백전달최대초": round(self._callback_emit_max_seconds[code], 6),
                    "실제읽기시도": self._reader_attempts[code],
                    "실제읽기실패": self._reader_failures[code],
                    "마지막읽기실패경과초": round(now - self._last_reader_failure_at[code], 3)
                    if code in self._last_reader_failure_at else None,
                    "최장연속입장관측초": round(max(
                        self._max_ready_streak_seconds[code],
                        max(0.0, min(now, self._stop_started_at
                                     if self._stop_started_at is not None else now)
                            - self._ready_interval_started[code])
                        if code in self._ready_interval_started else 0.0
                    ), 3),
                    "24시간연속입장관측완료구간": (
                        self._ended_ready_streak_24h_count[code]
                        + int(code in self._ready_interval_started and
                              max(0.0, now - self._ready_interval_started[code]) >= 86400)
                    ),
                    "입장관측누적초": round(
                        self._ready_observed_seconds[code]
                        + (max(0.0, min(now, self._stop_started_at
                                        if self._stop_started_at is not None else now)
                               - self._ready_interval_started[code])
                           if code in self._ready_interval_started else 0.0), 3),
                    "채팅방입장": self._room_ready[code] and not self._stop.is_set(),
                    "마지막입장경과초": round(now - self._last_ready_at[code], 3)
                    if code in self._last_ready_at else None,
                    "마지막채팅콜백경과초": round(now - self._last_chat_at[code], 3)
                    if code in self._last_chat_at else None,
                    "수신응답계수": self._transport_activity_count[code],
                    "통신무응답재연결": self._transport_stalled_count[code],
                    "마지막통신응답경과초": round(
                        now - self._last_transport_activity_at[code], 3)
                    if code in self._last_transport_activity_at else None,
                    "수신기종료": code in self._finished_readers,
                }
                for code in self._channels
            }

    def try_reconnect_snapshot(self):
        """GUI 대기열이 많을 때 상태 잠금을 기다리지 않고 다음 주기 재시도."""
        if not self._emit_lock.acquire(blocking=False):
            return None
        try:
            return self.reconnect_snapshot()
        finally:
            self._emit_lock.release()

    def _end_ready_interval_locked(self, code: str, ended_at: float) -> None:
        """_emit_lock 보유 중에 입장 관측 구간을 중복 없이 종료."""
        started = self._ready_interval_started.pop(code, None)
        if started is not None:
            duration = max(0.0, ended_at - started)
            self._ready_observed_seconds[code] += duration
            self._max_ready_streak_seconds[code] = max(
                self._max_ready_streak_seconds[code], duration)
            # 이 값은 오직 ready 상태 관측시간이며 실제 패킷 무손실,
            # 방송/인코더 출력, 라이브 시청자 수신 보증이 아니다.
            if duration >= 86400:
                self._ended_ready_streak_24h_count[code] += 1
        self._room_ready[code] = False

    def stop(self) -> None:
        """Close every transport without blocking Tk on a broken reader."""
        with self._run_lock:
            if self._stop.is_set():
                return
            self._stop_started_at = time.monotonic()
            self._stop.set()
        with self._emit_lock:
            for code in self._channels:
                self._end_ready_interval_locked(code, self._stop_started_at)
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
        with self._emit_lock:
            self._session_started_at = started_at
        run_deadline = (started_at + max_seconds
                        if max_seconds is not None else None)
        try:
            def read_one(code, reader):
                try:
                    failures = 0
                    while not self._stop.is_set():
                        connected_at = time.monotonic()
                        with self._emit_lock:
                            self._reader_attempts[code] += 1
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
                            with self._emit_lock:
                                self._reader_failures[code] += 1
                                self._last_reader_failure_at[code] = time.monotonic()
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
                                    self._end_ready_interval_locked(
                                        code, time.monotonic())
                                    self._disconnect_started.setdefault(
                                        code, time.monotonic())
                            # 오류 알림은 플랫폼 공용 상태 잠금 밖에서
                            # GUI 큐로 전달한다. 다른 수신기의 진행을 막지 않는다.
                            if not self._stop.is_set():
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
                                if not self._stop.is_set():
                                    self._emit("error", code +
                                               " 재연결 3회 이상 실패 · 수신 공백 지속 · 재시도 중")
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
                            self._finished_readers.add(code)
                            self._end_ready_interval_locked(code, time.monotonic())
                            remaining = len(self._readers) - len(self._finished_readers)
                        # 마지막 수신기 종료 알림도 상태 잠금 밖에서 전달한다.
                        if not self._stop.is_set():
                            detail = (f" · 나머지 {remaining}개 채널은 상태 개별 확인"
                                      if remaining else " · 선택한 모든 채널의 읽기 작업 종료")
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
