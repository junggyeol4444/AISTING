"""AISTING 기존 일정/OBS를 연결하는 운영자 승인형 로컬 실제 방송 제어.

새 웹 서비스·런타임 API·백그라운드 자동 시작 없음. 기존 Windows GUI에서
매번 활성화하고 OBS 출력을 별도로 승인한 경우에만 로컬 OBS WebSocket을
사용한다. 기존 broadcast_schedule_draft.json을 절대 수정하지 않는다.

설정된 최소/최대 시간, 동일 일정 중복 실행, 녹화/장면/페르소나/공식
Live2D 준비 확인, 공식 음성 마무리 시도를 코드에서 순서대로 수행한다.
사용자 승인된 상태에서도 네트워크·OBS 장애로 라이브 송출 성공/종료가
확인되지 않으면 성공으로 세지 않는다.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from .offline_broadcast_schedule import BroadcastScheduleDraft, KST
from .offline_broadcast_duration import BroadcastDurationRules
from .original_plan_obs import OfficialObsWebsocket
from .obs_live2d_frame_link import active_official_window_capture
from .obs_stream_health import ObsStreamHealthMonitor
from .approved_obs_reconnect import (
    ApprovedObsReconnector, ObsStreamIdentityLost, ObsReconnectExhausted)


@dataclass(frozen=True)
class ApprovedLiveSnapshot:
    state: str
    detail: str
    occurrence: str | None
    owns_stream: bool
    start_confirmed: bool
    stop_confirmed: bool
    closing_attempted: bool
    closing_delivered_candidate: bool
    start_notice: str = "미설정"
    end_notice: str = "미설정"
    live_chat: str = "미설정"
    journal_error: str = ""
    pre_notice: str = "미설정"
    stream_health: str = "실제 OBS 출력 통계 미관측"
    chat_recovery: str = "채팅 자동 복구 비활성"
    obs_recovery: str = "OBS 연결 복구 비활성"
    cafe_start_notice: str = "미설정"
    cafe_end_notice: str = "미설정"


class ApprovedLiveScheduler:
    """로컬 실행 중만 유효한 운영자 승인형 주간 방송 시계/OBS 제어.

    반복 일정의 각 슬롯을 한 번만 실행한다. 리더/모델/마무리 콜백은
    호출자에게 주입받아 기존 프로세스 구성·권리 승인 상태를 그대로
    이용한다. 외부 공지나 채팅을 임의로 게시하지 않는다.
    """

    def __init__(
        self,
        draft: BroadcastScheduleDraft,
        rules: BroadcastDurationRules,
        *,
        obs_password: str,
        obs_port: int,
        scene: str,
        closing_text: str,
        operator_approved: bool = False,
        rights_confirmed: bool = False,
        media_preflight: Callable[[], bool],
        deliver_closing: Callable[[str], bool],
        on_started_notice: Callable[[str], bool] | None = None,
        on_finished_notice: Callable[[str], bool] | None = None,
        notice_approved: bool = False,
        begin_live_chat: Callable[[], bool] | None = None,
        end_live_chat: Callable[[], bool] | None = None,
        chat_approved: bool = False,
        client_factory: Callable[..., OfficialObsWebsocket] = OfficialObsWebsocket,
        clock: Callable[[], float] = time.monotonic,
        occurrence_claim: Callable[[str], bool] | None = None,
        occurrence_event: Callable[[str, str], None] | None = None,
        on_pre_notice: Callable[[str], bool] | None = None,
        pre_notice_claim: Callable[[str], bool] | None = None,
        pre_notice_lead_minutes: int = 0,
        chat_alive: Callable[[], bool] | None = None,
        chat_recovery_limit: int = 3,
        on_cafe_started: Callable[[str], bool] | None = None,
        on_cafe_finished: Callable[[str], bool] | None = None,
        cafe_notice_approved: bool = False,
    ) -> None:
        if operator_approved is not True or rights_confirmed is not True:
            raise PermissionError("운영자 방송 자동 시작/종료와 한국어 음성 권리 승인이 필요합니다.")
        if os.environ.get("AISTING_APPROVED_OBS_OUTGOING") != "YES":
            raise PermissionError(
                "실제 방송 시작/종료가 아직 별도 승인되지 않았습니다. "
                "기존 OBS 송출 보안 설정을 유지합니다.")
        if type(draft) is not BroadcastScheduleDraft or not draft.slots:
            raise ValueError("운영자가 저장한 한국 시간 주간 방송 일정이 필요합니다.")
        if type(rules) is not BroadcastDurationRules:
            raise ValueError("운영자가 지정한 최소·최대 방송 시간이 필요합니다.")
        if type(obs_password) is not str or not obs_password:
            raise ValueError("OBS의 실제 인증 암호가 필요합니다.")
        if type(obs_port) is not int or not 1 <= obs_port <= 65535:
            raise ValueError("OBS 로컬 WebSocket 포트 형식 오류")
        if (type(scene) is not str or not scene.strip()
                or any(ord(x) < 32 for x in scene) or len(scene) > 256):
            raise ValueError("실제 방송에 사용할 OBS 장면을 지정해야 합니다.")
        if (type(closing_text) is not str
                or not 1 <= len(closing_text.strip()) <= 300
                or any(ord(c) < 32 for c in closing_text)):
            raise ValueError("운영자가 확정한 방송 마무리 대사가 필요합니다.")
        if not all(callable(fn) for fn in
                   (media_preflight, deliver_closing, client_factory, clock)):
            raise ValueError("실제 방송 동작/시계 연결 함수가 필요합니다.")
        if ((on_started_notice is not None or on_finished_notice is not None)
                and notice_approved is not True):
            raise PermissionError("디스코드 외부 공지 자동 게시 별도 승인이 필요합니다.")
        if (on_started_notice is not None and not callable(on_started_notice)
                or on_finished_notice is not None and not callable(on_finished_notice)):
            raise ValueError("실제 공지 전송 함수가 올바르지 않습니다.")
        if ((begin_live_chat is not None or end_live_chat is not None)
                and chat_approved is not True):
            raise PermissionError("실제 4플랫폼 공개 채팅 AI 자동 연결 별도 승인이 필요합니다.")
        if ((begin_live_chat is None) != (end_live_chat is None)
                or begin_live_chat is not None and not callable(begin_live_chat)
                or end_live_chat is not None and not callable(end_live_chat)):
            raise ValueError("실제 채팅 시작/종료 연결이 올바르지 않습니다.")
        if on_pre_notice is not None:
            if (notice_approved is not True
                    or not callable(on_pre_notice)
                    or not callable(pre_notice_claim)
                    or type(pre_notice_lead_minutes) is not int
                    or not 10 <= pre_notice_lead_minutes <= 40):
                raise PermissionError(
                    "사전 공지는 별도 승인·10~40분 설정·영구 중복 방지 장부가 필요합니다.")
        elif pre_notice_claim is not None or pre_notice_lead_minutes != 0:
            raise ValueError("사전 공지를 사용하지 않으면 예약 설정도 비워야 합니다.")
        if chat_alive is not None and (
                chat_approved is not True or begin_live_chat is None
                or end_live_chat is None or not callable(chat_alive)):
            raise PermissionError(
                "4플랫폼 자동 복구는 이미 승인된 시작·종료·상태 확인 연결이 필요합니다.")
        if type(chat_recovery_limit) is not int or not 1 <= chat_recovery_limit <= 5:
            raise ValueError("실제 채팅 복구 횟수는 1~5회만 허용됩니다.")
        if (on_cafe_started is not None or on_cafe_finished is not None):
            if cafe_notice_approved is not True:
                raise PermissionError("네이버 카페 실제 글쓰기 별도 승인이 필요합니다.")
            if (on_cafe_started is not None and not callable(on_cafe_started)
                    or on_cafe_finished is not None and not callable(on_cafe_finished)):
                raise ValueError("네이버 카페 글쓰기 콜백이 올바르지 않습니다.")
        self._on_cafe_started = on_cafe_started
        self._on_cafe_finished = on_cafe_finished
        self._cafe_start_notice = "대기" if on_cafe_started else "미설정"
        self._cafe_end_notice = "대기" if on_cafe_finished else "미설정"
        self._chat_alive = chat_alive
        self._chat_recovery_limit = chat_recovery_limit
        self._chat_recovery_attempts = 0
        self._chat_unhealthy_since: float | None = None
        self._chat_recovery_after = 0.0
        self._chat_recovery = (
            "자동 복구 대기" if chat_alive is not None else "채팅 자동 복구 비활성")
        self._on_pre_notice = on_pre_notice
        self._pre_notice_claim = pre_notice_claim
        self._pre_notice_lead_minutes = pre_notice_lead_minutes
        self._pre_notice = "대기" if on_pre_notice is not None else "미설정"
        self._pre_notice_attempted: set[str] = set()
        self._on_started_notice = on_started_notice
        self._on_finished_notice = on_finished_notice
        self._begin_live_chat = begin_live_chat
        self._end_live_chat = end_live_chat
        self._chat_started = False
        self._live_chat = "대기" if begin_live_chat is not None else "미설정"
        self._draft = draft
        self._rules = rules
        self._password = obs_password
        self._port = obs_port
        self._scene = scene
        self._closing_text = closing_text.strip()
        self._media_preflight = media_preflight
        self._deliver_closing = deliver_closing
        self._client_factory = client_factory
        self._clock = clock
        if occurrence_claim is not None and not callable(occurrence_claim):
            raise ValueError("방송 슬롯 영구 장부 연결 함수가 올바르지 않습니다.")
        self._occurrence_claim = occurrence_claim
        if occurrence_event is not None and not callable(occurrence_event):
            raise ValueError("방송 결과 영구 장부 연결 함수가 올바르지 않습니다.")
        self._occurrence_event = occurrence_event
        self._journal_error = ""
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._used: set[str] = set()
        self._state = "예약 승인됨"
        self._detail = "등록된 방송 시각에 실제 OBS 상태·공식 Live2D를 확인합니다."
        self._occurrence: str | None = None
        self._owns_stream = False
        self._started_at: float | None = None
        self._last_tick: float | None = None
        self._start_confirmed = False
        self._stop_confirmed = False
        self._closing_attempted = False
        self._closing_delivered_candidate = False
        self._start_notice = "대기" if on_started_notice is not None else "미설정"
        self._end_notice = "대기" if on_finished_notice is not None else "미설정"
        self._client = None
        self._health_monitor = ObsStreamHealthMonitor()
        self._obs_reconnector: ApprovedObsReconnector | None = None
        self._obs_recovery = "승인된 방송 시작 전 · OBS 연결 복구 대기"
        self._last_health_observation: float | None = None
        self._health_event_recorded: set[str] = set()
        self._running = False

    def snapshot(self) -> ApprovedLiveSnapshot:
        with self._lock:
            return ApprovedLiveSnapshot(
                self._state, self._detail, self._occurrence,
                self._owns_stream, self._start_confirmed,
                self._stop_confirmed, self._closing_attempted,
                self._closing_delivered_candidate, self._start_notice,
                self._end_notice, self._live_chat, self._journal_error,
                self._pre_notice,
                self._health_monitor.snapshot().description,
                self._chat_recovery, self._obs_recovery,
                self._cafe_start_notice, self._cafe_end_notice)

    def _record_event(self, state: str) -> None:
        """영구 상태 기록 실패가 이미 진행 중인 OBS 종료를 막지 않게 한다."""
        if self._occurrence_event is None or self._occurrence is None:
            return
        try:
            self._occurrence_event(self._occurrence, state)
        except Exception:
            self._journal_error = (
                "방송 시작/종료 결과의 영구 기록 실패 · 실제 OBS 상태 수동 확인 필요")

    def request_stop(self) -> None:
        """운영자 종료 요청. 소유한 방송만 안전하게 종료하도록 작업자를 깨움."""
        self._stop.set()

    def _maybe_pre_notice(self, now: datetime) -> None:
        """운영자가 승인한 다음 KST 방송 전에만 디스코드 공지 요청.

        실제 게시보다 먼저 SQLite 유일 슬롯을 커밋한다. 앱 재시작,
        HTTP 요청 응답 분실, 네트워크 중단 뒤 중복 발송하지 않는다.
        방송과 공지를 보지 못한 경우에도 발신 성공으로 세지 않는다.
        """
        if self._on_pre_notice is None or self._stop.is_set() or self._owns_stream:
            return
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ValueError("사전 공지 시계에 시간대가 없습니다.")
        kst = now.astimezone(KST)
        lead = timedelta(minutes=self._pre_notice_lead_minutes)
        upcoming = self._draft.upcoming(kst - lead - timedelta(seconds=1), limit=1)
        if not upcoming:
            return
        scheduled = upcoming[0]
        delta = (scheduled - kst).total_seconds()
        if not 0 < delta <= self._pre_notice_lead_minutes * 60:
            return
        occurrence = scheduled.strftime("%Y-%m-%d %H:%M KST")
        if occurrence in self._pre_notice_attempted:
            return
        self._pre_notice_attempted.add(occurrence)
        try:
            if self._pre_notice_claim(occurrence) is not True:
                self._pre_notice = "기존 실행에서 시도한 슬롯 · 중복 게시 차단"
                return
        except Exception:
            self._pre_notice = "SQLite 사전 공지 장부 기록 실패 · 게시 차단"
            return
        try:
            self._pre_notice = (
                "서버 204 확인"
                if self._on_pre_notice(occurrence) is True
                else "서버 완료 미확인 · 자동 재게시 없음")
        except Exception:
            self._pre_notice = "전송 실패 · 자동 재게시 없음"

    def _due_occurrence(self, now: datetime) -> str | None:
        if (not isinstance(now, datetime) or now.tzinfo is None
                or now.utcoffset() is None):
            raise ValueError("실제 방송 시각은 시간대를 포함해야 합니다.")
        kst = now.astimezone(KST)
        candidate = kst.strftime("%H:%M")
        if not any(slot.weekday == kst.weekday() and slot.start_time == candidate
                   for slot in self._draft.slots):
            return None
        occurrence = kst.strftime("%Y-%m-%d %H:%M KST")
        return occurrence if occurrence not in self._used else None

    def _set(self, state: str, detail: str) -> None:
        with self._lock:
            self._state, self._detail = state, detail

    def _close_client(self) -> None:
        client = self._client
        self._client = None
        if client is not None:
            inner = getattr(client, "_client", None)
            disconnect = getattr(inner, "disconnect", None)
            if callable(disconnect):
                try:
                    disconnect()
                except Exception:
                    pass

    def _start(self, occurrence: str, now: float) -> None:
        # Consume the slot BEFORE any external side effect; a failed attempt
        # never starts another stream automatically in the same minute.
        # 메모리 중복 방지 외에 실제 GUI가 주입한 SQLite 장부에서
        # 시작 시각을 먼저 원자적으로 청구한다. 정상 커밋 뒤에만
        # OBS를 건드리며 재시작/다른 앱 창의 같은 분 중복 실행을 막는다.
        if self._occurrence_claim is not None:
            try:
                if self._occurrence_claim(occurrence) is not True:
                    self._used.add(occurrence)
                    self._set(
                        "예약 승인됨",
                        "이번 KST 슬롯은 이전 실행 또는 다른 창에서 이미 "
                        "시도했습니다. 재송출하지 않고 다음 등록 일정을 기다립니다.")
                    return
            except Exception:
                # 기록 불능 때 방송을 먼저 시작하면 중복송출을 피할 수 없다.
                self._set(
                    "방송 장부 확인 실패",
                    "영구 슬롯 예약을 확정하지 못해 송출을 차단했습니다. "
                    "로컬 장부와 OBS 상태를 수동으로 확인하세요.")
                self._stop.set()
                return
        self._used.add(occurrence)
        self._occurrence = occurrence
        self._journal_error = ""
        # 다음 주간 슬롯의 결과는 이전 방송과 분리하고
        # 성공·실패 기록을 이번 슬롯의 관측값으로 새로 시작한다.
        self._start_confirmed = False
        self._stop_confirmed = False
        self._closing_attempted = False
        self._closing_delivered_candidate = False
        self._start_notice = "대기" if self._on_started_notice else "미설정"
        self._end_notice = "대기" if self._on_finished_notice else "미설정"
        self._cafe_start_notice = "대기" if self._on_cafe_started else "미설정"
        self._cafe_end_notice = "대기" if self._on_cafe_finished else "미설정"
        self._live_chat = "대기" if self._begin_live_chat else "미설정"
        self._health_monitor = ObsStreamHealthMonitor()
        self._obs_reconnector = None
        self._obs_recovery = "방송 시작 전 · OBS 연결 복구 대기"
        self._last_health_observation = None
        self._health_event_recorded.clear()
        self._chat_recovery_attempts = 0
        self._chat_unhealthy_since = None
        self._chat_recovery_after = 0.0
        self._chat_recovery = (
            "자동 복구 대기" if self._chat_alive is not None
            else "채팅 자동 복구 비활성")
        self._set("방송 시작 준비", "OBS 현재 장면·녹화·공식 Live2D·실제 음성 구성을 확인합니다.")
        try:
            if self._media_preflight() is not True:
                raise RuntimeError("공식 아바타·음성·캐릭터 실사용 준비가 확인되지 않았습니다.")
            client = self._client_factory(self._password, port=self._port)
            self._client = client
            current = client.connect()
            if current.streaming or current.scene != self._scene:
                raise RuntimeError("OBS가 이미 방송 중이거나 선택한 장면이 변경되었습니다.")
            recording = client._client.get_record_status().output_active
            if type(recording) is not bool or recording:
                raise RuntimeError("OBS 녹화가 활성화되어 있거나 상태가 불명확합니다.")
            path = client.read_scene_media_path()
            if (path.problems or not active_official_window_capture(path.capture_sources)
                    or not path.audio_sources):
                raise RuntimeError("OBS 공식 Live2D 화면·음성 입력 경로가 유효하지 않습니다.")
            # Existing OBS outbound gate checks operator_confirmed and env.
            started = client.start_stream(operator_confirmed=True)
            if started.streaming is not True or started.scene != self._scene:
                raise RuntimeError("OBS 실제 방송 시작 후 장면/송출 상태 확인 실패")
            self._owns_stream = True
            self._start_confirmed = True
            self._record_event("송출시작확인")
            self._started_at = now
            self._obs_reconnector = ApprovedObsReconnector(
                scene=self._scene, started_monotonic=now,
                password=self._password, port=self._port,
                client_factory=self._client_factory)
            self._obs_recovery = "실제 송출 확인 · OBS 연결 정상"
            self._set("실제 방송 중", "방송 송출 상태를 확인했습니다. 시청자 수신은 별도 실증입니다.")
            if self._begin_live_chat is not None:
                # OBS 실제 송출 확인 뒤, 사용자가 별도로 승인한 기존
                # 4플랫폼 공개 채팅/공식 AI 세션을 GUI에서 시작 요청한다.
                try:
                    if self._begin_live_chat() is not True:
                        raise RuntimeError("자동 실제 채팅 시작 상태 미확인")
                    self._chat_started = True
                    self._live_chat = "연결 요청 접수 · 서버 입장 미검증"
                except Exception:
                    self._live_chat = "실제 채팅 준비 실패 · OBS 종료 요청"
                    self._finish_owned(normal_maximum=False)
                    raise RuntimeError("실제 채팅 연결 실패 · 임의로 무음 방송 유지 금지") from None
            if self._on_started_notice is not None:
                # OBS가 실제 시작됐다는 확인 뒤에만 '시작 공지' 전송.
                # 실패 시 자동 중복 게시/방송 종료 없음. 상태는 별도 보존.
                try:
                    self._start_notice = (
                        "서버 204 확인" if self._on_started_notice(occurrence) is True
                        else "서버 완료 미확인")
                except Exception:
                    self._start_notice = "전송 실패 · 자동 재발신 없음"
            if self._on_cafe_started is not None:
                # 방송 시작 실제 확인 뒤에만 네이버 카페 독립 발신.
                # 콜백 내부 SQLite에서 HTTP 이전 슬롯을 청구한다.
                try:
                    self._cafe_start_notice = (
                        "공식 API 게시 확인"
                        if self._on_cafe_started(occurrence) is True
                        else "기존 시도/서버 확인 불가 · 자동 재게시 없음")
                except Exception:
                    self._cafe_start_notice = "전송 불명 · 자동 재게시 없음"
        except Exception as exc:
            # 송출 시작을 실제 확인한 뒤 채팅 연결이 실패한 경우에는
            # 이미 기록한 시작 성공·소유 방송 종료 결과를 보존한다.
            if not self._start_confirmed:
                self._record_event("송출시작실패")
            # A failed request might have reached OBS before a connection
            # dropped: never blindly stop or claim ownership of that stream.
            self._set("시작 확인 실패", type(exc).__name__ +
                      " · 같은 슬롯 재시도 금지 · OBS 실제 송출 상태 수동 확인 필요")
            self._stop.set()

    def _finish_owned(self, *, normal_maximum: bool) -> None:
        if not self._owns_stream:
            return
        self._set("방송 마무리", "운영자가 지정한 종료 대사와 OBS 실제 상태를 확인합니다.")
        if normal_maximum:
            self._closing_attempted = True
            try:
                self._closing_delivered_candidate = (
                    self._deliver_closing(self._closing_text) is True)
            except Exception:
                self._closing_delivered_candidate = False
        # 자동 공개 채팅을 실제 이 방송에서 시작한 경우만 Stop한다.
        # 실패하더라도 OBS 실제 종료를 건너뛰지 않는다.
        if self._chat_started and self._end_live_chat is not None:
            try:
                self._live_chat = (
                    "수신 종료 요청" if self._end_live_chat() is True
                    else "수신 종료 확인 실패 · 별도 확인 필요")
            except Exception:
                self._live_chat = "수신 종료 오류 · 별도 확인 필요"
            self._chat_started = False
        # Never keep streaming forever after a requested Stop or maximum time,
        # even if the closing voice failed; but never touch a stream we didn't own.
        try:
            client = self._client
            if client is None:
                raise RuntimeError("이 방송을 시작한 OBS 연결이 없습니다.")
            actual = client.status()
            if actual.scene != self._scene:
                raise RuntimeError("방송 중 OBS 장면이 변경되어 자동 종료를 차단합니다.")
            if actual.streaming:
                # 이전에 승인해 시작한 출력의 가동시간이 연속된 경우에만
                # OBS 종료 명령을 보낸다. 새로 시작된 타인 방송은 종료 금지.
                if self._obs_reconnector is not None:
                    self._obs_reconnector.verify_stream_identity(
                        client, self._clock())
                finished = client.stop_stream(operator_confirmed=True)
                if finished.streaming:
                    raise RuntimeError("OBS 방송 종료 상태가 확인되지 않았습니다.")
            self._stop_confirmed = True
            self._record_event("송출종료확인")
            self._owns_stream = False
            self._set("실제 방송 종료", "OBS 종료 확인 · 외부 플랫폼 수신은 별도 확인")
            if self._on_finished_notice is not None:
                # 원래 내가 시작한 OBS 방송 종료가 확인된 뒤에만 게시.
                try:
                    self._end_notice = (
                        "서버 204 확인"
                        if self._on_finished_notice(self._occurrence) is True
                        else "서버 완료 미확인")
                except Exception:
                    self._end_notice = "전송 실패 · 자동 재발신 없음"
            if self._on_cafe_finished is not None:
                # 내가 소유한 OBS 종료 확인 뒤에만 카페 종료 글 발신.
                try:
                    self._cafe_end_notice = (
                        "공식 API 게시 확인"
                        if self._on_cafe_finished(self._occurrence) is True
                        else "기존 시도/서버 확인 불가 · 자동 재게시 없음")
                except Exception:
                    self._cafe_end_notice = "전송 불명 · 자동 재게시 없음"
        except Exception as exc:
            self._record_event("송출종료실패")
            self._set("종료 확인 실패", type(exc).__name__ +
                      " · 자동 완료 기록 금지 · OBS 현재 방송 상태 수동 확인 필요")
            # Still the only stream we own; operator can use OBS itself.
        finally:
            if normal_maximum and self._stop_confirmed and not self._stop.is_set():
                # 예약을 사용자가 취소하지 않았다면 다음 주간 슬롯도
                # 같은 승인 기간에 실행한다. 본인 소유 이전 OBS 연결
                # 하나만 종료하고 다른 소유자의 방송은 제어하지 않는다.
                self._close_client()
                self._started_at = None
                self._set("예약 승인됨",
                          "이번 실제 방송 종료 확인 · 다음 등록 KST 시작 일정 대기")
            else:
                # 수동 Stop·불확실한 OBS 상태·출력 실패는 안전을 위해
                # 자동 재시작을 막고 운영자가 현재 방송을 직접 확인한다.
                self._stop.set()

    def _recover_live_chat_if_needed(self, monotonic_now: float) -> None:
        """이미 승인된 동일 방송의 공개 채팅 수신기만 제한적으로 재연결.

        기존 SQLite FIFO는 수신기가 아니라 GUI의 영구 큐가 보유한다.
        읽기 소켓이 죽었다고 OBS 방송을 다시 시작하거나 같은 슬롯을
        재청구하지 않는다. 복구 실패 후 무음 방송을 무제한 유지하지 않는다.
        """
        if (self._chat_alive is None or self._begin_live_chat is None
                or self._stop.is_set() or not self._owns_stream):
            return
        try:
            healthy = self._chat_alive() is True
        except Exception:
            healthy = False
        if healthy:
            self._chat_unhealthy_since = None
            self._chat_recovery = (
                f"채팅 수신기 연결 유지 · 복구 {self._chat_recovery_attempts}회 시도")
            return
        if self._chat_unhealthy_since is None:
            self._chat_unhealthy_since = monotonic_now
            self._chat_recovery = "채팅 수신기 종료 의심 · 15초 연속 상태 확인"
            return
        if (monotonic_now - self._chat_unhealthy_since < 15.0
                or monotonic_now < self._chat_recovery_after):
            return
        if self._chat_recovery_attempts >= self._chat_recovery_limit:
            self._chat_recovery = "채팅 자동 복구 횟수 소진 · 승인 방송 종료 요청"
            self._finish_owned(normal_maximum=False)
            self._stop.set()
            return
        self._chat_recovery_attempts += 1
        self._chat_recovery_after = monotonic_now + 30.0
        self._chat_recovery = (
            f"기존 채팅 세션 재연결 {self._chat_recovery_attempts}/"
            f"{self._chat_recovery_limit}회 요청")
        # GUI 콜백은 같은 승인 토큰의 세션만 종료/재시작할 수 있다.
        # 기존 AI 작업자가 완전히 종료되지 않았다면 다음 30초까지
        # 대기하고 절대 임의로 새 FIFO 소유권을 탈취하지 않는다.
        if self._chat_started:
            try:
                ended = self._end_live_chat() is True
            except Exception:
                ended = False
        else:
            # 직전 재연결 실패로 실제 소유 세션이 없으면
            # 종료 콜백을 다시 호출하지 않고 기존 승인으로 재연결한다.
            ended = True
        self._chat_started = False
        if not ended:
            self._chat_recovery = "기존 채팅 종료 미확인 · 재연결 보류"
            self._chat_started = True
            return
        try:
            restarted = self._begin_live_chat() is True
        except Exception:
            restarted = False
        self._chat_started = restarted
        if restarted:
            self._chat_unhealthy_since = None
            self._chat_recovery = "기존 승인 채팅 재연결 요청 접수 · 서버 입장 미확인"
        else:
            # 다음 복구 시도에서 실제 소유 세션이 없음을 유지한다.
            self._chat_recovery = "채팅 재연결 미확인 · 30초 뒤 제한 재시도"

    def tick(self, now: datetime, monotonic_now: float) -> ApprovedLiveSnapshot:
        """한 번의 실제 시각 점검. GUI 스레드가 아닌 작업자에서만 호출."""
        if type(monotonic_now) not in (int, float) or not 0 <= monotonic_now < float("inf"):
            raise ValueError("운영 시계가 올바르지 않습니다.")
        if self._last_tick is not None and monotonic_now < self._last_tick:
            raise RuntimeError("운영 시계가 역행하여 방송 판단을 중단합니다.")
        self._last_tick = float(monotonic_now)
        if self._stop.is_set():
            self._finish_owned(normal_maximum=False)
            return self.snapshot()
        if self._owns_stream:
            status_failed = False
            try:
                try:
                    current = self._client.status()
                except Exception:
                    status_failed = True
                    raise
                if current.streaming is not True or current.scene != self._scene:
                    # 실제 OBS 상태 이탈은 단순 GUI 문구로만 남기지 않고
                    # 승인된 방송 슬롯의 기존 영구 사건 장부에도 기록한다.
                    # 송출을 다시 시작하거나 다른 소유자의 방송을 종료하지 않는다.
                    self._record_event(
                        "OBS송출예기치않은중단"
                        if current.streaming is not True else "OBS장면변경감지")
                    self._set("방송 상태 이탈", "외부 OBS 종료 또는 장면 변경 · 재시작 금지")
                    self._owns_stream = False
                    self._stop.set()
                else:
                    # 승인된 기존 OBS 연결만 읽어 5초 간격 실제
                    # 프레임/혼잡/재연결 통계를 메모리에 갱신한다.
                    # 관찰 오류만으로 사용자 방송을 임의 종료하지 않는다.
                    if (self._last_health_observation is None or
                            monotonic_now - self._last_health_observation >= 5.0):
                        observed = self._health_monitor.observe(
                            self._client, monotonic_now=monotonic_now)
                        self._last_health_observation = monotonic_now
                        # 기존 승인형 방송 슬롯에서 실제 OBS가 보고한 위험만
                        # 최초 1회 기존 SQLite 사건 장부에 기록한다.
                        # 경고 관측만으로 방송/녹화/장면을 임의 변경하지 않는다.
                        for warning in observed.warning_codes:
                            if warning not in self._health_event_recorded:
                                self._health_event_recorded.add(warning)
                                self._record_event(warning)
                    self._recover_live_chat_if_needed(monotonic_now)
                    if (self._owns_stream and not self._stop.is_set()
                            and monotonic_now - self._started_at
                            >= self._rules.maximum_minutes * 60):
                        self._finish_owned(normal_maximum=True)
            except Exception as exc:
                if status_failed and self._obs_reconnector is not None:
                    # OBS 출력이 계속 진행 중일 수 있으므로 무조건 송출을
                    # 재시작하거나 즉시 종료하지 않고 동일 출력만 재연결.
                    if not self._obs_reconnector.snapshot().recovering:
                        self._record_event("OBS상태관측실패")
                    try:
                        candidate = self._obs_reconnector.recover(monotonic_now)
                    except ObsStreamIdentityLost:
                        self._record_event("OBS송출소유권상실")
                        self._obs_recovery = (
                            "출력 가동시간·장면 불연속 · 타 방송 소유권 보호")
                        self._set("OBS 소유권 상실",
                                  "다른 방송일 수 있어 자동 송출/종료 차단 · 수동 확인")
                        self._owns_stream = False
                        self._stop.set()
                    except ObsReconnectExhausted:
                        self._record_event("OBS연결복구실패")
                        self._obs_recovery = "OBS 연결 복구 한도 소진 · 송출 상태 불명"
                        self._set("OBS 연결 복구 중단",
                                  "현재 OBS 송출 여부 미확인 · 새 송출/종료 금지 · 수동 확인")
                        self._owns_stream = False
                        self._stop.set()
                    else:
                        if candidate is not None:
                            old = self._client
                            self._client = candidate
                            self._obs_reconnector.reset()
                            self._last_health_observation = None
                            self._obs_recovery = (
                                "기존 OBS WebSocket 재연결 완료 · 같은 출력 가동시간 확인")
                            self._record_event("OBS연결복구확인")
                            ApprovedObsReconnector._close(old)
                            self._set("실제 방송 중",
                                      "기존 송출 유지 상태에서 OBS 연결만 복구 · 재송출 없음")
                        else:
                            self._obs_recovery = self._obs_reconnector.snapshot().status
                            self._set("OBS 연결 복구 대기",
                                      "송출 상태 불명 · 기존 승인 출력만 제한 재연결 시도")
                    return self.snapshot()
                # 관측 실패는 실제 종료와 구분하여 기록한다.
                # OBS 상태가 불명확하므로 재시작/임의 종료는 수행하지 않는다.
                self._record_event("OBS상태관측실패")
                # A failing status does not prove output stopped.
                self._set("송출 상태 미확인", type(exc).__name__ +
                          " · 방송 중인지 수동 확인 필요 · 새 송출 금지")
                self._stop.set()
            return self.snapshot()
        if self._state == "예약 승인됨":
            self._maybe_pre_notice(now)
            slot = self._due_occurrence(now)
            if slot is not None:
                self._start(slot, monotonic_now)
        return self.snapshot()

    def run(self, *, interval_seconds: float = 1.0) -> None:
        """사용자가 GUI에서 활성화한 뒤에만 시작하는 Windows 로컬 작업자."""
        if (type(interval_seconds) not in (float, int)
                or not 0.2 <= interval_seconds <= 5):
            raise ValueError("실제 방송 점검 간격이 올바르지 않습니다.")
        with self._lock:
            if self._running:
                raise RuntimeError("방송 예약 작업자를 중복 실행할 수 없습니다.")
            self._running = True
        try:
            while not self._stop.is_set():
                self.tick(datetime.now(KST), self._clock())
                self._stop.wait(interval_seconds)
            # When Stop requested during active stream, only this owned
            # broadcast may be ended. The caller can also end it manually.
            if self._owns_stream:
                self._finish_owned(normal_maximum=False)
        finally:
            self._close_client()
            self._password = ""
            with self._lock:
                self._running = False
