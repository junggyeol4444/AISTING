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
    YouTubeReadOnlySession, YouTubeChatResumeState, PreJoinChatResumeState,
)
from .twitch_readonly import TwitchChatLine, TwitchReadOnlySession, TwitchServerReconnect

SUPPORTED = ("twitch", "chzzk", "soop", "youtube")

# 공개 수신기에서는 전달 성공(true)이지만 아직 AI FIFO에 들어간 것은
# 아니고, 원본 SQLite에만 확정된 신규 채팅을 구분하기 위한 결과 표식.
SQLITE_DEFERRED_CHAT = object()


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
        # 유한 읽기 검사와 무기한 실제 수신을 구별해
        # 정상 검사 종료를 재연결 장애로 기록하지 않는다.
        self._run_max_seconds = None
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
        self._sqlite_deferred_count = {code: 0 for code in channels}
        self._sqlite_deferred_enqueued_count = {code: 0 for code in channels}
        self._callback_error_count = {code: 0 for code in channels}
        self._callback_locks = {code: threading.Lock() for code in channels}
        self._callback_emit_total_seconds = {code: 0.0 for code in channels}
        self._callback_emit_max_seconds = {code: 0.0 for code in channels}
        # 아직 끝나지 않은 실제 전달 콜백도 현재 경과를 관측한다.
        # 완료된 콜백 p95만 보면 수 초 이상 멈춘 콜백을 놓칠 수 있다.
        self._callback_inflight_started_at = {code: None for code in channels}
        # 실제 수신기→GUI/AI FIFO 콜백 소요시간의 최근 512건 p95.
        # 성공·거절·예외를 모두 측정하며 전달 성공으로 혼동하지 않는다.
        self._callback_emit_samples = {code: deque(maxlen=512) for code in channels}
        self._callback_emit_over_three_seconds = {code: 0 for code in channels}
        # 채팅 파싱부터 기존 단일 AI FIFO 콜백이 실제 수용할 때까지
        # 보류/재연결/콜백 대기를 모두 포함한다. 모델 생성·음성·시청자
        # E2E 지연은 포함하지 않으며 본문·토큰은 저장하지 않는다.
        self._parse_to_accept_samples = {
            code: deque(maxlen=512) for code in channels
        }
        self._parse_to_accept_max_seconds = {code: 0.0 for code in channels}
        self._parse_to_accept_over_three = {code: 0 for code in channels}
        # 파싱→콜백 진입과 콜백 진입→FIFO 수용을 별도로 측정하여
        # 수신기 보류·재연결 병목과 GUI/AI 수용 병목을 구분한다.
        # 둘 다 실제 수용된 사건만 표본이며 E2E/모델 지연은 아니다.
        self._parse_to_callback_samples = {
            code: deque(maxlen=512) for code in channels
        }
        self._parse_to_callback_max_seconds = {code: 0.0 for code in channels}
        self._parse_to_callback_over_three = {code: 0 for code in channels}
        self._callback_to_accept_samples = {
            code: deque(maxlen=512) for code in channels
        }
        self._callback_to_accept_max_seconds = {code: 0.0 for code in channels}
        self._callback_to_accept_over_three = {code: 0 for code in channels}
        self._parse_timestamp_missing_count = {code: 0 for code in channels}
        self._callback_aborted_count = {code: 0 for code in channels}
        # 실제 콜백에서 이미 수용한 서버 ID를 다시 받은 경우와
        # YouTube 수신기 내부 페이지 재수신 통계는 별도로 정산한다.
        self._callback_duplicate_chat_count = {code: 0 for code in channels}
        # 운영자가 Stop한 뒤 들어온 늦은 채팅은 수용 성공으로 세지 않는다.
        self._post_stop_rejected_chat_count = {code: 0 for code in channels}
        # 상태 알림 실패는 수신기 재연결 실패와 별도로 관측한다.
        self._status_emit_failure_count = {code: 0 for code in channels}
        # 실제 서버 이벤트 ID가 재연결 뒤 다시 온 경우만 중복 전송 차단.
        # 본문/닉네임으로는 절대 합치지 않으며 ID 없는 사건은 모두 전달.
        # 수신기 콜백이 AI FIFO 수용에 성공한 ID만 최근 5만 개 유지한다.
        self._replayed_event_id_count = {code: 0 for code in channels}
        self._missing_event_id_count = {code: 0 for code in channels}
        self._recent_event_ids = {code: deque() for code in channels}
        self._seen_event_ids = {code: set() for code in channels}
        # 트위치·치지직·SOOP에서 이미 파싱한 소켓 프레임의
        # 미수용 채팅은 재연결된 수신기에 동일 메모리 deque를 전달.
        # 실제 서버가 보내지 않은 사건·프로세스 종료 시 메모리 내용은
        # 복구하지 못하며, 수용 완료만 전달 성공으로 기록한다.
        self._pending_websocket_chats = {
            code: deque() for code in channels if code in ("twitch", "chzzk", "soop")
        }
        # 치지직·SOOP는 JOIN 승인 이전에 도착한 채팅도 있을 수 있다.
        # 해당 서버 채팅방 ID와 함께 재연결 동안만 메모리에서 보존한다.
        # 서버가 다른 채팅방을 반환하면 과거 사건을 섞지 않고 오류로 차단.
        self._prejoin_resume_states = {
            code: PreJoinChatResumeState()
            for code in channels if code in ("chzzk", "soop")
        }
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
        # 무기한 수신 중 실제 리더 종료 통지가 예외 처리보다 먼저
        # 도착한 경우 최초 공백 시작과 종료 건수를 관측한다.
        self._unexpected_reader_stop_count = {code: 0 for code in channels}
        # 실제 ready 신호가 확인된 기간만 누적한다. 실제 네트워크
        # 무누락 또는 24시간 송출 성공과는 다른 읽기 전용 지표다.
        self._ready_interval_started: dict[str, float] = {}
        self._ready_observed_seconds = {code: 0.0 for code in channels}
        self._max_ready_streak_seconds = {code: 0.0 for code in channels}
        self._ended_ready_streak_24h_count = {code: 0 for code in channels}
        # 선택한 모든 플랫폼이 동시에 ready인 실제 관측 구간만 누적.
        # 개별 24시간 ready가 서로 다른 시간대였어도 전체 동시
        # 24시간이라고 오판하지 않는다. 패킷 무손실·송출 보증은 아님.
        self._all_ready_started_at: float | None = None
        self._all_ready_observed_seconds = 0.0
        self._all_ready_max_streak_seconds = 0.0
        self._all_ready_24h_completed_intervals = 0
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
                        if kind == "chat":
                            with self._emit_lock:
                                self._post_stop_rejected_chat_count[code] += 1
                        return False
                    if kind == "chat":
                        if code == "twitch" and isinstance(item, TwitchChatLine):
                            item = PlatformChat(
                                item.channel, item.sender, item.text, code,
                                item.event_id, item.parsed_at_monotonic)
                        if not isinstance(item, PlatformChat) or item.platform != code:
                            raise ValueError("채팅 플랫폼 식별자가 올바르지 않습니다.")
                        event_id = item.event_id
                        if event_id is not None and event_id in self._seen_event_ids[code]:
                            # 이미 수용한 같은 서버 사건만 재전달을 차단한다.
                            # 채팅 콜백 총수와 중복 ID 수를 한 잠금에서 함께
                            # 기록하여 GUI가 정산 중간 상태를 오인하지 않게 한다.
                            with self._emit_lock:
                                self._callback_chat_count[code] += 1
                                self._last_chat_at[code] = time.monotonic()
                                self._replayed_event_id_count[code] += 1
                                self._callback_duplicate_chat_count[code] += 1
                            return True
                        started = time.monotonic()
                        with self._emit_lock:
                            # 새 채팅의 접수와 처리 중 표시도 원자적으로 기록.
                            # 완료 전에는 정산을 성공/실패로 확정하지 않는다.
                            self._callback_chat_count[code] += 1
                            self._last_chat_at[code] = started
                            if event_id is None:
                                self._missing_event_id_count[code] += 1
                            self._callback_inflight_started_at[code] = started
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
                                    if accepted is SQLITE_DEFERRED_CHAT:
                                        self._sqlite_deferred_count[code] += 1
                                    parsed_at = item.parsed_at_monotonic
                                    if (type(parsed_at) in (int, float)
                                            and math.isfinite(parsed_at)
                                            and 0 < parsed_at <= started):
                                        accepted_at = time.monotonic()
                                        parse_to_callback = max(0.0, started - parsed_at)
                                        callback_to_accept = max(0.0, accepted_at - started)
                                        parse_to_accept = max(0.0, accepted_at - parsed_at)
                                        self._parse_to_callback_samples[code].append(
                                            parse_to_callback)
                                        self._parse_to_callback_max_seconds[code] = max(
                                            self._parse_to_callback_max_seconds[code],
                                            parse_to_callback)
                                        self._parse_to_callback_over_three[code] += int(
                                            parse_to_callback > 3.0)
                                        self._callback_to_accept_samples[code].append(
                                            callback_to_accept)
                                        self._callback_to_accept_max_seconds[code] = max(
                                            self._callback_to_accept_max_seconds[code],
                                            callback_to_accept)
                                        self._callback_to_accept_over_three[code] += int(
                                            callback_to_accept > 3.0)
                                        self._parse_to_accept_samples[code].append(
                                            parse_to_accept)
                                        self._parse_to_accept_max_seconds[code] = max(
                                            self._parse_to_accept_max_seconds[code],
                                            parse_to_accept)
                                        self._parse_to_accept_over_three[code] += int(
                                            parse_to_accept > 3.0)
                                    else:
                                        # 외부에서 직접 구성한 가상 사건이나
                                        # 비정상 시각은 실제 지연 표본으로 세지 않는다.
                                        self._parse_timestamp_missing_count[code] += 1
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
                                self._callback_inflight_started_at[code] = None
                                self._callback_emit_total_seconds[code] += elapsed
                                self._callback_emit_max_seconds[code] = max(
                                    self._callback_emit_max_seconds[code], elapsed)
                                self._callback_emit_samples[code].append(elapsed)
                                self._callback_emit_over_three_seconds[code] += int(
                                    elapsed > 3.0)
                        # 수신기까지 실제 수용 여부를 반환한다. False를
                        # 숨기면 WebSocket은 정상 전달로, YouTube는 다음
                        # 페이지로 확정해 채팅이 조용히 유실될 수 있다.
                        return accepted is not False
                    elif kind == "server_replay":
                        # YouTube 페이지 수신기가 자체 ID 재수신을
                        # 차단한 경우도 GUI 진단 수치에서 누락하지 않는다.
                        with self._emit_lock:
                            self._replayed_event_id_count[code] += 1
                    elif kind == "transport_stalled":
                        # 실제 읽기 소켓의 장시간 무응답 통지를 받는 순간
                        # ready 관측을 끝낸다. 상위 읽기 루프의 예외 처리나
                        # 소켓 정리를 기다리는 동안 24시간 연속 입장으로
                        # 잘못 누적하지 않는다. 채팅 유실 건수는 추정 금지.
                        with self._emit_lock:
                            stalled_at = time.monotonic()
                            self._transport_stalled_count[code] += 1
                            self._end_ready_interval_locked(code, stalled_at)
                            # 같은 소켓이 stopped/예외를 다시 통지해도
                            # 실제 관측 공백의 최초 시작시각을 보존한다.
                            self._disconnect_started.setdefault(code, stalled_at)
                    elif kind == "stopped":
                        # 실제 소켓의 finally에서 오는 종료 통지는 상위
                        # read_one의 예외 처리·재연결 준비보다 먼저 도착한다.
                        # 무기한 수신에서 예기치 않은 종료면 이 시각부터
                        # 공백을 기록하고, 늦은 예외 처리로 시각을 덮지 않는다.
                        # 유한 검사·운영자 Stop·YouTube 정상 방송 종료는
                        # 재연결 장애로 오인하지 않는다.
                        with self._emit_lock:
                            stopped_at = time.monotonic()
                            unexpected = (
                                self._running
                                and self._run_max_seconds is None
                                and not self._stop.is_set()
                                and not getattr(
                                    self._readers.get(code),
                                    "_terminal_chat_end", False))
                            if unexpected and code not in self._disconnect_started:
                                self._disconnect_started[code] = stopped_at
                                self._unexpected_reader_stop_count[code] += 1
                            self._end_ready_interval_locked(code, stopped_at)
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
                                self._refresh_all_ready_streak_locked(ready_at)
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
                            self._emit_status_safely(code, kind, code + " 공개 채팅 연결")
                        else:
                            self._emit_status_safely(
                                code, "ready", code + " 공개 채팅 재연결 완료 · 관측된 수신 공백 "
                                + f"{gap:.2f}초 · 누락 여부는 실증 불가")
                    elif kind == "error":
                        self._emit_status_safely(code, "error", code + " 공개 채팅 연결 오류")
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
            reader = factories[code](channel.strip(), self._callbacks[code])
            if code in self._pending_websocket_chats and hasattr(
                    reader, "_pending_chats"):
                reader._pending_chats = self._pending_websocket_chats[code]
            if code in self._prejoin_resume_states:
                reader._prejoin_resume = self._prejoin_resume_states[code]
            self._readers[code] = reader

    def note_deferred_sqlite_chat_enqueued(self, platform: str) -> None:
        """같은 실행 중 SQLite에만 저장됐던 채팅의 AI FIFO 등록 실측.

        이미 과거 실행에서 남아 있던 기록과 현재 새로 수신한 기록을
        구별하기 위한 숫자 기록만 하며 채팅 본문/신원은 보관하지 않는다.
        """
        if platform not in self._sqlite_deferred_count:
            raise ValueError("복구된 채팅의 플랫폼 종류 오류")
        with self._emit_lock:
            # 재등록이 완료된 직후 아직 같은 수신 콜백이 영속 성공을
            # 통계에 반영 중일 수 있다. 잠시 앞서 기록돼도 후속 콜백과
            # 합쳐 정산되므로 재등록 사실을 버리지 않는다.
            self._sqlite_deferred_enqueued_count[platform] += 1

    def _emit_status_safely(self, code: str, kind: str, detail: str) -> bool:
        """상태 알림 GUI 예외가 공개 채팅 수신/재연결 작업을 끝내지 않게 한다.

        채팅 자체는 이 경로로 보내지 않으며, 채팅 전달 실패는 그대로 전파한다.
        알림 실패 횟수만 메모리에 기록하고 민감한 예외 본문은 저장하지 않는다.
        """
        try:
            self._emit(kind, detail)
            return True
        except Exception:
            with self._emit_lock:
                self._status_emit_failure_count[code] += 1
            return False

    def reconnect_snapshot(self) -> dict[str, dict[str, float | int | bool]]:
        """실제 재연결 준비 완료 횟수·관측 공백만 메모리에서 조회한다.

        24시간 송출 성공 또는 무누락 수신으로 해석하지 않는다.
        토큰/채널명/채팅 본문은 결과에 넣지 않는다.
        """
        with self._emit_lock:
            now = time.monotonic()
            # Stop 이후 경과를 운영 중 관측시간으로 잘못 누적하지 않는다.
            if self._stop_started_at is not None:
                now = min(now, self._stop_started_at)
            simultaneous_current = (
                max(0.0, now - self._all_ready_started_at)
                if self._all_ready_started_at is not None else 0.0)
            simultaneous_max = max(
                self._all_ready_max_streak_seconds, simultaneous_current)
            simultaneous_24h = (
                self._all_ready_24h_completed_intervals
                + int(simultaneous_current >= 86400))
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
                        + max(0.0, min(
                            now, self._stop_started_at
                            if self._stop_started_at is not None else now
                        ) - self._disconnect_started[code])
                        if code in self._disconnect_started
                        else self._observed_gap_seconds[code], 6),
                    "현재공백": (
                        code in self._disconnect_started and not self._stop.is_set()
                    ),
                    "콜백수신": self._callback_chat_count[code],
                    "콜백전달완료": self._forwarded_chat_count[code],
                    "SQLite우선보존": self._sqlite_deferred_count[code],
                    "SQLite보존후AI재등록": self._sqlite_deferred_enqueued_count[code],
                    "SQLite보존AI대기": max(
                        0, self._sqlite_deferred_count[code]
                        - self._sqlite_deferred_enqueued_count[code]),
                    "콜백전달오류": self._callback_error_count[code],
                    "콜백전달중단": self._callback_aborted_count[code],
                    "중지후채팅거절": self._post_stop_rejected_chat_count[code],
                    "콜백내부중복ID": self._callback_duplicate_chat_count[code],
                    # 수신기 콜백→로컬 GUI/AI FIFO 전달의 정산만 확인한다.
                    # 서버가 전송하지 않은 사건/실제 시청자 무누락은 검증 불가.
                    # 진행 중인 콜백이 있으면 미확정(None)으로 남긴다.
                    # YouTube 수신기 내부 server_replay는 채팅 콜백이
                    # 아니므로 이 차이에서 빼지 않는다.
                    "콜백정산차이": (
                        self._callback_chat_count[code]
                        - self._forwarded_chat_count[code]
                        - self._callback_aborted_count[code]
                        - self._callback_error_count[code]
                        - self._callback_duplicate_chat_count[code]
                        if self._callback_inflight_started_at[code] is None
                        else None
                    ),
                    "상태알림전달실패": self._status_emit_failure_count[code],
                    "서버이벤트ID재수신차단": self._replayed_event_id_count[code],
                    "서버이벤트ID없음": self._missing_event_id_count[code],
                    # 트위치·치지직·SOOP 로컬 소켓 프레임을 이미
                    # 받았으나 GUI/AI FIFO가 수용하지 않은 메모리 사건 수.
                    # 재연결 전 대기 사건은 전달 완료로 세지 않는다.
                    "수신프레임미수용보류": len(
                        self._pending_websocket_chats[code])
                        if code in self._pending_websocket_chats else 0,
                    # 실제 서버 JOIN 승인을 받기 전에 도착한 프레임도
                    # 같은 채팅방 ID로 재연결될 때까지 메모리에 보존.
                    "JOIN전미수용보류": (
                        len(self._prejoin_resume_states[code].pending)
                        if code in self._prejoin_resume_states else 0),
                    "JOIN전중복서버ID차단": (
                        self._prejoin_resume_states[code].duplicate_server_ids
                        if code in self._prejoin_resume_states else 0),
                    # YouTube는 HTTP 페이지 단위로 전부 파싱한 뒤
                    # 로컬 AI FIFO 수용 전 메모리에 보관한다. 재연결된
                    # 새 리더가 같은 resume 상태를 이어받는다.
                    "수신페이지미수용보류": (
                        len(self._youtube_resume.pending_page_chats)
                        if code == "youtube" and self._youtube_resume is not None
                        else 0),
                    "수신페이지확정대기": bool(
                        code == "youtube" and self._youtube_resume is not None
                        and self._youtube_resume.pending_page_active),
                    "콜백전달누적초": round(self._callback_emit_total_seconds[code], 6),
                    "콜백전달최대초": round(self._callback_emit_max_seconds[code], 6),
                    "콜백소요최근표본": len(self._callback_emit_samples[code]),
                    "콜백소요최근p95초": (
                        round(sorted(self._callback_emit_samples[code])[
                            math.ceil(len(self._callback_emit_samples[code]) * 0.95) - 1
                        ], 6) if self._callback_emit_samples[code] else None
                    ),
                    "콜백소요3초초과": self._callback_emit_over_three_seconds[code],
                    # 파싱 시각과 실제 FIFO 수용 시각의 동일 사건 분해.
                    # 콜백 이전 보류와 콜백 내부 대기를 섞지 않는다.
                    "파싱후콜백최근표본": len(self._parse_to_callback_samples[code]),
                    "파싱후콜백최근p95초": (
                        round(sorted(self._parse_to_callback_samples[code])[
                            math.ceil(len(self._parse_to_callback_samples[code]) * 0.95) - 1
                        ], 6) if self._parse_to_callback_samples[code] else None
                    ),
                    "파싱후콜백최장초": round(
                        self._parse_to_callback_max_seconds[code], 6),
                    "파싱후콜백3초초과": self._parse_to_callback_over_three[code],
                    "콜백진입후수용최근표본": len(self._callback_to_accept_samples[code]),
                    "콜백진입후수용최근p95초": (
                        round(sorted(self._callback_to_accept_samples[code])[
                            math.ceil(len(self._callback_to_accept_samples[code]) * 0.95) - 1
                        ], 6) if self._callback_to_accept_samples[code] else None
                    ),
                    "콜백진입후수용최장초": round(
                        self._callback_to_accept_max_seconds[code], 6),
                    "콜백진입후수용3초초과": self._callback_to_accept_over_three[code],
                    "파싱후수용최근표본": len(self._parse_to_accept_samples[code]),
                    "파싱후수용최근p95초": (
                        round(sorted(self._parse_to_accept_samples[code])[
                            math.ceil(len(self._parse_to_accept_samples[code]) * 0.95) - 1
                        ], 6) if self._parse_to_accept_samples[code] else None
                    ),
                    "파싱후수용최장초": round(
                        self._parse_to_accept_max_seconds[code], 6),
                    "파싱후수용3초초과": self._parse_to_accept_over_three[code],
                    "파싱시각미확인수용": self._parse_timestamp_missing_count[code],
                    "파싱후미수용최장경과초": self._oldest_pending_parsed_age_seconds(
                        code, now),
                    "콜백전달진행중": self._callback_inflight_started_at[code] is not None,
                    "콜백전달진행초": (
                        round(max(0.0, now - self._callback_inflight_started_at[code]), 6)
                        if self._callback_inflight_started_at[code] is not None else None
                    ),
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
                    # 선택된 모든 플랫폼의 실제 ready 시간 교집합.
                    # 각 플랫폼이 따로 24시간 ready였다는 사실과 구별한다.
                    "선택플랫폼동시입장현재": self._all_ready_started_at is not None,
                    "선택플랫폼동시입장누적초": round(
                        self._all_ready_observed_seconds + simultaneous_current, 3),
                    "선택플랫폼동시입장최장초": round(simultaneous_max, 3),
                    "선택플랫폼동시입장24시간관측구간": simultaneous_24h,
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
                    "예기치않은수신기종료": self._unexpected_reader_stop_count[code],
                    "마지막통신응답경과초": round(
                        now - self._last_transport_activity_at[code], 3)
                    if code in self._last_transport_activity_at else None,
                    "수신기종료": code in self._finished_readers,
                }
                for code in self._channels
            }

    def _oldest_pending_parsed_age_seconds(
            self, code: str, now: float) -> float | None:
        """재연결 보류 선두의 실제 파싱 후 경과를 조회한다.

        각 보류 deque의 맨 앞만 확인하고 채팅 본문은 반환하지 않는다.
        이 값은 AI 처리시간이나 실제 서버가 보내지 않은 채팅 지연이 아니다.
        """
        heads = []
        pending = self._pending_websocket_chats.get(code)
        if pending:
            heads.append(pending[0])
        prejoin = self._prejoin_resume_states.get(code)
        if prejoin is not None and prejoin.pending:
            heads.append(prejoin.pending[0])
        if (code == "youtube" and self._youtube_resume is not None
                and self._youtube_resume.pending_page_chats):
            heads.append(self._youtube_resume.pending_page_chats[0])
        ages = []
        for item in heads:
            parsed = getattr(item, "parsed_at_monotonic", None)
            if (type(parsed) in (int, float) and math.isfinite(parsed)
                    and 0 < parsed <= now):
                ages.append(max(0.0, now - parsed))
        return round(max(ages), 6) if ages else None

    def try_reconnect_snapshot(self):
        """GUI 대기열이 많을 때 상태 잠금을 기다리지 않고 다음 주기 재시도."""
        if not self._emit_lock.acquire(blocking=False):
            return None
        try:
            return self.reconnect_snapshot()
        finally:
            self._emit_lock.release()

    def _refresh_all_ready_streak_locked(self, at: float) -> None:
        """선택한 모든 채팅 수신기의 동시 ready 관측 구간을 갱신.

        _emit_lock을 보유한 ready/연결 종료/Stop 경로에서만 호출한다.
        단순 연결 신호가 아닌 실제 ready 상태만 교집합에 포함한다.
        """
        all_ready = (
            not self._stop.is_set()
            and bool(self._room_ready)
            and all(self._room_ready.values()))
        if all_ready:
            if self._all_ready_started_at is None:
                self._all_ready_started_at = at
        elif self._all_ready_started_at is not None:
            duration = max(0.0, at - self._all_ready_started_at)
            self._all_ready_observed_seconds += duration
            self._all_ready_max_streak_seconds = max(
                self._all_ready_max_streak_seconds, duration)
            if duration >= 86400:
                self._all_ready_24h_completed_intervals += 1
            self._all_ready_started_at = None

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
        self._refresh_all_ready_streak_locked(ended_at)

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
            self._run_max_seconds = max_seconds
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
                                self._emit_status_safely(code, "error", code + " 읽기 실패 (" +
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
                                    self._emit_status_safely(code, "error", code +
                                               " 재연결 3회 이상 실패 · 수신 공백 지속 · 재시도 중")
                            if not self._stop.is_set():
                                self._emit_status_safely(code, "error", code +
                                           " 수신 연결 끊김 · 재연결 대기 중 (공백 가능)")
                            # 재연결 횟수가 커져도 거대한 정수 계산을 피한다.
                            # Twitch IRC 서버의 명시적 RECONNECT는 즉시 새 연결을
                            # 요구한다. 일반 통신 오류의 기존 1~4초 대기는 유지.
                            # 실제 채팅 무누락·1~3초 응답을 보장하지는 않는다.
                            if not isinstance(exc, TwitchServerReconnect):
                                if self._stop.wait(min(2 ** min(failures - 1, 2), 4)):
                                    break
                            # 실패한 옛 수신기는 재사용하지 않고 새 수신기만 재생성한다.
                            replacement = None
                            while replacement is None and not self._stop.is_set():
                                try:
                                    replacement = self._factories[code](
                                        self._channels[code], self._callbacks[code])
                                    if (code in self._pending_websocket_chats
                                            and hasattr(replacement, "_pending_chats")):
                                        replacement._pending_chats = (
                                            self._pending_websocket_chats[code])
                                    if code in self._prejoin_resume_states:
                                        replacement._prejoin_resume = (
                                            self._prejoin_resume_states[code])
                                except Exception as reconnect_error:
                                    if not self._stop.is_set():
                                        self._emit_status_safely(code, "error", code + " 재연결 준비 실패 (" +
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
                            self._emit_status_safely(code, "reader_stopped",
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
