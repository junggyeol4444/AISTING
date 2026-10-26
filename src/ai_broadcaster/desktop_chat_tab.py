"""AISTING EXE의 네이티브 로컬 AI 테스트 탭.

네트워크 요청은 운영자가 '텍스트 전송'을 누른 경우에만 한다.
작업자는 UI와 분리된 스레드에서 localhost에 접속하고,
결과만 tkinter 메인 이벤트 루프에서 표시한다.
"""
from __future__ import annotations

import queue
import sys
import threading
import math
import time
from collections import deque
from dataclasses import dataclass, replace
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from .conversation_memory import ConversationMemory, DEFAULT_MEMORY_FILE
from .long_term_conversation_memory import LongTermConversationMemory, archive_path_for
from .desktop_chat import run_local_chat, LocalChatRunner
from .reply_voice import ReplyVoicePlayer, should_auto_read
from .windows_tts import Voice
from .avatar_animation import SpeechActivity
from .twitch_readonly import TwitchReadOnlySession, TwitchReadError
from .multiplatform_readonly import ChzzkReadOnlySession, SoopReadOnlySession, YouTubeReadOnlySession
from .multi_platform_session import (
    MultiPlatformReadOnlySession, SQLITE_DEFERRED_CHAT)
from .live_runtime_metrics import (LiveLatencyMetrics, LiveParseReplyMetrics,
                                   LiveFirstWavLatencyMetrics,
                                   LiveFirstMouthLatencyMetrics)
from .live_queue_wait_observation import LiveQueueWaitTracker
from .live_pcm_cubism_alignment import (
    analyze_pcm_cubism_alignment, LivePcmCubismAlignmentMetrics)
from .offline_settings import load_settings
from .durable_public_chat_queue import DurablePublicChatQueue, PendingChat
from .live_ai_recovery import run_local_fifo_with_recovery
from .approved_live_idle_speech import ApprovedLiveIdleSpeech
from .approved_live_content_agenda import (
    ApprovedLiveContentAgenda, ApprovedLiveContentJournal)
from .approved_live_voice_output import ApprovedLiveVoiceOutput
from .ordered_parallel_local_ai import OrderedParallelLocalAI
from .youtube_page_checkpoint import YouTubePageCheckpoint
from .platform_reconnect_journal import DurablePlatformReconnectJournal


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
        # 공식 창으로 기존 텍스트만 한 번 전달하는 실시간 경로.
        # 립싱크 실증은 기존 운영자 단독 검사에서 그대로 수행한다.
        self._official_fast_send = tk.BooleanVar(value=True)
        # 사용자가 선택할 때만 같은 공식 WS의 실제 첫 RIFF/WAVE
        # 관찰(최대 3초)을 수행. 빠른 전송 기본 동작은 그대로 둔다.
        self._official_first_wav_receipt = tk.BooleanVar(value=False)
        self._idle_live_enabled = tk.BooleanVar(value=False)
        self._idle_live_threshold = tk.StringVar(value="90")
        self._idle_live_words = tk.StringVar()
        self._broadcast_memory_enabled = tk.BooleanVar(value=False)
        self._relevant_memory_enabled = tk.BooleanVar(value=False)
        self._long_term_memory_enabled = tk.BooleanVar(value=False)
        self._parallel_local_ai_enabled = tk.BooleanVar(value=False)
        self._twitch_parallel_ai: OrderedParallelLocalAI | None = None
        self._approved_live_voice_enabled = tk.BooleanVar(value=False)
        self._approved_live_voice_output: ApprovedLiveVoiceOutput | None = None
        self._approved_live_voice_status = tk.StringVar(
            value="실시간 GPT-SoVITS→공식 Cubism→OBS 발화: 비활성 · 기본 꺼짐")
        # 운영자 선택 시 로컬 Ollama 생성 진행 중인 일부 답변을
        # 방송·TTS·SQLite 저장 없이 현재 GUI 상태 줄에만 표시.
        self._local_stream_preview = tk.BooleanVar(value=False)
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
        # 기존 대화/캐릭터 SQLite에 영향을 주지 않는 공개 채팅 미처리 큐.
        self._twitch_chat_spool: DurablePublicChatQueue | None = None
        # 과거 보류 채팅을 FIFO에 재등록하는 동안에도 실수신 채팅을
        # 즉시 별도 SQLite에 영속 기록한다. GUI/AI 전송은 복구 순서 뒤.
        self._recovery_session = None
        # 승인형 OBS 일정에 연결하는 자동 채팅은 GUI에서 운영자
        # 동의 후 발급한 단발성 메모리 토큰을 사용한다. 재시작 저장 없음.
        self._scheduled_chat_permission: object | None = None
        # OBS 예약 GUI에서 운영자가 별도 승인한 콘텐츠 주제만 이 토큰에 귀속.
        self._scheduled_content_plan: dict | None = None
        self._recovery_arrival_times: dict[int, float] = {}
        # 동일 프로세스의 실제 파싱 시각만 별도 보관한다. SQLite의
        # 기존 채팅 본문·스키마를 바꾸지 않고 재시작 뒤 시각은 미확인.
        self._recovery_parsed_times: dict[int, float] = {}
        # 네트워크 읽기와 AI 큐 등록을 분리해 모델 적체 중에도 모든
        # 신규 채팅을 SQLite에 먼저 보존한다. 완료/깨움은 세션마다 초기화.
        self._recovery_wakeup = threading.Event()
        self._recovery_reader_done = threading.Event()
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
        self._platform_parse_reply_metrics: dict[str, LiveParseReplyMetrics] = {}
        self._platform_first_wav_metrics: dict[str, LiveFirstWavLatencyMetrics] = {}
        # 실제 운영자가 선택한 공식 관찰의 첫 Cubism 입 표본 후보를
        # 플랫폼별 별도 기록. WAV·OBS·시청자 전달의 실증은 아니다.
        self._platform_first_mouth_metrics: dict[str, LiveFirstMouthLatencyMetrics] = {}
        # 기존 공식 WAV·Cubism 렌더러 실측 RMS만 시간정렬 후보로 분석한다.
        self._platform_pcm_alignment_metrics: dict[str, LivePcmCubismAlignmentMetrics] = {}
        # 로컬 수신큐 백프레셔와 AI·GUI 적체의 실측값만 메모리에 보관한다.
        self._live_queue_block_events = 0
        self._live_queue_block_total_seconds = 0.0
        self._live_queue_block_max_seconds = 0.0
        self._live_peak_ai_backlog = 0
        self._live_peak_gui_backlog = 0
        # 116회차: 4플랫폼별 실제 수신큐 대기 완료 사건을 분리한다.
        self._live_queue_block_by_platform: dict[str, dict[str, float | int]] = {}
        self._live_queue_wait_tracker = LiveQueueWaitTracker()
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
        ttk.Checkbutton(
            self, text="로컬 Ollama 생성 중 답변 미리보기 (기본 꺼짐 · 방송/저장 없음)",
            variable=self._local_stream_preview,
        ).pack(anchor="w", pady=(2, 1), before=model_row)
        ttk.Checkbutton(
            self, text="로컬 AI: 저장된 실제 과거 대화 중 질문 관련 기록 2건 참고 "
                 "(기본 꺼짐 · SQLite 읽기만 · 별도 모델 없음)",
            variable=self._relevant_memory_enabled,
        ).pack(anchor="w", pady=(2,1), before=model_row)
        ttk.Checkbutton(
            self, text="확정된 대화 전체를 별도 로컬 SQLite에 장기 보관 "
                 "· 질문 관련 과거 검색 (기본 꺼짐 · 기존 최근 5000건 정책 유지)",
            variable=self._long_term_memory_enabled,
            command=self._refresh_memory_count,
        ).pack(anchor="w", pady=(2,1), before=model_row)
        ttk.Checkbutton(
            self, text="로컬 Ollama 동시 선행 추론 최대 4개 · "
                 "답변/SQLite 기억은 채팅 FIFO 순서대로 (기본 꺼짐)",
            variable=self._parallel_local_ai_enabled,
        ).pack(anchor="w", pady=(2,1), before=model_row)
        ttk.Checkbutton(
            self,
            text="공식 창 빠른 전송: 채팅당 8초 립싱크 실증 대기 생략 (전송 확인만 · 기본 켜짐)",
            variable=self._official_fast_send,
        ).pack(anchor="w", pady=(2, 1), before=model_row)
        ttk.Checkbutton(
            self,
            text="빠른 전송 시 같은 공식 WebSocket의 첫 WAV 이벤트도 최대 3초 관찰"
                 " (기본 꺼짐 · 이전 발화와 구분 불가)",
            variable=self._official_first_wav_receipt,
        ).pack(anchor="w", pady=(1, 1), before=model_row)
        idle_row = ttk.Frame(self)
        idle_row.pack(fill="x", before=model_row, pady=(1,1))
        ttk.Checkbutton(
            idle_row, text="공식 Live2D 무채팅 자발 발화 별도 승인 (기본 꺼짐)",
            variable=self._idle_live_enabled).pack(side="left")
        ttk.Label(idle_row, text="기준(30~3600초)").pack(side="left", padx=(8,0))
        ttk.Entry(idle_row, textvariable=self._idle_live_threshold,
                  width=7).pack(side="left", padx=(4,0))
        ttk.Label(self, text="운영자가 지정한 무채팅 발화 문구 (240자 이내 · 한 구간 한 번)",
                  wraplength=580).pack(anchor="w", before=model_row)
        ttk.Entry(self, textvariable=self._idle_live_words,
                  width=75).pack(fill="x", before=model_row)
        ttk.Checkbutton(
            self, text="방송 중 로컬 AI 실제 한국어 음성→공식 Live2D 입→OBS 송출"
                 " 별도 승인 (기본 꺼짐)",
            variable=self._approved_live_voice_enabled,
        ).pack(anchor="w", before=model_row, pady=(3,1))
        ttk.Label(self, textvariable=self._approved_live_voice_status,
                  wraplength=600).pack(anchor="w", before=model_row)
        ttk.Button(
            self, text="실제 방송 한국어 발화 시도·중단·전달불명 기록 보기",
            command=self._show_approved_voice_history,
        ).pack(anchor="w", before=model_row, pady=(1,2))
        ttk.Button(
            self, text="이전 방송 미발화 음성 직접 확인·동일 방송 승인 후 인계",
            command=self._review_previous_voice_pending,
        ).pack(anchor="w", before=model_row, pady=(1, 2))
        ttk.Checkbutton(
            self, text="이전 실제 OBS 방송 시작·종료 사실을 내 로컬 AI가 기억"
                 " (선택 시에만 · 기본 꺼짐 · 다른 캐릭터/채팅 원문 저장 없음)",
            variable=self._broadcast_memory_enabled,
        ).pack(anchor="w", before=model_row, pady=(2,1))
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
        self._tts_cubism_obs_button = ttk.Button(
            pipeline, text="같은 한국어 WAV → 공식 Live2D 입 → OBS 동시 확인",
            command=self._start_real_tts_cubism_obs_probe)
        self._tts_cubism_obs_button.pack(side="left", padx=(8, 0), pady=(5, 0))
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
            if self._long_term_memory_enabled.get():
                archived = LongTermConversationMemory().archive_count()
                self._memory_count.set(
                    f"최근 대화 {count}개 / 선택한 장기 보관 {archived}개")
            else:
                self._memory_count.set(f"최근 대화: {count}개")
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
        related = bool(self._relevant_memory_enabled.get())
        long_term = bool(self._long_term_memory_enabled.get())
        threading.Thread(
            target=self._work, args=(model, text, related, long_term),
            daemon=True).start()

    def _work(self, model: str, text: str, relevant_memory: bool = False,
              long_term_memory: bool = False) -> None:
        try:
            result = run_local_chat(
                model, text, use_committed_gui_character=True,
                relevant_memory=relevant_memory,
                long_term_memory=long_term_memory)
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
        if getattr(self, "_tts_cubism_obs_button", None) is not None:
            self._tts_cubism_obs_button.configure(state="disabled")
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

    def _start_real_tts_cubism_obs_probe(self) -> None:
        """같은 실제 WAV를 공식 Cubism RMS와 OBS 임시 미디어 입력에 함께 연결."""
        self._start_real_tts_obs_probe(couple_live2d=True)

    def _start_real_tts_obs_probe(self, *, couple_live2d: bool = False) -> None:
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
        if couple_live2d:
            try:
                from .offline_settings import settings_file, active_persona
                from .original_plan_studio import inspect_saved_persona_alignment
                from . import original_plan_frontend as frontend
                saved = settings_file()
                if (not saved.is_file() or saved.is_symlink()
                        or saved.parent.is_symlink()
                        or not inspect_saved_persona_alignment(
                            project, active_persona(load_settings(saved)))):
                    raise ValueError("기존 캐릭터·공식 Live2D 모델 불일치")
                if (frontend._native_viewer is None
                        or frontend._native_viewer.poll() is not None
                        or frontend._native_bridge is None):
                    raise ValueError("실행 중인 실제 공식 Live2D 창 없음")
            except Exception as exc:
                self._tts_probe_status.set(
                    "실제 Cubism 연동 전 캐릭터·공식 Live2D 창 확인 필요 ("
                    + type(exc).__name__ + ")")
                return
        if not messagebox.askyesno(
            "실제 한국어 WAV → 공식 Live2D 입 → OBS 연결 검사"
            if couple_live2d else "실제 한국어 GPT-SoVITS → OBS 임시 입력 검사",
            "실제 로컬 GPT-SoVITS 모델과 사용 권리가 확인된 참조 음성으로 "
            "한국어 문장 한 건을 합성합니다. 현재 OBS가 방송/녹화 중이 "
            "아닌 것을 확인한 뒤, OBS 현재 장면에 임시 음성 소스를 만들고 "
            "실제 오디오 미터 신호를 확인한 후 소스를 제거합니다. "
            "임시 WAV 파일도 삭제하며 기존 OBS 소스는 변경하지 않습니다. "
            "이번 1회 실제 한국어 음성의 사용 권리와 임시 OBS 입력 생성을 "
            "승인합니까? "
            + ("같은 실제 WAV의 PCM 음량으로 기존 공식 Cubism 입 구동 함수를 "
               "실행 시간 동안만 연결하고, 실제 입 파라미터와 OBS 미터를 "
               "동시에 관찰한 후 원본 함수를 복원합니다. OBS 현재 프로그램 "
               "영상은 시작 전과 재생 중 최대 33프레임을 읽되 즉시 해시만 "
               "남기고 이미지 원본은 저장하지 않습니다. 공식 Live2D 창을 "
               "캡처하는 기존 소스인지 시작·종료 때 확인합니다. "
               "방송·녹화·채팅 발신은 하지 않으며 시청자 출력은 별도 실증입니다."
               if couple_live2d else
               "Live2D 입 움직임과 시청자 송출은 별도 실증입니다."),
            parent=self):
            self._tts_probe_status.set("미승인 · GPT-SoVITS/OBS 요청 없음")
            return
        self._tts_probe_busy = True
        self._tts_probe_button.configure(state="disabled")
        self._tts_obs_button.configure(state="disabled")
        self._tts_cubism_obs_button.configure(state="disabled")
        self._pipeline_button.configure(state="disabled")
        self._send.configure(state="disabled")
        self._tts_probe_status.set(
            "권리 승인된 한국어 WAV·공식 Cubism 실제 입·OBS 미터 관찰 중…"
            if couple_live2d else
            "승인된 실제 GPT-SoVITS 합성·OBS 임시 음성 미터 확인 중…")
        threading.Thread(
            target=self._work_real_tts_obs_probe,
            args=(reference, reference_text, text, api_url, password,
                  couple_live2d),
            daemon=True).start()

    def _work_real_tts_obs_probe(
        self, reference, reference_text: str, text: str,
        api_url: str, obs_password: str, couple_live2d: bool = False,
    ) -> None:
        try:
            from .original_plan_voice_obs_bridge import verify_gpt_sovits_to_obs
            result = verify_gpt_sovits_to_obs(
                reference, reference_text, text,
                api_url=api_url, obs_password=obs_password,
                operator_approved=True, rights_confirmed=True,
                couple_live2d=couple_live2d)
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

    def _show_approved_voice_history(self) -> None:
        """기존 방송 음성 장부의 해시 일부·상태만 표시. 방송 발신 없음."""
        try:
            from .approved_live_voice_journal import ApprovedLiveVoiceJournal
            rows = ApprovedLiveVoiceJournal().recent(limit=30)
            message = ("기록 없음" if not rows else "\n".join(
                f"{stamp} · {state} · 발화 {key}"
                for key, state, stamp in rows))
        except Exception as exc:
            messagebox.showwarning(
                "방송 음성 기록 조회",
                "로컬 발화 장부를 열 수 없습니다 (" + type(exc).__name__ + ")",
                parent=self)
            return
        # 실제 방송 중 음성 원문은 Windows 사용자 DPAPI 암호문으로만
        # 영구 대기하며, 이전 방송 세션은 새 방송에서 자동 발화하지 않음.
        if sys.platform == "win32":
            try:
                from .approved_live_voice_outbox import ApprovedLiveVoiceOutbox
                pending, uncertain = ApprovedLiveVoiceOutbox().unresolved_totals()
                message += (
                    f"\n\n영구 음성 대기 {pending}건 · "
                    f"이전 시도/불명 가능 {uncertain}건"
                    "\n다른 방송으로 자동 재전송하지 않습니다.")
            except Exception as exc:
                message += (
                    "\n\n영구 음성 대기함 조회 불가 (" +
                    type(exc).__name__ + ")")
        try:
            from .approved_live_voice_causal_journal import ApprovedVoiceCausalJournal
            segments = ApprovedVoiceCausalJournal().recent(limit=10)
            if segments:
                message += "\n\n[동일 WAV→공식 Cubism 입→OBS 재생 요청]"
                for key, part, wav, seconds, state, gap in segments:
                    delay = "미요청" if gap is None else f"{gap:.3f}초"
                    message += (
                        f"\n발화 {key} 구간 {part} WAV {wav} "
                        f"({seconds:.2f}초) · {state} · 입→OBS {delay}")
        except Exception as exc:
            message += "\n\n동일 WAV 인과 기록 조회 불가 (" + type(exc).__name__ + ")"
        messagebox.showinfo(
            "한국어 GPT-SoVITS·Cubism·OBS 발화 기록",
            message + "\n\n※ 재생요청완료는 실제 시청자 수신 증명이 아닙니다. "
            "시도/불명 발화는 자동 재생하지 않습니다.", parent=self)

    def _review_previous_voice_pending(self) -> None:
        """운영자 수동 확인 두 번 없이는 이전 방송 대기 발화를 이동하지 않음."""
        voice = getattr(self, "_approved_live_voice_output", None)
        session = self._twitch_session
        if voice is None or session is None or sys.platform != "win32":
            messagebox.showwarning(
                "이전 방송 발화 인계",
                "Windows에서 실제 방송 음성 작업자를 승인·시작한 후에만 가능합니다.",
                parent=self)
            return
        try:
            rows = voice.previous_sessions_for_review()
        except Exception as exc:
            messagebox.showwarning(
                "이전 방송 발화 인계",
                "이전 방송 대기 기록을 조회하지 못했습니다 (" +
                type(exc).__name__ + ")", parent=self)
            return
        choices = [row for row in rows if row[1] > 0]
        if not choices:
            messagebox.showinfo(
                "이전 방송 발화 인계",
                "이전 방송에서 아직 시도하지 않은 대기 음성이 없습니다. "
                "시도·불명 기록은 인계하지 않습니다.", parent=self)
            return
        display = "\n".join(
            f"{sid} · 미발화 {pending}건 · 시도/불명 {attempted}건 · {at}"
            for sid, pending, attempted, at in choices[:15])
        selected = simpledialog.askstring(
            "이전 방송 미발화 수동 인계",
            "이전 세션의 미발화만 선택합니다.\n"
            "다른 방송의 오래된 문장을 읽을 수 있으므로 동일 OBS 방송인지 "
            "운영자가 직접 확인해야 합니다.\n"
            "시도/불명 발화는 절대 재발화하지 않습니다.\n\n"
            + display + "\n\n인계할 과거 세션 ID 32자:",
            parent=self)
        if selected is None:
            return
        selected = selected.strip()
        match = next((row for row in choices if row[0] == selected), None)
        if match is None:
            messagebox.showwarning(
                "이전 방송 발화 인계", "표시된 과거 미발화 세션 ID만 선택할 수 있습니다.",
                parent=self)
            return
        if not messagebox.askyesno(
                "동일 방송 확인 1/2",
                f"이전 미발화 {match[1]}건이 현재 진행 중인 동일 OBS 방송의 "
                "발화임을 직접 확인했습니까?\n"
                "다른 방송·확인 불명이라면 취소하세요.", parent=self):
            return
        if not messagebox.askyesno(
                "실제 음성 송출 최종 승인 2/2",
                "이 작업은 선택한 과거 미발화 문장을 현재 OBS/Live2D에 "
                "실제로 읽도록 대기열에 인계합니다.\n"
                "이전 시도/불명은 제외합니다. 실행을 승인합니까?",
                parent=self):
            return
        self._approved_live_voice_status.set(
            "운영자 승인한 과거 미발화 인계 · 현재 OBS 상태 확인 중")
        def worker():
            try:
                moved = voice.adopt_previous_pending(
                    selected, operator_approved=True,
                    same_broadcast_confirmed=True)
                self._results.put(("approved_voice_manual_recovery",
                                   (session, moved, "")))
            except Exception as exc:
                self._results.put(("approved_voice_manual_recovery",
                                   (session, 0, type(exc).__name__)))
        threading.Thread(
            target=worker, daemon=True,
            name="AISTING-과거음성수동인계").start()

    def _start_twitch(self, *, scheduled_approval: object | None = None) -> None:
        """사용자 버튼 또는 사용자 승인된 같은 방송의 단발성 채팅 연결."""
        if scheduled_approval is not None:
            if scheduled_approval is not self._scheduled_chat_permission:
                raise PermissionError("사전 승인되지 않은 방송의 채팅 자동 시작 차단")
            self._scheduled_chat_permission = None

            class _NoPrompt:
                """원격 시각의 무인 실행에서는 Tk 모달 창을 열지 않는다."""
                def __init__(self, owner):
                    self._owner = owner

                def showwarning(self, title, message, **_kwargs):
                    self._owner._twitch_status.set(title + " · 자동 연결 조건 미충족")

                def showerror(self, title, message, **_kwargs):
                    self._owner._twitch_status.set(title + " · 자동 연결 조건 미충족")

                def showinfo(self, title, message, **_kwargs):
                    self._owner._twitch_status.set(title + " · 자동 연결 조건 미충족")

                def askyesno(self, title, message, **_kwargs):
                    # 이 실행은 이미 메인 GUI에서 정확한 주간 일정·
                    # 공개 채팅/AI 권한까지 사용자 동의를 받은 경우뿐.
                    return True

            approval_dialog = _NoPrompt(self)
        else:
            approval_dialog = messagebox
        # Never interleave automatic platform prompts into a one-shot
        # operator-approved official Live2D/OBS session probe.
        if (self._closed or self._twitch_session is not None
                or self._pipeline_busy or getattr(self, "_tts_probe_busy", False)
                or getattr(self, "_oauth_busy", False)):
            return
        if self._busy:
            approval_dialog.showwarning(
                "수동 AI 작업 중", "진행 중인 수동 AI 질문과 기억 저장이 끝난 뒤 공개 채팅을 연결하세요.",
                parent=self)
            return
        if getattr(self, "_twitch_active_workers", None):
            approval_dialog.showwarning(
                "이전 AI 작업 종료 대기",
                "이전 채팅의 AI·기억 저장 작업이 끝난 뒤 새 연결을 시작할 수 있습니다.",
                parent=self)
            return
        # Do not silently receive chats that cannot reach the selected AI.
        model = self._model_name.get().strip()
        official = bool(self._official_live2d.get())
        if not official and not model:
            approval_dialog.showinfo(
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
                approval_dialog.showwarning("공식 AI 연결 준비",
                                       "저장한 캐릭터·음성 설정을 확인하세요 (" +
                                       type(exc).__name__ + ")", parent=self)
                return
        if official and not approval_dialog.askyesno(
                "공식 AI·Live2D 채팅 연결 승인",
                "연결 후 들어오는 모든 플랫폼 채팅을 기존 공식 Live2D 창의 "
                "Open-LLM-VTuber 서버에 1회씩 전달합니다. 공식 서버 설정에 따라 "
                "AI·음성·기억/외부 접속이 발생할 수 있습니다. "
                "Live2D 창을 먼저 열고 공식 서버의 무료·로컬 모델 설정을 확인했습니까? "
                "빠른 전송을 선택하면 공식 WebSocket의 질문 전달까지만 확인하고 "
                "각 채팅의 음성·입 움직임은 자동으로 실증하지 않습니다. "
                "선택한 짧은 첫 WAV 관찰도 이전 발화의 잔여 응답과 "
                "구별하거나 OBS·시청자 출력을 보장하지 않습니다.",
                parent=self):
            return
        idle_policy = None
        # 예약형 OBS의 이전 일괄 승인은 무채팅 발화 승인을 포함하지 않는다.
        # 이 기능은 사용자가 채팅 화면에서 직접 연결할 때 별도 승인한다.
        if self._idle_live_enabled.get() and scheduled_approval is None:
            if not official:
                approval_dialog.showwarning(
                    "공식 방송 AI 필요",
                    "무채팅 실제 발화는 기존 공식 Live2D·한국어 음성 연결에만 지원합니다.",
                    parent=self)
                return
            try:
                idle_seconds = int(self._idle_live_threshold.get().strip())
                idle_words = self._idle_live_words.get().strip()
                # 아직 외부 발화하지 않는 단계에서 인자 형식만 고정.
                idle_policy = ApprovedLiveIdleSpeech(
                    threshold_seconds=idle_seconds, utterance=idle_words,
                    operator_approved=True)
            except (ValueError, TypeError) as exc:
                approval_dialog.showwarning(
                    "무채팅 발화 설정",
                    "운영자가 지정한 기준/한 줄 문구가 유효하지 않습니다 (" +
                    type(exc).__name__ + ")", parent=self)
                return
            if not approval_dialog.askyesno(
                    "실제 자발 발화 별도 최종 승인",
                    f"실제 채팅이 {idle_seconds}초 동안 없고 AI FIFO·SQLite에 "
                    "미처리 채팅이 없으면 운영자가 입력한 문구를 "
                    "기존 공식 Live2D 서버에 한 번 전달합니다. "
                    "공식 서버가 실제 한국어 음성을 출력할 수 있습니다. "
                    "다음 채팅이 들어오기 전에는 다시 자발 발화하지 않습니다. "
                    "이 문구와 방송 중 발화를 직접 승인합니까?", parent=self):
                return
        content_agenda = None
        if scheduled_approval is not None:
            approved_plan = self._scheduled_content_plan
            if (approved_plan is not None
                    and approved_plan.get("token") is scheduled_approval):
                if not official:
                    approval_dialog.showwarning(
                        "자율 방송 콘텐츠",
                        "승인한 주제 진행은 기존 공식 Live2D 서버에서만 지원합니다.",
                        parent=self)
                    return
                try:
                    content_agenda = ApprovedLiveContentAgenda(
                        occurrence=approved_plan["occurrence"],
                        topics=approved_plan["topics"],
                        interval_seconds=approved_plan["interval_seconds"],
                        journal=ApprovedLiveContentJournal(),
                        broadcast_alive=approved_plan["broadcast_alive"],
                        operator_approved=True)
                except (ValueError, TypeError, RuntimeError, OSError) as exc:
                    approval_dialog.showwarning(
                        "방송 주제 진행 장부",
                        "콘텐츠 장부/주제/간격 준비에 실패했습니다 ("
                        + type(exc).__name__ + ")", parent=self)
                    return
        broadcast_facts = ""
        if self._broadcast_memory_enabled.get() and scheduled_approval is None:
            if official:
                approval_dialog.showwarning(
                    "실제 방송 기억 지원 범위",
                    "이전 OBS 사건 기억은 내 로컬 Ollama 답변에만 적용합니다. "
                    "공식 Live2D 서버의 별도 기억 설정은 변경하지 않습니다.",
                    parent=self)
                return
            try:
                from .approved_live_memory import approved_live_memory_context
                broadcast_facts = approved_live_memory_context(limit=5)
            except (ValueError, OSError, RuntimeError) as exc:
                approval_dialog.showwarning(
                    "이전 방송 사건 기억",
                    "실제 OBS 사건 장부를 안전하게 읽지 못했습니다 ("
                    + type(exc).__name__ + ")", parent=self)
                return
        relevant_memory = bool(self._relevant_memory_enabled.get())
        long_term_memory = bool(self._long_term_memory_enabled.get())
        if long_term_memory and official:
            approval_dialog.showwarning(
                "장기 기억 적용 대상",
                "장기 대화 보관은 로컬 Ollama 모드에서만 사용합니다. "
                "공식 Live2D 서버의 별도 기억은 변경하지 않습니다.", parent=self)
            return
        parallel_mode = bool(
            self._parallel_local_ai_enabled.get()
            and not official and scheduled_approval is None)
        if parallel_mode and self._local_stream_preview.get():
            approval_dialog.showwarning(
                "병렬 AI 실시간 미리보기",
                "4개 선행 추론 중 서로 다른 답변의 생성 조각을 섞지 않도록 "
                "부분 미리보기를 먼저 해제하세요.", parent=self)
            return
        live_voice_options = None
        if self._approved_live_voice_enabled.get() and scheduled_approval is None:
            if official:
                approval_dialog.showwarning(
                    "공식 음성 중복 차단",
                    "공식 Live2D 서버가 이미 음성을 소유합니다. "
                    "별도 GPT-SoVITS WAV 실방송 경로는 로컬 Ollama 채팅 모드에서만 사용하세요.",
                    parent=self)
                return
            if self._auto_voice.get():
                approval_dialog.showwarning(
                    "중복 음성 출력 차단",
                    "방송용 실제 한국어 음성을 활성화하려면 Windows 기본 음성 자동 읽기를 "
                    "먼저 해제하세요. 두 음성이 동시에 나오지 않도록 합니다.", parent=self)
                return
            try:
                from .official_tts_readiness import read_saved_korean_gpt_sovits_config
                from . import original_plan_frontend as frontend
                from .offline_settings import active_persona, settings_file
                from .original_plan_studio import inspect_saved_persona_alignment
                project = frontend._native_viewer_project
                if (project is None or frontend._native_viewer is None
                        or frontend._native_viewer.poll() is not None
                        or frontend._native_bridge is None):
                    raise ValueError("공식 Windows Live2D 창이 열려 있지 않습니다.")
                saved = settings_file()
                if (not saved.is_file() or saved.is_symlink()
                        or saved.parent.is_symlink()
                        or not inspect_saved_persona_alignment(
                            project, active_persona(load_settings(saved)))):
                    raise ValueError("저장된 캐릭터와 공식 Live2D 설정이 다릅니다.")
                api_url, reference, reference_text = (
                    read_saved_korean_gpt_sovits_config(project))
                password = self._pipeline_obs_password.get()
                if not password:
                    raise ValueError("현재 채팅 탭의 OBS 암호를 먼저 입력해야 합니다.")
                live_voice_options = dict(
                    reference_audio=reference, reference_text=reference_text,
                    api_url=api_url, obs_password=password, obs_port=4455,
                    operator_approved=True, rights_confirmed=True)
            except (ValueError, RuntimeError, OSError, KeyError) as exc:
                approval_dialog.showwarning(
                    "실방송 한국어 음성 준비",
                    "기존 공식 Live2D·저장 캐릭터·참조 음성 권리·OBS 암호를 확인하세요 ("
                    + type(exc).__name__ + ")", parent=self)
                return
            if not approval_dialog.askyesno(
                "실방송 한국어 GPT-SoVITS·Cubism·OBS 최종 승인",
                "선택한 실제 4플랫폼 채팅의 로컬 Ollama 답변을 한국어 "
                "GPT-SoVITS로 합성하고, 지금 이미 방송 중인 OBS 장면에 "
                "현재 발화 전용 음성 소스를 만들어 송출합니다. "
                "같은 WAV로 공식 Windows Live2D Cubism 입을 구동합니다. "
                "기존 소스·장면이나 송출 시작/종료는 건드리지 않습니다. "
                "실제 음성 사용 권리·시청자에게 들릴 수 있는 발화·"
                "임시 음성 소스 생성을 모두 승인합니까?", parent=self):
                return
        choice = self._chat_platform.get()
        types = {"트위치": "twitch", "치지직": "chzzk",
                 "SOOP": "soop", "유튜브": "youtube"}
        code = types.get(choice)
        try:
            saved_platforms = load_settings()["platforms"]
        except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
            approval_dialog.showinfo("플랫폼 설정",
                                "저장된 플랫폼 설정을 확인하세요 (" + type(exc).__name__ + ")",
                                parent=self)
            return
        if (not isinstance(saved_platforms, (list, tuple)) or not saved_platforms
                or any(type(name) is not str for name in saved_platforms)):
            approval_dialog.showinfo("플랫폼 설정", "저장된 플랫폼 선택을 확인하세요.", parent=self)
            return
        if (len(set(saved_platforms)) != len(saved_platforms)
                or any(name not in ("twitch","chzzk","soop","youtube")
                       for name in saved_platforms)):
            approval_dialog.showinfo("플랫폼 설정", "저장된 플랫폼 선택을 확인하세요.", parent=self)
            return
        if choice == "전체":
            missing = [name for name in saved_platforms
                       if not self._multi_channels[name].get().strip()]
            if missing:
                approval_dialog.showinfo("채널 입력",
                                    "선택한 플랫폼의 채널을 모두 입력하세요: " +
                                    ", ".join(missing), parent=self)
                return
        elif code not in saved_platforms:
            approval_dialog.showinfo("플랫폼 선택",
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
            reconnect_journal = DurablePlatformReconnectJournal()
            if choice == "전체":
                twitch_token = getattr(self, "_twitch_oauth_token", None)
                twitch_login = getattr(self, "_twitch_oauth_login", None)
                multi_options = {
                    "youtube_api_key": self._youtube_api_key.get(),
                    "youtube_oauth_token": self._youtube_oauth_token.get(),
                    "reconnect_journal": reconnect_journal}
                if "youtube" in saved_platforms:
                    # 사용자 선택 실제 방송의 YouTube API 페이지가 기존
                    # 채팅 SQLite에 전량 수용된 후만 재시작 커서를 기록한다.
                    multi_options["youtube_cursor_journal"] = YouTubePageCheckpoint()
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
                single_options = {"reconnect_journal": reconnect_journal}
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
                    single_options["youtube_cursor_journal"] = YouTubePageCheckpoint()
                session = MultiPlatformReadOnlySession(
                    {code: channel}, emit, **single_options)
        except (ValueError, TypeError, OSError, RuntimeError) as exc:
            approval_dialog.showinfo("채팅 채널",
                                "채널·API 설정을 확인하세요 (" + type(exc).__name__ + ")",
                                parent=self)
            return
        # 수신기를 시작하기 전 다른 방송/채널의 미처리 데이터를 격리하고
        # 이전 강제 종료로 남은 공개 채팅을 먼저 복구한다. DB 오류면
        # 누락된 척 연결하지 않고 원래 사용자 설정/기억도 건드리지 않는다.
        try:
            durable = DurablePublicChatQueue()
            durable.acquire_exclusive_consumer()
            recovery_snapshot = durable.recovery_snapshot(session._channels)
            prior_ai_incidents = durable.recent_processing_incidents(limit=25)
            prior_reconnect_events = reconnect_journal.recent_for(
                session._channels, limit=12)
        except Exception as exc:
            if "durable" in locals():
                durable.release_exclusive_consumer()
            approval_dialog.showerror(
                "채팅 복구 준비 실패",
                "미처리 채팅 저장소를 열거나 복구할 수 없습니다. "
                "원본은 변경하지 않았습니다 (" + type(exc).__name__ + ")",
                parent=self)
            return
        if prior_ai_incidents:
            self._append(
                "[과거 실제 AI 처리 실패] 마지막 25건 중 "
                + str(len(prior_ai_incidents))
                + "개 사건 기록 있음 · 해당 채팅의 성공/송출 미확인 · "
                "원본 SQLite 보존 상태 확인 필요")
        if prior_reconnect_events:
            self._append(
                "[선택 방송 재연결 기록] 이전 실행의 실제 수신 상태 "
                + str(len(prior_reconnect_events))
                + "건 확인 · 서버 누락/24시간 정상 송출의 증거는 아님")
            for platform, _channel, state, attempt, gap, recorded_at in (
                    prior_reconnect_events[:4]):
                detail = (f" · 실제 공백 {gap:.2f}초" if gap is not None else "")
                self._append(
                    "[수신 이력] " + platform + " / " + state
                    + (f" / 재연결 시도 {attempt}" if attempt else "")
                    + detail + " / UTC " + recorded_at)
        parallel_ai = None
        if parallel_mode:
            try:
                parallel_ai = OrderedParallelLocalAI(
                    model, broadcast_facts=broadcast_facts,
                    relevant_memory=relevant_memory,
                    long_term_memory=long_term_memory)
            except Exception as exc:
                durable.release_exclusive_consumer()
                approval_dialog.showwarning(
                    "로컬 AI 선행 추론",
                    "현재 선택한 모델·캐릭터·대화 기억을 준비하지 못했습니다 ("
                    + type(exc).__name__ + ")", parent=self)
                return
        if live_voice_options is not None:
            try:
                live_voice = ApprovedLiveVoiceOutput(
                    **live_voice_options,
                    on_event=lambda kind, value: self._results.put((
                        "approved_live_voice_event", (session, kind, value))))
                live_voice.start()
            except Exception as exc:
                if parallel_ai is not None:
                    parallel_ai.stop()
                durable.release_exclusive_consumer()
                approval_dialog.showwarning(
                    "방송용 실제 한국어 음성",
                    "음성 작업자를 시작하지 못해 채팅 연결도 시작하지 않습니다 ("
                    + type(exc).__name__ + ")", parent=self)
                return
            self._approved_live_voice_output = live_voice
            previous_pending, previous_unknown = live_voice.previous_unresolved
            self._approved_live_voice_status.set(
                "실제 한국어 방송 발화 FIFO 시작 · 기존 OBS 방송 중에만 음성 전송"
                + (f" · 이전 방송 보류 {previous_pending}건/"
                   f"불명 시도 {previous_unknown}건은 새 방송 자동 발화 금지"
                   if previous_pending or previous_unknown else ""))
        else:
            self._approved_live_voice_output = None
        self._twitch_parallel_ai = parallel_ai
        self._twitch_chat_spool = durable
        self._twitch_session = session
        self._platform_health_updated_at = 0.0
        self._platform_health_status.set("플랫폼별 채팅방 입장 대기 · 수신/누락 미확인")
        self._twitch_received = 0
        self._twitch_replied = 0
        self._twitch_ai_failures = 0
        self._twitch_official_forwarded = 0
        self._twitch_official_wav_observed = 0
        self._twitch_official_wav_unobserved = 0
        self._twitch_reader_finished = False
        self._twitch_reader_error = None
        inbox = queue.SimpleQueue()
        # AI 작업자와 수신 시각 큐를 같은 세션에 고정한다. 재연결 후
        # 예전 작업자가 새 세션의 시각을 소비하면 로컬 지연이 왜곡된다.
        arrival_times = queue.SimpleQueue()
        with self._live_ingress_lock:
            self._ai_arrival_times = arrival_times
            self._twitch_ai_inbox = inbox
            self._recovery_session = session
            self._recovery_arrival_times = {}
            self._recovery_parsed_times = {}
            self._recovery_wakeup.clear()
            self._recovery_reader_done.clear()
        # The user's real Windows receiver gets fresh private diagnostics on
        # each connection; no message text or credentials enter this meter.
        started_at = time.monotonic()
        self._live_latency_metrics = LiveLatencyMetrics(started_at)
        self._platform_live_metrics = {
            name: LiveLatencyMetrics(started_at)
            for name in session._channels
        }
        self._platform_parse_reply_metrics = {
            name: LiveParseReplyMetrics() for name in session._channels
        }
        # 실제 공식 WAV 수신 이벤트만 기록. 채팅별 발화 인과성은 미확인.
        self._platform_first_wav_metrics = {
            name: LiveFirstWavLatencyMetrics() for name in session._channels
        }
        self._platform_first_mouth_metrics = {
            name: LiveFirstMouthLatencyMetrics() for name in session._channels
        }
        self._platform_pcm_alignment_metrics = {
            name: LivePcmCubismAlignmentMetrics() for name in session._channels
        }
        with self._live_ingress_lock:
            self._live_queue_block_events = 0
            self._live_queue_block_total_seconds = 0.0
            self._live_queue_block_max_seconds = 0.0
            self._live_peak_ai_backlog = 0
            self._live_peak_gui_backlog = 0
            self._live_queue_block_by_platform = {
                name: {"건수": 0, "총초": 0.0, "최장초": 0.0, "3초초과": 0}
                for name in session._channels
            }
            self._live_queue_wait_tracker = LiveQueueWaitTracker()
        # 이미 보관된 미처리 채팅을 새 수신보다 먼저 같은 단일 AI FIFO로
        # 넣는다. 장비 재부팅 뒤 과거 monotonic 시각은 그대로 재사용하지
        # 않고 파싱 시각 미확인으로 분리한다. 기존 메시지는 삭제하지 않는다.
        if recovery_snapshot[0]:
            self._append(
                "[미처리 채팅 복구] " + str(recovery_snapshot[0])
                + "건을 백그라운드에서 순서대로 재등록 예정 · "
                "실제 네트워크 수신은 병행하며 신규 메시지는 우선 SQLite 보존 · "
                "새 메시지의 AI 처리는 복구분 이후 · 무누락 실증 전")
        self._twitch_active_workers.add(session)
        # One worker calls the EXISTING local Ollama conversation in order.
        # No extra model service, intentional delay or platform chat posting.
        fast_official = bool(self._official_fast_send.get()) if official else False
        first_wav_receipt = (
            bool(self._official_first_wav_receipt.get())
            if fast_official else False)
        stream_preview = (
            bool(self._local_stream_preview.get()) if not official else False)
        threading.Thread(
            target=self._work_twitch_ai,
            args=(model, inbox, official, session),
            kwargs={"fast_official_mode": fast_official,
                    "first_wav_receipt_mode": first_wav_receipt,
                    "stream_preview_mode": stream_preview,
                    "arrival_times": arrival_times,
                    "idle_policy": idle_policy,
                    "content_agenda": content_agenda,
                    "broadcast_facts": broadcast_facts,
                    "parallel_ai": parallel_ai,
                    "relevant_memory": relevant_memory,
                    "long_term_memory": long_term_memory},
            daemon=True,
        ).start()
        self._twitch_start.configure(state="disabled")
        self._twitch_end.configure(state="normal")
        self._twitch_status.set(choice + " 채팅 연결 요청 중 · 실제 수신 대기")
        threading.Thread(
            target=self._work_twitch_recover_then_read,
            args=(session, durable, recovery_snapshot, inbox, arrival_times),
            daemon=True).start()

    def _work_twitch_recover_then_read(
            self, session, spool, recovery_snapshot, inbox, arrival_times) -> None:
        """4플랫폼 수신과 단일 AI FIFO 사이의 지속적인 SQLite 인계 작업자.

        재시작 이전 보류 채팅도 새 채팅도 반드시 SQLite에 먼저 커밋한다.
        AI·GUI 큐가 가득 차더라도 네트워크 수신기를 추론 작업자 속도에
        묶지 않는다. 별도 작업자가 저장된 전역 sequence 순서로 등록한다.
        수신기가 정상 종료된 뒤까지 저장된 대기분을 등록한 다음에만 AI
        작업자 종료 표식을 보내므로, 마지막 페이지가 누락되지 않는다.
        이 구조는 시청자 1~3초 응답을 보증하지 않는다.
        """
        cursor = 0
        try:
            # 기존 네트워크 수신기를 먼저 열어 수천 건 복구 때문에
            # 수시간 동안 실시간 플랫폼 읽기가 통째로 중단되지 않게 한다.
            threading.Thread(
                target=self._work_twitch, args=(session,), daemon=True
            ).start()
            while not session._stop.is_set():
                ceiling = spool.recovery_ceiling(session._channels)
                if ceiling > cursor:
                    for pending in spool.iter_recovery(
                            session._channels, through_sequence=ceiling,
                            after_sequence=cursor):
                        while not session._stop.is_set():
                            with self._live_ingress_lock:
                                if (session is not self._twitch_session
                                        or getattr(self, "_closed", False)):
                                    return
                                if (inbox.qsize() < 4096
                                        and self._results.qsize() < 4096
                                        and (self._twitch_parallel_ai is None
                                             or self._twitch_parallel_ai.can_submit(
                                                 pending.sequence))):
                                    # 이번 부팅의 신규 수신만 실제 수신 시각을
                                    # 기억한다. 이전 부팅 monotonic은 재사용 금지.
                                    accepted_at = self._recovery_arrival_times.pop(
                                        pending.sequence, None)
                                    deferred_this_run = accepted_at is not None
                                    parsed_at = self._recovery_parsed_times.pop(
                                        pending.sequence, None)
                                    if accepted_at is None:
                                        accepted_at = time.monotonic()
                                    # 새로 들어온 채팅의 실제 파싱 시각을
                                    # 원래 메시지 필드에 복원한다. 재부팅 전
                                    # 시각은 다른 monotonic 기준이므로 재사용 금지.
                                    live_message = (
                                        replace(pending.message,
                                                parsed_at_monotonic=parsed_at)
                                        if parsed_at is not None else pending.message)
                                    arrival_times.put(accepted_at)
                                    self._results.put(("twitch_scoped", (
                                        session, "twitch_chat", _ReaderTimestampedChat(
                                            live_message, accepted_at,
                                            ai_prequeued=True))))
                                    if self._twitch_parallel_ai is not None:
                                        actor_name = "[" + {
                                            "twitch": "트위치", "chzzk": "치지직",
                                            "soop": "SOOP", "youtube": "유튜브"
                                        }.get(live_message.platform, "트위치") + "] " + live_message.sender
                                        self._twitch_parallel_ai.submit(
                                            pending.sequence, live_message.text,
                                            sender=actor_name)
                                    inbox.put(PendingChat(pending.sequence, live_message))
                                    if deferred_this_run:
                                        session.note_deferred_sqlite_chat_enqueued(
                                            pending.message.platform)
                                    break
                            session._stop.wait(0.02)
                        if session._stop.is_set():
                            return
                    cursor = ceiling
                    continue
                # 마지막 SQLite 스냅샷과 wakeup 초기화를 수신 콜백과
                # 동일한 락으로 직렬화해 새 채팅의 깨움 신호를 잃지 않는다.
                with self._live_ingress_lock:
                    if (session is not self._twitch_session
                            or session._stop.is_set()
                            or getattr(self, "_closed", False)):
                        return
                    final_ceiling = spool.recovery_ceiling(session._channels)
                    if final_ceiling > cursor:
                        continue
                    if self._recovery_reader_done.is_set():
                        # 모든 네트워크 수신기가 끝났고 SQLite에서도
                        # 마지막 seq까지 AI 등록했으므로 정상 종료 가능.
                        return
                    self._recovery_wakeup.clear()
                # 빈 채팅방에서 SQL COUNT를 무한 반복하지 않으면서
                # 수신 이벤트에는 즉시 반응한다. 최대 0.5초 점검 간격.
                self._recovery_wakeup.wait(0.5)
        except Exception as exc:
            session.stop()
            with self._live_ingress_lock:
                if self._recovery_session is session:
                    self._recovery_session = None
                self._recovery_arrival_times.clear()
            self._results.put(("twitch_scoped", (
                session, "twitch_error", "복구실패_" + type(exc).__name__)))
        finally:
            with self._live_ingress_lock:
                if self._recovery_session is session:
                    self._recovery_session = None
                    self._recovery_arrival_times.clear()
                    self._recovery_parsed_times.clear()
            # 일반 reader 종료에서는 위 SQLite 전량 등록 뒤에만
            # AI 종료 표식을 넣고, Stop에서는 기존 단일 작업자가
            # 잔여 메시지를 처리하지 않고 종료하도록 한다.
            inbox.put(None)

    def _enqueue_public_event(self, session, kind, item, *, limit: int = 4096) -> bool:
        """읽기 전용 실제 채팅을 먼저 내구 DB에 확정하고 FIFO로 인계한다.

        실제 멀티플랫폼 수신에서는 AI·Tk 적체 시 네트워크 읽기를
        붙잡지 않고 SQLite 작업자가 뒤에서 원래 순서대로 넘긴다.
        서버 이벤트 ID 중복 이외의 메시지는 선별·폐기하지 않는다.
        DB 보호 한도 도달은 조용한 성공이 아닌 명시적 실패이다.
        """
        if type(limit) is not int or limit < 1:
            raise ValueError("채팅 이벤트 큐 용량 설정 오류")
        # GUI 이벤트 큐 또는 AI FIFO가 밀려도 실제 수신 시작 시각을
        # 나중에 새로 찍지 않는다. 네트워크 수신기 콜백에서 한 번만 찍는다.
        stamped_item = (_ReaderTimestampedChat(item, time.monotonic())
                        if kind == "chat" else item)
        blocked_since = None
        blocked_token = None
        accepted = False
        try:
            # 오래된 FIFO 복구가 200,000건까지 쌓여도 네트워크
            # callback 자체를 4,096건 메모리 큐 때문에 중단하지 않는다.
            # 전체 메시지는 먼저 기존 내구 SQLite에 저장되어야 한다.
            if kind == "chat" and isinstance(session, MultiPlatformReadOnlySession):
                with self._live_ingress_lock:
                    if (getattr(self, "_recovery_session", None) is session
                            and session is self._twitch_session
                            and not session._stop.is_set() and not self._closed):
                        spool = self._twitch_chat_spool
                        if spool is None:
                            raise RuntimeError("복구 중 미처리 채팅 DB가 없습니다.")
                        seq = spool.append(item)
                        if seq is not None:
                            self._recovery_arrival_times[seq] = (
                                stamped_item.reader_received_at)
                            parsed_at = getattr(item, "parsed_at_monotonic", None)
                            if (type(parsed_at) in (int, float)
                                    and math.isfinite(parsed_at)
                                    and 0 < parsed_at <= stamped_item.reader_received_at):
                                self._recovery_parsed_times[seq] = parsed_at
                            # 복구 완료 이후에도 계속 같은 내구 경로를
                            # 사용하므로 AI 병목이 소켓 읽기를 중단하지 않는다.
                            self._recovery_wakeup.set()
                        accepted = True
                        # 수신기에게는 영속 접수 성공을 알려 커서/서버 ACK를
                        # 유지하지만 실제 AI FIFO 등록과는 구별 계측한다.
                        return SQLITE_DEFERRED_CHAT
            while not getattr(self, "_closed", False):
                if session is None or session._stop.is_set():
                    return False
                pending_ai = getattr(self, "_twitch_ai_inbox", None)
                # A pending Tk message can still flow into the AI FIFO. Do not
                # discard its data: pause reading until the serial AI worker
                # actually drains committed work.
                ai_backlog = pending_ai.qsize() if pending_ai is not None else 0
                if (self._results.qsize() < limit and ai_backlog < limit
                        and (kind != "chat" or self._twitch_parallel_ai is None
                             or self._twitch_parallel_ai.can_submit())):
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
                            if (self._results.qsize() < limit and inbox.qsize() < limit
                                    and (self._twitch_parallel_ai is None
                                         or self._twitch_parallel_ai.can_submit())):
                                if blocked_since is not None:
                                    waited = max(0.0, time.monotonic() - blocked_since)
                                    self._live_queue_block_events += 1
                                    self._live_queue_block_total_seconds += waited
                                    self._live_queue_block_max_seconds = max(
                                        self._live_queue_block_max_seconds, waited)
                                    platform = getattr(item, "platform", None)
                                    stats = self._live_queue_block_by_platform.get(platform)
                                    if stats is not None:
                                        stats["건수"] += 1
                                        stats["총초"] += waited
                                        stats["최장초"] = max(stats["최장초"], waited)
                                        if waited > 3.0:
                                            stats["3초초과"] += 1
                                self._live_peak_ai_backlog = max(
                                    self._live_peak_ai_backlog, inbox.qsize() + 1)
                                self._live_peak_gui_backlog = max(
                                    self._live_peak_gui_backlog, self._results.qsize() + 1)
                                # 영속 트랜잭션 성공 전에는 GUI·AI 어느 큐에도
                                # 수신 성공 사건을 넣지 않는다. 저장 실패 시
                                # 기존 세션의 네트워크 오류·재연결 경로로 전파.
                                spool = self._twitch_chat_spool
                                if spool is None:
                                    raise RuntimeError("미처리 채팅 보존 큐가 없습니다.")
                                sequence = spool.append(item)
                                if sequence is None:
                                    # 이미 SQLite에 보류 중인 동일 서버 ID의
                                    # 재전송만 기존 미처리 순서에 맡긴다.
                                    # 내용이 같은 신규 메시지는 항상 등록된다.
                                    accepted = True
                                    return True
                                arrivals.put(stamped_item.reader_received_at)
                                self._results.put(("twitch_scoped", (
                                    session, "twitch_chat", _ReaderTimestampedChat(
                                        item, stamped_item.reader_received_at,
                                        ai_prequeued=True))))
                                if self._twitch_parallel_ai is not None:
                                    actor_name = "[" + {
                                        "twitch": "트위치", "chzzk": "치지직",
                                        "soop": "SOOP", "youtube": "유튜브"
                                    }.get(item.platform, "트위치") + "] " + item.sender
                                    self._twitch_parallel_ai.submit(
                                        sequence, item.text, sender=actor_name)
                                inbox.put(PendingChat(sequence, item))
                                accepted = True
                                return True
                    else:
                        # 기존 직접 GUI 호출·상태 알림 경로는 보존한다.
                        self._results.put(("twitch_scoped", (
                            session, "twitch_" + kind, stamped_item)))
                        accepted = True
                        return True
                if kind == "chat" and blocked_since is None:
                    blocked_since = time.monotonic()
                    blocked_token = self._live_queue_wait_tracker.begin(
                        getattr(item, "platform", "미분류"))
                session._stop.wait(0.02)
            return False
    
        finally:
            self._live_queue_wait_tracker.finish(blocked_token, accepted=accepted)

    def _work_twitch(self, session: TwitchReadOnlySession) -> None:
        try:
            session.run()
        except Exception as exc:
            self._results.put(("twitch_scoped", (session, "twitch_error", type(exc).__name__)))
        finally:
            # GUI의 수신 종료 알림을 AI 완료보다 먼저 FIFO에 보낸다.
            self._results.put(("twitch_scoped", (session, "twitch_finished", session)))
            with self._live_ingress_lock:
                if self._recovery_session is session:
                    self._recovery_reader_done.set()
                    self._recovery_wakeup.set()

    def _work_twitch_ai(self, model: str, inbox: queue.SimpleQueue,
                        official: bool = False, session=None, *,
                        reply_function=None, fast_official_mode: bool = False,
                        first_wav_receipt_mode: bool = False,
                        stream_preview_mode: bool = False,
                        arrival_times: queue.SimpleQueue | None = None,
                        idle_policy: ApprovedLiveIdleSpeech | None = None,
                        content_agenda: ApprovedLiveContentAgenda | None = None,
                        broadcast_facts: str = "",
                        parallel_ai: OrderedParallelLocalAI | None = None,
                        relevant_memory: bool = False,
                        long_term_memory: bool = False) -> None:
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
                if (official and session is not None
                        and (idle_policy is not None or content_agenda is not None)):
                    try:
                        chat = inbox.get(timeout=0.5)
                    except queue.Empty:
                        # 입력 FIFO가 비었더라도 SQLite 복구 대상이 있으면
                        # 원래 실시간 채팅을 앞지르는 자발 발화를 하지 않는다.
                        if session._stop.is_set():
                            break
                        spool = getattr(self, "_twitch_chat_spool", None)
                        if spool is None or session is not self._twitch_session:
                            continue
                        try:
                            counts = spool.pending_selected_channels_snapshot(
                                session._channels)
                            pending = sum(int(x["미처리"]) for x in counts.values())
                            speech = (idle_policy.next_if_quiet(
                                pending_count=pending,
                                sending=not inbox.empty())
                                if idle_policy is not None else None)
                            content_turn = (content_agenda.next_if_quiet(
                                pending_count=pending,
                                sending=not inbox.empty())
                                if content_agenda is not None and speech is None
                                else None)
                        except Exception:
                            # DB 상태를 알 수 없으면 자발 발화만 차단.
                            continue
                        if ((speech is None and content_turn is None)
                                or session._stop.is_set() or not inbox.empty()
                                or (content_turn is not None and (
                                    self._twitch_reader_finished
                                    or not content_agenda.broadcast_is_active()))):
                            # 콘텐츠 발화는 위 장부에 이미 '시도'로 확정됨.
                            # 채팅이 끼어들어 발화를 보류해도 자동 재전송 금지.
                            continue
                        delivered = False
                        try:
                            from .original_plan_frontend import send_to_native_live2d_session
                            accepted = send_to_native_live2d_session(
                                speech if speech is not None else content_turn.prompt,
                                operator_approved=True)
                            if accepted is not True:
                                raise RuntimeError("공식 방송 콘텐츠 전송 결과 불명")
                            delivered = True
                        except Exception:
                            if content_turn is None:
                                report("twitch_idle_speech", (
                                    "전송 불명 · 재발화 없음", idle_policy.attempted))
                        else:
                            if content_turn is None:
                                report("twitch_idle_speech", (
                                    "기존 공식 서버 1회 전달 확인 · 실제 음성/OBS 미실증",
                                    idle_policy.attempted))
                        finally:
                            if content_turn is not None:
                                try:
                                    content_agenda.record_delivery(
                                        content_turn, delivered=delivered)
                                except Exception:
                                    report("twitch_content_turn", (
                                        content_turn.sequence, "장부 확정 실패 · 재전송 금지"))
                                else:
                                    report("twitch_content_turn", (
                                        content_turn.sequence,
                                        "공식 AI 서버 1회 전달 확인 · 실제 방송 출력 미실증"
                                        if delivered else "전송 불명 · 자동 재전송 없음"))
                        continue
                else:
                    chat = inbox.get()
                if chat is None or (session is not None and session._stop.is_set()):
                    break
                if idle_policy is not None:
                    # 실제 채팅 우선, 해당 무채팅 구간 다시 처음부터 측정.
                    idle_policy.note_chat()
                if content_agenda is not None:
                    content_agenda.note_chat()
                pending_sequence = None
                if isinstance(chat, PendingChat):
                    pending_sequence, chat = chat.sequence, chat.message

                def record_durable_failure(incident_kind):
                    if pending_sequence is None or session is None:
                        return
                    spool = getattr(self, "_twitch_chat_spool", None)
                    if spool is None:
                        report("twitch_ai_incident_error", "SQLite 장부 연결 없음")
                        return
                    try:
                        spool.record_processing_incident(
                            pending_sequence, incident_kind)
                    except Exception:
                        report("twitch_ai_incident_error",
                               "SQLite AI 처리 사건 영구 기록 실패")

                def confirm_durable_after_success():
                    # 실제 AI 처리 완료/공식 전달이 확인된 경우에만 항목 삭제.
                    # 재시작 직전에는 중복 처리 가능성이 남음을 숨기지 않는다.
                    if (pending_sequence is None or session is None
                            or session._stop.is_set()):
                        return
                    spool = getattr(self, "_twitch_chat_spool", None)
                    if spool is None:
                        report("twitch_ai_error", (chat, "미처리 채팅 보존 큐 누락"))
                        return
                    try:
                        if not spool.confirm(pending_sequence):
                            report("twitch_ai_error", (chat, "미처리 채팅 확인 대상 없음"))
                    except Exception:
                        report("twitch_ai_error", (chat, "미처리 채팅 완료기록 실패"))

                # 실제 GUI에서는 생성 시 전달한 세션 전용 시각 큐만 사용.
                # 인자 없는 이전 직접 호출 검사만 기존 속성을 사용한다.
                arrivals = (arrival_times if arrival_times is not None
                            else getattr(self, "_ai_arrival_times", None))
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
                                if isinstance(session, MultiPlatformReadOnlySession):
                                    # 파싱 시각이 없는 가상 채팅은 성공 표본에서 제외.
                                    report("twitch_ai_parse_terminal", (
                                        getattr(chat, "platform", "twitch"),
                                        getattr(chat, "parsed_at_monotonic", None),
                                        accepted_at, model_started_at,
                                        ended_at, attempt_failed))
                if official:
                    # Official WebView2 owns the AI, GPT-SoVITS audio and Cubism
                    # model in ONE upstream conversation. Never duplicate this
                    # turn by also submitting to the separate Ollama model.
                    try:
                        if fast_official_mode:
                            # 8초 실증 대기 없는 기존 1회 공식 WebSocket 전송.
                            # 사용자가 선택한 경우에만 첫 실제 WAV 이벤트를
                            # 최대 3초 관측한다. 이전 발화와의 구분은 불가.
                            if first_wav_receipt_mode:
                                from .original_plan_frontend import send_to_native_live2d_session_with_first_wav
                                wav_request_started_at = time.monotonic()
                                receipt = send_to_native_live2d_session_with_first_wav(
                                    chat.text, operator_approved=True,
                                    wait_seconds=3.0)
                                accepted = receipt.accepted
                            else:
                                from .original_plan_frontend import send_to_native_live2d_session
                                accepted = send_to_native_live2d_session(
                                    chat.text, operator_approved=True)
                            if accepted is not True:
                                raise RuntimeError("공식 WebSocket 실제 전송 미확인")
                        else:
                            from .original_plan_frontend import send_to_native_live2d_session_with_observation
                            mouth_request_started_at = time.monotonic()
                            evidence = send_to_native_live2d_session_with_observation(
                                chat.text, operator_approved=True, duration=8)
                            mouth_observed_finished_at = time.monotonic()
                    except Exception as exc:
                        attempt_failed = True
                        report("twitch_ai_error", (chat, type(exc).__name__))
                        if fast_official_mode and first_wav_receipt_mode:
                            report("twitch_ai_first_wav_error",
                                   getattr(chat, "platform", "twitch"))
                        elif (not fast_official_mode
                              and isinstance(session, MultiPlatformReadOnlySession)):
                            report("twitch_ai_first_mouth_error",
                                   getattr(chat, "platform", "twitch"))
                    else:
                        if fast_official_mode:
                            # 텍스트 전송 성공과 서버 WAV 관측을 별도 집계.
                            # wav_received라도 원인 발화나 출력까지는
                            # 증명되지 않으므로 AI 응답 성공에 넣지 않는다.
                            report("twitch_live2d_forwarded", chat)
                            confirm_durable_after_success()
                            if first_wav_receipt_mode:
                                report("twitch_live2d_first_wav", (chat, receipt))
                                # 파싱부터 공식 첫 WAV *후보* 수신까지의
                                # 실제 단조시각을 연결한다. 동일 발화 증거 아님.
                                report("twitch_ai_first_wav_timing", (
                                    getattr(chat, "platform", "twitch"),
                                    getattr(chat, "parsed_at_monotonic", None),
                                    accepted_at, wav_request_started_at,
                                    receipt.first_wav_seconds,
                                    receipt.wav_received))
                        else:
                            attempt_failed = not bool(evidence.verified_signal)
                            report("twitch_live2d_ok", (chat, evidence))
                            if evidence.verified_signal:
                                confirm_durable_after_success()
                            if isinstance(session, MultiPlatformReadOnlySession):
                                # 기존 공식 1회 질문에서 실제 Cubism 관찰한
                                # monotonic 표본만 연결한다. 추가 질문·음성 없음.
                                report("twitch_ai_first_mouth_timing", (
                                    getattr(chat, "platform", "twitch"),
                                    getattr(chat, "parsed_at_monotonic", None),
                                    accepted_at, mouth_request_started_at,
                                    mouth_observed_finished_at,
                                    getattr(evidence, "first_audio_mouth_monotonic", None),
                                    bool(evidence.verified_signal),
                                    getattr(evidence, "official_pcm_first_wav_received_monotonic", None),
                                ))
                    finally:
                        report_measured_elapsed()
                    # 실제 공식 서버는 요청이 접수된 뒤 연결 오류를
                    # 냈을 수도 있다. 무단 중복 발화를 시도하지 않고
                    # 이후 채팅을 보내기 전에 전체 수신을 중단한다.
                    if (attempt_failed and pending_sequence is not None
                            and isinstance(session, MultiPlatformReadOnlySession)
                            and not session._stop.is_set()):
                        record_durable_failure("공식AI전달불명")
                        report("twitch_ai_fifo_paused", (
                            getattr(chat, "platform", "twitch"), pending_sequence,
                            "공식 AI 발화 상태 불확실 · 원본 SQLite 보존"))
                        session.stop()
                        break
                    continue
                try:
                    actor = "[" + {"twitch":"트위치","chzzk":"치지직",
                        "soop":"SOOP","youtube":"유튜브"}.get(
                            getattr(chat, "platform", "twitch"), "트위치") + "] " + chat.sender
                    if (parallel_ai is not None and pending_sequence is not None
                            and isinstance(session, MultiPlatformReadOnlySession)):
                        result = run_local_fifo_with_recovery(
                            lambda: parallel_ai.finish(
                                pending_sequence, chat.text, sender=actor),
                            stop=session._stop,
                            on_retry=lambda attempt, delay: report(
                                "twitch_ai_retry", (
                                    getattr(chat, "platform", "twitch"),
                                    attempt, delay)))
                    else:
                        if reply_function is None:
                            # 한 번 선택한 로컬 Ollama·캐릭터/기억 경로를
                            # 동일 수신 워커 내에서만 보유한다. 다른 방송
                            # 세션과 공유하지 않고 원래 단일 FIFO를 유지한다.
                            if local_runner is None:
                                local_runner = LocalChatRunner(
                                    model, use_committed_gui_character=True,
                                    broadcast_facts=broadcast_facts,
                                    relevant_memory=relevant_memory,
                                    long_term_memory=long_term_memory)
                            if stream_preview_mode:
                                partial_preview = ""
                                received_chars = 0
                                last_progress_at = 0.0
                                def on_stream_chunk(delta: str) -> None:
                                    nonlocal partial_preview, received_chars, last_progress_at
                                    if session is not None and session._stop.is_set():
                                        # 끝난 세션의 추가 토큰/미리보기는 막는다.
                                        raise RuntimeError("운영자 중지 · 부분 텍스트 폐기")
                                    received_chars += len(delta)
                                    if len(partial_preview) < 160:
                                        partial_preview += delta[:160-len(partial_preview)]
                                    now = time.monotonic()
                                    if (last_progress_at == 0.0
                                            or now - last_progress_at >= 0.35):
                                        last_progress_at = now
                                        report("twitch_ai_stream_preview", (
                                            partial_preview, received_chars,
                                            max(0.0, now - model_started_at)))
                                def _generate_stream_reply():
                                    return local_runner.reply(
                                        chat.text, sender=actor,
                                        on_stream_chunk=on_stream_chunk,
                                        should_cancel=(
                                            (lambda: session._stop.is_set())
                                            if session is not None else None))
                                if isinstance(session, MultiPlatformReadOnlySession):
                                    def _stream_retry(attempt, delay):
                                        nonlocal partial_preview, received_chars, last_progress_at
                                        partial_preview, received_chars, last_progress_at = "", 0, 0.0
                                        report("twitch_ai_retry", (
                                            getattr(chat, "platform", "twitch"), attempt, delay))
                                    result = run_local_fifo_with_recovery(
                                        _generate_stream_reply, stop=session._stop,
                                        on_retry=_stream_retry)
                                else:
                                    result = _generate_stream_reply()
                            else:
                                def _generate_full_reply():
                                    return local_runner.reply(
                                        chat.text, sender=actor,
                                        should_cancel=(
                                            (lambda: session._stop.is_set())
                                            if session is not None else None))
                                if isinstance(session, MultiPlatformReadOnlySession):
                                    result = run_local_fifo_with_recovery(
                                        _generate_full_reply, stop=session._stop,
                                        on_retry=lambda attempt, delay: report(
                                            "twitch_ai_retry", (
                                                getattr(chat, "platform", "twitch"),
                                                attempt, delay)))
                                else:
                                    result = _generate_full_reply()
                        else:
                            result = reply_function(
                                model, chat.text, sender=actor,
                                use_committed_gui_character=True)
                except Exception as exc:
                    attempt_failed = True
                    report("twitch_ai_error", (chat, type(exc).__name__))
                else:
                    report("twitch_ai_ok", (chat, result))
                    confirm_durable_after_success()
                finally:
                    report_measured_elapsed()
                if (attempt_failed and pending_sequence is not None
                        and isinstance(session, MultiPlatformReadOnlySession)
                        and not session._stop.is_set()):
                    # 실패한 이전 sequence를 SQLite에 남긴 채 다음
                    # 채팅으로 넘어가면 FIFO 원순서가 훼손된다. 모델
                    # 복구 한도 초과/기타 확정 실패 시 안전하게 수신 종료.
                    record_durable_failure("로컬AI확정실패")
                    report("twitch_ai_fifo_paused", (
                        getattr(chat, "platform", "twitch"), pending_sequence,
                        "로컬 모델 연속 실패 · 원본 SQLite 보존"))
                    session.stop()
                    break
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
        parallel_ai = self._twitch_parallel_ai
        self._twitch_parallel_ai = None
        if parallel_ai is not None:
            parallel_ai.stop()
        live_voice = self._approved_live_voice_output
        self._approved_live_voice_output = None
        if live_voice is not None:
            live_voice.stop()
            self._approved_live_voice_status.set(
                "사용자 중지 · 음성 작업자 종료 요청 · OBS 방송 자체는 변경하지 않음")
        meter = getattr(self, "_live_latency_metrics", None)
        if meter is not None:
            meter.stop(time.monotonic())
            self._append("[로컬 수신 종료] " + meter.snapshot(time.monotonic()).describe())
        for platform_meter in getattr(self, "_platform_live_metrics", {}).values():
            platform_meter.stop(time.monotonic())
        with self._live_ingress_lock:
            if self._recovery_session is session:
                self._recovery_session = None
                self._recovery_arrival_times.clear()
            if self._twitch_ai_inbox is not None:
                # Stop 뒤 새 채팅이 종료 표식 다음에 등록되지 않도록 한다.
                self._twitch_ai_inbox.put(None)
            self._twitch_ai_inbox = None
        # Do not keep the UI locked waiting for a stalled socket/HTTP reader.
        # Each late reader/AI event carries this original session identity;
        # _poll discards it after a restart instead of contaminating the new
        # connection's FIFO, counts or persona.
        self._twitch_session = None
        if (not self._twitch_active_workers
                and self._twitch_chat_spool is not None):
            self._twitch_chat_spool.release_exclusive_consumer()
            self._twitch_chat_spool = None
        self._platform_health_status.set("플랫폼별 수신 종료 · 시청자 무누락 여부 미확인")
        self._twitch_reader_finished = False
        if getattr(self, "_twitch_start", None) is not None:
            self._twitch_start.configure(state="normal")
        if getattr(self, "_twitch_end", None) is not None:
            self._twitch_end.configure(state="disabled")
        if getattr(self, "_twitch_status", None) is not None:
            self._twitch_status.set("운영자가 공개 채팅 연결을 중지했습니다. 남은 AI 작업은 폐기합니다.")

    def destroy(self) -> None:
        self._scheduled_chat_permission = None
        self._closed = True
        if self._pipeline_cancel is not None:
            self._pipeline_cancel.set()
        self._queued_voice.clear()
        parallel_ai = self._twitch_parallel_ai
        if parallel_ai is not None:
            parallel_ai.stop()
            self._twitch_parallel_ai = None
        live_voice = self._approved_live_voice_output
        if live_voice is not None:
            live_voice.stop()
            self._approved_live_voice_output = None
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
        with self._live_ingress_lock:
            block_snapshots = {
                code: dict(stats)
                for code, stats in self._live_queue_block_by_platform.items()
            }
        wait_snapshots = self._live_queue_wait_tracker.snapshot()
        durable = getattr(self, "_twitch_chat_spool", None)
        disk_snapshot = (durable.pending_capacity_snapshot()
                         if durable is not None else {})
        disk_counts = disk_snapshot.get("플랫폼별", {})
        selected_disk = (
            durable.pending_selected_channels_snapshot(session._channels)
            if durable is not None
            and isinstance(session, MultiPlatformReadOnlySession) else {})
        # SQLite 원본·채팅 본문을 읽지 않는 이번 실행의 처리율과
        # 미처리 최장 시간을 표시한다. 3초 목표 충족을 추정으로 대체하지 않는다.
        operating = (durable.pending_operating_snapshot()
                     if durable is not None else {})
        operating_platforms = operating.get("플랫폼별", {})
        lines = []
        for code, state in snapshot.items():
            block_stats = block_snapshots.get(code, {
                "건수": 0, "총초": 0.0, "최장초": 0.0, "3초초과": 0})
            wait_stats = wait_snapshots.get(code, {
                "진행중": 0, "진행최장초": 0.0, "중단": 0, "중단누적초": 0.0})
            flow = operating_platforms.get(code, {})
            selected = selected_disk.get(code)
            oldest_age = (selected.get("최장미처리초")
                          if selected is not None
                          else flow.get("최장미처리초"))
            oldest_label = (
                "최장 미처리 시간 미측정" if oldest_age is None
                else f"최장 미처리 {oldest_age:.1f}초")
            drain = flow.get("추정소진초")
            drain_label = (
                "최근 완료율로 소진 추정 불가" if drain is None
                else f"최근 완료율 기준 소진 추정 {drain:.1f}초(보장 아님)")
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
            traffic = state.get("마지막통신응답경과초")
            traffic_label = ("통신 응답 미관측" if traffic is None
                             else f"마지막 통신 응답 {traffic:.0f}초 전")
            gap_p95 = state.get("완료공백최근p95초")
            gap_label = ("복구 공백 p95 미측정" if gap_p95 is None
                         else f"최근 복구 공백 p95 {gap_p95:.1f}초")
            callback_p95 = state.get("콜백소요최근p95초")
            callback_label = ("콜백 소요 p95 미측정" if callback_p95 is None
                              else f"최근 콜백 소요 p95 {callback_p95:.2f}초")
            callback_active = state.get("콜백전달진행초")
            callback_active_label = (
                "현재 전달 콜백 없음" if callback_active is None
                else f"현재 전달 콜백 {callback_active:.2f}초 진행 중")
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
            parse_meter = getattr(
                self, "_platform_parse_reply_metrics", {}).get(code)
            if parse_meter is not None:
                parsed = parse_meter.snapshot()
                parse_p95 = ("미측정" if parsed["최근p95초"] is None
                             else f'{parsed["최근p95초"]:.2f}초')
                parse_wait = ("미측정" if parsed["대기p95초"] is None
                              else f'{parsed["대기p95초"]:.2f}초')
                parse_model = ("미측정" if parsed["AIp95초"] is None
                               else f'{parsed["AIp95초"]:.2f}초')
                ai_status += (
                    f" / 파싱→AI 종결 {parsed['종결']}건"
                    f"(실패 {parsed['실패']}건, 시각누락 {parsed['파싱시각누락']}건,"
                    f" 오류 {parsed['시각오류']}건)"
                    f" / 파싱→AI 3초 초과 {parsed['3초초과']}건"
                    f" / 최근 p95 {parse_p95}(대기 {parse_wait}, 작업 {parse_model})"
                    " · 시청자 전달·WAV/OBS 지연 미포함")
            lines.append(
                f"{labels.get(code, code)} {phase} · 콜백 {state['콜백수신']}건"
                f" / GUI 전달 {state['콜백전달완료']}건"
                f" / 전달 오류 {state['콜백전달오류']}건"
                f" / 중단 {state['콜백전달중단']}건"
                f" / 동일 서버 이벤트 ID 재수신 차단 {state.get('서버이벤트ID재수신차단', 0)}건"
                f" / 이벤트 ID 없는 수신 {state.get('서버이벤트ID없음', 0)}건"
                f" / 전달 최대 {state['콜백전달최대초']:.2f}초"
                f" / {callback_label}"
                f" / {callback_active_label}"
                f" / 콜백 소요 3초 초과 {state.get('콜백소요3초초과', 0)}건"
                f" / 재연결 {state['재연결완료']}회"
                f" / 읽기 시도 {state['실제읽기시도']}회"
                f" / 읽기 실패 {state['실제읽기실패']}회"
                f" / 입장 관측 {state['입장관측누적초']:.0f}초"
                f" / 최장 연속 입장관측 {state.get('최장연속입장관측초', 0):.0f}초"
                f" / 24시간 입장 관측구간 {state.get('24시간연속입장관측완료구간', 0)}건"
                f" / 관측 공백 {state['관측공백초']:.1f}초"
                f" / 완료 공백 최장 {state['완료공백최장초']:.1f}초"
                f" / 복구 공백 3초 초과 {state['완료공백3초초과']}건"
                f" / {gap_label} / {ratio_label} / {idle_label}"
                f" / 소켓 프레임·API 응답 {state.get('수신응답계수', 0)}건"
                f" / 통신 응답정지 재연결 {state.get('통신무응답재연결', 0)}회"
                f" / {traffic_label}"
                f" / 수신큐 완료대기 {block_stats['건수']}건"
                f" / 대기 누적 {block_stats['총초']:.2f}초"
                f" / 최장 {block_stats['최장초']:.2f}초"
                f" / 3초 초과 {block_stats['3초초과']}건"
                f" / 현재 수신큐 대기 {wait_stats['진행중']}건"
                f" / 선택 채널 미처리 "
                f"{selected.get('미처리', 0) if selected is not None else disk_counts.get(code, 0)}건"
                f" / 플랫폼 전체 미처리 {disk_counts.get(code, 0)}건"
                f" / {oldest_label}"
                f" / 이번 실행 접수 {flow.get('최근접수', 0)}건"
                f" / 완료 {flow.get('최근완료', 0)}건"
                f" / 접수율 {flow.get('접수초당', 0.0):.2f}건/초"
                f" / 완료율 {flow.get('완료초당', 0.0):.2f}건/초"
                f" / 순증 {flow.get('순증초당', 0.0):+.2f}건/초"
                f" / {drain_label}"
                f" / 진행 최장 {wait_stats['진행최장초']:.2f}초"
                f" / 중단 대기 {wait_stats['중단']}건"
                f" / 중단 누적 {wait_stats['중단누적초']:.2f}초"
                + ai_status
            )
        inbox = self._twitch_ai_inbox
        pending = inbox.qsize() if inbox is not None else 0
        with self._live_ingress_lock:
            blocked_count = self._live_queue_block_events
            blocked_total = self._live_queue_block_total_seconds
            blocked_max = self._live_queue_block_max_seconds
            peak_ai = self._live_peak_ai_backlog
            peak_gui = self._live_peak_gui_backlog
        active_waits = sum(stats["진행중"] for stats in wait_snapshots.values())
        interrupted_waits = sum(stats["중단"] for stats in wait_snapshots.values())
        durable_count = disk_snapshot.get("미처리")
        disk_limit = disk_snapshot.get("보호한도")
        disk_usage = disk_snapshot.get("사용률", 0.0)
        projected_limit = operating.get("추정보호한도도달초")
        projected_label = (
            " / 전체 SQLite 한도 도달 시간 미추정"
            if projected_limit is None
            else f" / 현재 순증 기준 전체 SQLite 한도 예상 {projected_limit:.0f}초(보장 아님)")
        self._platform_health_status.set(
            "플랫폼별 실제 수신 진단 (무누락·24시간·시청자 지연 미검증):\n"
            + "\n".join(lines)
            + f"\nGUI 이벤트 대기 {self._results.qsize()}건"
            + f" / 로컬 AI FIFO 대기 {pending}건"
            + (f" / 선행 AI {self._twitch_parallel_ai.pending}/"
               f"{self._twitch_parallel_ai.prefetch_limit}건"
               " · 초과분은 원본 SQLite에 대기"
               if self._twitch_parallel_ai is not None else "")
            + (" / 디스크 미처리 채팅 "
               + (str(durable_count) + "건" if durable_count is not None
                  else "저장소 미연결"))
            + (f" / SQLite 보호한도 {disk_limit}건 중 {disk_usage * 100:.1f}%"
               if disk_limit is not None else "")
            + (" · 주의: 디스크 미처리 채팅 80% 이상 적체 · AI 처리 속도 확인"
               if disk_usage >= 0.8 else "")
            + projected_label
            + (" · 경고: 현재 증가율 지속 시 10분 내 SQLite 보호한도 도달 예상"
               if projected_limit is not None and projected_limit <= 600 else "")
            + " · 재시작 복구 가능/장애 경계 중복 처리 가능"
            + f" / 수신 큐 대기 완료 {blocked_count}건"
            + f" / 누적 {blocked_total:.2f}초 / 최장 {blocked_max:.2f}초"
            + f" / 최대 AI 적체 {peak_ai}건 / GUI 적체 {peak_gui}건"
            + f" / 수신 큐 진행 중 {active_waits}건 / 중단 {interrupted_waits}건"
            + " · 네트워크 이전 누락·시청자 E2E 미검증"
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
                if kind == "approved_voice_manual_recovery":
                    source, moved, error = payload
                    if source is self._twitch_session:
                        self._approved_live_voice_status.set(
                            "이전 방송 미발화 수동 인계 실패 (" + error + ")"
                            if error else
                            f"운영자 승인 · 이전 미발화 {moved}건 현재 음성 FIFO 인계"
                            " · 시도/불명은 그대로 보존")
                    continue
                if kind == "approved_live_voice_event":
                    source, event, value = payload
                    if source is self._twitch_session:
                        if event == "발화완료":
                            self._approved_live_voice_status.set(
                                f"실제 음성·Cubism·OBS 발화 구간 {value.segments_completed}개 "
                                "재생 요청 완료 · 시청자 수신 미확인")
                        elif event == "발화중복차단":
                            self._approved_live_voice_status.set(
                                "기존 서버 채팅 이벤트 음성 재전송 차단 · "
                                "과거 시도/전달 불명 상태 보존 · " + str(value))
                        elif event == "발화오류":
                            self._approved_live_voice_status.set(
                                "실방송 음성 연결 중단 (" + str(value) +
                                ") · 자동 중복 발화 금지 · 채팅 텍스트 처리 유지")
                        elif event == "발화시작":
                            self._approved_live_voice_status.set(
                                f"실제 한국어 음성 {value}개 구간 합성·송출 진행")
                        elif event == "발화중단":
                            self._approved_live_voice_status.set(
                                "실제 방송 음성 일부 미완료 · 이중 발화 재시도하지 않음")
                    continue
                if kind == "twitch_ai_worker_exited":
                    # Always consume the lifecycle marker, even from a
                    # stopped session. Scoped chat data is still discarded.
                    workers = getattr(self, "_twitch_active_workers", None)
                    if workers is not None:
                        workers.discard(payload)
                    if (not workers and self._twitch_session is None
                            and self._twitch_chat_spool is not None):
                        self._twitch_chat_spool.release_exclusive_consumer()
                        self._twitch_chat_spool = None
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
                    elif kind == "twitch_ai_stream_preview":
                        preview, chars, local_seconds = payload
                        # 완료 전 스트림은 임시 GUI 텍스트일 뿐,
                        # AI 답변·발화·기억/방송 성공으로 계수하지 않는다.
                        self._twitch_status.set(
                            f"로컬 Ollama 생성 중 {chars}글자 · "
                            f"모델 처리 시작 후 {local_seconds:.2f}초 경과"
                            " · 미완성 임시 텍스트 · 방송 발신/기억 저장 없음: "
                            + preview[:160])
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
                        live_voice = self._approved_live_voice_output
                        if live_voice is not None:
                            try:
                                count = live_voice.enqueue(
                                    result.reply,
                                    platform=getattr(chat, "platform", "twitch"),
                                    channel=getattr(chat, "channel", "직접선택"),
                                    event_id=getattr(chat, "event_id", None))
                            except (ValueError, RuntimeError) as exc:
                                self._approved_live_voice_status.set(
                                    "실제 한국어 음성 전송 불가 (" + type(exc).__name__
                                    + ") · 원문 AI 텍스트 유지")
                            else:
                                self._approved_live_voice_status.set(
                                    f"실제 한국어 발화 FIFO {count}번 영구 접수 "
                                    f"· 같은 방송 대기 {live_voice.pending}건 "
                                    "· 다른 방송 자동 재발화 금지")
                        else:
                            selected = self._tts_voices.get(self._voice_name.get())
                            if should_auto_read(self._auto_voice.get(), selected, result.reply):
                                self._queue_voice_reply(result.reply, selected)
                        self._twitch_status.set(
                            "실제 채팅 " + str(self._twitch_received)
                            + "건 · AI 응답 " + str(self._twitch_replied)
                            + "건 · AI 오류 " + str(self._twitch_ai_failures) + "건")
                    elif kind == "twitch_live2d_forwarded":
                        chat = payload
                        self._twitch_official_forwarded += 1
                        self._append(
                            "공식 WebSocket 채팅 전달 확인 · 모델 답변·GPT-SoVITS "
                            "음성·입 움직임은 미검증: " + chat.sender)
                        self._twitch_status.set(
                            "공식 채팅 전달 확인 " + str(self._twitch_official_forwarded)
                            + "건 · 실제 답변/립싱크 실증 "
                            + str(self._twitch_replied) + "건 · 오류 "
                            + str(self._twitch_ai_failures) + "건")
                    elif kind == "twitch_live2d_first_wav":
                        chat, receipt = payload
                        if receipt.wav_received:
                            self._twitch_official_wav_observed += 1
                            first = (f"{receipt.first_wav_seconds:.3f}초"
                                     if receipt.first_wav_seconds is not None
                                     else "미측정")
                            self._append(
                                "[공식 WebSocket WAV 실관측] 첫 RIFF 길이 일치 "
                                + first + " · 입력별 연관·입·OBS·시청자 미검증: "
                                + chat.sender)
                        else:
                            self._twitch_official_wav_unobserved += 1
                            self._append(
                                "[공식 WebSocket WAV 미관측] 선택한 3초 내 "
                                "유효 RIFF 이벤트 미확인 · 답변 실패로 단정하지 않음: "
                                + chat.sender)
                        self._twitch_status.set(
                            "공식 텍스트 전달 " + str(self._twitch_official_forwarded)
                            + "건 · WAV 관측 후보 "
                            + str(self._twitch_official_wav_observed)
                            + "건 · 미관측 "
                            + str(self._twitch_official_wav_unobserved)
                            + "건 · 실제 발화·립싱크·OBS 미검증")
                    elif kind == "twitch_ai_first_wav_timing":
                        code, parsed, accepted, started, delay, received = payload
                        wav_meter = getattr(
                            self, "_platform_first_wav_metrics", {}).get(code)
                        if wav_meter is not None:
                            wav_meter.observe(parsed, accepted, started, delay, received)
                            state = wav_meter.snapshot()
                            if state["관찰시도"] <= 3 or state["관찰시도"] % 25 == 0:
                                p95 = state["파싱부터후보p95초"]
                                self._append(
                                    "[" + code + " 공식 WAV 지연 후보] "
                                    + "관찰 " + str(state["관찰시도"]) + "건 / WAV 후보 "
                                    + str(state["WAV수신후보"]) + "건 / 미관측 "
                                    + str(state["WAV미관측"]) + "건 / 파싱→첫 WAV 후보 p95 "
                                    + (f"{p95:.3f}초" if p95 is not None else "미측정")
                                    + " · 과거 발화 혼입 가능, Cubism·OBS·시청자 미검증")
                    elif kind == "twitch_ai_first_wav_error":
                        wav_meter = getattr(
                            self, "_platform_first_wav_metrics", {}).get(payload)
                        if wav_meter is not None:
                            wav_meter.error()
                    elif kind == "twitch_ai_first_mouth_timing":
                        (code, parsed, accepted, started, finished,
                         first_mouth, verified, wav_at) = payload
                        meter = getattr(
                            self, "_platform_first_mouth_metrics", {}).get(code)
                        if meter is not None:
                            meter.observe(parsed, accepted, started, finished,
                                          first_mouth, verified, wav_at)
                            state = meter.snapshot()
                            if state["관찰시도"] <= 3 or state["관찰시도"] % 25 == 0:
                                total = state["파싱부터입후보p95초"]
                                wav_to_mouth = state["WAV부터입후보p95초"]
                                self._append(
                                    "[" + code + " 공식 Cubism 입 지연 후보] "
                                    + "관찰 " + str(state["관찰시도"]) + "건 / 입 후보 "
                                    + str(state["입표본후보"]) + "건 / 미관측 "
                                    + str(state["입미관측"]) + "건 / 파싱→첫 입 p95 "
                                    + (f"{total:.3f}초" if total is not None else "미측정")
                                    + " / WAV→입 시각 후보 p95 "
                                    + (f"{wav_to_mouth:.3f}초"
                                       if wav_to_mouth is not None else "미측정")
                                    + " · 동일 발화 인과성·OBS·시청자 미검증")
                    elif kind == "twitch_ai_first_mouth_error":
                        meter = getattr(
                            self, "_platform_first_mouth_metrics", {}).get(payload)
                        if meter is not None:
                            meter.error()
                    elif kind == "twitch_live2d_ok":
                        chat, evidence = payload
                        # 같은 기존 공식 1회 관찰의 첫 WAV PCM과
                        # 실제 렌더러 RMS를 추가 전송 없이 대조한다.
                        # 동일 발화/OBS/시청자 실증으로 승격하지 않는다.
                        code = getattr(chat, "platform", "twitch")
                        meter = getattr(
                            self, "_platform_pcm_alignment_metrics", {}).get(code)
                        if meter is not None:
                            candidate = analyze_pcm_cubism_alignment(
                                getattr(evidence, "official_pcm_first_wav_rms_envelope", ()),
                                getattr(evidence, "official_pcm_live2d_rms_samples", ()),
                                mouth_observed=bool(evidence.verified_signal))
                            meter.observe(candidate)
                            state = meter.snapshot()
                            if state["관찰시도"] <= 3 or state["관찰시도"] % 25 == 0:
                                corr = candidate.correlation
                                lag = candidate.lag_seconds
                                self._append(
                                    "[" + code + " 공식 PCM·Cubism 정렬 후보] "
                                    + candidate.status + " · WAV PCM↔렌더러 RMS "
                                    + (f"상관 {corr:.3f}" if corr is not None else "상관 미측정")
                                    + " · 지연 후보 "
                                    + (f"{lag:.3f}초" if lag is not None else "미측정")
                                    + " · 실제 관찰 " + str(state["관찰시도"])
                                    + "건 / 입 동시 후보 "
                                    + str(state["Cubism입동시후보"])
                                    + "건 · 동일 발화·OBS·시청자 미검증")
                        if evidence.verified_signal:
                            self._twitch_replied += 1
                            self._append("공식 AI·Live2D 입력 및 입 움직임 확인: " + chat.sender)
                        else:
                            self._twitch_ai_failures += 1
                            self._append("공식 AI 질문 전달됨 · 입 움직임 실증 미충족: " + chat.sender)
                        self._twitch_status.set(
                            "공식 Live2D 성공 " + str(self._twitch_replied) +
                            "건 · 미검증/오류 " + str(self._twitch_ai_failures) + "건")
                    elif kind == "twitch_content_turn":
                        sequence, result = payload
                        self._append(
                            "[승인된 자율 콘텐츠 " + str(sequence) + "회차] "
                            + str(result) + " · 실제 시청자 수신 미검증")
                        self._twitch_status.set(
                            "운영자 승인 주제 자동 진행: " + str(result))
                    elif kind == "twitch_idle_speech":
                        description, count = payload
                        self._append(
                            f"[공식 AI 무채팅 발화 {count}회차] {description} "
                            "· 시청자 수신/실제 립싱크 미검증")
                        self._twitch_status.set(
                            "공식 무채팅 자발 발화: " + str(description))
                    elif kind == "twitch_ai_incident_error":
                        self._append(
                            "[SQLite 사건 장부 오류] " + str(payload) +
                            " · 미처리 채팅은 삭제하지 않음")
                    elif kind == "twitch_ai_retry":
                        platform, attempt, wait_seconds = payload
                        # 실패한 한 채팅만 같은 FIFO 자리에서 재시도.
                        # 성공으로 계산하거나 다음 메시지부터 보내지 않는다.
                        self._twitch_status.set(
                            f"[{platform}] 로컬 AI 응답 복구 {attempt}회 실패 "
                            f"· {wait_seconds:.1f}초 뒤 동일 채팅 재시도 "
                            "· SQLite 미처리 보존 · 1~3초 미달")
                    elif kind == "twitch_ai_fifo_paused":
                        platform, sequence, reason = payload
                        self._append(
                            f"[FIFO 중단] {platform} 미완료 순번 {sequence} "
                            f"· {reason} · 재연결/원인 확인 필요")
                        self._twitch_status.set(
                            "AI 확정 실패 · 이후 채팅 응답 중단 · "
                            "SQLite 미처리 채팅 보존, 성공/무누락 판정 금지")
                    elif kind == "twitch_ai_error":
                        chat, detail = payload
                        self._twitch_ai_failures += 1
                        self._append(
                            "[플랫폼 AI 처리 실패] " + chat.sender + ": " + detail)
                        self._twitch_status.set(
                            "AI 처리 실패 " + str(self._twitch_ai_failures)
                            + "건 · 성공 응답으로 계산하지 않음")
                    elif kind == "twitch_ai_parse_terminal":
                        code, parsed, accepted, started, ended, failed = payload
                        parse_meter = getattr(
                            self, "_platform_parse_reply_metrics", {}).get(code)
                        if parse_meter is not None:
                            parse_meter.terminal(
                                parsed, accepted, started, ended, failed)
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
                                # 실제 수신의 종료 뒤에도 SQLite→AI 인계할
                                # 채팅이 남을 수 있다. 멀티플랫폼 작업자의
                                # 최종 FIFO 등록 전 종료 표식을 넣지 않는다.
                                if not isinstance(payload, MultiPlatformReadOnlySession):
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
                            if (not self._twitch_active_workers
                                    and self._twitch_chat_spool is not None):
                                self._twitch_chat_spool.release_exclusive_consumer()
                                self._twitch_chat_spool = None
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
                    if getattr(self, "_tts_cubism_obs_button", None) is not None:
                        self._tts_cubism_obs_button.configure(state="normal")
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
                                + ("· 재생 명령 이후 WAV 예상 구간 내 OBS 양성 표본 "
                                   if payload.obs_signal_during_wav_candidate
                                   else "· 재생 명령과 일치하는 OBS 양성 표본 미확인 ")
                                + str(payload.obs_positive_samples_after_restart) + "건"
                                + (" · 첫 양성 표본 " +
                                   f"{payload.first_obs_signal_after_restart_seconds:.3f}초"
                                   if payload.first_obs_signal_after_restart_seconds is not None
                                   else " · 첫 양성 표본 미측정")
                                + (" · 실제 WAV·OBS 음량 변화 유사성 "
                                   + f"{payload.obs_wav_envelope_correlation:.2f}"
                                   + f"({payload.obs_wav_envelope_mapped_samples}표본)"
                                   if payload.obs_wav_envelope_correlation is not None
                                   else " · WAV·OBS 파형 음량 비교 미측정/지원 형식 부족")
                                + (" · 관측 음량 패턴 유사 후보"
                                   if payload.obs_wav_envelope_candidate
                                   else " · 관측 음량 패턴 유사 조건 미충족")
                                + (" · WAV 말하기·쉼 대응 "
                                   + f"{payload.obs_wav_segment_score:.2f}"
                                   + f"({payload.obs_wav_segment_samples}표본,"
                                   + f"발화 {payload.obs_wav_speech_samples},"
                                   + f"쉼 {payload.obs_wav_silence_samples})"
                                   if payload.obs_wav_segment_score is not None
                                   else " · WAV 말하기·쉼 대응 미측정")
                                + (" · 실제 관측 구간 패턴 유사 후보"
                                   if payload.obs_wav_segment_candidate
                                   else " · 발화·쉼 대응 미확인")
                                + (f" · OBS 연결 {payload.obs_connect_seconds:.3f}초"
                                   if payload.obs_connect_seconds is not None
                                   else " · OBS 연결 미측정")
                                + (f" / 실제 GPT-SoVITS 합성 {payload.tts_synthesis_seconds:.3f}초"
                                   if payload.tts_synthesis_seconds is not None
                                   else " / 음성 합성 미측정")
                                + (f" / OBS 입력 준비 {payload.obs_source_prepare_seconds:.3f}초"
                                   if payload.obs_source_prepare_seconds is not None
                                   else " / OBS 입력 준비 미측정")
                                + (f" / OBS 미터 관측 {payload.obs_meter_observed_seconds:.3f}초"
                                   if payload.obs_meter_observed_seconds is not None
                                   else " / 미터 관측 미측정")
                                + (f" / 합성 완료→OBS 첫 미터 {payload.tts_done_to_first_meter_seconds:.3f}초"
                                   if payload.tts_done_to_first_meter_seconds is not None
                                   else " / 합성 완료→OBS 첫 미터 미측정")
                                + " · 각 단계 실제 로컬 시간이며 시청자 E2E 아님"
                                + (" · 실제 원본 PCM 기반 Cubism 입 파라미터 관측 "
                                   + str(payload.cubism_actual_mouth_samples)
                                   + "표본·변화 "
                                   + str(payload.cubism_actual_mouth_changes)
                                   + "건 / 실제 WAV·Cubism·OBS 입력 경로 "
                                   + ("연동 후보" if payload.same_wav_cubism_obs_candidate
                                      else "미충족")
                                   + " · 실제 OBS 프로그램 영상 WAV 중 "
                                   + str(payload.obs_program_frames_during_wav)
                                   + "회·화면 변화 "
                                   + ("관측 후보" if payload.obs_program_motion_near_wav_candidate
                                      else "미충족")
                                   + " · 공식 Live2D 대상 창 캡처 "
                                   + ("설정 일치" if payload.obs_program_capture_candidate
                                      else "미확인")
                                   + " · 입 인과성·동일 발화 시청자 출력·인코딩은 미검증"
                                   if payload.actual_pcm_cubism_requested else
                                   " · Live2D·시청자 송출은 별도 검사"))
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
                            " / " + ("실제 Cubism 입·OBS 미터 근접 표본 2쌍 후보" if getattr(
                                evidence, "same_session_pcm_sample_pair_candidate", False)
                                else "실제 입·OBS 근접 표본 2쌍 미확인") +
                            " / " + ("OBS 영상 획득 경계·오디오·입 근접 표본 일치 후보" if getattr(
                                evidence, "same_session_observed_video_audio_timing_candidate", False)
                                else "OBS 영상 경계·오디오·입 동시성 미확인") +
                            " / " + ("공식 동일 WS WAV·OBS 실제 음량 윤곽 유사 후보" if getattr(
                                evidence, "same_session_official_wav_obs_level_candidate", False)
                                else "공식 동일 WS WAV·OBS 음량 패턴 미확인") +
                            " / " + ("공식 WAV·Live2D 렌더러 RMS 음량 변화 유사 후보" if getattr(
                                evidence, "same_session_official_wav_renderer_rms_candidate", False)
                                else "공식 WAV·실제 Live2D RMS 패턴 미확인") +
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
        approved = messagebox.askyesno(
            "대화 기억 삭제",
            "최근 대화와 장기 보관소가 존재하면 그 기록까지 모두 삭제합니다. "
            "되돌릴 수 없습니다. 진행할까요?", parent=self)
        if not approved:
            return
        try:
            if archive_path_for().exists():
                LongTermConversationMemory().clear()
            else:
                ConversationMemory().clear()
        except (OSError, Exception) as exc:
            messagebox.showerror(
                "삭제 실패", "기억 저장소 처리 오류 (" + type(exc).__name__ + ")",
                parent=self)
            return
        self._refresh_memory_count()
        self._append("시스템: PC에 저장된 대화 기억을 삭제했어요.")
