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


class LocalChatTab(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self._results: queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()
        self._busy = False
        self._model_name = tk.StringVar()
        self._input = tk.StringVar()
        self._memory_count = tk.StringVar(value="저장된 대화: 확인 전")

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
        self._input_info = tk.StringVar(value="대화 테스트는 음성·방송 송출을 하지 않습니다.")
        ttk.Label(self, textvariable=self._input_info, wraplength=550).pack(anchor="w", pady=(3, 10))
        bottom = ttk.Frame(self)
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self._memory_count).pack(side="left")
        ttk.Button(bottom, text="대화 기억 삭제", command=self._clear_memory).pack(side="right")
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
                    self._memory_count.set(f"저장된 대화: {payload.remembered_count}개")
                    self._input_info.set(payload.warning or "로컬 텍스트 응답 완료. 실방송 아님.")
                else:
                    self._append("연결 오류: " + str(payload))
                    self._input_info.set("PC에 Ollama와 해당 모델이 설치·실행 중인지 확인해 주세요.")
        except queue.Empty:
            pass
        self.after(150,self._poll)

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
