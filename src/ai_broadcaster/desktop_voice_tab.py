"""Windows EXE TTS preview tab. All playback is explicitly operator-triggered."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .windows_tts import Voice, WindowsSpeechPreview


class VoicePreviewTab(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self._backend = WindowsSpeechPreview()
        self._events: queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()
        self._voices: dict[str, Voice] = {}
        self._loading = False
        self._speaking = False
        self._selected = tk.StringVar()
        self._status = tk.StringVar(value="설치된 한국어 음성 목록을 확인해 주세요.")
        self._rate = tk.IntVar(value=0)
        self._volume = tk.IntVar(value=85)

        ttk.Label(
            self,
            text="무료 Windows 기본 음성 미리 듣기 (실방송에 출력되지 않음)",
            font=("Malgun Gothic", 11, "bold"),
        ).pack(anchor="w", pady=(1, 10))
        ttk.Label(
            self,
            text="이미 설치된 한국어 음성만 사용합니다. 음성이 없다면 임의로 다운로드하지 않아요.",
            wraplength=580,
        ).pack(anchor="w", pady=(0, 12))

        header = ttk.Frame(self)
        header.pack(fill="x", pady=5)
        ttk.Label(header, text="한국어 음성:", width=13).pack(side="left")
        self._voice_choice = ttk.Combobox(
            header, textvariable=self._selected, state="readonly", values=[], width=40,
        )
        self._voice_choice.pack(side="left", fill="x", expand=True)
        self._load_button = ttk.Button(header, text="음성 찾기", command=self._load)
        self._load_button.pack(side="left", padx=(8, 0))

        ttk.Label(self, text="미리 듣기 문장 (600글자 이하)").pack(anchor="w", pady=(12, 3))
        self._text = tk.Text(self, height=7, wrap="word", font=("Malgun Gothic", 10))
        self._text.pack(fill="both", expand=True)
        self._text.insert("1.0", "안녕하세요! 저는 아이스팅이에요. 반가워요!")

        settings = ttk.Frame(self)
        settings.pack(fill="x", pady=(12, 6))
        ttk.Label(settings, text="음량").pack(side="left")
        ttk.Scale(settings, from_=0, to=100, variable=self._volume, length=125).pack(side="left", padx=10)
        ttk.Label(settings, text="속도").pack(side="left", padx=(16, 0))
        ttk.Scale(settings, from_=-4, to=4, variable=self._rate, length=125).pack(side="left", padx=10)

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=10)
        self._play_button = ttk.Button(actions, text="미리 듣기", command=self._play)
        self._play_button.pack(side="left")
        self._play_button.configure(state="disabled")
        self._stop_button = ttk.Button(actions, text="소리 중지", command=self._stop)
        self._stop_button.pack(side="left", padx=8)
        self._stop_button.configure(state="disabled")
        ttk.Label(self, textvariable=self._status, wraplength=580).pack(anchor="w", pady=(5, 5))
        ttk.Label(
            self,
            text="방송 송출·AI 자동 발화와는 별개인 테스트 기능입니다.",
        ).pack(anchor="w")
        self.after(150, self._poll)

    def _load(self) -> None:
        if self._loading or self._speaking:
            return
        self._loading = True
        self._load_button.configure(state="disabled")
        self._play_button.configure(state="disabled")
        self._status.set("Windows 한국어 음성을 확인 중…")
        threading.Thread(target=self._list_worker, daemon=True).start()

    def _list_worker(self) -> None:
        try:
            voices = self._backend.list_korean_voices()
        except Exception as exc:
            self._events.put(("voice_error", str(exc)))
        else:
            self._events.put(("voices", voices))

    def _play(self) -> None:
        if self._loading or self._speaking:
            return
        voice = self._voices.get(self._selected.get())
        if voice is None:
            messagebox.showinfo("목소리 선택", "먼저 한국어 목소리를 선택해 주세요.", parent=self)
            return
        text = self._text.get("1.0", "end-1c").strip()
        if not text or len(text) > 600:
            messagebox.showwarning("입력 확인", "미리 듣기 문장은 1~600글자로 입력해 주세요.", parent=self)
            return
        self._speaking = True
        self._play_button.configure(state="disabled")
        self._load_button.configure(state="disabled")
        self._stop_button.configure(state="normal")
        self._status.set("PC에서 음성을 재생 중입니다…")
        rate = round(self._rate.get())
        volume = round(self._volume.get())
        threading.Thread(
            target=self._speak_worker, args=(text, voice, volume, rate), daemon=True,
        ).start()

    def _speak_worker(self, text: str, voice: Voice, volume: int, rate: int) -> None:
        try:
            self._backend.speak(text, voice, volume=volume, rate=rate)
        except Exception as exc:
            self._events.put(("playback_error", str(exc)))
        else:
            self._events.put(("playback_done", None))

    def _stop(self) -> None:
        if self._speaking:
            if self._backend.stop():
                self._status.set("미리 듣기를 중지했습니다.")

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._events.get_nowait()
                if kind in ("voices", "voice_error"):
                    self._loading = False
                    self._load_button.configure(state="normal")
                    if kind == "voice_error":
                        self._voices.clear()
                        self._voice_choice["values"] = []
                        self._selected.set("")
                        self._status.set("목소리 목록 조회 실패: " + str(payload))
                    else:
                        self._voices = {f"{voice.name} ({voice.culture})": voice for voice in payload}
                        options = list(self._voices)
                        self._voice_choice["values"] = options
                        self._selected.set(options[0] if options else "")
                        self._status.set(
                            f"한국어 목소리 {len(options)}개 발견. 미리 듣기 버튼을 눌러야만 소리가 납니다."
                            if options else "사용 가능한 한국어 시스템 음성이 없습니다. 설치는 자동으로 하지 않습니다."
                        )
                        self._play_button.configure(state="normal" if options else "disabled")
                elif kind in ("playback_error", "playback_done"):
                    self._speaking = False
                    self._load_button.configure(state="normal")
                    self._play_button.configure(state="normal" if self._voices else "disabled")
                    self._stop_button.configure(state="disabled")
                    self._status.set(
                        "음성 재생 완료." if kind == "playback_done"
                        else "미리 듣기 종료 또는 오류: " + str(payload)
                    )
        except queue.Empty:
            pass
        self.after(150, self._poll)
