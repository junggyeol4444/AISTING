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
        client_factory: Callable[..., OfficialObsWebsocket] = OfficialObsWebsocket,
        clock: Callable[[], float] = time.monotonic,
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
        self._on_started_notice = on_started_notice
        self._on_finished_notice = on_finished_notice
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
        self._running = False

    def snapshot(self) -> ApprovedLiveSnapshot:
        with self._lock:
            return ApprovedLiveSnapshot(
                self._state, self._detail, self._occurrence,
                self._owns_stream, self._start_confirmed,
                self._stop_confirmed, self._closing_attempted,
                self._closing_delivered_candidate, self._start_notice,
                self._end_notice)

    def request_stop(self) -> None:
        """운영자 종료 요청. 소유한 방송만 안전하게 종료하도록 작업자를 깨움."""
        self._stop.set()

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
        self._used.add(occurrence)
        self._occurrence = occurrence
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
            self._started_at = now
            self._set("실제 방송 중", "방송 송출 상태를 확인했습니다. 시청자 수신은 별도 실증입니다.")
            if self._on_started_notice is not None:
                # OBS가 실제 시작됐다는 확인 뒤에만 '시작 공지' 전송.
                # 실패 시 자동 중복 게시/방송 종료 없음. 상태는 별도 보존.
                try:
                    self._start_notice = (
                        "서버 204 확인" if self._on_started_notice(occurrence) is True
                        else "서버 완료 미확인")
                except Exception:
                    self._start_notice = "전송 실패 · 자동 재발신 없음"
        except Exception as exc:
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
                finished = client.stop_stream(operator_confirmed=True)
                if finished.streaming:
                    raise RuntimeError("OBS 방송 종료 상태가 확인되지 않았습니다.")
            self._stop_confirmed = True
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
        except Exception as exc:
            self._set("종료 확인 실패", type(exc).__name__ +
                      " · 자동 완료 기록 금지 · OBS 현재 방송 상태 수동 확인 필요")
            # Still the only stream we own; operator can use OBS itself.
        finally:
            self._stop.set()

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
            try:
                current = self._client.status()
                if current.streaming is not True or current.scene != self._scene:
                    self._set("방송 상태 이탈", "외부 OBS 종료 또는 장면 변경 · 재시작 금지")
                    self._owns_stream = False
                    self._stop.set()
                elif monotonic_now - self._started_at >= self._rules.maximum_minutes * 60:
                    self._finish_owned(normal_maximum=True)
            except Exception as exc:
                # A failing status does not prove output stopped.
                self._set("송출 상태 미확인", type(exc).__name__ +
                          " · 방송 중인지 수동 확인 필요 · 새 송출 금지")
                self._stop.set()
            return self.snapshot()
        if self._state == "예약 승인됨":
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
