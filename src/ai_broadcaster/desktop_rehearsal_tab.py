"""EXE 안에서 다중 시청자 채팅을 순서대로 시험하는 로컬 GUI.

기본 모의 답변은 외부 연결이 전혀 없다. 로컬 Ollama 선택은 버튼 클릭 이후만.
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .chat_rehearsal import ChatRehearsal, ChatScriptError
from .conversation_memory import ConversationMemory
from .local_llm import LocalModelConfig, LocalOllamaReplyGenerator
from .operator_settings import load_settings


class ChatRehearsalTab(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self._runner = ChatRehearsal()
        self._configured = False
        self._busy = False
        self._events: queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()
        self._stop_event = threading.Event()
        self._mode = tk.StringVar(value="설치 없는 모의 응답")
        self._model = tk.StringVar()
        self._status = tk.StringVar(value="대기 중 · 실제 채팅 플랫폼과는 연결하지 않습니다.")
        self._counts = tk.StringVar(value="입력 0개 · 답변 0개 · 대기 0개")

        ttk.Label(self, text="시청자 채팅 순서 처리 시험",
                  font=("Malgun Gothic", 12, "bold")).pack(anchor="w", pady=(2, 8))
        ttk.Label(
            self, text="실제 시청자가 아니라 직접 입력한 대본입니다. 동일한 문장도 생략하지 않고 처리해요.",
            wraplength=620,
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(self, text="채팅 대본: 한 줄에 '닉네임: 내용' 형식 (한 번에 최대 500개)").pack(anchor="w")
        self._input = tk.Text(self, height=6, wrap="word", font=("Malgun Gothic", 10))
        self._input.pack(fill="both", expand=True, pady=(4, 7))
        self._input.insert("1.0", "철수: 안녕!\n영희: 오늘 뭐 할 거야?\n철수: 아까 질문에 답해 줘")

        row = ttk.Frame(self)
        row.pack(fill="x", pady=(2, 6))
        ttk.Label(row, text="답변 방식").pack(side="left")
        self._selector = ttk.Combobox(
            row, textvariable=self._mode, state="readonly",
            values=("설치 없는 모의 응답", "무료 로컬 AI (Ollama)"), width=24,
        )
        self._selector.pack(side="left", padx=(10, 8))
        ttk.Label(row, text="로컬 모델").pack(side="left")
        self._model_input = ttk.Entry(row, textvariable=self._model, width=20)
        self._model_input.pack(side="left", fill="x", expand=True, padx=(5, 0))

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(0, 4))
        self._add = ttk.Button(buttons, text="채팅 대기열에 추가", command=self._add_script)
        self._add.pack(side="left")
        self._run = ttk.Button(buttons, text="모두 답변", command=self._start)
        self._run.pack(side="left", padx=(6, 0))
        self._stop = ttk.Button(buttons, text="현재 답변 후 중지", command=self._request_stop)
        self._stop.pack(side="left", padx=(6, 0))
        self._stop.configure(state="disabled")
        self._new = ttk.Button(buttons, text="새 연습", command=self._reset)
        self._new.pack(side="right")

        ttk.Label(self, textvariable=self._counts).pack(anchor="w", pady=4)
        ttk.Label(self, textvariable=self._status, wraplength=620).pack(anchor="w", pady=(2, 6))
        self._output = tk.Text(self, height=9, wrap="word", state="disabled",
                               font=("Malgun Gothic", 9))
        self._output.pack(fill="both", expand=True)
        ttk.Label(
            self,
            text="기본 모드는 가짜 답변입니다. 실제 AI 사용은 사용자가 Ollama를 선택하고 실행해야 합니다."
                 " 테스트는 PC 내부 처리이며 방송·결제·계정 연결을 시작하지 않습니다.",
            wraplength=630,
        ).pack(anchor="w", pady=(7, 0))
        self.after(120, self._poll)

    def _append(self, text: str) -> None:
        self._output.configure(state="normal")
        self._output.insert("end", text + "\n")
        self._output.see("end")
        self._output.configure(state="disabled")

    def _update_counts(self) -> None:
        status = self._runner.status
        self._counts.set(
            f"입력 {status.total}개 · 답변 {status.processed}개 · 대기 {status.pending}개"
        )

    def _add_script(self) -> None:
        if self._busy:
            return
        text = self._input.get("1.0", "end-1c")
        try:
            added = self._runner.add_script(text)
        except ChatScriptError as exc:
            messagebox.showwarning("채팅 대본 확인", str(exc), parent=self)
            return
        self._append(f"시스템: {added}개 채팅을 대기열에 추가했습니다.")
        self._input.delete("1.0", "end")
        self._update_counts()
        self._status.set("모두 답변을 누르면 받은 순서대로 처리합니다.")

    def _start(self) -> None:
        if self._busy or self._runner.status.pending == 0:
            return
        if not self._configured:
            try:
                if self._mode.get() == "무료 로컬 AI (Ollama)":
                    model = self._model.get().strip()
                    generator = LocalOllamaReplyGenerator(
                        LocalModelConfig(model), load_settings(),
                        memory=ConversationMemory(),
                    )
                    self._runner.pipeline.generator = generator
                elif self._mode.get() != "설치 없는 모의 응답":
                    raise ValueError("알 수 없는 테스트 답변 방식입니다.")
            except (OSError, ValueError, TypeError) as exc:
                messagebox.showwarning("설정 확인", str(exc), parent=self)
                return
            self._configured = True
            self._selector.configure(state="disabled")
            self._model_input.configure(state="disabled")
        self._busy = True
        self._stop_event.clear()
        self._add.configure(state="disabled")
        self._run.configure(state="disabled")
        self._new.configure(state="disabled")
        self._stop.configure(state="normal")
        self._status.set("받은 순서대로 답변 처리 중… (의도적 지연 없음)")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        try:
            while not self._stop_event.is_set():
                result = self._runner.process_next()
                if result is None:
                    break
                self._events.put(("answer", (result.original.sender, result.original.text, result.reply)))
        except Exception as exc:
            self._events.put(("failed", str(exc)))
        else:
            self._events.put(("stopped" if self._stop_event.is_set() else "complete", None))

    def _request_stop(self) -> None:
        if self._busy:
            self._stop_event.set()
            self._status.set("현재 처리 중인 답변이 끝나면 중지합니다. 대기열은 유지됩니다.")

    def _reset(self) -> None:
        if self._busy:
            return
        if self._runner.status.pending and not messagebox.askyesno(
            "새 연습", "아직 답하지 않은 채팅이 있습니다. 명시적으로 대기열을 비우고 새 연습을 시작할까요?",
            parent=self,
        ):
            return
        self._runner = ChatRehearsal()
        self._configured = False
        self._selector.configure(state="readonly")
        self._model_input.configure(state="normal")
        self._output.configure(state="normal")
        self._output.delete("1.0", "end")
        self._output.configure(state="disabled")
        self._update_counts()
        self._status.set("새 연습 준비 완료.")

    def _poll(self) -> None:
        try:
            while True:
                kind, value = self._events.get_nowait()
                if kind == "answer":
                    sender, text, reply = value
                    self._append(f"{sender}: {text}\nAI: {reply}\n")
                    self._update_counts()
                else:
                    self._busy = False
                    self._add.configure(state="normal")
                    self._run.configure(state="normal")
                    self._new.configure(state="normal")
                    self._stop.configure(state="disabled")
                    self._update_counts()
                    if kind == "failed":
                        self._status.set(
                            "응답 오류: " + str(value) +
                            " · 실패한 채팅부터 대기 중입니다. 연결 확인 후 '모두 답변'으로 재시도하세요."
                        )
                    elif kind == "stopped":
                        self._status.set("중지했습니다. 답하지 않은 채팅은 대기열에 남아 있습니다.")
                    else:
                        self._status.set("입력한 채팅을 모두 처리했습니다. 실제 방송은 진행되지 않았습니다.")
        except queue.Empty:
            pass
        self.after(120, self._poll)
