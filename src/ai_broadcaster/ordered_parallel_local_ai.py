"""실제 Ollama 4개 동시 추론·완료순서가 아닌 원래 수신 FIFO 출력.

운영자 선택 시에만 기존 로컬 Ollama·페르소나로 같은 SQLite 미처리
순번에 해당하는 개별 답변을 선행 생성한다. 한 요청이 끝나도 이전
순번의 답변이 확정되기 전에는 GUI 전달/기억 저장/확인 ACK가 없다.
추론 시점의 대화 기억은 이미 확정된 대화만 포함하며, 추론 중인
다른 답변은 과거 사실인 양 프롬프트에 섞지 않는다.
GPU 실처리량이나 시청자 1~3초 응답은 보장하지 않는다.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from .conversation_memory import ConversationMemory, DEFAULT_MEMORY_FILE
from .long_term_conversation_memory import LongTermConversationMemory
from .desktop_chat import ChatResult
from .local_llm import LocalModelConfig, LocalOllamaReplyGenerator
from .operator_settings import load_settings, DEFAULT_FILE
from .offline_settings import active_persona, load_settings as load_gui_settings
from .session import ChatMessage


@dataclass(frozen=True)
class ParallelInferencePressure:
    """텍스트·사용자 식별자 없는 실제 선행 추론의 FIFO 대기 관측."""
    pending: int
    running: int
    waiting_to_run: int
    generated_waiting_fifo: int
    oldest_pending_seconds: float | None
    first_pending_seconds: float | None
    first_pending_is_complete: bool
    fifo_head_blocked: bool
    limit: int


class OrderedParallelLocalAI:
    """같은 세션에서 추론은 병렬, 메시지 기억/ACK는 FIFO로 확정."""

    def __init__(
        self, model: str, *, max_workers: int = 4,
        max_prefetch: int = 32,
        settings_path: Path = DEFAULT_FILE,
        memory_path: Path = DEFAULT_MEMORY_FILE,
        broadcast_facts: str = "",
        relevant_memory: bool = False,
        long_term_memory: bool = False,
    ) -> None:
        if type(max_workers) is not int or not 1 <= max_workers <= 4:
            raise ValueError("로컬 AI 동시 추론 개수는 1~4여야 합니다.")
        if (type(max_prefetch) is not int or
                not max_workers <= max_prefetch <= 512):
            raise ValueError("로컬 AI 선행 추론 창은 동시 작업자 이상·512건 이하여야 합니다.")
        self._prefetch_limit = max_prefetch
        if type(relevant_memory) is not bool or type(long_term_memory) is not bool:
            raise ValueError("과거 관련 기억/장기 보관 선택값이 올바르지 않습니다.")
        self._config = LocalModelConfig(
            model=model, max_relevant_exchanges=2 if relevant_memory else 0)
        self._memory = (LongTermConversationMemory(path=memory_path)
                        if long_term_memory else ConversationMemory(path=memory_path))
        settings = load_settings(settings_path)
        confirmed = active_persona(load_gui_settings())
        settings["persona"]["name"] = confirmed["name"]
        settings["persona"]["traits"] = confirmed["character"]
        settings["persona"]["speech_style"] = confirmed["style"]
        self._settings = settings
        self._broadcast_facts = broadcast_facts
        self._lock = threading.RLock()
        self._stopped = False
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="AISTING-로컬추론")
        self._pending: dict[int, Future] = {}
        self._submitted_at: dict[int, float] = {}
        self._completed_at: dict[int, float] = {}
        self._committed_sequence = 0

    def can_submit(self, sequence: int | None = None) -> bool:
        """SQLite를 삭제하지 않고 다음 선행 추론 슬롯을 받을 수 있는지 확인.

        수신기는 이 값이 거짓일 때 현재 SQLite 원본 순번에 머물며
        메모리 FIFO/스레드풀로 다음 수천 건을 미리 옮기지 않는다.
        """
        with self._lock:
            if self._stopped:
                return False
            if sequence is not None and sequence in self._pending:
                return True
            return len(self._pending) < self._prefetch_limit

    @property
    def prefetch_limit(self) -> int:
        return self._prefetch_limit

    def submit(self, sequence: int, text: str, *, sender: str) -> None:
        """원본 SQLite에 저장된 메시지만 중복 없이 비동기 선행 생성."""
        if type(sequence) is not int or sequence < 1:
            raise ValueError("로컬 AI 공개 채팅 FIFO 순번이 잘못되었습니다.")
        if type(text) is not str or not text.strip() or len(text) > 4000:
            raise ValueError("로컬 AI 공개 채팅 원문 길이가 잘못되었습니다.")
        if type(sender) is not str or not sender.strip() or len(sender) > 160:
            raise ValueError("로컬 AI 공개 채팅 닉네임이 잘못되었습니다.")
        with self._lock:
            if self._stopped:
                raise RuntimeError("이미 종료한 로컬 AI 병렬 작업자입니다.")
            if sequence <= self._committed_sequence:
                raise RuntimeError("완료된 순번을 다시 추론하지 않습니다.")
            if sequence in self._pending:
                return
            if len(self._pending) >= self._prefetch_limit:
                raise RuntimeError(
                    "로컬 AI 선행 추론 창이 가득 찼습니다 · "
                    "원본 SQLite 채팅을 건너뛰지 않고 다음 슬롯을 기다리세요")
            message = ChatMessage(str(uuid4()), sender.strip(), text.strip())
            future = self._executor.submit(self._infer_only, message)
            self._pending[sequence] = future
            self._submitted_at[sequence] = time.monotonic()
            def completed(_future, seq=sequence):
                with self._lock:
                    if self._pending.get(seq) is _future:
                        self._completed_at[seq] = time.monotonic()
            future.add_done_callback(completed)

    def _infer_only(self, message: ChatMessage) -> tuple[ChatMessage, str, dict | None]:
        """실제 모델 생성만 병렬화; 이 스레드에서는 기억/ACK/OBS 변경 금지."""
        generator = LocalOllamaReplyGenerator(
            self._config, self._settings, memory=self._memory,
            broadcast_facts=self._broadcast_facts)
        reply = generator.generate(message)
        return message, reply, generator.last_server_timings_seconds

    def finish(self, sequence: int, text: str, *, sender: str) -> ChatResult:
        """호출자가 기존 단일 AI FIFO에서 순서대로만 호출해야 함.

        완료 순번과 별개로 미래 응답을 전달하지 않는다. 모델 실패는
        caller로 전달되며 동일 원문 재시도는 다시 submit할 수 있다.
        """
        with self._lock:
            if self._stopped:
                raise RuntimeError("종료한 로컬 AI 세션 응답을 확정하지 않습니다.")
            if sequence <= self._committed_sequence:
                raise RuntimeError("로컬 AI 응답을 중복 저장하지 않습니다.")
            future = self._pending.get(sequence)
        if future is None:
            self.submit(sequence, text, sender=sender)
            with self._lock:
                future = self._pending[sequence]
        try:
            message, reply, timings = future.result()
        except Exception:
            with self._lock:
                self._pending.pop(sequence, None)
                self._submitted_at.pop(sequence, None)
                self._completed_at.pop(sequence, None)
            raise
        with self._lock:
            if self._stopped:
                raise RuntimeError("중지된 방송의 선행 추론 답변은 폐기합니다.")
            if self._pending.get(sequence) is not future:
                raise RuntimeError("실제 채팅의 선행 추론 순번이 변경되었습니다.")
            # 다른 채팅의 확정/기억보다 먼저 나가지 않게 commit은 이
            # FIFO 완료 스레드에서만 실행한다. 사용자의 대화 DB 불변식 보존.
            warning = ""
            try:
                self._memory.append(message, reply)
            except Exception:
                warning = "AI 답변 생성됨 · 기존 SQLite 대화 기억 저장 실패"
            count = self._memory.count()
            self._pending.pop(sequence, None)
            self._submitted_at.pop(sequence, None)
            self._completed_at.pop(sequence, None)
            self._committed_sequence = sequence
            return ChatResult(
                reply=reply, remembered_count=count, warning=warning,
                ollama_server_timings_seconds=timings)

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            self._pending.clear()
            self._submitted_at.clear()
            self._completed_at.clear()
            self._executor.shutdown(wait=False, cancel_futures=True)

    def pressure_snapshot(self) -> ParallelInferencePressure:
        """완료된 미래 답변이 앞 순번의 추론을 기다리는 실제 병목 관측.

        메시지/발화/대화 메모리에 영향을 주지 않고 조회하며, 모델 속도가
        빠르다고 추정하거나 완료 전 시청자 응답을 성공으로 집계하지 않는다.
        """
        with self._lock:
            now = time.monotonic()
            count = len(self._pending)
            if not count:
                return ParallelInferencePressure(0, 0, 0, 0, None, None,
                                                False, False, self._prefetch_limit)
            first_seq = min(self._pending)
            first = self._pending[first_seq]
            running = sum(future.running() for future in self._pending.values())
            queued = sum(not future.running() and not future.done()
                         for future in self._pending.values())
            ready = sum(future.done() for future in self._pending.values())
            born = self._submitted_at.get(first_seq)
            head_age = None if born is None else max(0.0, now - born)
            oldest = min(self._submitted_at.values(), default=None)
            oldest_age = None if oldest is None else max(0.0, now - oldest)
            return ParallelInferencePressure(
                count, running, queued, ready, oldest_age, head_age,
                first.done(), ready > 0 and not first.done(), self._prefetch_limit)

    @property
    def pending(self) -> int:
        with self._lock:
            return len(self._pending)
