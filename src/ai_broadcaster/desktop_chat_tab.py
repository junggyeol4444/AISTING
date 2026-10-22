"""AISTING EXE의 네이티브 로컬 AI 테스트 탭.

네트워크 요청은 운영자가 '텍스트 전송'을 누른 경우에만 한다.
작업자는 UI와 분리된 스레드에서 localhost에 접속하고,
결과만 tkinter 메인 이벤트 루프에서 표시한다.
"""
from __future__ import annotations

import queue
import threading
import math
import time
from collections import deque
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from .conversation_memory import ConversationMemory, DEFAULT_MEMORY_FILE
from .desktop_chat import run_local_chat, LocalChatRunner
from .reply_voice import ReplyVoicePlayer, should_auto_read
from .windows_tts import Voice
from .avatar_animation import SpeechActivity
from .twitch_readonly import TwitchReadOnlySession, TwitchReadError
from .multiplatform_readonly import ChzzkReadOnlySession, SoopReadOnlySession, YouTubeReadOnlySession
from .multi_platform_session import MultiPlatformReadOnlySession
from .live_runtime_metrics import LiveLatencyMetrics
from .offline_settings import load_settings


@dataclass(frozen=True)
class _ReaderTimestampedChat:
    """원본 채팅과 네트워크 읽기 콜백 시각을 별도 보관한다.

    채팅 본문·플랫폼·닉네임을 수정하거나 다른 메시지와 병합하지 않는다.
    서버가 실제 게시한 시각이나 시청자 화면 시간은 측정하지 않는다.
    """
    message: object
    reader_received_at: float
    # 실제 4플랫폼 수신기에서 GUI 대기 이전에 AI FIFO에 넣었는지 구분.
    # 과거 직접 호출·오프라인 테스트는 기존 GUI 경로를 그대로 사용한다.
    ai_prequeued: bool = False


class LocalChatTab(ttk.Frame):
    def __init__(self, master: tk.Misc, *, activity: SpeechActivity | None = None) -> None:
        super().__init__(master)
        self._activity = activity if activity is not None else SpeechActivity()
        self._results: queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()
        self._busy = False
        self._model_name = tk.StringVar()
        self._input = tk.StringVar()
        self._memory_count = tk.StringVar(value="저장된 대화: 확인 전")
        self._voice_player = ReplyVoicePlayer()
        self._tts_loading = False
        self._tts_busy = False
        self._tts_voices: dict[str, Voice] = {}
        self._voice_name = tk.StringVar()
        self._auto_voice = tk.BooleanVar(value=False)
        self._last_reply: str | None = None
        self._queued_voice: deque[tuple[str, Voice]] = deque()
        self._closed = False
        self._twitch_session: TwitchReadOnlySession | None = None
        # Includes stopped readers while their in-flight AI/SQLite turn drains.
        # Only the Tk event loop removes completed workers from this set.
        self._twitch_active_workers: set[object] = set()
        self._twitch_channel = tk.StringVar()
        self._twitch_oauth_token = tk.StringVar()
        self._twitch_oauth_login = tk.StringVar()
        self._chat_platform = tk.StringVar(value='트위치')
        self._multi_channels = {name: tk.StringVar() for name in ('twitch','chzzk','soop','youtube')}
        self._official_live2d = tk.BooleanVar(value=False)
        self._youtube_api_key = tk.StringVar()
        self._youtube_oauth_token = tk.StringVar()
        self._oauth_busy = False
        self._pipeline_busy = False
        self._tts_probe_busy = False
        self._tts_probe_status = tk.StringVar(value="실제 GPT-SoVITS 한국어 합성 미실행")
        self._pipeline_cancel: threading.Event | None = None
        self._pipeline_audio_input = tk.StringVar()
        self._pipeline_obs_password = tk.StringVar()
        self._pipeline_status = tk.StringVar(value="공식 Live2D·OBS 동시 실측 미실행")
        self._twitch_status = tk.StringVar(value="읽기 전용 미연결 · 로그인·채팅 송신 없음")
        self._platform_health_status = tk.StringVar(value="플랫폼별 수신 상태: 미연결")
        self._platform_health_updated_at = 0.0
        self._twitch_received = 0
        self._twitch_replied = 0
        self._twitch_ai_failures = 0
        self._twitch_ai_inbox: queue.SimpleQueue | None = None
        # 실제 수신 콜백의 AI 등록과 Stop 종료 표식을 직렬화한다.
        # tkinter 객체를 잠금 보유 상태에서 직접 조작하지 않는다.
        self._live_ingress_lock = threading.Lock()
        # Monotonic at actual reader callback for scoped network events,
        # before Tk backlog. No extra text copy, logging or deduplication.
        self._ai_arrival_times: queue.SimpleQueue = queue.SimpleQueue()
        self._live_latency_metrics: LiveLatencyMetrics | None = None
        # 4플랫폼별 실제 AI FIFO 등록·종결·대기/추론 시간을 분리한다.
        # 본문/닉네임/계정 정보는 별도 저장하지 않으며 시청자 E2E와 다르다.
        self._platform_live_metrics: dict[str, LiveLatencyMetrics] = {}
        # Reader EOF is distinct from operator Stop; keep accepted AI work alive.
        self._twitch_reader_finished = False
        self._twitch_reader_error = None
        self._tts_status = tk.StringVar(value="음성 읽기는 기본 꺼짐. 먼저 한국어 음성을 확인하세요.")

        intro = (
            "PC에 무료 Ollama와 모델이 이미 설치돼 있어야 작동합니다.\n"
            "텍스트 전송을 눌러야만 내 PC의 127.0.0.1에 접속합니다."
        )
        ttk.Label(self, text=intro, justify="left").pack(anchor="w", pady=(2, 12))
        model_row = ttk.Frame(self)
        model_row.pack(fill="x", pady=4)
        ttk.Label(model_row, text="설치한 모델 이름", width=17).pack(side="left")
        ttk.Entry(model_row, textvariable=self._model_name).pack(side="left", fill="x", expand=True)
        self._dialog = tk.Text(self, height=12, wrap="word", state="disabled", font=("Malgun Gothic", 10))
        self._dialog.pack(fill="both", expand=True, pady=8)
        input_row = ttk.Frame(self)
        input_row.pack(fill="x", pady=4)
        ttk.Entry(input_row, textvariable=self._input).pack(side="left", fill="x", expand=True)
        self._send = ttk.Button(input_row, text="텍스트 전송", command=self._submit)
        self._send.pack(side="left", padx=(8, 0))
        self._input_info = tk.StringVar(value="텍스트 AI와 무료 PC 음성 테스트 전용. 방송 송출은 하지 않습니다.")
        ttk.Label(self, textvariable=self._input_info, wraplength=550).pack(anchor="w", pady=(3, 10))
        bottom = ttk.Frame(self)
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self._memory_count).pack(side="left")
        ttk.Button(bottom, text="대화 기억 삭제", command=self._clear_memory).pack(side="right")

        # 사용자 승인 없이 모델 호출, 음성 재생, 방송 송출하지 않음.
        audio = ttk.LabelFrame(self, text="무료 AI 답변 읽어주기 (PC 스피커 전용)", padding=9)
        audio.pack(fill="x", pady=(10, 0))
        controls = ttk.Frame(audio)
        controls.pack(fill="x")
        self._tts_select = ttk.Combobox(controls, textvariable=self._voice_name,
                                         values=[], state="readonly", width=32)
        self._tts_select.pack(side="left", fill="x", expand=True)
        self._tts_select.bind("<<ComboboxSelected>>", lambda _: self._refresh_voice_buttons())
        self._tts_find = ttk.Button(controls, text="한국어 음성 찾기", command=self._find_voices)
        self._tts_find.pack(side="left", padx=(8, 0))
        self._tts_auto_toggle = ttk.Checkbutton(
            audio, text="AI 답변 생성 후 자동으로 읽기 (기본 꺼짐)",
            variable=self._auto_voice,
        )
        self._tts_auto_toggle.pack(anchor="w", pady=(8, 2))
        buttons = ttk.Frame(audio)
        buttons.pack(fill="x")
        self._tts_play = ttk.Button(buttons, text="마지막 AI 답변 읽기", command=self._read_last)
        self._tts_play.pack(side="left")
        self._tts_play.configure(state="disabled")
        self._tts_stop = ttk.Button(buttons, text="소리 중지", command=self._stop_voice)
        self._tts_stop.pack(side="left", padx=(8, 0))
        self._tts_stop.configure(state="disabled")
        ttk.Label(audio, textvariable=self._tts_status, wraplength=580).pack(anchor="w", pady=(5, 0))
        public_chat = ttk.LabelFrame(
            self, text="플랫폼 공개 채팅 수신 → 로컬 AI (송신·실방송 없음)", padding=8)
        # Keep actual channel selection reachable above the expanding transcript.
        public_chat.pack(fill="x", pady=(6, 0), before=model_row)
        self._chat_selector = ttk.Combobox(
            public_chat, textvariable=self._chat_platform,
            values=("트위치", "치지직", "SOOP", "유튜브", "전체"),
            width=8, state="readonly")
        self._chat_selector.pack(side="left", padx=4)
        self._chat_selector.bind("<<ComboboxSelected>>",
                                 lambda _event: self._toggle_multi_channels())
        ttk.Label(public_chat, text="채널 ID / SOOP ID/번호 / YouTube 영상 ID·URL·liveChatId").pack(side="left")
        ttk.Entry(public_chat, textvariable=self._twitch_channel, width=20).pack(
            side="left", padx=5)
        self._twitch_start = ttk.Button(
            public_chat, text="읽기 전용 연결", command=self._start_twitch)
        self._twitch_start.pack(side="left", padx=3)
        self._twitch_end = ttk.Button(
            public_chat, text="읽기 중지", command=self._stop_twitch,
            state="disabled")
        self._twitch_end.pack(side="left", padx=3)
        keyline = ttk.Frame(self)
        keyline.pack(fill="x", before=model_row)
        self._chat_keyline = keyline
        twitch_oauth_line = ttk.Frame(self)
        twitch_oauth_line.pack(fill="x", before=model_row)
        ttk.Label(twitch_oauth_line,
                  text="Twitch chat:read 토큰 (메모리 전용)").pack(side="left")
        ttk.Entry(twitch_oauth_line, textvariable=self._twitch_oauth_token,
                  show="*", width=29).pack(side="left", padx=4)
        ttk.Label(twitch_oauth_line, text="승인 계정 ID").pack(side="left")
        ttk.Entry(twitch_oauth_line, textvariable=self._twitch_oauth_login,
                  width=19).pack(side="left", padx=4)
        oauth_line = ttk.Frame(self)
        oauth_line.pack(fill="x", before=model_row)
        ttk.Label(oauth_line, text="유튜브 OAuth 읽기 토큰 (승인 완료분·메모리에만 보관)").pack(side="left")
        ttk.Entry(oauth_line, textvariable=self._youtube_oauth_token,
                  show="*", width=34).pack(side="left", padx=5)
        self._youtube_oauth_button = ttk.Button(
            oauth_line, text="Google 소유 계정 읽기 승인",
            command=self._begin_owner_youtube_oauth)
        self._youtube_oauth_button.pack(side="left", padx=3)
        ttk.Label(oauth_line, text="승인 후 '내 활성 방송' 입력").pack(
            side="left", padx=2)
        ttk.Label(keyline, text="YouTube API 키 (실행 중 메모리만 사용)").pack(side="left")
        ttk.Entry(keyline, textvariable=self._youtube_api_key, width=46,
                  show="*").pack(side="left", padx=5)
        self._multi_fields = ttk.Frame(self)
        for entries in (
                (("twitch", "트위치 채널", 22), ("chzzk", "치지직 ID", 37)),
                (("soop", "SOOP ID/번호", 22), ("youtube", "유튜브 ID/URL", 37))):
            line = ttk.Frame(self._multi_fields)
            line.pack(fill="x", pady=1)
            for code, label, width in entries:
                ttk.Label(line, text=label).pack(side="left", padx=(4, 3))
                ttk.Entry(line, textvariable=self._multi_channels[code],
                          width=width).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(self, text="공식 Open-LLM-VTuber/Live2D 창으로 채팅 전달 (한 세션 · Ollama 중복 호출 없음)",
                        variable=self._official_live2d).pack(anchor="w", pady=(4, 0), before=model_row)
        ttk.Label(self, textvariable=self._twitch_status, wraplength=600).pack(
            anchor="w", pady=(2, 5), before=model_row)
        ttk.Label(self, textvariable=self._platform_health_status,
                  wraplength=650, justify="left").pack(
            anchor="w", pady=(0, 6), before=model_row)
        # Programmatic restoration and mouse selection both update geometry.
        # A synthetic ComboboxSelected event alone is unreliable on Windows Tk.
        self._chat_platform.trace_add(
            "write", lambda *_args: self._toggle_multi_channels())
        # The existing Tk tab can invoke the official viewer and OBS
        # integration. The official viewer must already be running; the
        # saved character and official project must agree before any send.
        pipeline = ttk.LabelFrame(
            self, text="공식 AI · 실제 Live2D 입 움직임 · OBS 동시 검사", padding=6)
        # Put the manual test above the large chat history/voice controls;
        # at standard 1280x768 it must be reachable without a hidden scroll.
        pipeline.pack(fill="x", pady=(3, 0), before=model_row)
        pipeline_fields = ttk.Frame(pipeline)
        pipeline_fields.pack(fill="x")
        ttk.Label(pipeline_fields, text="OBS 음성 입력").pack(side="left")
        ttk.Entry(pipeline_fields, textvariable=self._pipeline_audio_input,
                  width=21).pack(side="left", padx=(4, 10))
        ttk.Label(pipeline_fields, text="OBS 암호").pack(side="left")
        ttk.Entry(pipeline_fields, textvariable=self._pipeline_obs_password,
                  show="*", width=20).pack(side="left", padx=(4, 0))
        self._pipeline_button = ttk.Button(
            pipeline, text="입력한 질문 한 건으로 실제 음성·Live2D·OBS 검사",
            command=self._start_official_pipeline)
        self._pipeline_button.pack(side="left", pady=(5, 0))
        self._pipeline_cancel_button = ttk.Button(
            pipeline, text="실측 중지 요청", command=self._cancel_official_pipeline,
            state="disabled")
        self._pipeline_cancel_button.pack(side="left", padx=(8, 0), pady=(5, 0))
        self._tts_probe_button = ttk.Button(
            pipeline, text="실제 GPT-SoVITS 음성 단독 합성",
            command=self._start_official_tts_probe)
        self._tts_probe_button.pack(side="left", padx=(8, 0), pady=(5, 0))
        self._tts_obs_button = ttk.Button(
            pipeline, text="실제 GPT-SoVITS 음성 → OBS 입력 검사",
            command=self._start_real_tts_obs_probe)
        self._tts_obs_button.pack(side="left", padx=(8, 0), pady=(5, 0))
        ttk.Label(pipeline, textvariable=self._tts_probe_status,
                  wraplength=580).pack(anchor="w")
        ttk.Label(pipeline, textvariable=self._pipeline_status,
                  wraplength=580).pack(anchor="w")
        self._refresh_memory_count()
        self.after(150, self._poll)

    def _toggle_multi_channels(self) -> None:
        if self._chat_platform.get() == "전체":
            self._multi_fields.pack(fill="x", before=self._chat_keyline, pady=(2, 0))
        else:
            self._multi_fields.pack_forget()

    def _append(self, line: str) -> None:
        # Keep the *visible* native Tk transcript bounded during long shows.
        # This must never filter, drop or reorder AI/chat FIFO events or modify
        # persistent SQLite conversation memory; it only trims older display
        # lines in chunks to avoid an O(n) delete on every received chat.
        self._dialog.configure(state="normal")
        try:
            self._dialog.insert("end", line + "\n\n")
            lines = int(self._dialog.index("end-1c").split(".", 1)[0])
            if lines > 12000:
                self._dialog.delete("1.0", "4001.0")
            self._dialog.see("end")
        finally:
            self._dialog.configure(state="disabled")

    def _refresh_memory_count(self) -> None:
        try:
            if not DEFAULT_MEMORY_FILE.exists():
                self._memory_count.set('저장된 대화: 0개')
                return
            count = ConversationMemory().count()
            self._memory_count.set(f"저장된 대화: {count}개")
        except (OSError, ValueError, Exception) as exc:
            self._memory_count.set("대화 기억 확인 실패")

    def _submit(self) -> None:
        if self._closed or self._busy or self._pipeline_busy or getattr(self, "_tts_probe_busy", False):
            return
        # A stopped public reader can still have an LLM turn writing SQLite.
        # Do not start a separate Ollama conversation against that same
        # committed character or memory until every prior AI worker exits.
        if self._twitch_session is not None or getattr(self, "_twitch_active_workers", None):
            self._input_info.set(
                "공개 채팅 AI/이전 응답의 기억 저장이 종료된 뒤 수동 질문을 보낼 수 있습니다.")
            return
        model = self._model_name.get().strip()
        text = self._input.get().strip()
        if not model:
            messagebox.showinfo("모델 입력", "PC에 이미 설치된 Ollama 모델 이름을 입력해 주세요.", parent=self)
            return
        if not text or len(text) > 4000:
            messagebox.showinfo("메시지 입력", "1~4000자 메시지를 입력해 주세요.", parent=self)
            return
        self._busy = True
        self._send.configure(state="disabled")
        self._input_info.set("로컬 AI의 응답을 확인하고 있습니다…")
        self._append("운영자: " + text)
        self._input.set("")
        threading.Thread(target=self._work, args=(model,text),daemon=True).start()

    def _work(self, model: str, text: str) -> None:
        try:
            result = run_local_chat(model, text, use_committed_gui_character=True)
        except Exception as exc:
            self._results.put(("error", type(exc).__name__))
        else:
            self._results.put(("ok",result))

    def _start_official_tts_probe(self) -> None:
        """Actual authorized GPT-SoVITS inference from the saved official voice."""
        if (self._closed or self._busy or self._pipeline_busy
                or self._tts_probe_busy or self._twitch_session is not None
                or getattr(self, "_twitch_active_workers", None)):
            self._tts_probe_status.set(
                "다른 AI·채팅·음성 검사 작업이 끝난 뒤 실제 합성을 실행하세요.")
            return
        text = self._input.get().strip()
        if not 1 <= len(text) <= 200 or any(ord(ch) < 32 for ch in text):
            self._tts_probe_status.set("한국어 시험 발화 1~200자를 입력하세요.")
            return
        try:
            from . import original_plan_frontend as frontend
            from .official_tts_readiness import require_saved_korean_gpt_sovits
            project = frontend._native_viewer_project
            if project is None:
                raise ValueError("공식 Live2D 프로젝트가 선택되지 않았습니다.")
            require_saved_korean_gpt_sovits(project)
        except Exception as exc:
            self._tts_probe_status.set(
                "기존 공식 음성 설정·참조 WAV/FLAC을 확인하세요 ("
                + type(exc).__name__ + ")")
            return
        if not messagebox.askyesno(
            "실제 한국어 GPT-SoVITS 합성 승인",
            "선택한 기존 공식 프로젝트의 한국어 참조 음성과 대사를 사용해 "
            "로컬 GPT-SoVITS /tts 서버에 입력 문장 한 건을 실제 합성합니다. "
            "참조 음성의 소유·동의·라이선스 권리가 있고 이번 사용을 승인합니까? "
            "소리 재생·파일 저장·모델 학습·방송 송출·채팅 발신은 하지 않습니다. "
            "생성 WAV의 구조·음성 신호만 검사하며 Live2D·OBS 성공을 의미하지 않습니다.",
            parent=self):
            self._tts_probe_status.set("실제 합성을 승인하지 않아 요청하지 않았습니다.")
            return
        self._tts_probe_busy = True
        self._tts_probe_button.configure(state="disabled")
        if getattr(self, "_tts_obs_button", None) is not None:
            self._tts_obs_button.configure(state="disabled")
        self._pipeline_button.configure(state="disabled")
        self._send.configure(state="disabled")
        self._tts_probe_status.set("승인받은 로컬 GPT-SoVITS 실제 합성 중…")
        threading.Thread(
            target=self._work_official_tts_probe,
            args=(project, text), daemon=True).start()

    def _work_official_tts_probe(self, project, text: str) -> None:
        try:
            from .official_tts_readiness import synthesize_saved_korean_gpt_sovits
            actual = synthesize_saved_korean_gpt_sovits(
                project, text, operator_approved=True,
                rights_confirmed=True, timeout=90)
        except Exception as exc:
            # Never show reference path, TTS URL or upstream traceback.
            self._results.put(("tts_probe_error", type(exc).__name__))
        else:
            self._results.put(("tts_probe_ok", actual))

    def _start_real_tts_obs_probe(self) -> None:
        """Actually synthesize authorized Korean GPT-SoVITS -> OBS one-shot WAV.

        Only the bridge's newly created, temporary OFFLINE audio source is
        touched. An installed model and running OBS are needed; CI never
        represents substitute audio as a model success.
        """
        if (self._closed or self._busy or self._pipeline_busy
                or self._tts_probe_busy or getattr(self, "_oauth_busy", False)
                or self._twitch_session is not None
                or getattr(self, "_twitch_active_workers", None)):
            self._tts_probe_status.set(
                "다른 AI·채팅·음성 실측 작업을 종료한 뒤 다시 실행하세요.")
            return
        text = self._input.get().strip()
        password = self._pipeline_obs_password.get()
        if not 1 <= len(text) <= 200 or any(ord(c) < 32 for c in text):
            self._tts_probe_status.set("한국어 시험 발화 1~200자를 입력하세요.")
            return
        if not password:
            self._tts_probe_status.set("기존 OBS WebSocket 암호가 필요합니다.")
            return
        try:
            from . import original_plan_frontend as frontend
            from .official_tts_readiness import read_saved_korean_gpt_sovits_config
            project = frontend._native_viewer_project
            if project is None:
                raise ValueError("공식 Live2D 프로젝트 미선택")
            api_url, reference, reference_text = read_saved_korean_gpt_sovits_config(project)
        except Exception as exc:
            self._tts_probe_status.set(
                "한국어 음성 설정·참조 음성을 확인하세요 ("
                + type(exc).__name__ + ")")
            return
        if not messagebox.askyesno(
            "실제 한국어 GPT-SoVITS → OBS 임시 입력 검사",
            "실제 로컬 GPT-SoVITS 모델과 사용 권리가 확인된 참조 음성으로 "
            "한국어 문장 한 건을 합성합니다. 현재 OBS가 방송/녹화 중이 "
            "아닌 것을 확인한 뒤, OBS 현재 장면에 임시 음성 소스를 만들고 "
            "실제 오디오 미터 신호를 확인한 후 소스를 제거합니다. "
            "임시 WAV 파일도 삭제하며 기존 OBS 소스는 변경하지 않습니다. "
            "실제 음성 합성·임시 OBS 입력 생성과 사용 권리를 이번 1회에 "
            "승인합니까? Live2D 입 움직임과 최종 시청자 송출은 별도 실증입니다.",
            parent=self):
            self._tts_probe_status.set("미승인 · GPT-SoVITS/OBS 요청 없음")
            return
        self._tts_probe_busy = True
        self._tts_probe_button.configure(state="disabled")
        self._tts_obs_button.configure(state="disabled")
        self._pipeline_button.configure(state="disabled")
        self._send.configure(state="disabled")
        self._tts_probe_status.set(
            "승인된 실제 GPT-SoVITS 합성·OBS 임시 음성 미터 확인 중…")
        threading.Thread(
            target=self._work_real_tts_obs_probe,
            args=(reference, reference_text, text, api_url, password),
            daemon=True).start()

    def _work_real_tts_obs_probe(
        self, reference, reference_text: str, text: str,
        api_url: str, obs_password: str,
    ) -> None:
        try:
            from .original_plan_voice_obs_bridge import verify_gpt_sovits_to_obs
            result = verify_gpt_sovits_to_obs(
                reference, reference_text, text,
                api_url=api_url, obs_password=obs_password,
                operator_approved=True, rights_confirmed=True)
        except Exception as exc:
            # No model URL, local audio path, password or raw exception message.
            self._results.put(("tts_obs_error", type(exc).__name__))
        else:
            self._results.put(("tts_obs_ok", result))

    def _start_official_pipeline(self) -> None:
        """Explicitly approved existing native Live2D + OBS observation."""
        if self._closed or self._pipeline_busy or self._busy or getattr(self, "_tts_probe_busy", False):
            return
        if (self._twitch_session is not None
                or getattr(self, "_twitch_active_workers", None)):
            self._pipeline_status.set(
                "공개 채팅 AI 및 이전 응답의 기억 저장이 완전히 끝난 뒤 실측을 시작하세요.")
            return
        text = self._input.get().strip()
        selected_input = self._pipeline_audio_input.get().strip()
        password = self._pipeline_obs_password.get()
        if not 1 <= len(text) <= 4000 or not selected_input or not password:
            self._pipeline_status.set("질문(1~4000자)·OBS 음성 입력 이름·OBS 암호를 입력하세요.")
            return
        try:
            from .offline_settings import settings_file, active_persona
            from . import original_plan_frontend as frontend
            from .original_plan_studio import inspect_saved_persona_alignment
            from .official_tts_readiness import require_saved_korean_gpt_sovits
            saved = settings_file()
            if (not saved.is_file() or saved.is_symlink()
                    or saved.parent.is_symlink()):
                raise ValueError("먼저 캐릭터 이름·말투·성격을 확정 저장하세요.")
            fields = active_persona(load_settings(saved))
            project = frontend._native_viewer_project
            if project is None or not inspect_saved_persona_alignment(project, fields):
                raise ValueError("저장된 캐릭터·공식 설정·실행 중인 Live2D 창을 확인하세요.")
            require_saved_korean_gpt_sovits(project)
        except (ValueError, OSError, KeyError, RuntimeError) as exc:
            self._pipeline_status.set("공식 캐릭터 실측 준비 실패: 캐릭터 확정 저장·연동 설정 확인 (" + type(exc).__name__ + ")")
            return
        if not messagebox.askyesno(
            "실제 공식 AI·한국어 음성·Live2D·OBS 동시 검사 승인",
            "기존 공식 Live2D 창의 실제 AI에 질문 한 건을 전달합니다. "
            "공식 설정에 따라 기록이나 외부 API 요청이 발생할 수 있으므로 "
            "무료·로컬 모델 설정을 먼저 확인하세요. "
            "참조 음성의 소유·동의·라이선스 권리를 확보했습니까? "
            "이번 검사 동안 OBS 프로그램 화면과 선택 음성 입력의 실제 미터 "
            "및 공식 Live2D RMS/입 움직임을 읽기 전용으로 관찰합니다. "
            "방송/녹화 시작, 채팅 게시, 모델 학습은 수행하지 않습니다. "
            "관찰 성공도 실제 시청자 송출 증거는 아닙니다. "
            "이 한 번만 실행하시겠습니까?",
            parent=self,
        ):
            self._pipeline_status.set("승인 취소 · 실제 질문을 전송하지 않았습니다.")
            return
        try:
            # Re-evaluate the committed persona, not unsaved local GUI fields.
            from .offline_settings import settings_file, active_persona
            from . import original_plan_frontend as frontend
            from .original_plan_studio import inspect_saved_persona_alignment
            from .official_tts_readiness import require_saved_korean_gpt_sovits
            saved = settings_file()
            if (not saved.is_file() or saved.is_symlink()
                    or saved.parent.is_symlink()
                    or active_persona(load_settings(saved)) != fields
                    or frontend._native_viewer_project != project
                    or not inspect_saved_persona_alignment(project, fields)):
                raise ValueError("승인 중 캐릭터/공식 Live2D 설정이 변경됐습니다.")
            require_saved_korean_gpt_sovits(project)
        except (ValueError, OSError, KeyError, RuntimeError) as exc:
            self._pipeline_status.set("변경 감지 · 실제 전송 취소 (" + type(exc).__name__ + ")")
            return
        self._pipeline_busy = True
        self._pipeline_cancel = threading.Event()
        self._pipeline_button.configure(state="disabled")
        if getattr(self, "_pipeline_cancel_button", None) is not None:
            self._pipeline_cancel_button.configure(state="normal")
        self._send.configure(state="disabled")
        self._pipeline_status.set("공식 AI→Live2D와 OBS 실제 화면·음성 관찰 중…")
        threading.Thread(
            target=self._work_official_pipeline,
            args=(text, password, selected_input, self._pipeline_cancel),
            daemon=True,
        ).start()

    def _cancel_official_pipeline(self) -> None:
        if not self._pipeline_busy or self._pipeline_cancel is None:
            return
        self._pipeline_cancel.set()
        if getattr(self, "_pipeline_cancel_button", None) is not None:
            self._pipeline_cancel_button.configure(state="disabled")
        self._pipeline_status.set(
            "중지 요청됨 · 이미 전송된 질문은 취소할 수 없습니다. 검사 종료 후 재실행할 수 있습니다.")

    def _work_official_pipeline(self, text: str, password: str, selected_input: str,
                                cancel_event: threading.Event | None = None) -> None:
        try:
            from .original_plan_full_pipeline import verify_official_chat_live2d_obs
            options = dict(obs_password=password, obs_input_name=selected_input,
                           operator_approved=True, voice_rights_confirmed=True)
            if cancel_event is not None:
                options["cancel_event"] = cancel_event
            outcome = verify_official_chat_live2d_obs(text, **options)
        except Exception as exc:
            # Exceptions may be raised after a server accepted the prompt.
            # Never automatically retry, or print the OBS credential.
            if cancel_event is not None and cancel_event.is_set():
                self._results.put(("pipeline_cancelled", None))
            else:
                self._results.put(("pipeline_error", type(exc).__name__))
        else:
            if cancel_event is not None and cancel_event.is_set():
                self._results.put(("pipeline_cancelled", None))
            else:
                self._results.put(("pipeline_ok", (text, outcome)))

    def _begin_owner_youtube_oauth(self) -> None:
        """Explicit OS-browser-only owner OAuth, never GUI web login."""
        if (self._closed or self._oauth_busy or self._busy
                or self._pipeline_busy or getattr(self, "_tts_probe_busy", False)
                or self._twitch_session is not None
                or getattr(self, "_twitch_active_workers", None)):
            self._twitch_status.set(
                "기존 채팅/AI/방송 읽기 작업 종료 후 소유 Google 읽기를 승인하세요.")
            return
        if not messagebox.askyesno(
            "소유 YouTube 방송 OAuth 인증",
            "Google 공식 브라우저의 소유 계정 동의를 시작합니다. "
            "YouTube 읽기 전용 권한만 요청합니다. "
            "동의 토큰은 프로그램 메모리에만 저장하고 파일·갱신 토큰은 저장하지 "
            "않습니다. 계정·방송 변경, 채팅 발신, 자동 방송 송출은 없습니다. "
            "Google 데스크톱 OAuth 클라이언트 ID가 필요합니다. 계속합니까?",
            parent=self):
            return
        client_id = simpledialog.askstring(
            "Google 데스크톱 OAuth",
            "Google Cloud에서 발급받은 데스크톱 OAuth 클라이언트 ID",
            parent=self)
        if client_id is None:
            return
        client_secret = simpledialog.askstring(
            "Google 데스크톱 OAuth",
            "데스크톱 OAuth 클라이언트 secret (없으면 빈 값)",
            parent=self, show="*")
        if client_secret is None:
            return
        self._oauth_busy = True
        self._youtube_oauth_button.configure(state="disabled")
        self._twitch_status.set("승인된 Google 브라우저에서 YouTube 읽기 동의 대기…")
        threading.Thread(
            target=self._work_owner_youtube_oauth,
            args=(client_id.strip(), client_secret), daemon=True).start()

    def _work_owner_youtube_oauth(self, client_id: str, client_secret: str) -> None:
        try:
            from .youtube_desktop_oauth import authorize_owner_readonly
            token = authorize_owner_readonly(
                client_id, client_secret, operator_approved=True)
        except Exception as exc:
            # No Google error body, authorization code, API token or secret.
            self._results.put(("youtube_oauth_error", type(exc).__name__))
        else:
            self._results.put(("youtube_oauth_ok", token))

    def _start_twitch(self) -> None:
        # Never interleave automatic platform prompts into a one-shot
        # operator-approved official Live2D/OBS session probe.
        if (self._closed or self._twitch_session is not None
                or self._pipeline_busy or getattr(self, "_tts_probe_busy", False)
                or getattr(self, "_oauth_busy", False)):
            return
        if self._busy:
            messagebox.showwarning(
                "수동 AI 작업 중", "진행 중인 수동 AI 질문과 기억 저장이 끝난 뒤 공개 채팅을 연결하세요.",
                parent=self)
            return
        if getattr(self, "_twitch_active_workers", None):
            messagebox.showwarning(
                "이전 AI 작업 종료 대기",
                "이전 채팅의 AI·기억 저장 작업이 끝난 뒤 새 연결을 시작할 수 있습니다.",
                parent=self)
            return
        # Do not silently receive chats that cannot reach the selected AI.
        model = self._model_name.get().strip()
        official = bool(self._official_live2d.get())
        if not official and not model:
            messagebox.showinfo(
                "로컬 AI 모델", "먼저 설치한 Ollama 모델 이름을 입력해 주세요.",
                parent=self)
            return
        if official:
            # Apply the same saved-character/official Korean TTS gate to
            # continuous live chat that the operator's manual probe requires.
            try:
                from .offline_settings import settings_file, active_persona
                from .original_plan_studio import inspect_saved_persona_alignment
                from .official_tts_readiness import require_saved_korean_gpt_sovits
                from . import original_plan_frontend as official_frontend
                saved = settings_file()
                if (not saved.is_file() or saved.is_symlink()
                        or saved.parent.is_symlink()):
                    raise ValueError("먼저 이름·말투·성격을 확정 저장하세요.")
                fields = active_persona(load_settings(saved))
                project = official_frontend._native_viewer_project
                if (project is None
                        or not inspect_saved_persona_alignment(project, fields)):
                    raise ValueError("저장한 캐릭터와 실행 중인 공식 Live2D 설정이 다릅니다.")
                require_saved_korean_gpt_sovits(project)
            except (ValueError, OSError, KeyError, RuntimeError) as exc:
                messagebox.showwarning("공식 AI 연결 준비",
                                       "저장한 캐릭터·음성 설정을 확인하세요 (" +
                                       type(exc).__name__ + ")", parent=self)
                return
        if official and not messagebox.askyesno(
                "공식 AI·Live2D 채팅 연결 승인",
                "연결 후 들어오는 모든 플랫폼 채팅을 기존 공식 Live2D 창의 "
                "Open-LLM-VTuber 서버에 1회씩 전달합니다. 공식 서버 설정에 따라 "
                "AI·음성·기억/외부 접속이 발생할 수 있습니다. "
                "Live2D 창을 먼저 열고 공식 서버의 무료·로컬 모델 설정을 확인했습니까?",
                parent=self):
            return
        choice = self._chat_platform.get()
        types = {"트위치": "twitch", "치지직": "chzzk",
                 "SOOP": "soop", "유튜브": "youtube"}
        code = types.get(choice)
        try:
            saved_platforms = load_settings()["platforms"]
        except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
            messagebox.showinfo("플랫폼 설정",
                                "저장된 플랫폼 설정을 확인하세요 (" + type(exc).__name__ + ")",
                                parent=self)
            return
        if (not isinstance(saved_platforms, (list, tuple)) or not saved_platforms
                or any(type(name) is not str for name in saved_platforms)):
            messagebox.showinfo("플랫폼 설정", "저장된 플랫폼 선택을 확인하세요.", parent=self)
            return
        if (len(set(saved_platforms)) != len(saved_platforms)
                or any(name not in ("twitch","chzzk","soop","youtube")
                       for name in saved_platforms)):
            messagebox.showinfo("플랫폼 설정", "저장된 플랫폼 선택을 확인하세요.", parent=self)
            return
        if choice == "전체":
            missing = [name for name in saved_platforms
                       if not self._multi_channels[name].get().strip()]
            if missing:
                messagebox.showinfo("채널 입력",
                                    "선택한 플랫폼의 채널을 모두 입력하세요: " +
                                    ", ".join(missing), parent=self)
                return
        elif code not in saved_platforms:
            messagebox.showinfo("플랫폼 선택",
                                "방송 설정에서 선택한 플랫폼을 저장해 주세요.", parent=self)
            return
        try:
            channel = self._twitch_channel.get().strip()
            # Every event is bound to the session that produced it. A previous
            # connection can finish after a new one starts; never let that
            # previous listener's late messages enter the new AI queue.
            session = None
            emit = lambda kind, item: LocalChatTab._enqueue_public_event(
                self, session, kind, item)
            if choice == "전체":
                twitch_token = getattr(self, "_twitch_oauth_token", None)
                twitch_login = getattr(self, "_twitch_oauth_login", None)
                multi_options = {
                    "youtube_api_key": self._youtube_api_key.get(),
                    "youtube_oauth_token": self._youtube_oauth_token.get()}
                if twitch_token is not None and twitch_token.get():
                    multi_options["twitch_oauth_token"] = twitch_token.get()
                    multi_options["twitch_oauth_login"] = (
                        twitch_login.get().strip() if twitch_login is not None else "")
                session = MultiPlatformReadOnlySession(
                    {name: self._multi_channels[name].get().strip()
                     for name in saved_platforms}, emit, **multi_options)
            else:
                # 단일 플랫폼도 4플랫폼과 동일한 기존 재연결 관리자에
                # 연결한다. 채팅 원본은 종류/내용/순서 그대로 AI 단일 FIFO로
                # 전달하며, 오류 후 커서를 초기화하거나 전체 정지하지 않는다.
                single_options = {}
                if code == "twitch":
                    twitch_token = self._twitch_oauth_token.get()
                    if twitch_token:
                        single_options["twitch_oauth_token"] = twitch_token
                        single_options["twitch_oauth_login"] = (
                            self._twitch_oauth_login.get().strip())
                elif code == "youtube":
                    single_options["youtube_api_key"] = self._youtube_api_key.get()
                    single_options["youtube_oauth_token"] = (
                        self._youtube_oauth_token.get())
                session = MultiPlatformReadOnlySession(
                    {code: channel}, emit, **single_options)
        except (ValueError, TypeError, OSError, RuntimeError) as exc:
            messagebox.showinfo("채팅 채널",
                                "채널·API 설정을 확인하세요 (" + type(exc).__name__ + ")",
                                parent=self)
            return
        self._twitch_session = session
        self._platform_health_updated_at = 0.0
        self._platform_health_status.set("플랫폼별 채팅방 입장 대기 · 수신/누락 미확인")
        self._twitch_received = 0
        self._twitch_replied = 0
        self._twitch_ai_failures = 0
        self._twitch_reader_finished = False
        self._twitch_reader_error = None
        inbox = queue.SimpleQueue()
        with self._live_ingress_lock:
            self._ai_arrival_times = queue.SimpleQueue()
            self._twitch_ai_inbox = inbox
        # The user's real Windows receiver gets fresh private diagnostics on
        # each connection; no message text or credentials enter this meter.
        started_at = time.monotonic()
        self._live_latency_metrics = LiveLatencyMetrics(started_at)
        self._platform_live_metrics = {
            name: LiveLatencyMetrics(started_at)
            for name in session._channels
        }
        self._twitch_active_workers.add(session)
        # One worker calls the EXISTING local Ollama conversation in order.
        # No extra model service, intentional delay or platform chat posting.
        threading.Thread(
            target=self._work_twitch_ai, args=(model, inbox, official, session),
            daemon=True,
        ).start()
        self._twitch_start.configure(state="disabled")
        self._twitch_end.configure(state="normal")
        self._twitch_status.set(choice + " 채팅 연결 요청 중 · 실제 수신 대기")
        threading.Thread(target=self._work_twitch, args=(session,), daemon=True).start()

    def _enqueue_public_event(self, session, kind, item, *, limit: int = 4096) -> bool:
        """Back-pressure on the network reader, never on the Tk GUI thread.

        No text/content deduplication and no rejected ordinary viewer chat.
        Bound both the Tk event backlog AND the serial AI work backlog: the
        latter can grow without limit if viewers arrive faster than the
        locally installed model can answer. This is reader-side only and
        never blocks Tk's event handling. On Stop, wake even a full queue.
        The single reader preserves incoming event order within each session.
        """
        if type(limit) is not int or limit < 1:
            raise ValueError("채팅 이벤트 큐 용량 설정 오류")
        # GUI 이벤트 큐 또는 AI FIFO가 밀려도 실제 수신 시작 시각을
        # 나중에 새로 찍지 않는다. 네트워크 수신기 콜백에서 한 번만 찍는다.
        stamped_item = (_ReaderTimestampedChat(item, time.monotonic())
                        if kind == "chat" else item)
        while not getattr(self, "_closed", False):
            if session is None or session._stop.is_set():
                return False
            pending_ai = getattr(self, "_twitch_ai_inbox", None)
            # A pending Tk message can still flow into the AI FIFO. Do not
            # discard its data: pause reading until the serial AI worker
            # actually drains committed work.
            ai_backlog = pending_ai.qsize() if pending_ai is not None else 0
            if self._results.qsize() < limit and ai_backlog < limit:
                if kind == "chat" and isinstance(session, MultiPlatformReadOnlySession):
                    # 실제 네트워크 수신은 Tk 화면 출력보다 먼저 로컬 AI
                    # FIFO에 들어간다. Tk의 128건/주기 표시 지연이 추론
                    # 시작 지연에 그대로 더해지는 병목을 제거한다.
                    # 화면에는 같은 사건을 한 번만 전달하고 AI 이중 등록을 금지.
                    with self._live_ingress_lock:
                        if (session is not self._twitch_session
                                or session._stop.is_set() or self._closed):
                            return False
                        inbox = self._twitch_ai_inbox
                        arrivals = self._ai_arrival_times
                        if inbox is None or arrivals is None:
                            return False
                        if self._results.qsize() < limit and inbox.qsize() < limit:
                            arrivals.put(stamped_item.reader_received_at)
                            self._results.put(("twitch_scoped", (
                                session, "twitch_chat", _ReaderTimestampedChat(
                                    item, stamped_item.reader_received_at,
                                    ai_prequeued=True))))
                            inbox.put(item)
                            return True
                else:
                    # 기존 직접 GUI 호출·상태 알림 경로는 보존한다.
                    self._results.put(("twitch_scoped", (
                        session, "twitch_" + kind, stamped_item)))
                    return True
            session._stop.wait(0.02)
        return False

    def _work_twitch(self, session: TwitchReadOnlySession) -> None:
        try:
            session.run()
        except Exception as exc:
            self._results.put(("twitch_scoped", (session, "twitch_error", type(exc).__name__)))
        finally:
            self._results.put(("twitch_scoped", (session, "twitch_finished", session)))

    def _work_twitch_ai(self, model: str, inbox: queue.SimpleQueue,
                        official: bool = False, session=None, *,
                        reply_function=None) -> None:
        # Old direct-call regression contracts still use unscoped result
        # events; real UI connections always provide their unique session.
        def report(kind, value):
            if session is not None and session._stop.is_set():
                # Do not expose stale replies or start voice after Stop.
                return
            if session is None:
                self._results.put((kind, value))
            else:
                self._results.put(("twitch_scoped", (session, kind, value)))
        local_runner: LocalChatRunner | None = None
        try:
            while True:
                chat = inbox.get()
                if chat is None or (session is not None and session._stop.is_set()):
                    break
                arrivals = getattr(self, "_ai_arrival_times", None)
                try:
                    accepted_at = (arrivals.get_nowait()
                                   if arrivals is not None else None)
                except queue.Empty:
                    accepted_at = None

                # Measure the actual reader callback + Tk/FIFO waiting separately
                # from model execution; preserve the legacy latency event.
                model_started_at = time.monotonic()
                attempt_failed = False

                def report_measured_elapsed():
                    if accepted_at is not None:
                        ended_at = time.monotonic()
                        elapsed = ended_at - accepted_at
                        if math.isfinite(elapsed) and elapsed >= 0:
                            report("twitch_ai_latency", elapsed)
                            if getattr(self, "_live_latency_metrics", None) is not None:
                                wait = max(0.0, model_started_at - accepted_at)
                                inference = max(0.0, ended_at - model_started_at)
                                report("twitch_ai_timing", (
                                    wait, inference, elapsed, attempt_failed))
                                if session is not None:
                                    # 같은 실제 처리 사건을 출처 플랫폼별로
                                    # 계수한다. 기존 전체 FIFO 측정도 유지.
                                    report("twitch_ai_platform_timing", (
                                        getattr(chat, "platform", "twitch"),
                                        wait, inference, elapsed, attempt_failed))
                if official:
                    # Official WebView2 owns the AI, GPT-SoVITS audio and Cubism
                    # model in ONE upstream conversation. Never duplicate this
                    # turn by also submitting to the separate Ollama model.
                    try:
                        from .original_plan_frontend import send_to_native_live2d_session_with_observation
                        evidence = send_to_native_live2d_session_with_observation(
                            chat.text, operator_approved=True, duration=8)
                    except Exception as exc:
                        attempt_failed = True
                        report("twitch_ai_error", (chat, type(exc).__name__))
                    else:
                        attempt_failed = not bool(evidence.verified_signal)
                        report("twitch_live2d_ok", (chat, evidence))
                    finally:
                        report_measured_elapsed()
                    continue
                try:
                    actor = "[" + {"twitch":"트위치","chzzk":"치지직",
                        "soop":"SOOP","youtube":"유튜브"}.get(
                            getattr(chat, "platform", "twitch"), "트위치") + "] " + chat.sender
                    if reply_function is None:
                        # 한 번 선택한 로컬 Ollama·캐릭터/기억 경로를
                        # 동일 수신 워커 내에서만 보유한다. 다른 방송
                        # 세션과 공유하지 않고 원래 단일 FIFO를 유지한다.
                        if local_runner is None:
                            local_runner = LocalChatRunner(
                                model, use_committed_gui_character=True)
                        result = local_runner.reply(chat.text, sender=actor)
                    else:
                        result = reply_function(
                            model, chat.text, sender=actor,
                            use_committed_gui_character=True)
                except Exception as exc:
                    attempt_failed = True
                    report("twitch_ai_error", (chat, type(exc).__name__))
                else:
                    report("twitch_ai_ok", (chat, result))
                finally:
                    report_measured_elapsed()
            # The reader can reach EOF while the serial model is still replying.
            # This marker follows EVERY accepted AI result in the same results FIFO.
            if session is not None and not session._stop.is_set():
                report("twitch_ai_finished", session)

        finally:
            # Stopping a reader is not the same as completing an AI turn.
            # This event is processed by Tk even if the originating session
            # was stopped or replaced; it never touches a user memory file.
            if session is not None and session in getattr(self, "_twitch_active_workers", ()):
                self._results.put(("twitch_ai_worker_exited", session))
    def _stop_twitch(self) -> None:
        session = self._twitch_session
        if session is None:
            return
        session.stop()
        meter = getattr(self, "_live_latency_metrics", None)
        if meter is not None:
            meter.stop(time.monotonic())
            self._append("[로컬 수신 종료] " + meter.snapshot(time.monotonic()).describe())
        for platform_meter in getattr(self, "_platform_live_metrics", {}).values():
            platform_meter.stop(time.monotonic())
        with self._live_ingress_lock:
            if self._twitch_ai_inbox is not None:
                # Stop 뒤 새 채팅이 종료 표식 다음에 등록되지 않도록 한다.
                self._twitch_ai_inbox.put(None)
            self._twitch_ai_inbox = None
        # Do not keep the UI locked waiting for a stalled socket/HTTP reader.
        # Each late reader/AI event carries this original session identity;
        # _poll discards it after a restart instead of contaminating the new
        # connection's FIFO, counts or persona.
        self._twitch_session = None
        self._platform_health_status.set("플랫폼별 수신 종료 · 시청자 무누락 여부 미확인")
        self._twitch_reader_finished = False
        if getattr(self, "_twitch_start", None) is not None:
            self._twitch_start.configure(state="normal")
        if getattr(self, "_twitch_end", None) is not None:
            self._twitch_end.configure(state="disabled")
        if getattr(self, "_twitch_status", None) is not None:
            self._twitch_status.set("운영자가 공개 채팅 연결을 중지했습니다. 남은 AI 작업은 폐기합니다.")

    def destroy(self) -> None:
        self._closed = True
        if self._pipeline_cancel is not None:
            self._pipeline_cancel.set()
        self._queued_voice.clear()
        self._pipeline_obs_password.set("")
        # YouTube API key is memory-only, and must not survive GUI shutdown.
        self._youtube_api_key.set("")
        self._youtube_oauth_token.set("")
        self._twitch_oauth_token.set("")
        self._twitch_oauth_login.set("")
        self._stop_twitch()
        if self._twitch_ai_inbox is not None:
            self._twitch_ai_inbox.put(None)
            self._twitch_ai_inbox = None
        super().destroy()

    def _update_platform_health(self) -> None:
        """4플랫폼 실제 콜백/재연결/AI 적체를 Windows UI에서 읽기 전용 관찰."""
        session = self._twitch_session
        if session is None:
            return
        now = time.monotonic()
        if now - self._platform_health_updated_at < 5:
            return
        read = getattr(session, "try_reconnect_snapshot", None)
        snapshot = read() if callable(read) else None
        if snapshot is None:
            return
        self._platform_health_updated_at = now
        labels = {"twitch": "트위치", "chzzk": "치지직",
                  "soop": "SOOP", "youtube": "유튜브"}
        lines = []
        for code, state in snapshot.items():
            if state["수신기종료"]:
                phase = "읽기종료"
            elif state["현재공백"]:
                phase = "재연결중"
            elif state["채팅방입장"]:
                phase = "입장확인"
            else:
                phase = "입장대기"
            idle = state["마지막채팅콜백경과초"]
            idle_label = ("채팅 콜백 아직 없음" if idle is None
                          else f"마지막 콜백 {idle:.0f}초 전")
            gap_p95 = state.get("완료공백최근p95초")
            gap_label = ("복구 공백 p95 미측정" if gap_p95 is None
                         else f"최근 복구 공백 p95 {gap_p95:.1f}초")
            observed_ratio = state.get("관측입장시간비율")
            ratio_label = ("입장 시간비율 미측정" if observed_ratio is None
                           else f"입장 관측비율 {observed_ratio * 100:.1f}%")
            platform_meter = getattr(
                self, "_platform_live_metrics", {}).get(code)
            if platform_meter is not None:
                ai = platform_meter.snapshot(now)
                p95 = ("미측정" if ai.total_p95 is None
                       else f"{ai.total_p95:.2f}초")
                wait_p95 = ("미측정" if ai.wait_p95 is None
                            else f"{ai.wait_p95:.2f}초")
                model_p95 = ("미측정" if ai.inference_p95 is None
                             else f"{ai.inference_p95:.2f}초")
                ai_status = (
                    f" / AI 등록 {ai.accepted}건 / 종결 {ai.completed}건"
                    f" / AI 실패 {ai.failed}건 / 미종결 {ai.unterminated}건"
                    f" / 로컬 3초 초과 {ai.over_three_seconds}건"
                    f" / 최근 p95 {p95}(대기 {wait_p95}, 처리 {model_p95})")
            else:
                ai_status = " / AI 플랫폼별 실측 미시작"
            lines.append(
                f"{labels.get(code, code)} {phase} · 콜백 {state['콜백수신']}건"
                f" / GUI 전달 {state['콜백전달완료']}건"
                f" / 전달 오류 {state['콜백전달오류']}건"
                f" / 중단 {state['콜백전달중단']}건"
                f" / 전달 최대 {state['콜백전달최대초']:.2f}초"
                f" / 재연결 {state['재연결완료']}회"
                f" / 읽기 시도 {state['실제읽기시도']}회"
                f" / 읽기 실패 {state['실제읽기실패']}회"
                f" / 입장 관측 {state['입장관측누적초']:.0f}초"
                f" / 관측 공백 {state['관측공백초']:.1f}초"
                f" / 완료 공백 최장 {state['완료공백최장초']:.1f}초"
                f" / 복구 공백 3초 초과 {state['완료공백3초초과']}건"
                f" / {gap_label} / {ratio_label} / {idle_label}"
                + ai_status
            )
        inbox = self._twitch_ai_inbox
        pending = inbox.qsize() if inbox is not None else 0
        self._platform_health_status.set(
            "플랫폼별 실제 수신 진단 (무누락·24시간·시청자 지연 미검증):\n"
            + "\n".join(lines)
            + f"\nGUI 이벤트 대기 {self._results.qsize()}건"
            + f" / 로컬 AI FIFO 대기 {pending}건"
        )

    def _poll(self) -> None:
        if self._closed:
            return
        self._update_platform_health()
        try:
            processed = 0
            while True:
                # Yield Tk's main thread after a bounded slice; do not drop,
                # filter, reorder or delay individual viewer messages in
                # the FIFO. A large live-chat surge cannot freeze the GUI.
                if processed >= 128:
                    if not self._closed:
                        # An exact multiple of the slice size does not need
                        # an extra 1ms wake-up when the queue is already empty.
                        delay = 1 if not self._results.empty() else 150
                        self.after(delay, self._poll)
                    return
                kind, payload = self._results.get_nowait()
                processed += 1
                if kind in ("youtube_oauth_ok", "youtube_oauth_error"):
                    self._oauth_busy = False
                    self._youtube_oauth_button.configure(state="normal")
                    if kind == "youtube_oauth_ok":
                        self._youtube_oauth_token.set(payload)
                        self._twitch_status.set(
                            "소유 Google 읽기 동의 완료 · 메모리 토큰 준비"
                            " · 채널에 '내 활성 방송' 선택 후 수신 시작"
                            " · 실제 수신은 아직 미실행")
                    else:
                        self._twitch_status.set(
                            "소유 Google 읽기 인증 실패 (" + str(payload)
                            + ") · 계정/클라이언트/브라우저 설정 확인")
                    continue
                if kind == "twitch_ai_worker_exited":
                    # Always consume the lifecycle marker, even from a
                    # stopped session. Scoped chat data is still discarded.
                    workers = getattr(self, "_twitch_active_workers", None)
                    if workers is not None:
                        workers.discard(payload)
                    continue
                if kind == "twitch_scoped":
                    source_session, kind, payload = payload
                    if source_session is not self._twitch_session:
                        # Stale connection/worker output is never counted,
                        # displayed, or passed to another session's AI.
                        continue
                    stopped = getattr(source_session, "_stop", None)
                    if (stopped is not None and stopped.is_set()
                            and kind != "twitch_finished"):
                        continue
                if kind.startswith("twitch_"):
                    if kind == "twitch_connected":
                        self._twitch_status.set(
                            self._chat_platform.get() + " " + str(payload) +
                            " 서버 소켓 연결 · 채팅방 입장 미확인")
                    elif kind == "twitch_ready":
                        self._twitch_status.set(
                            self._chat_platform.get() + " " + str(payload) +
                            " 채팅방 입장 확인 · 실제 채팅 대기")
                    elif kind == "twitch_chat":
                        # 이전 직접 GUI 테스트와 기존 플랫폼 채팅 객체는 보존.
                        # 실제 수신기 출처 이벤트만 콜백 원시각을 사용한다.
                        accepted_at = time.monotonic()
                        ai_prequeued = False
                        if isinstance(payload, _ReaderTimestampedChat):
                            accepted_at = payload.reader_received_at
                            ai_prequeued = payload.ai_prequeued
                            payload = payload.message
                        meter = getattr(self, "_live_latency_metrics", None)
                        if meter is not None:
                            meter.accept()
                        self._twitch_received += 1
                        name = {"twitch":"트위치","chzzk":"치지직",
                                "soop":"SOOP","youtube":"유튜브"}.get(
                                    getattr(payload, "platform", "twitch"), "트위치")
                        self._append("[" + name + " #" + payload.channel + "] "
                                     + payload.sender + ": " + payload.text)
                        # Every incoming message, including duplicates, is
                        # queued regardless of the status of previous replies.
                        if self._twitch_ai_inbox is not None:
                            platform = getattr(payload, "platform", "twitch")
                            platform_meter = getattr(
                                self, "_platform_live_metrics", {}).get(platform)
                            if platform_meter is not None:
                                platform_meter.accept()
                            if not ai_prequeued:
                                # 기존 GUI 직접 호출만 여기서 AI에 등록한다.
                                # 네트워크 실제 콜백은 이미 1회 등록됨.
                                arrivals = getattr(self, "_ai_arrival_times", None)
                                if arrivals is not None:
                                    arrivals.put(accepted_at)
                                self._twitch_ai_inbox.put(payload)
                        self._twitch_status.set(
                            "실제 채팅 " + str(self._twitch_received)
                            + "건 · AI 응답 " + str(self._twitch_replied)
                            + "건 · AI 오류 " + str(self._twitch_ai_failures) + "건")
                    elif kind == "twitch_ai_ok":
                        chat, result = payload
                        self._twitch_replied += 1
                        # 서버가 보고한 실제 모델 로딩/입력/생성 시간만 표시.
                        # 시청자 전달이나 송출 구간 시간으로 잘못 해석하지 않는다.
                        timing = getattr(result, "ollama_server_timings_seconds", None)
                        if (isinstance(timing, dict) and
                                (self._twitch_replied <= 3
                                 or self._twitch_replied % 25 == 0)):
                            parts = []
                            for name, label in (
                                ("load_duration", "모델 로딩"),
                                ("prompt_eval_duration", "입력 처리"),
                                ("eval_duration", "답변 생성")):
                                seconds = timing.get(name)
                                if (type(seconds) in (int, float)
                                        and math.isfinite(seconds) and seconds >= 0):
                                    parts.append(f"{label} {seconds:.3f}초")
                            if parts:
                                self._append("[Ollama 서버 단계 실측] " +
                                             " / ".join(parts) +
                                             " · 로컬 서버 내부 시간, 시청자 지연 미검증")
                        self._append(
                            "AI → [" + {"twitch":"트위치","chzzk":"치지직",
                             "soop":"SOOP","youtube":"유튜브"}.get(
                                getattr(chat, "platform", "twitch"), "트위치") + "] "
                             + chat.sender + ": " + result.reply)
                        self._last_reply = result.reply
                        self._memory_count.set(
                            f"저장된 대화: {result.remembered_count}개")
                        self._refresh_voice_buttons()
                        selected = self._tts_voices.get(self._voice_name.get())
                        if should_auto_read(self._auto_voice.get(), selected, result.reply):
                            self._queue_voice_reply(result.reply, selected)
                        self._twitch_status.set(
                            "실제 채팅 " + str(self._twitch_received)
                            + "건 · AI 응답 " + str(self._twitch_replied)
                            + "건 · AI 오류 " + str(self._twitch_ai_failures) + "건")
                    elif kind == "twitch_live2d_ok":
                        chat, evidence = payload
                        if evidence.verified_signal:
                            self._twitch_replied += 1
                            self._append("공식 AI·Live2D 입력 및 입 움직임 확인: " + chat.sender)
                        else:
                            self._twitch_ai_failures += 1
                            self._append("공식 AI 질문 전달됨 · 입 움직임 실증 미충족: " + chat.sender)
                        self._twitch_status.set(
                            "공식 Live2D 성공 " + str(self._twitch_replied) +
                            "건 · 미검증/오류 " + str(self._twitch_ai_failures) + "건")
                    elif kind == "twitch_ai_error":
                        chat, detail = payload
                        self._twitch_ai_failures += 1
                        self._append(
                            "[플랫폼 AI 처리 실패] " + chat.sender + ": " + detail)
                        self._twitch_status.set(
                            "AI 처리 실패 " + str(self._twitch_ai_failures)
                            + "건 · 성공 응답으로 계산하지 않음")
                    elif kind == "twitch_ai_platform_timing":
                        # 실제 단일 AI FIFO에서 종결된 플랫폼별 사건만 계수.
                        # GUI 결과 처리 이전 대기나 서버 게시 누락은 증명하지 않는다.
                        code, wait, inference, total, failed = payload
                        platform_meter = getattr(
                            self, "_platform_live_metrics", {}).get(code)
                        if platform_meter is not None:
                            platform_meter.terminal(
                                wait, inference, total, failed)
                    elif kind == "twitch_ai_timing":
                        # Real GUI receiver's local FIFO wait and AI time,
                        # no inferred OBS/video/audience delivery timestamps.
                        meter = getattr(self, "_live_latency_metrics", None)
                        if meter is not None:
                            valid = meter.terminal(*payload)
                            if valid and (meter.completed <= 3
                                          or meter.completed % 25 == 0):
                                self._append(
                                    "[로컬 채팅 실측] "
                                    + meter.snapshot(time.monotonic()).describe())
                            elif not valid:
                                self._append(
                                    "[로컬 채팅 실측] 시각 데이터 오류 또는 수신 종료 "
                                    "· 해당 메시지는 성공 판정에서 제외")
                    elif kind == "twitch_ai_latency":
                        # This is *not* transport-to-viewer latency. It is
                        # GUI acceptance + local queue wait + model processing.
                        if type(payload) in (int, float) and math.isfinite(payload) and payload >= 0:
                            flag = " · 3초 초과" if payload > 3 else ""
                            self._twitch_status.set(
                                f"AI 대기·처리 {payload:.2f}초 (수신기 콜백부터){flag}"
                                " · 플랫폼 서버 이전·시청자 전달 시간은 미측정")
                    elif kind == "twitch_reader_stopped":
                        # A single channel can disconnect without terminating
                        # other transports or dropping queued AI replies.
                        self._append("수신기 상태: " + str(payload))
                        self._twitch_status.set("플랫폼별 수신 상태: " + str(payload))
                    elif kind == "twitch_error":
                        meter = getattr(self, "_live_latency_metrics", None)
                        if meter is not None:
                            meter.reader_fault()
                        self._twitch_reader_error = str(payload)
                        self._twitch_status.set(
                            "실제 " + self._chat_platform.get() +
                            " 읽기 오류: " + str(payload))
                    elif kind == "twitch_finished":
                        if payload is self._twitch_session:
                            self._twitch_reader_finished = True
                            if self._twitch_ai_inbox is not None:
                                self._twitch_ai_inbox.put(None)
                                self._twitch_ai_inbox = None
                            stopped = getattr(payload, "_stop", None)
                            if stopped is not None and stopped.is_set():
                                # Explicit Stop discards queued work as requested.
                                self._twitch_session = None
                                self._twitch_reader_finished = False
                                self._twitch_start.configure(state="normal")
                                self._twitch_end.configure(state="disabled")
                            else:
                                error = getattr(self, "_twitch_reader_error", None)
                                self._twitch_status.set(
                                    ("채팅 수신 오류: " + error + " · " if error
                                     else "채팅 수신 종료 · ") +
                                    "수신 완료한 AI 메시지 응답 처리 중")
                    elif kind == "twitch_ai_finished":
                        if payload is self._twitch_session and getattr(
                                self, "_twitch_reader_finished", False):
                            # Only now have ALL accepted FIFO replies arrived.
                            self._twitch_session = None
                            self._twitch_reader_finished = False
                            self._twitch_start.configure(state="normal")
                            self._twitch_end.configure(state="disabled")
                            error = getattr(self, "_twitch_reader_error", None)
                            self._twitch_status.set(
                                ("채팅 수신 오류: " + error + " · " if error
                                 else "채팅 수신 종료 · ") +
                                "대기 AI 응답 처리 완료 "
                                + str(self._twitch_replied) + "건 · AI 오류 "
                                + str(self._twitch_ai_failures) + "건")
                    continue
                if kind in ("tts_probe_ok", "tts_probe_error",
                            "tts_obs_ok", "tts_obs_error"):
                    self._tts_probe_busy = False
                    self._tts_probe_button.configure(state="normal")
                    if getattr(self, "_tts_obs_button", None) is not None:
                        self._tts_obs_button.configure(state="normal")
                    if not self._pipeline_busy:
                        self._pipeline_button.configure(state="normal")
                    if not self._busy and not self._pipeline_busy:
                        self._send.configure(state="normal")
                    if kind == "tts_obs_error":
                        self._tts_probe_status.set(
                            "실제 GPT-SoVITS→OBS 신호 실증 실패 ("
                            + str(payload) + ") · 음성/OBS/소스 정리 확인 필요")
                    elif kind == "tts_obs_ok":
                        if payload.actual_signal and payload.audio_input_events > 0:
                            self._tts_probe_status.set(
                                "실제 GPT-SoVITS WAV → OBS 임시 입력 미터 신호 확인 "
                                f"· {payload.sample_rate}Hz "
                                f"· 미터 이벤트 {payload.audio_input_events}건 "
                                f"· WAV {payload.wav_duration_seconds:.2f}초 "
                                f"· OBS 관찰 {payload.meter_observation_seconds:.2f}초 "
                                + ("· 전체 WAV 시간 관찰 범위 포함 "
                                   if payload.observation_covers_wav_duration
                                   else "· WAV 후반 미관찰(8초 상한) ")
                                + "· Live2D·시청자 송출은 별도 검사")
                        else:
                            self._tts_probe_status.set(
                                "음성/OBS 실증 미충족 · 유효한 미터 신호 없음")
                    elif kind == "tts_probe_error":
                        self._tts_probe_status.set(
                            "실제 한국어 GPT-SoVITS 합성 실패 (" + str(payload)
                            + ") · 모델/서버/권리 확인 필요 · 미실증")
                    else:
                        seconds = payload.frame_count / payload.sample_rate
                        self._tts_probe_status.set(
                            f"실제 로컬 WAV 합성 확인 · {payload.sample_rate}Hz"
                            f" · {seconds:.2f}초 · {payload.wav_bytes}바이트"
                            " · 재생/Live2D/OBS/방송은 별도 검사")
                    continue
                if kind in ("pipeline_ok", "pipeline_error", "pipeline_cancelled"):
                    # A worker can queue success immediately before the GUI
                    # handles Stop. Check cancellation at the UI boundary too;
                    # a late success must never erase the operator stop request.
                    pending_cancel = getattr(self, "_pipeline_cancel", None)
                    user_cancelled = pending_cancel is not None and pending_cancel.is_set()
                    self._pipeline_busy = False
                    self._pipeline_cancel = None
                    self._pipeline_button.configure(state="normal")
                    if getattr(self, "_pipeline_cancel_button", None) is not None:
                        self._pipeline_cancel_button.configure(state="disabled")
                    if not self._busy:
                        self._send.configure(state="normal")
                    if kind == "pipeline_cancelled" or user_cancelled:
                        self._pipeline_status.set("실측 중지됨 · 이미 전송된 질문은 재전송하지 않았습니다.")
                    elif kind == "pipeline_error":
                        self._pipeline_status.set(
                            "실제 AI·Live2D·OBS 동시 실측 실패/미확인 (" +
                            str(payload) + "). 중복 질문 방지를 위해 자동 재시도하지 않음.")
                    else:
                        sent, evidence = payload
                        lip_ok = bool(evidence.lip.verified_signal)
                        obs_ok = bool(evidence.obs.coherent_media_candidate)
                        self._pipeline_status.set(
                            ("실제 입 움직임 확인" if lip_ok else "립싱크 미확인") +
                            " / " + ("OBS 영상·음성 후보 확인" if obs_ok
                                      else "OBS 화면·음성 경로 미확인") +
                            " / " + ("OBS 관찰 시간 중첩 후보" if getattr(
                                evidence, "temporal_overlap_candidate", False)
                                else "동일 발화 관찰 시간 중첩 미확인") +
                            " / " + ("공식 동일 WS WAV·입·OBS 연관 후보" if getattr(
                                evidence, "same_session_voice_candidate", False)
                                else "공식 음성 WAV·입·OBS 연관 미충족") +
                            " / " + ("OBS 프로그램 영상 프레임 변화 후보" if getattr(
                                evidence.obs, "program_video_change_candidate", False)
                                else "OBS 영상 변화 미확인") +
                            " / " + ("음성·입·영상 관측 결합 후보" if getattr(
                                evidence, "same_session_audio_video_candidate", False)
                                else "음성·입·영상 결합 미충족") +
                            " / " + ("공식 WAV PCM 구조·입·OBS 결합 후보" if getattr(
                                evidence, "same_session_pcm_audio_video_candidate", False)
                                else "공식 WAV PCM 구조·입·OBS 결합 미충족") +
                            " / " + ("WAV 예상 음성창 내 Cubism 입·OBS 미터 실제 시간 중첩 후보" if getattr(
                                evidence, "same_session_pcm_mouth_audio_video_candidate", False)
                                else "WAV 예상 음성창 내 실제 입·OBS 결합 미충족") +
                            " · " + getattr(evidence, "latency_summary_ko", "지연 미측정") +
                            " · 실제 방송/시청자 출력은 별도 실증 필요")
                        if evidence.verified_observation:
                            self._append("공식 AI·Live2D·OBS 동시 읽기 검사 통과: " + sent)
                            if self._input.get().strip() == sent:
                                self._input.set("")
                    continue
                if kind in ("ok", "error"):
                    self._busy = False
                    self._send.configure(state="normal")
                if kind == "ok":
                    self._append("AI: " + payload.reply)
                    self._last_reply = payload.reply
                    self._memory_count.set(f"저장된 대화: {payload.remembered_count}개")
                    self._input_info.set(payload.warning or "로컬 텍스트 응답 완료. 실방송 아님.")
                    self._refresh_voice_buttons()
                    selected = self._tts_voices.get(self._voice_name.get())
                    if should_auto_read(self._auto_voice.get(), selected, payload.reply):
                        self._queue_voice_reply(payload.reply, selected)
                elif kind in ("voices", "voices_error"):
                    self._tts_loading = False
                    self._tts_find.configure(state="normal")
                    if kind == "voices_error":
                        self._tts_status.set("한국어 음성 목록 오류: " + str(payload))
                    else:
                        self._tts_voices = {f"{v.name} ({v.culture})": v for v in payload}
                        options = list(self._tts_voices)
                        self._tts_select.configure(values=options)
                        self._voice_name.set(options[0] if options else "")
                        self._tts_status.set(
                            f"설치된 한국어 음성 {len(options)}개. 자동 재생은 기본 꺼짐."
                            if options else "설치된 한국어 음성이 없습니다. 자동 설치하지 않습니다."
                        )
                    self._refresh_voice_buttons()
                elif kind in ("speech_done", "speech_error"):
                    self._activity.finish("chat_reply")
                    self._tts_busy = False
                    self._tts_find.configure(state="normal")
                    self._tts_stop.configure(state="disabled")
                    self._refresh_voice_buttons()
                    self._tts_status.set(
                        "AI 답변 음성 재생이 완료됐습니다." if kind == "speech_done"
                        else "음성 재생 종료 또는 오류: " + str(payload)
                    )
                    self._start_next_queued_voice()
                else:
                    self._append("연결 오류: " + str(payload))
                    self._input_info.set("PC에 Ollama와 해당 모델이 설치·실행 중인지 확인해 주세요.")
        except queue.Empty:
            pass
        if not self._closed:
            self.after(150,self._poll)

    def _refresh_voice_buttons(self) -> None:
        selected = self._tts_voices.get(self._voice_name.get())
        enabled = self._last_reply is not None and selected is not None
        self._tts_play.configure(
            state="normal" if enabled and not self._tts_busy and not self._tts_loading
            else "disabled"
        )

    def _find_voices(self) -> None:
        if self._tts_busy or self._tts_loading:
            return
        self._tts_loading = True
        self._tts_find.configure(state="disabled")
        self._refresh_voice_buttons()
        self._tts_status.set("PC에 설치된 한국어 음성을 확인 중…")
        threading.Thread(target=self._voice_lookup_worker, daemon=True).start()

    def _voice_lookup_worker(self) -> None:
        try:
            voices = self._voice_player.backend.list_korean_voices()
        except Exception as exc:
            self._results.put(("voices_error", str(exc)))
        else:
            self._results.put(("voices", voices))

    def _read_last(self) -> None:
        if self._last_reply is None or self._tts_busy:
            return
        voice = self._tts_voices.get(self._voice_name.get())
        if voice is None:
            messagebox.showinfo("음성 선택", "먼저 한국어 음성을 선택해 주세요.", parent=self)
            return
        self._begin_read(self._last_reply, voice)

    def _queue_voice_reply(self, reply: str, voice: Voice) -> None:
        """Keep every opted-in AI reply instead of dropping it when audio is busy."""
        if self._closed:
            return
        if not self._tts_busy and not self._queued_voice:
            self._begin_read(reply, voice)
        else:
            self._queued_voice.append((reply, voice))
            self._tts_status.set("음성 재생 대기: " + str(len(self._queued_voice)) + "건")

    def _start_next_queued_voice(self) -> None:
        if not self._closed and not self._tts_busy and self._queued_voice:
            reply, voice = self._queued_voice.popleft()
            self._begin_read(reply, voice)

    def _begin_read(self, reply: str, voice: Voice) -> None:
        if self._tts_busy:
            return
        self._tts_busy = True
        self._activity.start("chat_reply")
        self._tts_find.configure(state="disabled")
        self._tts_stop.configure(state="normal")
        self._refresh_voice_buttons()
        self._tts_status.set("AI 답변을 PC 스피커로 읽는 중… 방송 송출 아님.")
        threading.Thread(target=self._read_worker, args=(reply, voice), daemon=True).start()

    def _read_worker(self, reply: str, voice: Voice) -> None:
        try:
            result = self._voice_player.read(reply, voice)
        except Exception as exc:
            self._results.put(("speech_error", type(exc).__name__))
        else:
            self._results.put(("speech_done", result))

    def _stop_voice(self) -> None:
        self._queued_voice.clear()
        if self._tts_busy and self._voice_player.stop():
            self._tts_status.set("음성 재생 중지를 요청했습니다.")

    def _clear_memory(self) -> None:
        if (self._busy or self._pipeline_busy or getattr(self, "_tts_probe_busy", False)
                or self._twitch_session is not None
                or getattr(self, "_twitch_active_workers", None)):
            messagebox.showwarning("사용 중", "AI·채팅·실측 및 이전 응답의 기억 저장 종료 후에만 삭제할 수 있습니다.", parent=self)
            return
        approved = messagebox.askyesno("대화 기억 삭제", "저장된 대화 기억 전체를 삭제할까요? 되돌릴 수 없습니다.", parent=self)
        if not approved:
            return
        try:
            ConversationMemory().clear()
        except (OSError, Exception) as exc:
            messagebox.showerror(
                "삭제 실패", "기억 저장소 처리 오류 (" + type(exc).__name__ + ")",
                parent=self)
            return
        self._refresh_memory_count()
        self._append("시스템: PC에 저장된 대화 기억을 삭제했어요.")
