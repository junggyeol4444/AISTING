"""Run REAL installed local Ollama through the existing AISTING live-chat FIFO.

No fake language model is used by this CLI. It injects synthetic multi-platform
viewer messages into the production ONE-WORKER AI path, keeps the memory db
isolated in an OS temporary directory, and reports truthful local queue/AI
metrics. It does NOT prove actual viewer or OBS delivery. No stream, account,
chat posting, recording, voice cloning or external services are started.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
from collections.abc import Callable
import json
import math
import os
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
import tracemalloc
from types import SimpleNamespace

# 동시 보고서 저장 시 Windows 공유 잠금 경합을 방지한다.
_checkpoint_write_lock = threading.Lock()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop_chat import LocalChatRunner
from ai_broadcaster.desktop_chat_tab import LocalChatTab
from ai_broadcaster.live_runtime_metrics import LiveLatencyMetrics
from ai_broadcaster.multiplatform_readonly import PlatformChat
from ai_broadcaster.twitch_readonly import TwitchChatLine


class _TimestampedInputQueue(queue.Queue):
    """검증용 이벤트와 도착 시각을 같은 큐 잠금 안에서 접수한다.

    포화로 접수에 실패한 이벤트의 시각이 남아 다음 이벤트의
    AI 대기시간을 왜곡하지 않는다. 실제 방송 큐는 변경하지 않는다.
    """

    def put_chat(self, item, arrivals, *, timeout: float) -> None:
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout < 0:
            raise ValueError("검증 큐 대기 시간이 올바르지 않습니다.")
        with self.not_full:
            deadline = time.monotonic() + timeout
            while self._qsize() >= self.maxsize:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise queue.Full
                self.not_full.wait(remaining)
            arrivals.put(time.monotonic())
            self._put(item)
            self.unfinished_tasks += 1
            self.not_empty.notify()


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


def _make_isolated_production_reply(model: str, *, port: int, isolated: Path):
    """실제 GUI 수신기와 같은 세션별 로컬 모델 실행기를 단 한 번 만든다.

    기존 부하검사는 매 채팅마다 설정·기억·모델 실행기를 재생성하여
    실사용 GUI의 LocalChatRunner 재사용 경로와 측정 조건이 달랐다.
    이 함수는 테스트 전용 임시 SQLite/설정만 사용하고, 원본 단일
    FIFO·메시지별 개별 생성·기존 모델 옵션을 그대로 유지한다.
    """
    runner = LocalChatRunner(
        model, port=port,
        settings_path=isolated / "model_settings.json",
        memory_path=isolated / "live_test.sqlite",
        use_committed_gui_character=False,
    )

    def reply(model_name, text, *, sender, use_committed_gui_character):
        if model_name != model:
            raise ValueError("부하검사 중 로컬 모델이 변경되었습니다.")
        # 실제 GUI의 LocalChatRunner.reply와 동일한 재사용 경로.
        # 채팅 내용이나 모델 출력은 보고서에 저장하지 않는다.
        return runner.reply(text, sender=sender)

    return reply


def run_real_load(*, model: str, messages: int, duration_seconds: float,
                  port: int = 11434, queue_size: int = 10000,
                  duplicate: bool = False, arrival_rate: float = 0.0,
                  hold_full_duration: bool = False,
                  progress_callback: Callable[[dict], None] | None = None) -> dict:
    validate_parameters(messages, duration_seconds, queue_size, port)
    if (type(arrival_rate) not in (int, float)
            or not math.isfinite(arrival_rate) or arrival_rate < 0):
        raise ValueError("초당 합성 채팅 인입량은 0 이상의 유한수여야 합니다.")
    if type(hold_full_duration) is not bool:
        raise ValueError("전체 시간 검증 옵션 오류")
    if (type(model) is not str or not model.strip() or len(model) > 128
            or any(ord(ch) < 33 for ch in model)):
        raise ValueError("실제로 설치한 로컬 Ollama 모델 이름을 입력하세요.")

    input_fifo = _TimestampedInputQueue(maxsize=queue_size)
    observed = queue.Queue()
    arrivals = queue.SimpleQueue()
    start = time.monotonic()
    deadline = start + duration_seconds
    metrics = LiveLatencyMetrics(start, capacity=1024)
    real_reply = Counter()
    # 모델 메타데이터는 실제 Ollama가 제공한 응답에만 존재한다.
    # 과거 기본 응답과 테스트용 모의값에는 미측정으로 남긴다.
    server_stage_names = (
        "load_duration", "prompt_eval_duration", "eval_duration", "total_duration")
    server_stage_samples = {name: deque(maxlen=1024) for name in server_stage_names}
    server_stage_counts = Counter()

    def server_stage_p95(name):
        values = sorted(server_stage_samples[name])
        if not values:
            return None
        return values[math.ceil(len(values) * .95) - 1]

    platform_counts = Counter()
    # 수신 사건과 결과의 순서가 원본 단일 AI FIFO를 통과해도
    # 4개 플랫폼별 완료/지연이 뒤섞이지 않았는지 별도로 검증한다.
    platform_names = ("twitch", "chzzk", "soop", "youtube")
    pending_timing_platforms = deque()
    platform_latency_samples = {
        code: deque(maxlen=1024) for code in platform_names}
    platform_timing_counts = Counter()
    platform_over_three = Counter()
    platform_model_failures = Counter()
    max_observed_fifo_backlog = 0

    def platform_p95(code):
        samples = sorted(platform_latency_samples[code])
        return (samples[math.ceil(len(samples) * .95) - 1]
                if samples else None)

    emitted = 0
    worker_finished = threading.Event()
    stop_worker = threading.Event()
    # Hashable identity is used by the existing worker lifecycle set.
    session = type("_IsolatedSoakSession", (), {})()
    session._stop = stop_worker
    errors = []
    last_progress_completed = 0
    last_progress_at = start
    def publish_progress(*, force: bool = False) -> None:
        nonlocal last_progress_completed, last_progress_at
        if progress_callback is None:
            return
        now = time.monotonic()
        finished = metrics.completed
        # Once per 25 completed messages or every 60 seconds of running,
        # including long periods stuck in an Ollama request.
        if not (force or finished - last_progress_completed >= 25
                or now - last_progress_at >= 60):
            return
        snap = metrics.snapshot(now)
        try:
            progress_callback({
                "status": "running" if not force else "checkpoint",
                "real_model": True,
                "real_viewers": False,
                "target_messages": messages,
                "accepted": emitted,
                "not_accepted": messages - emitted,
                "completed": snap.completed,
                "success": real_reply["success"],
                "model_failure": real_reply["error"],
                "in_flight_or_queued": max(0, emitted - snap.completed),
                "over_three_seconds": snap.over_three_seconds,
                "p95_total_seconds": snap.total_p95,
                "p95_wait_seconds": snap.wait_p95,
                "p95_ai_seconds": snap.inference_p95,
                "max_observed_fifo_backlog": max_observed_fifo_backlog,
                "platform_completed_timing_counts": dict(platform_timing_counts),
                "platform_over_three_seconds": dict(platform_over_three),
                "platform_model_failures": dict(platform_model_failures),
                "platform_p95_total_seconds": {
                    code: platform_p95(code) for code in platform_names},
                "ollama_server_stage_p95_seconds": {
                    name: server_stage_p95(name) for name in server_stage_names},
                "ollama_server_stage_sample_counts": dict(server_stage_counts),
                "elapsed_seconds": round(now - start, 3),
                "goal_three_seconds_met_so_far": (
                    snap.completed > 0 and snap.over_three_seconds == 0),
                "actual_viewer_delivery_verified": False,
                "actual_24h_broadcast_verified": False,
            })
        except Exception:
            # 보고서 저장 실패는 실제 모델 처리 중단 대신 명시적인 실패로 남긴다.
            if "checkpoint_write_failed" not in errors:
                errors.append("checkpoint_write_failed")
        last_progress_completed = finished
        last_progress_at = now

    actual_arrival_rate = (
        (messages - 1) / max(1.0, duration_seconds - 60.0)
        if hold_full_duration and arrival_rate == 0 and messages > 1
        else arrival_rate
    )

    # This wrapper changes ONLY the test memory/settings location. Every AI
    # generation invokes the REAL production LocalOllamaReplyGenerator and
    # ChatPipeline against 127.0.0.1, not a canned or mocked response.
    with tempfile.TemporaryDirectory(prefix="AISTING_real_soak_") as sandbox:
        isolated = Path(sandbox)
        # 실제 수신 GUI와 동일하게 한 세션의 로컬 실행기를 재사용한다.
        # 테스트용 임시 설정·SQLite만 연결하며, 실사용자 파일은 열지 않는다.
        real_isolated_chat = _make_isolated_production_reply(
            model, port=port, isolated=isolated)

        ui = SimpleNamespace(
            _results=observed, _ai_arrival_times=arrivals,
            _live_latency_metrics=metrics, _twitch_active_workers={session})
        def consumer():
            try:
                # Injection only in the isolated load harness. Do NOT
                # monkeypatch the global production function while a daemon
                # could still be running after a timeout.
                LocalChatTab._work_twitch_ai(
                    ui, model, input_fifo, session=session,
                    reply_function=real_isolated_chat)
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                worker_finished.set()

        def consume_result(kind, value):
            # 실사용자 채팅·AI 응답 내용은 부하 보고서에 저장하지 않는다.
            if kind == "twitch_scoped":
                scope, kind, value = value
                if scope is not session:
                    errors.append("unexpected_session_scope")
                    return
            if kind == "twitch_ai_ok":
                real_reply["success"] += 1
                if isinstance(value, tuple) and len(value) == 2:
                    pending_timing_platforms.append(
                        getattr(value[0], "platform", "twitch"))
                else:
                    errors.append("invalid_platform_reply_pair")
                # 원래 성공 이벤트의 ChatResult에서 서버 계측만 추출한다.
                # 실제 채팅 문장·송신자·모델 출력은 보고서에 기록하지 않는다.
                reply = value[1] if isinstance(value, tuple) and len(value) == 2 else None
                timing = getattr(reply, "ollama_server_timings_seconds", None)
                if isinstance(timing, dict):
                    for name in server_stage_names:
                        value_seconds = timing.get(name)
                        if (type(value_seconds) in (int, float)
                                and math.isfinite(value_seconds) and value_seconds >= 0):
                            server_stage_samples[name].append(float(value_seconds))
                            server_stage_counts[name] += 1
            elif kind == "twitch_ai_error":
                real_reply["error"] += 1
                if isinstance(value, tuple) and len(value) == 2:
                    pending_timing_platforms.append(
                        getattr(value[0], "platform", "twitch"))
                else:
                    errors.append("invalid_platform_error_pair")
            elif kind == "twitch_ai_timing":
                platform = (pending_timing_platforms.popleft()
                            if pending_timing_platforms else None)
                if not metrics.terminal(*value):
                    real_reply["invalid_timing"] += 1
                elif platform not in platform_latency_samples:
                    errors.append("missing_platform_timing_pair")
                else:
                    elapsed = float(value[2])
                    platform_latency_samples[platform].append(elapsed)
                    platform_timing_counts[platform] += 1
                    platform_over_three[platform] += int(elapsed > 3)
                    platform_model_failures[platform] += int(value[3])
                # 결과를 한 묶음으로 회수해도 25/50건 체크포인트를 놓치지 않는다.
                publish_progress()

        def drain_observed(limit=128):
            # 24시간 동안 간격을 둔 입력에서도 완료된 결과를 누적 집계한다.
            for _ in range(limit):
                try:
                    kind, value = observed.get_nowait()
                except queue.Empty:
                    break
                consume_result(kind, value)
            publish_progress()

        tracemalloc.start()
        try:
            worker = threading.Thread(target=consumer, daemon=True)
            worker.start()
            for index in range(messages):
                if actual_arrival_rate > 0:
                    # Harness-only paced arrival; this pacing NEVER touches
                    # AISTING's production chat handling or adds AI delay.
                    planned = start + index / actual_arrival_rate
                    while time.monotonic() < planned:
                        if time.monotonic() >= deadline:
                            break
                        time.sleep(min(.25, max(0.0, planned - time.monotonic())))
                        drain_observed()
                if time.monotonic() >= deadline:
                    break
                event = make_message(index, duplicate=duplicate)
                # Queue capacity blocks instead of silently dropping any
                # accepted synthetic message. Deadline ends the test, not
                # the production policy of responding to every chat.
                try:
                    # Timestamp must precede the worker dequeue. Existing
                    # GUI uses a second FIFO with exactly this ordering.
                    input_fifo.put_chat(
                        event, arrivals,
                        timeout=min(3, max(.01, deadline-time.monotonic())))
                except queue.Full:
                    errors.append("bounded_test_backpressure_timeout")
                    break
                metrics.accept()
                emitted += 1
                platform_counts[getattr(event, "platform", "twitch")] += 1
                max_observed_fifo_backlog = max(
                    max_observed_fifo_backlog, input_fifo.qsize())
                drain_observed()

            # Do not force a sentinel behind a saturated queue for ever.
            while time.monotonic() < deadline:
                try:
                    input_fifo.put(None, timeout=min(1, max(.01, deadline-time.monotonic())))
                    break
                except queue.Full:
                    drain_observed()
                    continue

            while time.monotonic() < deadline:
                drain_observed()
                if worker_finished.is_set() and observed.empty():
                    if hold_full_duration:
                        # 이는 프로세스 생존 검사이지 실제 송출 검증은 아니다.
                        time.sleep(min(1.0, max(.01, deadline-time.monotonic())))
                        continue
                    break
                try:
                    kind, value = observed.get(timeout=.25)
                except queue.Empty:
                    publish_progress()
                    continue
                consume_result(kind, value)
                publish_progress()
            # Collect completed events even if the worker stopped just before
            # the deadline. Never call remaining events successful.
            if not worker_finished.is_set():
                # The deadline stops a *test*, not the user's live chat.
                # Abort ONLY this synthetic session and wait for the
                # current Ollama HTTP request to finish before destroying
                # its temp SQLite. The real reader's Stop semantics remain.
                stop_worker.set()
                try:
                    input_fifo.put_nowait(None)
                except queue.Full:
                    pass
                worker.join(timeout=45)
                if worker.is_alive():
                    errors.append("local_model_worker_unresponsive_after_stop")
            while not observed.empty():
                drain_observed()
            if pending_timing_platforms:
                errors.append("unmatched_platform_completion_timing")
            if emitted != messages:
                # Never mark a 500-message test as PASS if only the first
                # few arrived before the operator's finite test deadline.
                errors.append("requested_messages_not_fully_accepted")
            publish_progress(force=True)
            current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

    ended = time.monotonic()
    snap = metrics.snapshot(ended)
    return {
        "engine": "real-local-ollama-through-existing-aisting-fifo",
        "real_viewers": False,
        "model_name": model,
        "duration_seconds": round(ended - start, 3),
        "requested_duration_seconds": duration_seconds,
        "synthetic_arrival_rate_per_second": actual_arrival_rate,
        "completed_full_local_duration": bool(
            hold_full_duration and ended - start >= duration_seconds),
        "accepted": emitted,
        "not_accepted": messages - emitted,
        "requested_load_fully_accepted": emitted == messages,
        "platform_event_counts": dict(platform_counts),
        "completed": snap.completed,
        "model_success": real_reply["success"],
        "model_failure": real_reply["error"],
        "unfinished": emitted - snap.completed,
        "invalid_timing": snap.invalid,
        "over_three_seconds": snap.over_three_seconds,
        "local_p95_seconds": snap.total_p95,
        "local_wait_p95_seconds": snap.wait_p95,
        "local_ai_p95_seconds": snap.inference_p95,
        "local_p95_sample_count": snap.sampled,
        "max_observed_fifo_backlog": max_observed_fifo_backlog,
        "platform_completed_timing_counts": dict(platform_timing_counts),
        "platform_over_three_seconds": dict(platform_over_three),
        "platform_model_failures": dict(platform_model_failures),
        "platform_p95_total_seconds": {
            code: platform_p95(code) for code in platform_names},
        "ollama_server_stage_p95_seconds": {
            name: server_stage_p95(name) for name in server_stage_names},
        "ollama_server_stage_sample_counts": dict(server_stage_counts),
        "python_peak_bytes": peak,
        "worker_ended": worker_finished.is_set(),
        "processing_errors": errors,
        "viewer_end_to_end_verified": False,
        "long_running_broadcast_verified": False,
        "passed_no_drops": (
            not errors and emitted == messages and snap.completed == emitted and
            snap.invalid == 0 and real_reply["invalid_timing"] == 0 and
            sum(platform_timing_counts.values()) == emitted and
            real_reply["success"] == emitted and worker_finished.is_set()),
        "passed_three_second_local": (
            not errors and emitted == messages and snap.completed == emitted
            and snap.invalid == 0 and real_reply["invalid_timing"] == 0
            and sum(platform_timing_counts.values()) == emitted
            and real_reply["success"] == emitted and snap.over_three_seconds == 0),
    }


def _atomic_aggregate_checkpoint(path: Path, record: dict) -> None:
    """운영자가 지정한 집계 파일만 원자적으로 저장하며 채팅 원문은 기록하지 않는다."""
    destination = Path(path)
    # 12개 병렬 CI 쓰기에서도 하나의 프로세스는 단일 순서로 파일을 교체한다.
    with _checkpoint_write_lock:
        intermediate = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", delete=False,
                    dir=str(destination.parent),
                    prefix="." + destination.name + ".", suffix=".tmp") as output:
                intermediate = Path(output.name)
                output.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
                output.flush()
                os.fsync(output.fileno())
            # 외부 프로그램/다른 프로세스의 일시적 Windows 파일 잠금에만
            # 제한된 재시도를 수행한다. 영구 실패는 숨기지 않는다.
            for attempt in range(8):
                try:
                    os.replace(intermediate, destination)
                    break
                except PermissionError:
                    if attempt == 7:
                        raise
                    time.sleep(0.02 * (attempt + 1))
        finally:
            if intermediate is not None:
                intermediate.unlink(missing_ok=True)


def main() -> int:
    # Native Windows console/PowerShell often assigns cp1252 to frozen EXEs.
    # Force Korean UTF-8 *only* for the isolated test tool's console I/O.
    # Do not modify the main AISTING GUI encoding or user settings.
    for output in (sys.stdout, sys.stderr):
        if output is not None and hasattr(output, "reconfigure"):
            output.reconfigure(encoding="utf-8", errors="replace")
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
    def show_progress(record: dict) -> None:
        # Periodic real totals are essential during 500/24h live-model runs.
        print(
            f"[실제 모델 부하 진행] 완료 {record['completed']}"
            f"/접수 {record['accepted']}/목표 {record['target_messages']}건"
            f" · 실패 {record['model_failure']}건"
            f" · 3초 초과 {record['over_three_seconds']}건"
            f" · 대기 p95 {record['p95_wait_seconds']}"
            f" · 경과 {record['elapsed_seconds']}초",
            flush=True)
        if args.report is not None:
            _atomic_aggregate_checkpoint(args.report, record)

    result = run_real_load(
        model=args.model, messages=args.messages,
        duration_seconds=args.duration_seconds,
        port=args.port, queue_size=args.queue_size,
        duplicate=args.duplicate,
        arrival_rate=args.arrival_rate,
        hold_full_duration=args.hold_full_duration,
        progress_callback=show_progress)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report is not None:
        # 보고서 저장 실패를 성공 종료로 표시하거나 실제 처리 결과를 숨기지 않는다.
        # 원자적 저장 실패 시 이전 정상 보고서는 보존된다.
        try:
            _atomic_aggregate_checkpoint(args.report, result)
        except OSError as exc:
            print(f"[실제 모델 부하 보고서 저장 실패] {type(exc).__name__}",
                  file=sys.stderr, flush=True)
            return 2
    return 0 if result["passed_no_drops"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
