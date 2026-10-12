"""AISTING EXE의 네이티브 로컬 AI 테스트 탭.

네트워크 요청은 운영자가 '텍스트 전송'을 누른 경우에만 한다.
작업자는 UI와 분리된 스레드에서 localhost에 접속하고,
결과만 tkinter 메인 이벤트 루프에서 표시한다.
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from .conversation_memory import ConversationMemory
from .desktop_chat import run_local_chat
from .reply_voice import ReplyVoicePlayer, should_auto_read
from .windows_tts import Voice


class LocalChatTab(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
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
        self._refresh_memory_count()
        self.after(150, self._poll)

    def _append(self, line: str) -> None:
        self._dialog.configure(state="normal")
        self._dialog.insert("end", line + "\n\n")
        self._dialog.see("end")
        self._dialog.configure(state="disabled")

    def _refresh_memory_count(self) -> None:
        try:
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
            result = run_local_chat(model,text)
        except Exception as exc:
            self._results.put(("error", str(exc)))
        else:
            self._results.put(("ok",result))

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._results.get_nowait()
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
                        if not self._tts_busy:
                            self._begin_read(payload.reply, selected)
                        else:
                            self._tts_status.set("음성 재생 중이므로 새 답변은 자동 재생하지 않았습니다.")
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
                    self._tts_busy = False
                    self._tts_find.configure(state="normal")
                    self._tts_stop.configure(state="disabled")
                    self._refresh_voice_buttons()
                    self._tts_status.set(
                        "AI 답변 음성 재생이 완료됐습니다." if kind == "speech_done"
                        else "음성 재생 종료 또는 오류: " + str(payload)
                    )
                else:
                    self._append("연결 오류: " + str(payload))
                    self._input_info.set("PC에 Ollama와 해당 모델이 설치·실행 중인지 확인해 주세요.")
        except queue.Empty:
            pass
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

    def _begin_read(self, reply: str, voice: Voice) -> None:
        if self._tts_busy:
            return
        self._tts_busy = True
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
