"""Windows EXE OBS 5.x status probe tab. READ-ONLY, explicit button only."""
from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from .obs_readonly import get_obs_snapshot, ObsSnapshot, avatar_capture_diagnostic


class ObsStatusTab(ttk.Frame):
    def __init__(self, master: tk.Misc, *, chat_tab=None) -> None:
        super().__init__(master)
        self._chat_tab = chat_tab
        self._owned_chat_session = None
        self._scheduled_chat_token = None
        self._port=tk.StringVar(value="4455")
        self._password=tk.StringVar()
        self._status=tk.StringVar(value="연결 안 됨 · 버튼을 눌렀을 때만 내 PC의 OBS 상태를 확인합니다.")
        self._version=tk.StringVar(value="OBS 버전: 미확인")
        self._stream=tk.StringVar(value="방송 송출: 미확인")
        self._capture=tk.StringVar(value="장면을 선택해 소스 상태를 확인할 수 있어요.")
        self._events: queue.SimpleQueue[tuple[str,object]]=queue.SimpleQueue()
        self._working=False
        self._approved_scheduler = None
        self._approved_scheduler_thread = None
        self._live_schedule_status = tk.StringVar(
            value="자동 방송 시작/종료: 비활성 · 사용자 명시 승인 전에는 실제 OBS 제어 없음")
        self._schedule_minimum = tk.StringVar()
        self._schedule_maximum = tk.StringVar()
        self._schedule_closing = tk.StringVar()
        self._auto_chat_approved = tk.BooleanVar(value=False)
        self._discord_notice_approved = tk.BooleanVar(value=False)
        self._discord_webhook = tk.StringVar()
        self._discord_start_text = tk.StringVar()
        self._discord_end_text = tk.StringVar()
        ttk.Label(self,text="OBS Studio 로컬 연결 확인 (읽기 전용)",
                  font=("Malgun Gothic",12,"bold")).pack(anchor="w",pady=(4,10))
        ttk.Label(self,text="OBS가 PC에 이미 설치돼 있어야 해요. 연결 확인만 하며 방송을 시작하거나 설정을 변경하지 않습니다.",
                  wraplength=560).pack(anchor="w",pady=(0,10))
        row=ttk.Frame(self)
        row.pack(fill="x",pady=(4,5))
        ttk.Label(row,text="로컬 포트",width=13).pack(side="left")
        ttk.Entry(row,textvariable=self._port,width=12).pack(side="left")
        ttk.Label(row,text="암호",width=7).pack(side="left",padx=(15,0))
        ttk.Entry(row,textvariable=self._password,show="*",width=24).pack(side="left",fill="x",expand=True)
        ttk.Label(self,text="암호는 설정 파일에 저장하지 않습니다. 연결 요청에서만 사용합니다.",
                  wraplength=560).pack(anchor="w")
        self._button=ttk.Button(self,text="OBS 연결 상태 확인",command=self._check)
        self._button.pack(anchor="w",pady=13)
        ttk.Label(self,textvariable=self._status,wraplength=560).pack(anchor="w",pady=(0,12))
        ttk.Label(self,textvariable=self._version).pack(anchor="w",pady=2)
        ttk.Label(self,textvariable=self._stream).pack(anchor="w",pady=2)
        ttk.Label(self,text="OBS 장면 목록 (보기만 가능)").pack(anchor="w",pady=(14,5))
        self._scenes=tk.Listbox(self,height=4,activestyle="none",exportselection=False)
        self._scenes.pack(fill="both",expand=True)
        self._inspect_button=ttk.Button(
            self,text="선택 장면 소스 확인 (읽기 전용)",command=self._inspect_scene,
        )
        self._inspect_button.pack(anchor="w",pady=(8,4))
        self._inspect_button.configure(state="disabled")
        ttk.Label(self,text="선택 장면 안의 소스 · OBS에서 설정은 직접 변경").pack(anchor="w",pady=(4,3))
        self._sources=tk.Listbox(self,height=5,activestyle="none",exportselection=False)
        self._sources.pack(fill="both",expand=True)
        ttk.Label(self,textvariable=self._capture,wraplength=560).pack(anchor="w",pady=(7,2))
        ttk.Label(self,text="소스가 있다고 해서 실제 아바타 창이 캡처 중이라는 뜻은 아닙니다.",
                  wraplength=560).pack(anchor="w",pady=(2,3))
        ttk.Label(self,text="위 연결 확인은 읽기 전용입니다. 아래 예약 제어는 사용자 별도 승인과 "
                           "기존 OBS 송출 허가 환경 설정이 모두 있어야만 작동합니다.",
                  wraplength=560).pack(anchor="w",pady=(2,8))
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(5,7))
        ttk.Label(self, text="주간 일정에 따라 실제 OBS 시작·종료 (승인형, 기본 꺼짐)",
                  font=("Malgun Gothic", 11, "bold")).pack(anchor="w")
        ttk.Label(self, text="이 프로그램이 열린 동안만 작동하며, 기존에 저장한 KST 주간 일정과 "
                             "실제 공식 Live2D/한국어 GPT-SoVITS를 사용합니다. "
                             "이 기능은 방송 시작/종료만 연결합니다. 공지 자동 게시·게임 조작·시청자 "
                             "수신 1~3초 보장은 별도 개발/검증 대상입니다.",
                  wraplength=560).pack(anchor="w", pady=(3,7))
        live_row=ttk.Frame(self)
        live_row.pack(fill="x")
        ttk.Label(live_row, text="최소(분)").pack(side="left")
        ttk.Entry(live_row, textvariable=self._schedule_minimum, width=7).pack(side="left", padx=4)
        ttk.Label(live_row, text="최대(분)").pack(side="left", padx=(10,0))
        ttk.Entry(live_row, textvariable=self._schedule_maximum, width=7).pack(side="left", padx=4)
        ttk.Label(self, text="종료 인사(운영자 지정):").pack(anchor="w", pady=(6,0))
        ttk.Entry(self, textvariable=self._schedule_closing, width=64).pack(
            fill="x", pady=(1,4))
        ttk.Checkbutton(
            self, text="방송 시작 시 기존 4플랫폼 채팅·공식 AI 자동 연결 승인 (기본 해제)",
            variable=self._auto_chat_approved).pack(anchor="w", pady=(5,0))
        ttk.Checkbutton(
            self, text="디스코드 시작·종료 공지도 자동 게시 승인 (기본 해제)",
            variable=self._discord_notice_approved).pack(anchor="w", pady=(5,0))
        ttk.Label(
            self, text="승인 시에만 사용할 공식 Discord 웹훅 (파일에 저장하지 않음)"
        ).pack(anchor="w")
        ttk.Entry(self, textvariable=self._discord_webhook,
                  show="*", width=64).pack(fill="x")
        ttk.Label(self, text="방송 시작 공지(직접 지정, 자동 생성 아님)").pack(anchor="w")
        ttk.Entry(self, textvariable=self._discord_start_text).pack(fill="x")
        ttk.Label(self, text="방송 종료 공지(직접 지정, 자동 생성 아님)").pack(anchor="w")
        ttk.Entry(self, textvariable=self._discord_end_text).pack(fill="x", pady=(0,4))
        actions=ttk.Frame(self)
        actions.pack(fill="x", pady=(5,4))
        self._live_arm_button=ttk.Button(
            actions, text="저장된 일정으로 실제 방송 자동 실행 승인",
            command=self._arm_live_schedule)
        self._live_arm_button.pack(side="left")
        self._live_disarm_button=ttk.Button(
            actions, text="자동 실행 중지 / 내가 시작한 방송 종료",
            command=self._disarm_live_schedule, state="disabled")
        self._live_disarm_button.pack(side="left", padx=(8,0))
        ttk.Label(self, textvariable=self._live_schedule_status, wraplength=560).pack(
            anchor="w", pady=(2,5))
        self._scenes.bind("<<ListboxSelect>>",lambda _event:self._update_inspect_button())
        self.after(150,self._poll)

    def _approved_live_preflight(self) -> bool:
        """실제 방송 제어 직전 원래 사용자가 저장한 캐릭터·한국어 음성 점검."""
        from .offline_settings import settings_file, load_settings, active_persona
        from .official_tts_readiness import require_saved_korean_gpt_sovits
        from .original_plan_studio import inspect_saved_persona_alignment
        from . import original_plan_frontend as frontend

        model = frontend._native_viewer
        project = frontend._native_viewer_project
        settings_path = settings_file()
        if (model is None or model.poll() is not None
                or frontend._native_bridge is None or project is None
                or not settings_path.is_file() or settings_path.is_symlink()
                or settings_path.parent.is_symlink()):
            return False
        saved = active_persona(load_settings(settings_path))
        if not inspect_saved_persona_alignment(project, saved):
            return False
        require_saved_korean_gpt_sovits(project)
        return True

    def _approved_live_closing(self, words: str) -> bool:
        """기존 공식 Live2D 음성 경로에 운영자가 입력한 종료 문구만 전달."""
        from .original_plan_frontend import (
            send_to_native_live2d_session_with_observation)
        observation = send_to_native_live2d_session_with_observation(
            words, operator_approved=True, duration=8)
        return observation.verified_signal is True

    def _request_live_chat_start(self, token: object) -> bool:
        reply=queue.Queue(maxsize=1)
        self._events.put(("live_chat_start_request", (token, reply)))
        try:
            return reply.get(timeout=15) is True
        except queue.Empty:
            return False

    def _request_live_chat_stop(self) -> bool:
        reply=queue.Queue(maxsize=1)
        self._events.put(("live_chat_stop_request", (
            self._owned_chat_session, reply)))
        try:
            return reply.get(timeout=15) is True
        except queue.Empty:
            return False

    def _arm_live_schedule(self) -> None:
        """실제 방송은 사용자가 선택해 명시적으로 승인한 다음에만 허용."""
        if self._approved_scheduler_thread is not None and self._approved_scheduler_thread.is_alive():
            messagebox.showwarning("방송 예약 중", "기존 방송 예약 작업을 먼저 종료하세요.", parent=self)
            return
        try:
            from .approved_live_scheduler import ApprovedLiveScheduler
            from .offline_broadcast_schedule import load_schedule, schedule_path
            from .offline_broadcast_duration import BroadcastDurationRules

            if os.environ.get("AISTING_APPROVED_OBS_OUTGOING") != "YES":
                raise PermissionError("기존 AISTING_APPROVED_OBS_OUTGOING=YES 허가가 없습니다.")
            draft=load_schedule(schedule_path())
            if draft is None or not draft.slots:
                raise ValueError("운영자가 기존 주간 일정 탭에서 KST 일정을 저장해야 합니다.")
            selected=self._scenes.curselection()
            if not selected:
                raise ValueError("OBS 연결 상태를 확인한 뒤 실제 방송 장면을 선택해야 합니다.")
            scene=self._scenes.get(selected[0])
            minimum=int(self._schedule_minimum.get().strip())
            maximum=int(self._schedule_maximum.get().strip())
            rules=BroadcastDurationRules(minimum, maximum)
            port=int(self._port.get())
            password=self._password.get()
            closing=self._schedule_closing.get().strip()
            if not self._approved_live_preflight():
                raise ValueError("기존 공식 Live2D·저장된 캐릭터·한국어 음성이 준비되지 않았습니다.")
            auto_chat = self._auto_chat_approved.get() is True
            if auto_chat:
                source = self._chat_tab
                if (source is None or source._twitch_session is not None
                        or source._busy or source._pipeline_busy
                        or source._tts_probe_busy or source._closed
                        or source._official_live2d.get() is not True):
                    raise ValueError("실제 채팅 탭에서 공식 AI와 대기 상태를 확인하세요.")
            approval_token = object() if auto_chat else None
            discord_enabled = self._discord_notice_approved.get() is True
            on_started_notice = None
            on_finished_notice = None
            if discord_enabled:
                from .approved_discord_notice import ApprovedDiscordNoticeSender
                sender=ApprovedDiscordNoticeSender(
                    self._discord_webhook.get(), operator_approved=True)
                start_message=self._discord_start_text.get().strip()
                end_message=self._discord_end_text.get().strip()
                # 전송할 메시지는 승인 시 그대로 고정. 이후 GUI 입력을
                # 수정하더라도 승인한 다른 문구로 조용히 바뀌지 않는다.
                if (not 1 <= len(start_message) <= 2000
                        or not 1 <= len(end_message) <= 2000):
                    raise ValueError("시작·종료 공지 문구는 각각 1~2000자여야 합니다.")
                on_started_notice=lambda _occurrence: sender.send(
                    start_message, operator_approved=True)
                on_finished_notice=lambda _occurrence: sender.send(
                    end_message, operator_approved=True)
            if not messagebox.askyesno(
                "실제 자동 방송 시작·종료 최종 승인",
                "이 컴퓨터의 실제 OBS가 주간 일정에 따라 외부 플랫폼에 방송을 시작합니다. "
                "내가 직접 입력한 최소/최대 방송 시간과 종료 인사를 사용합니다. "
                "프로그램을 종료하거나 중지 버튼을 누르면 이 기능이 시작한 방송만 "
                "종료하도록 시도합니다. OBS 서버 오류 시 직접 확인이 필요합니다. "
                + ("내가 지정한 Discord 시작/종료 공지를 실제 외부 채널에 "
                   "각 1회씩 자동 게시합니다. 실패 시 자동 재게시하지 않습니다. "
                   if discord_enabled else
                   "디스코드 자동 공지는 비활성입니다. ")
                + ("선택된 기존 4플랫폼 채팅·공식 AI 읽기 전용 수신기도 "
                   "이 방송 시 자동 연결합니다. 계정 동의나 채팅 발신은 하지 않으며 "
                   "기존 공식 AI 서버 설정의 권리·외부 접속은 운영자가 확인합니다. "
                   if auto_chat else "채팅 자동 연결은 비활성입니다. ")
                + "채팅 발신은 하지 않습니다. 저장된 캐릭터와 한국어 "
                "음성에 사용 권리가 있고 실제 방송 자동 제어와 선택한 "
                "공지 전송을 승인합니까?", parent=self):
                return
            runner=ApprovedLiveScheduler(
                draft, rules, obs_password=password, obs_port=port,
                scene=scene, closing_text=closing,
                operator_approved=True, rights_confirmed=True,
                media_preflight=self._approved_live_preflight,
                deliver_closing=self._approved_live_closing,
                on_started_notice=on_started_notice,
                on_finished_notice=on_finished_notice,
                notice_approved=discord_enabled,
                begin_live_chat=(
                    (lambda token=approval_token: self._request_live_chat_start(token))
                    if auto_chat else None),
                end_live_chat=(self._request_live_chat_stop if auto_chat else None),
                chat_approved=auto_chat)
            if auto_chat:
                self._chat_tab._scheduled_chat_permission = approval_token
                self._scheduled_chat_token = approval_token
        except Exception as exc:
            # OBS credential, endpoint, exception body must not enter the GUI.
            self._live_schedule_status.set(
                "실제 방송 예약을 시작하지 않았습니다 · " + type(exc).__name__ +
                " · 일정/모델/입력/기존 송출 허가 확인 필요")
            return
        self._approved_scheduler=runner
        self._approved_scheduler_thread=threading.Thread(
            target=self._run_approved_schedule, args=(runner,),
            name="AISTING-운영자승인-실제OBS일정", daemon=False)
        self._live_arm_button.configure(state="disabled")
        self._live_disarm_button.configure(state="normal")
        self._live_schedule_status.set(
            "사용자 승인 완료 · 등록된 KST 일정 대기 · 송출 아직 시작하지 않음")
        self._approved_scheduler_thread.start()

    def _run_approved_schedule(self, runner) -> None:
        try:
            runner.run()
        except Exception as exc:
            # Do not include remote OBS URLs or credentials in error messages.
            self._events.put(("live_schedule_error", type(exc).__name__))
        finally:
            self._events.put(("live_schedule_done", None))

    def _disarm_live_schedule(self) -> None:
        if self._chat_tab is not None and self._scheduled_chat_token is not None:
            if self._chat_tab._scheduled_chat_permission is self._scheduled_chat_token:
                self._chat_tab._scheduled_chat_permission = None
        self._scheduled_chat_token = None
        runner=self._approved_scheduler
        if runner is not None:
            runner.request_stop()
            self._live_schedule_status.set(
                "실제 방송 종료 요청 · 해당 예약이 시작한 방송만 종료 확인 중")

    def _update_inspect_button(self) -> None:
        self._inspect_button.configure(
            state="normal" if not self._working and self._scenes.curselection() else "disabled"
        )

    def _inspect_scene(self) -> None:
        selected=self._scenes.curselection()
        if selected and not self._working:
            scene_name=self._scenes.get(selected[0])
            self._check(scene_name=scene_name)

    def _check(self, scene_name: str | None = None)->None:
        if self._working:
            return
        try:
            port=int(self._port.get())
            if not 1<=port<=65535:
                raise ValueError
        except ValueError:
            messagebox.showwarning("포트 확인","OBS 포트를 1~65535 정수로 입력해 주세요.",parent=self)
            return
        password=self._password.get()
        self._working=True
        self._button.configure(state="disabled")
        self._inspect_button.configure(state="disabled")
        self._status.set("내 PC의 OBS WebSocket 상태 확인 중…")
        threading.Thread(target=self._worker,args=(port,password,scene_name),daemon=True).start()

    def _worker(self,port:int,password:str,scene_name:str | None)->None:
        try:
            snapshot=get_obs_snapshot(port=port,password=password,scene_name=scene_name)
        except Exception as exc:
            self._events.put(("error",str(exc)))
        else:
            self._events.put(("ok",snapshot))
        finally:
            password=""  # 암호 로그와 로컬 설정 저장을 하지 않음.

    def _poll(self)->None:
        try:
            while True:
                kind,item=self._events.get_nowait()
                if kind=="live_chat_start_request":
                    token, reply = item
                    accepted=False
                    if (self._chat_tab is not None
                            and self._approved_scheduler is not None
                            and token is self._scheduled_chat_token):
                        try:
                            # 같은 운영자 승인으로 등록한 주간 일정의
                            # 다음 방송에서도 1회 사용 권한을 다시 발급.
                            # 다른 세션이나 수동 시작은 이 토큰을 받지 못함.
                            self._chat_tab._scheduled_chat_permission = token
                            self._chat_tab._start_twitch(scheduled_approval=token)
                            self._owned_chat_session = self._chat_tab._twitch_session
                            accepted=self._owned_chat_session is not None
                        except Exception:
                            accepted=False
                    reply.put_nowait(accepted)
                    continue
                if kind=="live_chat_stop_request":
                    session, reply = item
                    result=False
                    if (self._chat_tab is not None and session is not None
                            and self._chat_tab._twitch_session is session):
                        self._chat_tab._stop_twitch()
                        result=True
                    self._owned_chat_session=None
                    reply.put_nowait(result)
                    continue
                if kind=="live_schedule_error":
                    self._live_schedule_status.set(
                        "실제 예약 작업 오류 (" + str(item) +
                        ") · OBS가 계속 송출 중인지 직접 확인이 필요합니다.")
                    continue
                if kind=="live_schedule_done":
                    self._live_arm_button.configure(state="normal")
                    self._live_disarm_button.configure(state="disabled")
                    if self._approved_scheduler is not None:
                        snap=self._approved_scheduler.snapshot()
                        self._live_schedule_status.set(
                            snap.state + " · " + snap.detail +
                            " · 디스코드 시작 공지 " + snap.start_notice +
                            " / 종료 공지 " + snap.end_notice)
                    self._approved_scheduler=None
                    if self._chat_tab is not None and self._scheduled_chat_token is not None:
                        if self._chat_tab._scheduled_chat_permission is self._scheduled_chat_token:
                            self._chat_tab._scheduled_chat_permission=None
                    self._scheduled_chat_token=None
                    continue
                self._working=False
                self._button.configure(state="normal")
                if kind=="error":
                    self._status.set("OBS 연결 확인 실패: "+str(item))
                    self._version.set("OBS 버전: 미확인")
                    self._stream.set("방송 송출: 미확인")
                    self._scenes.delete(0,"end")
                    self._sources.delete(0,"end")
                    self._capture.set("연결 정보를 확인하지 못했습니다. 실제 OBS 설정은 변경하지 않았습니다.")
                else:
                    self._status.set("OBS 읽기 전용 연결 확인 성공")
                    self._version.set(f"OBS {item.obs_version} · WebSocket {item.websocket_version}")
                    self._stream.set("방송 송출: 진행 중" if item.streaming else "방송 송출: 꺼짐")
                    self._scenes.delete(0,"end")
                    for index,scene in enumerate(item.scenes):
                        self._scenes.insert("end",scene)
                        if scene==item.inspected_scene:
                            self._scenes.selection_set(index)
                            self._scenes.see(index)
                    self._sources.delete(0,"end")
                    for source in item.scene_items:
                        enabled="사용" if source.enabled else "꺼짐"
                        kind=source.input_kind or "기타"
                        self._sources.insert(
                            "end",f"[{enabled}] {source.source_name} · {kind} · ID {source.item_id}"
                        )
                    self._capture.set(avatar_capture_diagnostic(item))
                self._update_inspect_button()
        except queue.Empty:
            pass
        if self._approved_scheduler is not None:
            snap=self._approved_scheduler.snapshot()
            self._live_schedule_status.set(
                snap.state + " · " + snap.detail +
                " · 공지 시작 " + snap.start_notice +
                " / 종료 " + snap.end_notice +
                " · 채팅/AI " + snap.live_chat)
        self.after(150,self._poll)

    def destroy(self) -> None:
        # 사용자 GUI가 종료되면 이후의 방송 예약 시작을 확실히 차단.
        # daemon=False 작업자가 자신이 실제 시작한 OBS 송출만 종료 시도한다.
        if self._approved_scheduler is not None:
            self._approved_scheduler.request_stop()
        if self._chat_tab is not None and self._scheduled_chat_token is not None:
            if self._chat_tab._scheduled_chat_permission is self._scheduled_chat_token:
                self._chat_tab._scheduled_chat_permission = None
        if (self._chat_tab is not None and self._owned_chat_session is not None
                and self._chat_tab._twitch_session is self._owned_chat_session):
            self._chat_tab._stop_twitch()
        self._password.set("")
        self._discord_webhook.set("")
        self._discord_start_text.set("")
        self._discord_end_text.set("")
        super().destroy()
