"""Run REAL installed local Ollama through the existing AISTING live-chat FIFO.

No fake language model is used by this CLI. It injects synthetic multi-platform
viewer messages into the production ONE-WORKER AI path, keeps the memory db
isolated in an OS temporary directory, and reports truthful local queue/AI
metrics. It does NOT prove actual viewer or OBS delivery. No stream, account,
chat posting, recording, voice cloning or external services are started.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
import tracemalloc
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop_chat import run_local_chat as real_ollama_chat
from ai_broadcaster.desktop_chat_tab import LocalChatTab
from ai_broadcaster.live_runtime_metrics import LiveLatencyMetrics
from ai_broadcaster.multiplatform_readonly import PlatformChat
from ai_broadcaster.twitch_readonly import TwitchChatLine


def make_message(index: int, *, duplicate: bool = False):
    platform = ("twitch", "chzzk", "soop", "youtube")[index % 4]
    text = "안녕하세요. 한 문장으로 답하세요." if duplicate else (
        f"안녕하세요. {index + 1}번째 질문에 한 문장으로 답하세요.")
    channel = "isolated-load-only"
    sender = f"synthetic-{index + 1}"
    if platform == "twitch":
        return TwitchChatLine(channel, sender, text)
    return PlatformChat(channel, sender, text, platform)


def validate_parameters(messages: int, duration_seconds: float,
                        queue_size: int, local_port: int) -> None:
    if type(messages) is not int or not 1 <= messages <= 500000:
        raise ValueError("메시지 수는 1~500000 사이의 정수여야 합니다.")
    if type(duration_seconds) not in (int, float) or not (
            math.isfinite(duration_seconds) and 1 <= duration_seconds <= 86400):
        raise ValueError("검증 기간은 1초~24시간(86400초)이어야 합니다.")
    if type(queue_size) is not int or not 1 <= queue_size <= 100000:
        raise ValueError("검증용 큐 한도는 1~100000이어야 합니다.")
    if type(local_port) is not int or not 1 <= local_port <= 65535:
        raise ValueError("로컬 Ollama 포트 번호 오류")


def run_real_load(*, model: str, messages: int, duration_seconds: float,
                  port: int = 11434, queue_size: int = 10000,
                  duplicate: bool = False, arrival_rate: float = 0.0,
                  hold_full_duration: bool = False) -> dict:
    validate_parameters(messages, duration_seconds, queue_size, port)
    if (type(arrival_rate) not in (int, float)
            or not math.isfinite(arrival_rate) or arrival_rate < 0):
        raise ValueError("초당 합성 채팅 인입량은 0 이상의 유한수여야 합니다.")
    if type(hold_full_duration) is not bool:
        raise ValueError("전체 시간 검증 옵션 오류")
    if (type(model) is not str or not model.strip() or len(model) > 128
            or any(ord(ch) < 33 for ch in model)):
        raise ValueError("실제로 설치한 로컬 Ollama 모델 이름을 입력하세요.")

    input_fifo = queue.Queue(maxsize=queue_size)
    observed = queue.Queue()
    arrivals = queue.SimpleQueue()
    start = time.monotonic()
    deadline = start + duration_seconds
    metrics = LiveLatencyMetrics(start, capacity=1024)
    real_reply = Counter()
    platform_counts = Counter()
    emitted = 0
    producer_finished = threading.Event()
    worker_finished = threading.Event()
    errors = []

    # This wrapper changes ONLY the test memory/settings location. Every AI
    # generation invokes the REAL production LocalOllamaReplyGenerator and
    # ChatPipeline against 127.0.0.1, not a canned or mocked response.
    with tempfile.TemporaryDirectory(prefix="AISTING_real_soak_") as sandbox:
        isolated = Path(sandbox)
        def real_isolated_chat(model_name, text, *, sender,
                               use_committed_gui_character):
            return real_ollama_chat(
                model_name, text, port=port, sender=sender,
                use_committed_gui_character=False,
                settings_path=isolated / "model_settings.json",
                memory_path=isolated / "live_test.sqlite")

        ui = SimpleNamespace(
            _results=observed, _ai_arrival_times=arrivals,
            _live_latency_metrics=metrics)
        def consumer():
            try:
                LocalChatTab._work_twitch_ai(ui, model, input_fifo)
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                worker_finished.set()

        tracemalloc.start()
        with patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                   side_effect=real_isolated_chat):
            worker = threading.Thread(target=consumer, daemon=True)
            worker.start()
            for index in range(messages):
                if arrival_rate > 0:
                    # Harness-only paced arrival; this pacing NEVER touches
                    # AISTING's production chat handling or adds AI delay.
                    planned = start + index / arrival_rate
                    while time.monotonic() < planned:
                        if time.monotonic() >= deadline:
                            break
                        time.sleep(min(.25, planned - time.monotonic()))
                if time.monotonic() >= deadline:
                    break
                event = make_message(index, duplicate=duplicate)
                # Queue capacity blocks instead of silently dropping any
                # accepted synthetic message. Deadline ends the test, not
                # the production policy of responding to every chat.
                try:
                    # Timestamp must precede the worker dequeue. Existing
                    # GUI uses a second FIFO with exactly this ordering.
                    arrivals.put(time.monotonic())
                    input_fifo.put(event, timeout=min(3, max(.01, deadline-time.monotonic())))
                except queue.Full:
                    errors.append("bounded_test_backpressure_timeout")
                    break
                metrics.accept()
                emitted += 1
                platform_counts[getattr(event, "platform", "twitch")] += 1

            producer_finished.set()
            # Do not force a sentinel behind a saturated queue for ever.
            while time.monotonic() < deadline:
                try:
                    input_fifo.put(None, timeout=min(1, max(.01, deadline-time.monotonic())))
                    break
                except queue.Full:
                    continue

            while time.monotonic() < deadline:
                if worker_finished.is_set() and observed.empty():
                    if hold_full_duration:
                        # This checks the Python process can stay alive, NOT
                        # that OBS streamed for 24 hours or viewers heard it.
                        time.sleep(min(1.0, max(.01, deadline-time.monotonic())))
                        continue
                    break
                try:
                    kind, value = observed.get(timeout=.25)
                except queue.Empty:
                    continue
                if kind == "twitch_ai_ok":
                    real_reply["success"] += 1
                elif kind == "twitch_ai_error":
                    real_reply["error"] += 1
                elif kind == "twitch_ai_timing":
                    if not metrics.terminal(*value):
                        real_reply["invalid_timing"] += 1
            # Collect completed events even if the worker stopped just before
            # the deadline. Never call remaining events successful.
            while not observed.empty():
                kind, value = observed.get_nowait()
                if kind == "twitch_ai_ok":
                    real_reply["success"] += 1
                elif kind == "twitch_ai_error":
                    real_reply["error"] += 1
                elif kind == "twitch_ai_timing":
                    if not metrics.terminal(*value):
                        real_reply["invalid_timing"] += 1
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

    ended = time.monotonic()
    snap = metrics.snapshot(ended)
    return {
        "engine": "real-local-ollama-through-existing-aisting-fifo",
        "real_viewers": False,
        "model_name": model,
        "duration_seconds": round(ended - start, 3),
        "requested_duration_seconds": duration_seconds,
        "synthetic_arrival_rate_per_second": arrival_rate,
        "completed_full_local_duration": bool(
            hold_full_duration and ended - start >= duration_seconds),
        "accepted": emitted,
        "platform_event_counts": dict(platform_counts),
        "completed": snap.completed,
        "model_success": real_reply["success"],
        "model_failure": real_reply["error"],
        "unfinished": emitted - snap.completed,
        "over_three_seconds": snap.over_three_seconds,
        "local_p95_seconds": snap.total_p95,
        "local_wait_p95_seconds": snap.wait_p95,
        "local_ai_p95_seconds": snap.inference_p95,
        "python_peak_bytes": peak,
        "worker_ended": worker_finished.is_set(),
        "processing_errors": errors,
        "viewer_end_to_end_verified": False,
        "long_running_broadcast_verified": False,
        "passed_no_drops": (
            not errors and snap.completed == emitted and
            real_reply["success"] == emitted and worker_finished.is_set()),
        "passed_three_second_local": (
            snap.completed == emitted and snap.over_three_seconds == 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="실제 로컬 Ollama 모델·AISTING 원본 FIFO 장시간 부하실증")
    parser.add_argument("--model", required=True, help="설치된 실제 로컬 Ollama 모델")
    parser.add_argument("--messages", type=int, default=500)
    parser.add_argument("--duration-seconds", type=float, default=86400)
    parser.add_argument("--queue-size", type=int, default=10000)
    parser.add_argument("--port", type=int, default=11434)
    parser.add_argument("--duplicate", action="store_true")
    parser.add_argument("--arrival-rate", type=float, default=0.0,
                        help="시험 입력 초당 건수(0=최대한 빠르게 전송)")
    parser.add_argument("--hold-full-duration", action="store_true",
                        help="처리 완료 후에도 지정 시간까지 로컬 프로세스 유지 측정")
    parser.add_argument("--operator-approved", action="store_true",
                        help="운영자가 로컬 실제 모델 실행을 명시적으로 승인")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if not args.operator_approved:
        parser.error("--operator-approved로 실제 로컬 Ollama 호출을 승인해야 합니다")
    result = run_real_load(
        model=args.model, messages=args.messages,
        duration_seconds=args.duration_seconds,
        port=args.port, queue_size=args.queue_size,
        duplicate=args.duplicate,
        arrival_rate=args.arrival_rate,
        hold_full_duration=args.hold_full_duration)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report is not None:
        # Explicit operator-requested aggregate report only. No content,
        # sender names, voice data, model responses, credentials or tokens.
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["passed_no_drops"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
