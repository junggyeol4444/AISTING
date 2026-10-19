"""AISTING EXE의 네이티브 로컬 AI 테스트 탭.

네트워크 요청은 운영자가 '텍스트 전송'을 누른 경우에만 한다.
작업자는 UI와 분리된 스레드에서 localhost에 접속하고,
결과만 tkinter 메인 이벤트 루프에서 표시한다.
"""
from __future__ import annotations

import queue
import threading
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox

from .conversation_memory import ConversationMemory, DEFAULT_MEMORY_FILE
from .desktop_chat import run_local_chat
from .reply_voice import ReplyVoicePlayer, should_auto_read
from .windows_tts import Voice
from .avatar_animation import SpeechActivity
from .twitch_readonly import TwitchReadOnlySession, TwitchReadError
from .multiplatform_readonly import ChzzkReadOnlySession, SoopReadOnlySession, YouTubeReadOnlySession
from .offline_settings import load_settings


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
        self._twitch_channel = tk.StringVar()
        self._chat_platform = tk.StringVar(value='트위치')
        self._official_live2d = tk.BooleanVar(value=False)
        self._youtube_api_key = tk.StringVar()
        self._twitch_status = tk.StringVar(value="읽기 전용 미연결 · 로그인·채팅 송신 없음")
        self._twitch_received = 0
        self._twitch_replied = 0
        self._twitch_ai_failures = 0
        self._twitch_ai_inbox: queue.SimpleQueue | None = None
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
        public_chat.pack(fill="x", pady=(10, 0))
        ttk.Combobox(public_chat, textvariable=self._chat_platform,
                     values=("트위치", "치지직", "SOOP", "유튜브"),
                     width=8, state="readonly").pack(side="left", padx=4)
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
        keyline.pack(fill="x")
        ttk.Label(keyline, text="YouTube API 키 (실행 중 메모리만 사용)").pack(side="left")
        ttk.Entry(keyline, textvariable=self._youtube_api_key, width=46,
                  show="*").pack(side="left", padx=5)
        ttk.Checkbutton(self, text="공식 Open-LLM-VTuber/Live2D 창으로 채팅 전달 (한 세션 · Ollama 중복 호출 없음)",
                        variable=self._official_live2d).pack(anchor="w", pady=(4, 0))
        ttk.Label(self, textvariable=self._twitch_status, wraplength=600).pack(
            anchor="w", pady=(2, 5))
        self._refresh_memory_count()
        self.after(150, self._poll)

    def _append(self, line: str) -> None:
        self._dialog.configure(state="normal")
        self._dialog.insert("end", line + "\n\n")
        self._dialog.see("end")
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
        if self._busy:
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
            self._results.put(("error", str(exc)))
        else:
            self._results.put(("ok",result))

    def _start_twitch(self) -> None:
        if self._twitch_session is not None:
            return
        # Do not silently receive chats that cannot reach the selected AI.
        model = self._model_name.get().strip()
        official = bool(self._official_live2d.get())
        if not official and not model:
            messagebox.showinfo(
                "로컬 AI 모델", "먼저 설치한 Ollama 모델 이름을 입력해 주세요.",
                parent=self)
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
        if code not in load_settings()["platforms"]:
            messagebox.showinfo("플랫폼 선택",
                                "방송 설정에서 선택한 플랫폼을 저장해 주세요.", parent=self)
            return
        try:
            channel = self._twitch_channel.get().strip()
            # Every event is bound to the session that produced it. A previous
            # connection can finish after a new one starts; never let that
            # previous listener's late messages enter the new AI queue.
            session = None
            emit = lambda kind, item: self._results.put((
                "twitch_scoped", (session, "twitch_" + kind, item)))
            if code == "twitch":
                session = TwitchReadOnlySession(channel, emit)
            elif code == "chzzk":
                session = ChzzkReadOnlySession(channel, emit)
            elif code == "soop":
                session = SoopReadOnlySession(channel, emit)
            else:
                session = YouTubeReadOnlySession(
                    channel, emit, self._youtube_api_key.get())
        
        except (ValueError, TypeError) as exc:
            messagebox.showinfo("트위치 채널", str(exc), parent=self)
            return
        self._twitch_session = session
        self._twitch_received = 0
        self._twitch_replied = 0
        self._twitch_ai_failures = 0
        inbox = queue.SimpleQueue()
        self._twitch_ai_inbox = inbox
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

    def _work_twitch(self, session: TwitchReadOnlySession) -> None:
        try:
            session.run()
        except Exception as exc:
            self._results.put(("twitch_scoped", (session, "twitch_error", str(exc))))
        finally:
            self._results.put(("twitch_scoped", (session, "twitch_finished", session)))

    def _work_twitch_ai(self, model: str, inbox: queue.SimpleQueue,
                        official: bool = False, session=None) -> None:
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
        while True:
            chat = inbox.get()
            if chat is None or (session is not None and session._stop.is_set()):
                break
            if official:
                # Official WebView2 owns the AI, GPT-SoVITS audio and Cubism
                # model in ONE upstream conversation. Never duplicate this
                # turn by also submitting to the separate Ollama model.
                try:
                    from .original_plan_frontend import send_to_native_live2d_session_with_observation
                    evidence = send_to_native_live2d_session_with_observation(
                        chat.text, operator_approved=True, duration=8)
                except Exception as exc:
                    report("twitch_ai_error", (chat, str(exc)))
                else:
                    report("twitch_live2d_ok", (chat, evidence))
                continue
            try:
                result = run_local_chat(
                    model, chat.text, sender="[" + {"twitch":"트위치","chzzk":"치지직",
                        "soop":"SOOP","youtube":"유튜브"}.get(
                            getattr(chat, "platform", "twitch"), "트위치") + "] " + chat.sender,
                    use_committed_gui_character=True)
            except Exception as exc:
                report("twitch_ai_error", (chat, str(exc)))
            else:
                report("twitch_ai_ok", (chat, result))

    def _stop_twitch(self) -> None:
        if self._twitch_session is not None:
            self._twitch_session.stop()
            if self._twitch_ai_inbox is not None:
                # Wake the idle AI worker. Queued messages will not be sent.
                self._twitch_ai_inbox.put(None)

    def destroy(self) -> None:
        self._closed = True
        self._queued_voice.clear()
        self._stop_twitch()
        if self._twitch_ai_inbox is not None:
            self._twitch_ai_inbox.put(None)
            self._twitch_ai_inbox = None
        super().destroy()

    def _poll(self) -> None:
        if self._closed:
            return
        try:
            while True:
                kind, payload = self._results.get_nowait()
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
                        self._twitch_received += 1
                        name = {"twitch":"트위치","chzzk":"치지직",
                                "soop":"SOOP","youtube":"유튜브"}.get(
                                    getattr(payload, "platform", "twitch"), "트위치")
                        self._append("[" + name + " #" + payload.channel + "] "
                                     + payload.sender + ": " + payload.text)
                        # Every incoming message, including duplicates, is
                        # queued regardless of the status of previous replies.
                        if self._twitch_ai_inbox is not None:
                            self._twitch_ai_inbox.put(payload)
                        self._twitch_status.set(
                            "실제 채팅 " + str(self._twitch_received)
                            + "건 · AI 응답 " + str(self._twitch_replied)
                            + "건 · AI 오류 " + str(self._twitch_ai_failures) + "건")
                    elif kind == "twitch_ai_ok":
                        chat, result = payload
                        self._twitch_replied += 1
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
                    elif kind == "twitch_error":
                        self._twitch_status.set(
                            "실제 " + self._chat_platform.get() +
                            " 읽기 오류: " + str(payload))
                    elif kind == "twitch_finished":
                        if payload is self._twitch_session:
                            if self._twitch_ai_inbox is not None:
                                self._twitch_ai_inbox.put(None)
                                self._twitch_ai_inbox = None
                            self._twitch_session = None
                            self._twitch_start.configure(state="normal")
                            self._twitch_end.configure(state="disabled")
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
            self._results.put(("speech_error", str(exc)))
        else:
            self._results.put(("speech_done", result))

    def _stop_voice(self) -> None:
        self._queued_voice.clear()
        if self._tts_busy and self._voice_player.stop():
            self._tts_status.set("음성 재생 중지를 요청했습니다.")

    def _clear_memory(self) -> None:
        if self._busy:
            messagebox.showwarning("사용 중", "현재 응답 처리가 끝난 뒤 삭제할 수 있습니다.", parent=self)
            return
        approved = messagebox.askyesno("대화 기억 삭제", "저장된 대화 기억 전체를 삭제할까요? 되돌릴 수 없습니다.", parent=self)
        if not approved:
            return
        try:
            ConversationMemory().clear()
        except (OSError, Exception) as exc:
            messagebox.showerror("삭제 실패", str(exc), parent=self)
            return
        self._refresh_memory_count()
        self._append("시스템: PC에 저장된 대화 기억을 삭제했어요.")
