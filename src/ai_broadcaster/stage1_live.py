"""AISTING rebuild / original-plan stage 1: real local AI conversation.

Separate from the old 100-screen diagnostic GUI. There is NO canned reply,
fake websocket, emulated clock, OBS control, streaming or model installation.
The operator must already have a real Ollama service/model installed; network
traffic is restricted by LocalOllamaGenerator to http://127.0.0.1:11434.
Voice uses only a real installed Windows ko-KR system voice, on opt-in.
The avatar is clearly labeled a placeholder Canvas portrait, NOT Live2D/VRM.
Stage 1 is NOT complete until real model/voice/avatar evidence is observed.
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from .avatar_renderer import AvatarFrame, draw_avatar
from .offline_chat import Answer, ChatMessage, LocalOllamaGenerator
from .offline_settings import active_persona, load_settings
from .offline_tts import KoreanVoice, WindowsKoreanSpeech, speech_chunks

BG = "#0e1729"
PANEL = "#1a2940"
TEXT = "#ecf2fb"
MUTED = "#a9bcd5"
ACCENT = "#70a7ff"


class Stage1LiveWindow(tk.Tk):
    """A real, explicitly operator-triggered localhost LLM + Windows TTS loop."""

    def __init__(self) -> None:
        super().__init__()
        self.title("AISTING · 1단계 실제 AI 연결")
        self.geometry("1120x720")
        self.minsize(950, 620)
        self.configure(bg=BG)
        self.settings = load_settings()
        self.persona = active_persona(self.settings)
        self.model = tk.StringVar()
        self.autospeak = tk.BooleanVar(value=False)
        self.voice_name = tk.StringVar()
        self.status = tk.StringVar(value="대기 · 실제 로컬 AI 모델을 연결하지 않았습니다.")
        self.voice_status = tk.StringVar(value="목소리 조회 전 · 소리 재생 안 함")
        self._speaker = WindowsKoreanSpeech()
        self._voices: dict[str, KoreanVoice] = {}
        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._history: list[Answer] = []
        self._busy = False
        self._voice_busy = False
        self._closing = False
        self._frame = 0
        self._poll_handle: str | None = None
        self._tick_handle: str | None = None
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._tick_handle = self.after(120, self._animate)
        self._poll_handle = self.after(100, self._poll)

    def _build(self) -> None:
        outer = tk.Frame(self, bg=BG, padx=24, pady=18)
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text="AISTING  /  실제 로컬 AI 스튜디오",
                 bg=BG, fg=TEXT, font=("Malgun Gothic", 20, "bold")
                 ).pack(anchor="w")
        tk.Label(
            outer, bg=BG, fg=MUTED, font=("Malgun Gothic", 10),
            text="원본 기획안 1단계의 실제 연결 경로를 개발 중 · 모델 자동 설치 없음 · OBS / 방송 플랫폼 미연결",
        ).pack(anchor="w", pady=(2, 18))

        stage = tk.Frame(outer, bg=BG)
        stage.pack(fill="both", expand=True)
        character = tk.Frame(stage, bg=PANEL, padx=15, pady=13)
        character.pack(side="left", fill="y", padx=(0, 14))
        tk.Label(character, text=self.persona["name"], bg=PANEL, fg=TEXT,
                 font=("Malgun Gothic", 18, "bold")).pack(anchor="w")
        tk.Label(character, text="저장된 캐릭터 사용 · 임시 2D 화면", bg=PANEL,
                 fg=MUTED, font=("Malgun Gothic", 9)).pack(anchor="w", pady=(2, 12))
        self.canvas = tk.Canvas(character, width=370, height=350,
                                bg="#17223c", highlightthickness=0, borderwidth=0)
        self.canvas.pack()
        tk.Label(character, text="현재: Canvas 샘플 · 실제 Live2D / VRM 엔진 연결 전",
                 bg=PANEL, fg=MUTED, wraplength=370,
                 font=("Malgun Gothic", 9)).pack(pady=(12, 8))
        tk.Label(character, text="음성 프로세스가 실제 재생 중일 때만 입 움직임",
                 bg=PANEL, fg=MUTED, wraplength=370,
                 font=("Malgun Gothic", 9)).pack()

        right = tk.Frame(stage, bg=PANEL, padx=15, pady=13)
        right.pack(side="left", fill="both", expand=True)
        tk.Label(right, text="실제 AI 대화", bg=PANEL, fg=TEXT,
                 font=("Malgun Gothic", 16, "bold")).pack(anchor="w")
        modelrow = tk.Frame(right, bg=PANEL)
        modelrow.pack(fill="x", pady=(10, 7))
        tk.Label(modelrow, text="Ollama 모델", fg=TEXT, bg=PANEL).pack(side="left")
        self.model_entry = ttk.Entry(modelrow, textvariable=self.model, width=21)
        self.model_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        tk.Label(
            right, text="PC의 127.0.0.1:11434에서 실제 실행 중인 모델만 사용합니다.",
            fg=MUTED, bg=PANEL, font=("Malgun Gothic", 9)
        ).pack(anchor="w", pady=(0, 5))
        self.conversation = tk.Text(
            right, height=11, state="disabled", wrap="word",
            bg="#101d31", fg=TEXT, insertbackground=TEXT,
            relief="flat", padx=12, pady=9, font=("Malgun Gothic", 11),
        )
        self.conversation.pack(fill="both", expand=True, pady=(3, 8))
        self._append_text("연결 전. 모의 답변은 사용하지 않습니다.\n")
        tk.Label(right, text="직접 대화 입력 (플랫폼 시청자 채팅 아님)",
                 fg=MUTED, bg=PANEL).pack(anchor="w")
        self.message = ttk.Entry(right, font=("Malgun Gothic", 11))
        self.message.pack(fill="x", pady=(4, 8))
        self.message.bind("<Return>", lambda _event: self._send())
        self.send = ttk.Button(right, text="실제 로컬 모델에 보내기", command=self._send)
        self.send.pack(fill="x", pady=(0, 9))
        tk.Label(right, textvariable=self.status, fg=ACCENT, bg=PANEL,
                 wraplength=560, justify="left").pack(anchor="w")

        audio = tk.Frame(right, bg=PANEL)
        audio.pack(fill="x", pady=(13, 3))
        ttk.Button(audio, text="설치된 한국어 목소리 확인",
                   command=self._lookup_voices).pack(side="left")
        self.voice_choice = ttk.Combobox(
            audio, textvariable=self.voice_name, state="readonly", width=25
        )
        self.voice_choice.pack(side="left", padx=(9, 0), fill="x", expand=True)
        ttk.Checkbutton(
            right, text="실제 AI 답변을 내 PC 스피커로 읽기 (직접 동의)",
            variable=self.autospeak,
        ).pack(anchor="w", pady=(5, 2))
        tk.Label(right, textvariable=self.voice_status,
                 fg=MUTED, bg=PANEL, wraplength=550).pack(anchor="w")

    def _append_text(self, text: str) -> None:
        self.conversation.configure(state="normal")
        self.conversation.insert("end", text)
        self.conversation.see("end")
        self.conversation.configure(state="disabled")

    def _send(self) -> None:
        if self._busy or self._closing:
            return
        utterance = self.message.get().strip()
        if not utterance or len(utterance) > 4000:
            messagebox.showwarning("대화 입력", "1~4000글자의 한국어 메시지를 입력해 주세요.")
            return
        try:
            generator = LocalOllamaGenerator(
                self.model.get().strip(),
                persona=self.persona,
                content=self.settings["content"],
            )
        except ValueError as exc:
            messagebox.showwarning("실제 로컬 모델", str(exc))
            return
        self._busy = True
        self.send.configure(state="disabled")
        self.model_entry.configure(state="disabled")
        self.message.configure(state="disabled")
        self.status.set("실제 127.0.0.1 Ollama에 요청 중 · 응답 확인 전")
        threading.Thread(
            target=self._request_worker, args=(generator, utterance, list(self._history)),
            daemon=True,
        ).start()

    def _request_worker(self, model: LocalOllamaGenerator, message: str,
                        history: list[Answer]) -> None:
        try:
            answer = model.generate(ChatMessage("운영자", message), history)
            if not isinstance(answer, str) or not answer.strip():
                raise RuntimeError("실제 로컬 AI가 빈 문장을 반환했습니다.")
            self._events.put(("answer", (message, answer)))
        except Exception as exc:
            self._events.put(("error", str(exc)))

    def _lookup_voices(self) -> None:
        if self._voice_busy or self._closing:
            return
        self._voice_busy = True
        self.voice_status.set("설치된 Windows 한국어 음성을 실제로 확인 중")
        threading.Thread(target=self._voices_worker, daemon=True).start()

    def _voices_worker(self) -> None:
        try:
            voices = self._speaker.installed_voices()
            self._events.put(("voices", voices))
        except Exception as exc:
            self._events.put(("voice_error", str(exc)))

    def _start_voice(self, reply: str) -> None:
        selected = self._voices.get(self.voice_name.get())
        if selected is None:
            self.voice_status.set("실제 음성 재생 불가 · 설치된 한국어 목소리를 선택해 주세요.")
            return
        try:
            parts = speech_chunks(reply)
        except ValueError as exc:
            self.voice_status.set("실제 음성 재생 불가: " + str(exc))
            return
        self._voice_busy = True
        self.voice_status.set("실제 Windows TTS 재생 요청 중 · 성공 미확인")
        threading.Thread(target=self._voice_worker, args=(parts, selected), daemon=True).start()

    def _voice_worker(self, parts: list[str], selected: KoreanVoice) -> None:
        try:
            for part in parts:
                if self._closing:
                    break
                result = self._speaker.speak(part, selected)
                if not result:
                    raise RuntimeError("음성 출력이 중단되었습니다.")
            else:
                self._events.put(("voice_done", None))
                return
            self._events.put(("voice_error", "종료로 음성 재생 중단"))
        except Exception as exc:
            self._events.put(("voice_error", str(exc)))

    def _poll(self) -> None:
        if self._closing:
            return
        try:
            while True:
                kind, data = self._events.get_nowait()
                if kind == "answer":
                    question, reply = data
                    self._history.append(Answer(ChatMessage("운영자", question), reply))
                    self.message.configure(state="normal")
                    self.message.delete(0, "end")
                    self._append_text("운영자: " + question + "\n" +
                                      self.persona["name"] + ": " + reply + "\n\n")
                    self.status.set("로컬 Ollama에서 실제 답변 수신 · 방송 미송출")
                    self._busy = False
                    self.send.configure(state="normal")
                    self.model_entry.configure(state="normal")
                    if self.autospeak.get():
                        self._start_voice(reply)
                elif kind == "error":
                    self.status.set("실제 AI 응답 실패 · 모의 답변 대체 없음: " + str(data))
                    self._busy = False
                    self.send.configure(state="normal")
                    self.model_entry.configure(state="normal")
                    self.message.configure(state="normal")
                elif kind == "voices":
                    self._voices = {v.name: v for v in data}
                    self.voice_choice.configure(values=tuple(self._voices))
                    if len(self._voices) == 1:
                        self.voice_name.set(next(iter(self._voices)))
                    self.voice_status.set(
                        "실제 설치된 ko-KR 음성 " + str(len(self._voices)) + "개 확인"
                        if self._voices else "설치된 한국어 음성 없음 · 자동 설치하지 않음"
                    )
                    self._voice_busy = False
                elif kind == "voice_error":
                    self.voice_status.set("실제 음성 실패: " + str(data))
                    self._voice_busy = False
                elif kind == "voice_done":
                    self.voice_status.set("실제 Windows TTS 재생 완료 · 방송 미송출")
                    self._voice_busy = False
        except queue.Empty:
            pass
        self._poll_handle = self.after(100, self._poll)

    def _animate(self) -> None:
        if self._closing:
            return
        draw_avatar(
            self.canvas,
            AvatarFrame(
                self.persona["name"], bool(self._speaker.speaking),
                self._frame, expression="neutral",
            )
        )
        self._frame += 1
        self._tick_handle = self.after(120, self._animate)

    def _close(self) -> None:
        self._closing = True
        if self._poll_handle is not None:
            self.after_cancel(self._poll_handle)
        if self._tick_handle is not None:
            self.after_cancel(self._tick_handle)
        self._speaker.stop()
        self.destroy()


def main() -> None:
    app = Stage1LiveWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
