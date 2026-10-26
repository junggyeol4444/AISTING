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
        # 방송 스레드에서 갱신하는 문자열; Tk 위젯은 GUI 스레드에서만 변경.
        self._approved_chat_health_detail = "채팅 연결 미시작 · 실제 서버 입장 미확인"
        self._scheduled_chat_token = None
        self._port=tk.StringVar(value="4455")
        self._password=tk.StringVar()
        self._status=tk.StringVar(value="연결 안 됨 · 버튼을 눌렀을 때만 내 PC의 OBS 상태를 확인합니다.")
        self._version=tk.StringVar(value="OBS 버전: 미확인")
        self._stream=tk.StringVar(value="방송 송출: 미확인")
        self._capture=tk.StringVar(value="장면을 선택해 소스 상태를 확인할 수 있어요.")
        self._events: queue.SimpleQueue[tuple[str,object]]=queue.SimpleQueue()
        self._working=False
        self._vision_busy=False
        self._game_runner=None
        self._game_worker=None
        self._game_title=tk.StringVar()
        self._game_goal=tk.StringVar()
        self._game_steps=tk.StringVar(value="10")
        self._game_progress_interval=tk.StringVar(value="3")
        self._game_status=tk.StringVar(value="게임 자동 조작: 비활성 · 별도 승인 필요")
        self._vision_status=tk.StringVar(
            value="게임 화면 이해: 미실행 · 사용자 승인 전에는 실제 화면 읽지 않음")
        self._approved_scheduler = None
        self._approved_scheduler_thread = None
        self._live_schedule_status = tk.StringVar(
            value="자동 방송 시작/종료: 비활성 · 사용자 명시 승인 전에는 실제 OBS 제어 없음")
        self._schedule_minimum = tk.StringVar()
        self._schedule_maximum = tk.StringVar()
        self._schedule_closing = tk.StringVar()
        self._auto_chat_approved = tk.BooleanVar(value=False)
        self._auto_content_approved = tk.BooleanVar(value=False)
        self._auto_content_interval = tk.StringVar(value="300")
        self._approved_content_settings = None
        self._discord_notice_approved = tk.BooleanVar(value=False)
        self._discord_webhook = tk.StringVar()
        self._discord_start_text = tk.StringVar()
        self._discord_end_text = tk.StringVar()
        self._cafe_notice_approved = tk.BooleanVar(value=False)
        self._cafe_club_id = tk.StringVar()
        self._cafe_menu_id = tk.StringVar()
        self._cafe_access_token = tk.StringVar()
        self._cafe_start_title = tk.StringVar()
        self._cafe_start_body = tk.StringVar()
        self._cafe_end_title = tk.StringVar()
        self._cafe_end_body = tk.StringVar()
        self._discord_pre_approved = tk.BooleanVar(value=False)
        self._discord_pre_lead = tk.StringVar()
        self._discord_pre_text = tk.StringVar()
        self._notice_ai_busy = False
        self._notice_ai_status = tk.StringVar(
            value="로컬 공지 AI 미실행 · 생성된 공지는 자동 게시하지 않습니다.")
        self._notice_topic = tk.StringVar()
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
        self._vision_button=ttk.Button(
            self, text="현재 OBS 화면을 내 로컬 시각 AI로 이해 (검토만)",
            command=self._start_game_vision)
        self._vision_button.pack(anchor="w", pady=(1,2))
        ttk.Label(self, textvariable=self._vision_status,
                  wraplength=560).pack(anchor="w", pady=(0,3))
        ttk.Label(self, text="게임 자율 진행: OBS 실제 화면 → 기존 로컬 AI 판단 → "
                  "선택한 Windows 게임 창만 조작 (기본 꺼짐)",
                  wraplength=560).pack(anchor="w", pady=(4,2))
        ttk.Label(self, text="Windows 게임 창 제목 (정확히 일치)").pack(anchor="w")
        ttk.Entry(self, textvariable=self._game_title, width=64).pack(fill="x")
        ttk.Label(self, text="운영자가 지정한 게임 목표").pack(anchor="w")
        ttk.Entry(self, textvariable=self._game_goal, width=64).pack(fill="x")
        game_row=ttk.Frame(self)
        game_row.pack(fill="x", pady=(3,2))
        ttk.Label(game_row, text="최대 행동 수 (1~100)").pack(side="left")
        ttk.Entry(game_row, textvariable=self._game_steps, width=7).pack(
            side="left", padx=(4,8))
        ttk.Label(game_row, text="목표 진행 판정 간격 (1~10)").pack(side="left")
        ttk.Entry(game_row, textvariable=self._game_progress_interval,
                  width=5).pack(side="left", padx=(4,8))
        self._game_start_button=ttk.Button(
            game_row, text="게임 자동 진행 별도 승인 후 시작",
            command=self._start_approved_game)
        self._game_start_button.pack(side="left")
        self._game_stop_button=ttk.Button(
            game_row, text="게임 조작 즉시 중지 요청",
            command=self._stop_approved_game, state="disabled")
        self._game_stop_button.pack(side="left", padx=(5,0))
        game_history_row=ttk.Frame(self)
        game_history_row.pack(fill="x", pady=(2,1))
        ttk.Button(
            game_history_row, text="게임 목표·행동 영구 기록 보기 (읽기 전용)",
            command=self._show_game_goal_history).pack(side="left")
        self._game_resume_button=ttk.Button(
            game_history_row, text="동일 목표 지난 기록 참고해 새 승인으로 이어하기",
            command=self._resume_approved_game)
        self._game_resume_button.pack(side="left", padx=(5,0))
        ttk.Button(
            game_history_row, text="AI 목표후보 운영자 직접 확인/미확인 기록",
            command=self._confirm_game_goal_candidate).pack(side="left", padx=(5,0))
        ttk.Label(self, textvariable=self._game_status, wraplength=560).pack(
            anchor="w", pady=(1,5))
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
            self, text="승인한 방송 주제로 무채팅 중 자율 콘텐츠 진행 "
                 "(공식 AI·채팅 자동 연결 필수 · 기본 해제)",
            variable=self._auto_content_approved).pack(anchor="w", pady=(4,0))
        content_row = ttk.Frame(self)
        content_row.pack(fill="x", pady=(2,0))
        ttk.Label(content_row, text="콘텐츠 간격(초, 60~3600)").pack(side="left")
        ttk.Entry(content_row, textvariable=self._auto_content_interval,
                  width=8).pack(side="left", padx=(5,0))
        ttk.Button(
            self, text="지난 자율 콘텐츠 발화 시도·전달 기록 보기 (읽기 전용)",
            command=self._show_live_content_history).pack(anchor="w", pady=(2,0))
        ttk.Label(self, text="운영자가 승인할 방송 주제 (줄마다 1개, 1~30개):").pack(
            anchor="w", pady=(3,0))
        self._auto_content_topics = tk.Text(self, height=3, wrap="word")
        self._auto_content_topics.pack(fill="x", pady=(1,2))
        ttk.Label(self, text="시청자 채팅과 SQLite 미처리 채팅이 우선이며 "
                  "주제별 질문을 공식 AI에 전달합니다. "
                  "방송·시청자 수신과 실제 콘텐츠 품질은 별도 확인 대상입니다.",
                  wraplength=560).pack(anchor="w", pady=(1,3))
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
        ttk.Checkbutton(
            self, text="방송 시작 전 사전 공지도 별도 승인 (기본 해제)",
            variable=self._discord_pre_approved).pack(anchor="w", pady=(2,0))
        pre_row = ttk.Frame(self)
        pre_row.pack(fill="x")
        ttk.Label(pre_row, text="시작 전 몇 분(10~40)").pack(side="left")
        ttk.Entry(pre_row, textvariable=self._discord_pre_lead,
                  width=6).pack(side="left", padx=(5,0))
        ttk.Label(self, text="사전 공지 문구 (직접 입력·승인):").pack(anchor="w")
        ttk.Entry(self, textvariable=self._discord_pre_text).pack(fill="x")
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(5,4))
        ttk.Checkbutton(
            self, text="네이버 카페 공식 API 시작·종료 공지 자동 게시 별도 승인 "
                 "(기본 해제 · 실제 방송 확인 후에만)",
            variable=self._cafe_notice_approved).pack(anchor="w", pady=(3,2))
        cafe_ids = ttk.Frame(self)
        cafe_ids.pack(fill="x")
        ttk.Label(cafe_ids, text="카페 clubid").pack(side="left")
        ttk.Entry(cafe_ids, textvariable=self._cafe_club_id, width=14).pack(
            side="left", padx=(4,10))
        ttk.Label(cafe_ids, text="일반 게시판 menuid").pack(side="left")
        ttk.Entry(cafe_ids, textvariable=self._cafe_menu_id, width=12).pack(
            side="left", padx=4)
        ttk.Label(self, text="네이버 로그인 카페 글쓰기 권한 OAuth 접근 토큰 "
                  "(직접 발급·현재 실행 중 메모리만 · 자동 로그인/갱신 없음)").pack(anchor="w")
        ttk.Entry(self, textvariable=self._cafe_access_token,
                  show="*", width=64).pack(fill="x")
        ttk.Label(self, text="카페 시작 공지 제목·본문 (직접 지정)").pack(anchor="w")
        ttk.Entry(self, textvariable=self._cafe_start_title).pack(fill="x")
        ttk.Entry(self, textvariable=self._cafe_start_body).pack(fill="x")
        ttk.Label(self, text="카페 종료 공지 제목·본문 (직접 지정)").pack(anchor="w")
        ttk.Entry(self, textvariable=self._cafe_end_title).pack(fill="x")
        ttk.Entry(self, textvariable=self._cafe_end_body).pack(fill="x")
        ttk.Button(
            self, text="지난 네이버 카페 공지 시도·서버 확인 기록 보기 (읽기 전용)",
            command=self._show_cafe_notice_history).pack(anchor="w", pady=(2,3))
        ttk.Label(self, text="카페 게시글은 실제 외부 게시입니다. 승인하지 않으면 "
                  "어떤 API 요청도 보내지 않습니다. 응답 불명/실패 시 자동 재게시 금지.",
                  wraplength=560).pack(anchor="w", pady=(0,3))
        ttk.Label(self, text="AI 공지 문구 생성용 방송 주제 (운영자 입력)").pack(anchor="w")
        ttk.Entry(self, textvariable=self._notice_topic).pack(fill="x")
        self._notice_ai_button = ttk.Button(
            self, text="현재 로컬 AI로 시작·종료 공지 2개 작성 (검토만)",
            command=self._compose_local_notice_ai)
        self._notice_ai_button.pack(anchor="w", pady=(3,1))
        ttk.Label(self, textvariable=self._notice_ai_status, wraplength=560).pack(
            anchor="w", pady=(0,4))
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
        ttk.Button(self, text="지난 방송 시작·종료 시도 기록 조회 (읽기 전용)",
                   command=self._show_live_history).pack(anchor="w", pady=(3,2))
        ttk.Label(self, textvariable=self._live_schedule_status, wraplength=560).pack(
            anchor="w", pady=(2,5))
        ttk.Button(
            self, text="24시간 실제 방송 매체·채팅 관측 이력 (읽기 전용)",
            command=self._show_live_runtime_checkpoints).pack(anchor="w", pady=(2,1))
        self._scenes.bind("<<ListboxSelect>>",lambda _event:self._update_inspect_button())
        self.after(150,self._poll)

    def _start_game_vision(self) -> None:
        """현재 실제 OBS 화면의 1회 로컬 분석. 방송/게임 조작 없음."""
        if self._vision_busy:
            return
        try:
            if self._chat_tab is None:
                raise ValueError("기존 로컬 AI 탭이 필요합니다.")
            model=self._chat_tab._model_name.get().strip()
            if not model:
                raise ValueError("로컬 AI 탭에서 시각 입력 지원 모델을 선택하세요.")
            port=int(self._port.get())
            password=self._password.get()
            if not password:
                raise ValueError("실제 OBS WebSocket 암호가 필요합니다.")
            if not messagebox.askyesno(
                "현재 OBS 게임 화면 읽기 승인",
                "현재 OBS 장면에는 비공개 화면·채팅 등이 포함될 수 있습니다. "
                "이 버튼을 누르는 이번 1회에만 OBS 실제 PNG 프레임을 "
                "읽어 내 PC의 127.0.0.1 로컬 Ollama 모델에 전달합니다. "
                "외부 계정/방송 발신·게임 자동 조작·파일 저장은 하지 않습니다. "
                "현재 화면 분석을 승인합니까?", parent=self):
                return
            self._vision_busy=True
            self._vision_button.configure(state="disabled")
            self._vision_status.set(
                "내 OBS 실제 PNG 1장 읽기·로컬 시각 AI 추론 중 · 외부 게시 없음")
            threading.Thread(
                target=self._work_game_vision, args=(password,port,model),
                name="AISTING-로컬게임화면이해", daemon=True).start()
        except Exception as exc:
            self._vision_status.set(
                "화면 이해 미시작 · " + type(exc).__name__ +
                " · 모델/OBS 암호/포트를 확인하세요.")

    def _work_game_vision(self, password: str, port: int, model: str) -> None:
        try:
            from .approved_local_game_vision import observe_game_scene_with_local_vision
            item=observe_game_scene_with_local_vision(
                password, port, model, operator_approved=True)
            self._events.put(("game_vision_ready", item))
        except Exception as exc:
            self._events.put(("game_vision_error", type(exc).__name__))
        finally:
            password=""

    def _start_approved_game(self, *, resume_run_id: str | None = None) -> None:
        """운영자가 별도 승인한 경우에만 Windows 게임을 직접 조작."""
        if self._game_runner is not None:
            return
        try:
            from .approved_local_game_control import ApprovedLocalGameAutoplay
            if self._chat_tab is None:
                raise ValueError("기존 로컬 AI 탭이 없습니다.")
            model=self._chat_tab._model_name.get().strip()
            title=self._game_title.get().strip()
            goal=self._game_goal.get().strip()
            steps=int(self._game_steps.get())
            progress_interval=int(self._game_progress_interval.get())
            port=int(self._port.get())
            password=self._password.get()
            if not model or not title or not goal or not password:
                raise ValueError("게임 창 제목·목표·로컬 AI 모델·OBS 암호가 필요합니다.")
            if not 1 <= steps <= 100:
                raise ValueError("최대 게임 행동은 1~100회입니다.")
            if not 1 <= progress_interval <= 10:
                raise ValueError("게임 목표 판정 간격은 1~10회입니다.")
            if not messagebox.askyesno(
                "실제 게임 자동 조작 최종 승인",
                "내 PC의 게임 창 '" + title + "'에 실제 키보드/마우스 입력을 "
                + str(steps) + "회 이내로 전송합니다. 매 행동 전에 현재 "
                "OBS 화면을 로컬 Ollama로 분석하며 AI가 행동을 선택합니다. "
                + str(progress_interval) +
                "회 행동마다 후속 화면도 다시 읽어 목표 후보를 확인합니다. "
                "운영자가 승인한 OBS 장면/게임 창 포커스가 바뀌면 추가 입력을 차단합니다. "
                "다른 프로그램/채팅/방송 제어는 승인하지 않습니다. " +
                ("이전 실행의 입력시도는 재실행하지 않고 이력만 참고합니다. "
                 if resume_run_id else "") +
                "운영자가 지정한 목표: " + goal + "\n\n"
                "이 실제 게임 자동 조작을 승인합니까?", parent=self):
                return
            runner=ApprovedLocalGameAutoplay(
                obs_password=password, obs_port=port, model_name=model,
                game_window_title=title, goal=goal, max_steps=steps,
                progress_check_every=progress_interval,
                operator_approved=True, resume_run_id=resume_run_id,
                on_event=lambda kind, value: self._events.put((
                    "approved_game_" + kind, value)))
            self._game_runner=runner
            self._game_start_button.configure(state="disabled")
            self._game_resume_button.configure(state="disabled")
            self._game_stop_button.configure(state="normal")
            self._game_status.set("게임 자동 진행 승인됨 · 실제 Windows 게임 창 확인 중")
            self._game_worker=threading.Thread(
                target=self._work_approved_game, args=(runner,),
                name="AISTING-운영자승인-게임자동조작", daemon=False)
            self._game_worker.start()
        except Exception as exc:
            self._game_status.set(
                "게임 자동 진행 미시작 (" + type(exc).__name__
                + ") · 게임 창/목표/OBS/모델 입력을 확인하세요.")

    def _show_game_goal_history(self) -> None:
        """실제 게임 입력 없이 기존 별도 목표 장부만 조회."""
        from .approved_game_goal_journal import ApprovedGameGoalJournal
        from .offline_settings import data_dir
        path=data_dir() / "approved_game_goals.sqlite3"
        if not path.is_file() or path.is_symlink():
            messagebox.showinfo(
                "게임 목표 이력", "아직 승인된 게임 목표 실행 기록이 없습니다.",
                parent=self)
            return
        try:
            journal=ApprovedGameGoalJournal(path)
            rows=journal.recent_runs(limit=12)
            lines=[]
            for run in rows:
                lines.append(
                    f"{run.created_at} · {run.game_title} · {run.goal[:80]} "
                    f"· {run.state} · 최대 {run.max_steps}회"
                    + (" · 이전 회차 참고" if run.parent_run_id else ""))
                review=journal.confirmation_for(run.run_id)
                if review is not None:
                    lines.append(
                        "  운영자 수동 확인: "
                        + ("달성 확인" if review.operator_confirmed
                           else "미달성 확인")
                        + " · " + review.recorded_at
                        + " · 게임 서버 성공 증빙은 별도")
                for event in journal.history(run.run_id, limit=5):
                    lines.append(
                        f"  {event.step_no}회 {event.phase}: {event.detail[:120]}")
            messagebox.showinfo(
                "게임 목표·행동 이력 (최근 12회)",
                ("\n".join(lines) if lines else "기록 없음")[:7500]
                + "\n\n입력시도 기록은 게임 성공 증명이 아닙니다. "
                "강제 종료 시 행동을 자동 재생하지 않습니다.", parent=self)
        except Exception as exc:
            messagebox.showwarning(
                "게임 이력 읽기 실패",
                "원본 게임 기록을 변경하지 않았습니다 (" +
                type(exc).__name__ + ")", parent=self)

    def _confirm_game_goal_candidate(self) -> None:
        """실제 게임 입력 없이 AI 후보에 대한 운영자 검토만 1회 기록."""
        from .approved_game_goal_journal import ApprovedGameGoalJournal
        from .offline_settings import data_dir
        if self._game_runner is not None:
            messagebox.showwarning(
                "게임 목표 확인", "현재 게임 자동 진행 종료 후 확인할 수 있습니다.",
                parent=self)
            return
        path=data_dir() / "approved_game_goals.sqlite3"
        if not path.is_file() or path.is_symlink():
            messagebox.showinfo(
                "게임 목표 확인", "과거 게임 실행 장부가 없습니다.", parent=self)
            return
        try:
            if self._chat_tab is None:
                raise ValueError("기존 로컬 모델 선택이 없습니다.")
            title=self._game_title.get().strip()
            goal=self._game_goal.get().strip()
            model=self._chat_tab._model_name.get().strip()
            if not title or not goal or not model:
                raise ValueError("게임 창·목표·로컬 모델을 먼저 입력하세요.")
            journal=ApprovedGameGoalJournal(path)
            candidates=[
                run for run in journal.recent_runs(limit=100)
                if (run.game_title, run.goal, run.model) == (title, goal, model)
                and run.state == "목표후보"
                and journal.confirmation_for(run.run_id) is None
            ]
            if not candidates:
                messagebox.showinfo(
                    "게임 목표 확인",
                    "해당 게임·목표·모델의 미확인 AI 달성후보가 없습니다. "
                    "기존 판정은 임의로 목표 성공으로 변경하지 않습니다.",
                    parent=self)
                return
            run=candidates[0]
            events=journal.history(run.run_id, limit=50)
            evidence=next((
                event.detail for event in reversed(events)
                if event.phase == "목표판정" and "달성후보" in event.detail
            ), "후보 상세 근거 없음")
            checked=messagebox.askyesnocancel(
                "AI 후보에 대한 운영자 독립 확인",
                f"실행: {run.run_id[:8]} · {run.created_at}\n"
                f"게임: {run.game_title}\n목표: {run.goal}\n"
                f"로컬 모델: {run.model}\n"
                f"AI 화면 판단: {evidence[:900]}\n\n"
                "운영자가 실제 게임 화면/결과를 직접 확인했나요?\n"
                "예 = 운영자가 목표 달성을 직접 확인\n"
                "아니오 = 운영자가 목표 미달성을 직접 확인\n"
                "취소 = 아무 기록도 하지 않음\n\n"
                "확인 내용은 1회만 별도 SQLite에 보존되고 "
                "게임·OBS·방송·공지에는 어떠한 명령도 보내지 않습니다.",
                parent=self)
            if checked is None:
                return
            saved=journal.confirm_candidate(
                run.run_id, operator_confirmed=checked, operator_approved=True)
            self._game_status.set(
                "AI 달성후보 " + saved.run_id[:8] + " · 운영자 직접 "
                + ("목표 달성 확인" if saved.operator_confirmed
                   else "목표 미달성 확인")
                + " 영구 기록 · 실제 게임 조작/송출 없음")
        except Exception as exc:
            messagebox.showerror(
                "게임 목표 확인 기록 실패",
                "원래 후보 및 실행 이력은 유지합니다 ("
                + type(exc).__name__ + ")", parent=self)

    def _resume_approved_game(self) -> None:
        """동일 게임/목표/모델만 과거 이력 참고; 실제 입력은 다시 승인."""
        if self._game_runner is not None:
            return
        from .approved_game_goal_journal import ApprovedGameGoalJournal
        from .offline_settings import data_dir
        path=data_dir() / "approved_game_goals.sqlite3"
        if not path.is_file() or path.is_symlink():
            messagebox.showinfo(
                "이어하기", "이전에 승인된 동일 게임 목표 기록이 없습니다.",
                parent=self)
            return
        try:
            if self._chat_tab is None:
                raise ValueError("기존 로컬 모델 선택이 없습니다.")
            model=self._chat_tab._model_name.get().strip()
            journal=ApprovedGameGoalJournal(path)
            prior=journal.latest(
                self._game_title.get().strip(),
                self._game_goal.get().strip(), model)
            if prior is None:
                messagebox.showinfo(
                    "이어하기",
                    "게임 창 제목·목표·로컬 모델이 정확히 같은 이전 실행이 없습니다.",
                    parent=self)
                return
            tail=journal.history(prior.run_id, limit=6)
            excerpt="\n".join(
                f"{event.step_no}회 {event.phase}: {event.detail[:130]}"
                for event in tail)
            if not messagebox.askyesno(
                "이전 게임 목표 진행 이력 사용 승인",
                f"최근 기록 상태: {prior.state}\n"
                f"게임: {prior.game_title}\n목표: {prior.goal}\n"
                f"최근 이력:\n{excerpt}\n\n"
                "과거 입력시도는 실제 전달 여부가 불명확할 수 있습니다. "
                "자동 재생하지 않고 화면을 새로 관찰해 다음 행동을 선택합니다. "
                "새로운 행동 수/게임 조작은 다음 승인 창에서 다시 확인합니다. "
                "이전 이력을 참고하도록 허용합니까?", parent=self):
                return
            self._start_approved_game(resume_run_id=prior.run_id)
        except Exception as exc:
            self._game_status.set(
                "게임 목표 이어하기 준비 실패 (" + type(exc).__name__ +
                ") · 기존 기록 변경 없음")

    def _work_approved_game(self, runner) -> None:
        try:
            runner.run()
        except Exception as exc:
            self._events.put(("approved_game_error", type(exc).__name__))
        finally:
            self._events.put(("approved_game_done", runner))

    def _stop_approved_game(self) -> None:
        runner=self._game_runner
        if runner is not None:
            runner.request_stop()
            self._game_status.set(
                "게임 조작 중지 요청됨 · 진행 중 키/마우스 해제 및 작업 종료 대기")

    def _show_live_content_history(self) -> None:
        """사용자 콘텐츠 주제와 실제 전달 상태만 조회; 방송/채팅 발신 없음."""
        from .approved_live_content_agenda import ApprovedLiveContentJournal
        from .offline_settings import data_dir
        path = data_dir() / "approved_live_content.sqlite3"
        if not path.is_file():
            messagebox.showinfo(
                "자율 콘텐츠 기록", "아직 방송 주제 발화 시도가 없습니다.",
                parent=self)
            return
        try:
            rows = ApprovedLiveContentJournal(path).recent(limit=30)
            body = ("\\n".join(
                f"{occurrence} · {number}회 · {topic} · {state}"
                for occurrence, number, topic, state in rows)
                if rows else "아직 방송 주제 발화 시도가 없습니다.")
            messagebox.showinfo(
                "자율 콘텐츠 발화 장부 (최근 30회)",
                body + "\\n\\n전달확인은 공식 AI 입력 접수이며 "
                "실제 음성·영상·시청자 수신을 증명하지 않습니다.",
                parent=self)
        except Exception as exc:
            self._live_schedule_status.set(
                "자율 콘텐츠 장부 조회 불가 (" + type(exc).__name__
                + ") · 원본 파일을 변경하지 않았습니다.")

    def _show_live_runtime_checkpoints(self) -> None:
        """수동 조회만 수행. 실제 OBS/계정 접속·방송 변경 없음."""
        from .approved_live_runtime_checkpoint import ApprovedLiveRuntimeCheckpoint
        from .offline_settings import data_dir
        path = data_dir() / "approved_live_runtime_checkpoints.sqlite3"
        if not path.is_file() or path.is_symlink() or path.parent.is_symlink():
            messagebox.showinfo(
                "장시간 방송 관측", "아직 승인 방송의 상태 관측 기록이 없습니다.",
                parent=self)
            return
        try:
            checkpoints = ApprovedLiveRuntimeCheckpoint(path).recent(limit=25)
            lines = [
                item.observed_at + " · " + item.occurrence
                + " · " + item.state
                + " / OBS " + ("확인" if item.obs_streaming else "미확인")
                + " / 공식 매체 " + (
                    "관측없음" if item.media_alive is None else
                    "생존" if item.media_alive else "불명")
                + " / 채팅 " + (
                    "미사용" if item.chat_alive is None else
                    "정상" if item.chat_alive else "불명")
                for item in checkpoints]
            messagebox.showinfo(
                "24시간 실제 OBS·AI·채팅 상태 관측 장부",
                ("\n".join(lines) if lines else "기록 없음")[:7500]
                + "\n\n로컬 상태 관측일 뿐 실제 플랫폼·시청자 최종 수신 증거가 아닙니다.",
                parent=self)
        except Exception as exc:
            messagebox.showwarning(
                "방송 관측 기록 읽기 실패",
                "기존 독립 SQLite 장부를 변경하지 않았습니다 ("
                + type(exc).__name__ + ")", parent=self)

    def _show_live_history(self) -> None:
        """로컬 시작/종료 이력만 표시. OBS 연결·송출·파일 삭제 없음."""
        from .approved_live_slot_journal import ApprovedLiveSlotJournal
        from .offline_settings import data_dir
        path = data_dir() / "approved_live_slots.sqlite3"
        if not path.exists():
            messagebox.showinfo(
                "방송 시작 기록", "아직 로컬 방송 시작 시도 기록이 없습니다.",
                parent=self)
            return
        try:
            journal = ApprovedLiveSlotJournal(path)
            claims = journal.recent_claims(limit=20)
            events = journal.recent_events(limit=100)
            latest = {}
            for occurrence, state, logged_at in events:
                if occurrence not in latest:
                    latest[occurrence] = (state, logged_at)
            if not claims:
                body = "아직 로컬 방송 시작 시도 기록이 없습니다."
            else:
                body = "\n".join(
                    occurrence + " · " + (
                        latest[occurrence][0]
                        if occurrence in latest
                        else "종료 여부 미확인 · OBS 실제 상태 확인 필요"
                    ) for occurrence, _ in claims)
            messagebox.showinfo(
                "방송 시작·종료 기록 (최근 20회)",
                body + "\n\n이 기록은 실제 플랫폼 송출/시청자 수신 증명이 아닙니다.",
                parent=self)
        except Exception:
            messagebox.showwarning(
                "방송 기록 조회 실패",
                "로컬 방송 시작 장부를 확인할 수 없습니다. OBS 실제 상태를 직접 확인하세요.",
                parent=self)

    def _show_cafe_notice_history(self) -> None:
        """카페 계정 접근 없이 현재 로컬 발신 시도만 조회한다."""
        try:
            from .approved_naver_cafe_notice_journal import (
                ApprovedNaverCafeNoticeJournal)
            rows = ApprovedNaverCafeNoticeJournal().recent(limit=20)
            lines = [
                " · ".join((occurrence, phase, club, menu, state,
                            "글 " + article if article else "글번호 미확인", at))
                for occurrence, phase, club, menu, state, article, at in rows
            ]
            messagebox.showinfo(
                "네이버 카페 실제 공지 시도 기록",
                "\\n".join(lines) if lines else "아직 카페 공지 시도 기록이 없습니다.",
                parent=self)
        except Exception:
            messagebox.showwarning(
                "카페 공지 기록 조회 실패",
                "로컬 카페 공지 장부를 읽을 수 없습니다. 실제 게시글은 직접 확인하세요.",
                parent=self)

    def _compose_local_notice_ai(self) -> None:
        """운영자가 현재 선택한 로컬 AI로 검토용 공지만 작성한다."""
        if self._notice_ai_busy or self._approved_scheduler is not None:
            return
        try:
            from .offline_broadcast_schedule import KST, load_schedule, schedule_path
            from datetime import datetime
            draft = load_schedule(schedule_path())
            if draft is None or not draft.slots:
                raise ValueError("먼저 운영자 KST 주간 방송 일정을 저장해야 합니다.")
            if self._chat_tab is None:
                raise ValueError("기존 로컬 AI 대화 탭이 없습니다.")
            model = self._chat_tab._model_name.get().strip()
            topic = self._notice_topic.get().strip()
            closing = self._schedule_closing.get().strip()
            if not model:
                raise ValueError("기존 로컬 AI 탭에서 사용할 모델을 선택하세요.")
            if not closing:
                raise ValueError("종료 인사를 직접 지정하세요.")
            upcoming = draft.upcoming(datetime.now(KST), limit=1)
            if not upcoming:
                raise ValueError("예정된 KST 방송 일정이 없습니다.")
            self._notice_ai_busy = True
            self._notice_ai_button.configure(state="disabled")
            self._notice_ai_status.set(
                "기존 로컬 Ollama에서 2건 생성 중 · 외부 공지/방송은 시작하지 않음")
            threading.Thread(
                target=self._work_local_notice_ai,
                args=(model, upcoming[0], topic, closing),
                name="AISTING-로컬공지AI", daemon=True).start()
        except Exception as exc:
            self._notice_ai_status.set(
                "로컬 AI 공지 생성 미시작 · " + type(exc).__name__ +
                " · 일정/모델/종료 인사를 확인하세요.")

    def _work_local_notice_ai(self, model, when, topic, closing) -> None:
        try:
            from .approved_local_notice_ai import generate_approved_notice_drafts
            texts = generate_approved_notice_drafts(
                model, scheduled_at=when, topic=topic, end_message=closing)
            self._events.put(("notice_ai_ready", texts))
        except Exception as exc:
            # Ollama 응답 본문 또는 토큰·계정 내용을 GUI/로그에 노출하지 않는다.
            self._events.put(("notice_ai_error", type(exc).__name__))

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

    def _approved_live_media_alive(self) -> bool:
        """기존 동일 승인 방송의 공식 Cubism와 로컬 한국어 TTS 생존만 관찰.

        원격 서버 접속, 합성/OBS 조작, 새 OAuth/방송 자동 시작은 하지
        않는다. TCP 포트가 살아 있어도 합성 결과나 시청자 출력 성공을
        증명하지 않는다.
        """
        if not self._approved_live_preflight():
            return False
        from . import original_plan_frontend as frontend
        from .official_tts_readiness import read_saved_korean_gpt_sovits_config
        from .approved_local_tts_listener import local_korean_tts_listener_alive
        url, _reference, _words = read_saved_korean_gpt_sovits_config(
            frontend._native_viewer_project)
        return local_korean_tts_listener_alive(url, timeout=0.75)

    def _approved_live_closing(self, words: str) -> bool:
        """기존 공식 Live2D 음성 경로에 운영자가 입력한 종료 문구만 전달."""
        from .original_plan_frontend import (
            send_to_native_live2d_session_with_observation)
        observation = send_to_native_live2d_session_with_observation(
            words, operator_approved=True, duration=8)
        return observation.verified_signal is True

    def _approved_chat_alive(self) -> bool:
        """승인 OBS 방송이 소유한 **선택 플랫폼별 실제 방 입장**을 확인.

        예전에는 수신 세션이 Stop되지 않았다는 이유만으로 4플랫폼
        채팅이 정상이라고 판단했다. 이제 적어도 선택된 모든 방에
        실제 입장 완료됐는지 관측한다. 원래 수신기의 자동 재연결이
        짧은 오류를 먼저 회복하며, 15초 이상 지속되면 기존 예약
        방송 복구/안전 종료 흐름으로 전달된다.
        """
        session = self._owned_chat_session
        chat = self._chat_tab
        if (session is None or chat is None
                or chat._twitch_session is not session
                or chat._twitch_reader_finished):
            self._approved_chat_health_detail = (
                "승인된 채팅 세션이 없거나 수신기가 종료됨")
            return False
        stopped = getattr(session, "_stop", None)
        if stopped is None or stopped.is_set():
            self._approved_chat_health_detail = "선택 채팅 세션 중지됨"
            return False
        try:
            # 초당 예약 조회에서 무거운 전체 채팅 통계 정렬 금지.
            # 실제 리더 JOIN/API ready 상태만 해당 세션의 RLock으로 읽음.
            observed = session.live_room_readiness()
            selected = tuple(session._channels)
            if not selected or set(observed) != set(selected):
                self._approved_chat_health_detail = "선택 채팅 플랫폼 관측 누락"
                return False
            missing = tuple(
                code for code in selected
                if observed[code][0] is not True
                or observed[code][2] is True
                or observed[code][1] is True)
            if missing:
                self._approved_chat_health_detail = (
                    "실제 채팅방 입장 미확인: " + ", ".join(missing)
                    + " · 기존 수신기 내부 자동 재연결 대기")
                return False
        except (AttributeError, RuntimeError, TypeError, ValueError):
            self._approved_chat_health_detail = "채팅방 실제 입장 관측 불가"
            return False
        self._approved_chat_health_detail = (
            "운영자가 선택한 " + str(len(selected))
            + "개 플랫폼의 실제 채팅방 입장 관측"
            " · 서버 공백 중 채팅 무누락은 미검증")
        return True

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
        if self._notice_ai_busy:
            self._live_schedule_status.set(
                "AI 공지 생성 중 · 작성 완료 후 문구를 검토하고 승인하세요.")
            return
        if self._approved_scheduler_thread is not None and self._approved_scheduler_thread.is_alive():
            messagebox.showwarning("방송 예약 중", "기존 방송 예약 작업을 먼저 종료하세요.", parent=self)
            return
        try:
            from .approved_live_scheduler import ApprovedLiveScheduler
            from .approved_live_slot_journal import ApprovedLiveSlotJournal
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
            content_enabled = self._auto_content_approved.get() is True
            content_settings = None
            if content_enabled:
                if not auto_chat:
                    raise ValueError("주제 자동 진행에는 기존 4플랫폼 공식 AI 채팅 자동 연결이 필요합니다.")
                from .approved_live_content_agenda import parse_approved_topics
                topics = parse_approved_topics(
                    self._auto_content_topics.get("1.0", "end-1c"))
                interval_seconds = int(self._auto_content_interval.get().strip())
                if not 60 <= interval_seconds <= 3600:
                    raise ValueError("자율 콘텐츠 간격은 60~3600초입니다.")
                content_settings = (topics, interval_seconds)
            if auto_chat:
                source = self._chat_tab
                if (source is None or source._twitch_session is not None
                        or source._busy or source._pipeline_busy
                        or source._tts_probe_busy or source._closed
                        or source._official_live2d.get() is not True):
                    raise ValueError("실제 채팅 탭에서 공식 AI와 대기 상태를 확인하세요.")
            approval_token = object() if auto_chat else None
            discord_enabled = self._discord_notice_approved.get() is True
            pre_enabled = self._discord_pre_approved.get() is True
            if pre_enabled and not discord_enabled:
                raise ValueError("사전 공지에는 Discord 웹훅 게시 승인도 필요합니다.")
            pre_lead = 0
            pre_callback = None
            if pre_enabled:
                pre_lead = int(self._discord_pre_lead.get().strip())
                if not 10 <= pre_lead <= 40:
                    raise ValueError("사전 공지 시각은 방송 10~40분 전만 가능합니다.")
                pre_text = self._discord_pre_text.get().strip()
                if not 1 <= len(pre_text) <= 1500:
                    raise ValueError("사전 공지 문구를 1~1500자 직접 입력하세요.")
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
                if pre_enabled:
                    pre_callback = lambda _occurrence: sender.send(
                        pre_text, operator_approved=True)
            cafe_enabled = self._cafe_notice_approved.get() is True
            cafe_sender = None
            cafe_messages = None
            if cafe_enabled:
                from .approved_naver_cafe_notice import (
                    ApprovedNaverCafeNoticeSender, _validate_text)
                cafe_sender = ApprovedNaverCafeNoticeSender(
                    self._cafe_club_id.get().strip(),
                    self._cafe_menu_id.get().strip(),
                    self._cafe_access_token.get().strip(),
                    operator_approved=True)
                cafe_messages = (
                    _validate_text(self._cafe_start_title.get(),
                                   label="카페 시작 공지 제목", maximum=150),
                    _validate_text(self._cafe_start_body.get(),
                                   label="카페 시작 공지 본문", maximum=4000),
                    _validate_text(self._cafe_end_title.get(),
                                   label="카페 종료 공지 제목", maximum=150),
                    _validate_text(self._cafe_end_body.get(),
                                   label="카페 종료 공지 본문", maximum=4000),
                )
            if not messagebox.askyesno(
                "실제 자동 방송 시작·종료 최종 승인",
                "이 컴퓨터의 실제 OBS가 주간 일정에 따라 외부 플랫폼에 방송을 시작합니다. "
                "내가 직접 입력한 최소/최대 방송 시간과 종료 인사를 사용합니다. "
                "프로그램을 종료하거나 중지 버튼을 누르면 이 기능이 시작한 방송만 "
                "종료하도록 시도합니다. OBS WebSocket 연결만 끊기면 최대 90초 "
                "같은 출력 가동시간·장면을 확인하며 연결 복구를 시도합니다. "
                "공식 Live2D 창·한국어 음성 준비가 방송 중 5초 간격으로 "
                "확인되지 않으면 30초 유예 뒤 이 예약이 시작한 OBS 방송만 "
                "종료하며 자동 재시작하지 않습니다. "
                "방송을 자동 재시작하지 않으며 출력 소유권이 불확실하면 "
                "종료 명령도 보내지 않고 수동 확인을 요청합니다. "
                + ("내가 지정한 Discord 시작/종료 공지를 실제 외부 채널에 "
                   "각 1회씩 자동 게시합니다. 실패 시 자동 재게시하지 않습니다. "
                   if discord_enabled else
                   "디스코드 자동 공지는 비활성입니다. ")
                + (f"방송 {pre_lead}분 전에 내가 작성한 사전 공지 1회 게시를 "
                   "추가 승인합니다. 재시작해도 같은 방송 공지를 재게시하지 않습니다. "
                   if pre_enabled else "사전 공지는 게시하지 않습니다. ")
                + ("내가 입력한 네이버 카페 번호/게시판에 방송 시작·종료 "
                   "각 1회씩 실제 게시글을 올립니다. 네이버 로그인 카페 글쓰기 "
                   "OAuth 토큰을 현재 실행 중 메모리에서만 사용하고, "
                   "글쓰기 실패·응답 불명·재시작 시 자동 재게시하지 않습니다. "
                   if cafe_enabled else "네이버 카페 자동 공지는 비활성입니다. ")
                + ("운영자가 입력한 방송 주제를 승인된 공식 AI에 "
                   f"{content_settings[1]}초 간격으로 전달합니다. "
                   "시청자 채팅과 SQLite 미처리 작업이 우선이고 "
                   "콘텐츠 질문은 영구 장부에 먼저 기록하며 "
                   "전송 불명 시 중복 재발화하지 않습니다. "
                   if content_settings is not None else
                   "자율 콘텐츠 진행은 비활성입니다. ")
                + ("선택된 기존 4플랫폼 채팅·공식 AI 읽기 전용 수신기도 "
                   "이 방송 시 자동 연결합니다. 계정 동의나 채팅 발신은 하지 않으며 "
                   "기존 공식 AI 서버 설정의 권리·외부 접속은 운영자가 확인합니다. "
                   if auto_chat else "채팅 자동 연결은 비활성입니다. ")
                + "채팅 발신은 하지 않습니다. 저장된 캐릭터와 한국어 "
                "음성에 사용 권리가 있고 실제 방송 자동 제어와 선택한 "
                "공지 전송을 승인합니까?", parent=self):
                return
            # 별도 로컬 SQLite 영구 장부: 강제 종료 후 같은 슬롯의
            # 중복 OBS 시작을 예방한다. 사용자 승인 전에는 생성하지 않는다.
            journal=ApprovedLiveSlotJournal()
            from .approved_live_runtime_checkpoint import ApprovedLiveRuntimeCheckpoint
            # 사용자가 이 예약을 실제 승인한 때에만 독립 상태 장부 준비.
            # 원래 슬롯/이벤트·채팅/기억 SQLite는 변경하지 않는다.
            runtime_log=ApprovedLiveRuntimeCheckpoint()
            on_cafe_started = None
            on_cafe_finished = None
            if cafe_enabled:
                from .approved_naver_cafe_notice_journal import (
                    ApprovedNaverCafeNoticeJournal)
                cafe_journal = ApprovedNaverCafeNoticeJournal()
                def post_cafe_notice(occurrence: str, phase: str) -> bool:
                    # 승인된 방송 슬롯에서 실제 송출 확인 뒤에만 호출됨.
                    # DB 원자적 청구 이전에는 외부 게시를 절대 시작하지 않음.
                    if phase == "시작":
                        subject, body = cafe_messages[:2]
                    elif phase == "종료":
                        subject, body = cafe_messages[2:]
                    else:
                        raise ValueError("카페 공지 단계가 올바르지 않습니다.")
                    if not cafe_journal.claim(
                            occurrence, phase, cafe_sender.club_id,
                            cafe_sender.menu_id, subject, body):
                        return False
                    try:
                        receipt = cafe_sender.post(
                            subject, body, operator_approved=True)
                    except Exception:
                        try:
                            cafe_journal.mark(
                                occurrence, phase, cafe_sender.club_id,
                                cafe_sender.menu_id, "서버응답불명")
                        except Exception:
                            pass
                        raise
                    cafe_journal.mark(
                        occurrence, phase, cafe_sender.club_id,
                        cafe_sender.menu_id, "서버게시확인",
                        article_id=receipt.article_id)
                    return True
                on_cafe_started = lambda occurrence: post_cafe_notice(
                    occurrence, "시작")
                on_cafe_finished = lambda occurrence: post_cafe_notice(
                    occurrence, "종료")
            runner=ApprovedLiveScheduler(
                draft, rules, obs_password=password, obs_port=port,
                scene=scene, closing_text=closing,
                operator_approved=True, rights_confirmed=True,
                media_preflight=self._approved_live_preflight,
                media_alive=self._approved_live_media_alive,
                media_watch_interval_seconds=5.0,
                media_grace_seconds=30.0,
                deliver_closing=self._approved_live_closing,
                on_started_notice=on_started_notice,
                on_finished_notice=on_finished_notice,
                notice_approved=discord_enabled,
                on_cafe_started=on_cafe_started,
                on_cafe_finished=on_cafe_finished,
                cafe_notice_approved=cafe_enabled,
                begin_live_chat=(
                    (lambda token=approval_token: self._request_live_chat_start(token))
                    if auto_chat else None),
                end_live_chat=(self._request_live_chat_stop if auto_chat else None),
                chat_approved=auto_chat,
                chat_alive=(self._approved_chat_alive if auto_chat else None),
                chat_recovery_limit=3,
                occurrence_claim=journal.claim,
                occurrence_event=journal.record_event,
                runtime_checkpoint=(
                    lambda occurrence, obs, media, chat:
                    runtime_log.record(
                        occurrence, obs_streaming=obs,
                        media_alive=media, chat_alive=chat)),
                on_pre_notice=pre_callback,
                pre_notice_claim=(journal.claim_pre_notice if pre_enabled else None),
                pre_notice_lead_minutes=pre_lead)
            self._approved_content_settings = content_settings
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
        # 토큰 입력창을 비우더라도 승인된 현재 실행의 콜백만
        # 메모리에서 사용한다. 파일/인수인계/상태 로그에 저장 금지.
        self._cafe_access_token.set("")
        self._approved_scheduler_thread=threading.Thread(
            target=self._run_approved_schedule, args=(runner,),
            name="AISTING-운영자승인-실제OBS일정", daemon=False)
        self._live_arm_button.configure(state="disabled")
        self._live_disarm_button.configure(state="normal")
        self._live_schedule_status.set(
            "사용자 승인 완료 · KST 일정 대기 · SQLite 중복시작 방지 적용 · "
            "송출 아직 시작하지 않음")
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
        self._approved_content_settings = None
        if self._chat_tab is not None:
            self._chat_tab._scheduled_content_plan = None
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
                if kind == "approved_game_기록시작":
                    self._game_status.set(
                        "게임 장기 목표 로컬 SQLite 새 실행 시작 · "
                        + item.run_id[:8] + " · 과거 입력 자동 재생 없음")
                    continue
                if kind == "approved_game_후속관찰":
                    self._game_status.set(
                        "게임 행동 후 실제 OBS 화면 관찰 기록됨 · "
                        "목표 완료 여부는 로컬 AI 판정 후보와 구분")
                    continue
                if kind == "approved_game_목표판정":
                    self._game_status.set(
                        "게임 목표 화면 추정: " + item.status + " · " +
                        item.evidence[:160] + " · 실제 게임 내부 결과 미확인")
                    continue
                if kind == "approved_game_게임장면변경":
                    self._game_status.set(
                        "승인 시작 OBS 장면과 현재 장면이 다릅니다 · "
                        "다른 화면 키/마우스 조작 중단 · 원래 OBS 장면 " +
                        str(item)[:100])
                    continue
                if kind == "approved_game_목표판정불가":
                    self._game_status.set(
                        "게임 목표 화면 추정 불가 (" + str(item) +
                        ") · 목표 완료로 표시하지 않음")
                    continue
                if kind == "approved_game_기록종료":
                    run_id, state = item
                    self._game_status.set(
                        "게임 자동 진행 기록 " + run_id[:8] +
                        " · 종료 상태 " + state +
                        " · 실제 목표 성공/키 전달 증명 아님")
                    continue
                if kind == "approved_game_행동":
                    self._game_status.set(
                        f"게임 행동 {item.number}회: {item.result} · "
                        "다음 화면 재관찰 예정 · 목표 달성 미확인")
                    continue
                if kind == "approved_game_종료":
                    self._game_status.set(
                        f"게임 자동 진행 {item}개 행동 요청 완료 · "
                        "실제 게임 목표 달성 여부는 화면으로 별도 확인 필요")
                    continue
                if kind == "approved_game_error":
                    self._game_status.set(
                        "게임 자동 진행 중단 (" + str(item) +
                        ") · 실제 게임 창/모델/OBS 상태 확인 필요")
                    continue
                if kind == "approved_game_done":
                    if self._game_runner is item:
                        self._game_runner=None
                        self._game_worker=None
                        self._game_start_button.configure(state="normal")
                        self._game_resume_button.configure(state="normal")
                        self._game_stop_button.configure(state="disabled")
                    continue
                if kind == "game_vision_ready":
                    self._vision_busy=False
                    self._vision_button.configure(state="normal")
                    self._vision_status.set(
                        "실제 OBS 프레임 1장 로컬 모델 분석 응답 수신 · "
                        "게임 조작/송출/시청자 수신 증명 아님")
                    popup=tk.Toplevel(self)
                    popup.title("로컬 시각 AI의 실제 OBS 화면 이해 결과")
                    popup.geometry("720x450")
                    view=tk.Text(popup, wrap="word")
                    scroll=ttk.Scrollbar(popup, orient="vertical",command=view.yview)
                    view.configure(yscrollcommand=scroll.set)
                    scroll.pack(side="right", fill="y")
                    view.pack(side="left",fill="both",expand=True)
                    view.insert("end",
                        "OBS 장면: " + item.scene + "\n"
                        + "프레임: " + str(item.width) + "x" + str(item.height)
                        + "\n로컬 모델: " + item.local_model + "\n\n"
                        + item.description + "\n\n"
                        + "※ 이번 화면의 관찰 후보일 뿐, 실제 게임 조작·"
                        "시청자 화면/24시간 운영 증명이 아닙니다.")
                    view.configure(state="disabled")
                    continue
                if kind == "game_vision_error":
                    self._vision_busy=False
                    self._vision_button.configure(state="normal")
                    self._vision_status.set(
                        "로컬 시각 AI 분석 실패 (" + str(item) +
                        ") · 실제 프레임 미분석 또는 모델 이미지 미지원")
                    continue
                if kind == "notice_ai_ready":
                    self._notice_ai_busy = False
                    self._notice_ai_button.configure(state="normal")
                    # 예약 승인 이후 늦게 도착한 AI 문구를 승인된 공지로
                    # 몰래 바꾸지 않는다. 모든 작성 결과는 검토용이다.
                    if self._approved_scheduler is not None:
                        self._notice_ai_status.set(
                            "방송 승인 이후 결과 도착 · 승인된 공지 변경 차단")
                    else:
                        start_notice, end_notice = item
                        self._discord_start_text.set(start_notice)
                        self._discord_end_text.set(end_notice)
                        self._notice_ai_status.set(
                            "로컬 AI 공지 2건 작성됨 · 내용 직접 검토 필요 · "
                            "자동 게시 없음 · 실제 발신은 별도 체크/확인 필요")
                    continue
                if kind == "notice_ai_error":
                    self._notice_ai_busy = False
                    self._notice_ai_button.configure(state="normal")
                    self._notice_ai_status.set(
                        "로컬 공지 작성 미완료 (" + str(item) +
                        ") · 기존 공지 문구 변경 없음")
                    continue
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
                            content_settings = self._approved_content_settings
                            if content_settings is not None:
                                snapshot = self._approved_scheduler.snapshot()
                                if not snapshot.occurrence:
                                    raise RuntimeError("승인된 방송 일정 슬롯을 확인할 수 없습니다.")
                                self._chat_tab._scheduled_content_plan = {
                                    "token": token,
                                    "occurrence": snapshot.occurrence,
                                    "topics": content_settings[0],
                                    "interval_seconds": content_settings[1],
                                    "broadcast_alive": lambda: (
                                        self._approved_scheduler is not None
                                        and self._approved_scheduler.snapshot().owns_stream
                                        and self._approved_scheduler.snapshot().start_confirmed),
                                }
                            else:
                                self._chat_tab._scheduled_content_plan = None
                            self._chat_tab._start_twitch(scheduled_approval=token)
                            self._owned_chat_session = self._chat_tab._twitch_session
                            accepted=self._owned_chat_session is not None
                        except Exception:
                            accepted=False
                    if not accepted and self._chat_tab is not None:
                        self._chat_tab._scheduled_content_plan = None
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
                    if self._chat_tab is not None:
                        self._chat_tab._scheduled_content_plan = None
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
                            " / 종료 공지 " + snap.end_notice +
                            " / 카페 시작 " + snap.cafe_start_notice +
                            " / 카페 종료 " + snap.cafe_end_notice +
                            " / 공식 Live2D·한국어 음성 " + snap.media_health +
                            " / 장시간 방송 관측 " + snap.runtime_checkpoint)
                    self._approved_scheduler=None
                    if self._chat_tab is not None and self._scheduled_chat_token is not None:
                        if self._chat_tab._scheduled_chat_permission is self._scheduled_chat_token:
                            self._chat_tab._scheduled_chat_permission=None
                    self._scheduled_chat_token=None
                    self._approved_content_settings=None
                    if self._chat_tab is not None:
                        self._chat_tab._scheduled_content_plan=None
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
                " · 사전 공지 " + snap.pre_notice +
                " · 공지 시작 " + snap.start_notice +
                " / 종료 " + snap.end_notice +
                " · 채팅/AI " + snap.live_chat +
                " · 채팅 복구 " + snap.chat_recovery +
                " / 실제 채팅방 입장 " + self._approved_chat_health_detail +
                " · OBS 연결 " + snap.obs_recovery +
                " · Live2D·한국어 음성 " + snap.media_health +
                " · 장시간 방송 관측 " + snap.runtime_checkpoint +
                " · 카페 시작 " + snap.cafe_start_notice +
                " / 종료 " + snap.cafe_end_notice +
                " · " + snap.stream_health +
                (" · " + snap.journal_error if snap.journal_error else ""))
        self.after(150,self._poll)

    def destroy(self) -> None:
        # 창 종료 후 실제 게임에 새로운 입력을 전송하지 않는다.
        if self._game_runner is not None:
            self._game_runner.request_stop()
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
