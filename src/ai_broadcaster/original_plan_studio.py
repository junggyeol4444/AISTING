"""Original AISTING operator studio extension, not a replacement application.

Original plan 7-2: run the REAL preinstalled Open-LLM-VTuber and let its own
Live2D+TTS+LLM perform the actual first-stage demonstration. No fake chat,
sample-avatar success, download, install, broadcast, microphone or model use.

This module plugs into the existing ai_broadcaster.desktop.AistingApp Notebook.
"""
from __future__ import annotations

import http.client
import os
import re
from pathlib import Path
import queue
import shutil
import tempfile
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Official Open-LLM-VTuber default local endpoint, not a new backend.
OFFICIAL_HOST = "127.0.0.1"
OFFICIAL_PORT = 12393


class StageOneUnavailable(RuntimeError):
    """A real local dependency is missing; never replace it with a mock."""


def check_official_project(folder: str | Path) -> Path:
    """Only inspect the explicit project path; do not install or guess paths."""
    if not str(folder).strip():
        raise StageOneUnavailable("공식 Open-LLM-VTuber 프로젝트 폴더를 먼저 선택하세요.")
    try:
        base = Path(folder).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise StageOneUnavailable("선택된 프로젝트 폴더가 존재하지 않습니다.") from exc
    if not base.is_dir() or not (base / "run_server.py").is_file():
        raise StageOneUnavailable("이 폴더에는 공식 run_server.py가 없습니다.")
    if not (base / "pyproject.toml").is_file():
        raise StageOneUnavailable("이 폴더에는 공식 pyproject.toml이 없습니다.")
    return base


def official_frontend_http_status(timeout: float = 3.0) -> int:
    """Ask the real upstream HTTP server for '/' (not just an open TCP port).

    There are no redirects or requests to an external host. HTTP 200 does NOT
    establish that Live2D, LLM, speech or WebSockets have been loaded.
    """
    connection = None
    try:
        connection = http.client.HTTPConnection(OFFICIAL_HOST, OFFICIAL_PORT, timeout=timeout)
        connection.request('GET', '/', headers={'Host': 'localhost:12393'})
        response = connection.getresponse()
        response.read(4096)
        return int(response.status)
    except (OSError, http.client.HTTPException) as exc:
        raise StageOneUnavailable('공식 서버 HTTP 응답을 확인하지 못했습니다.') from exc
    finally:
        if connection is not None:
            connection.close()


def official_server_is_reachable(timeout: float = 3.0) -> bool:
    """Compatibility predicate. Only HTTP 200 from actual local upstream."""
    try:
        return official_frontend_http_status(timeout) == 200
    except StageOneUnavailable:
        return False


def prepare_official_launch(folder: str | Path) -> Path:
    """Read-only inspection of known upstream bootstrap side effects.

    The upstream run_server.py may execute ``git submodule update`` when the
    frontend is missing, and synchronize ``conf.yaml`` at startup. We cannot
    promise a side-effect-free launch merely from uv --offline --no-sync.
    """
    root = check_official_project(folder)
    frontend = root / "frontend" / "index.html"
    if frontend.is_symlink() or not frontend.is_file():
        raise StageOneUnavailable(
            "공식 프런트엔드가 준비되지 않았습니다 (frontend/index.html). "
            "공식 실행 시 Git 서브모듈을 자동 다운로드할 수 있으므로 실행하지 않습니다. "
            "설치·다운로드는 운영자의 별도 승인이 필요합니다."
        )
    config = root / "conf.yaml"
    if config.is_symlink() or not config.is_file():
        raise StageOneUnavailable(
            "공식 conf.yaml이 없습니다. 실행 중 자동 설정 생성·수정 방지를 위해 중단합니다."
        )
    return root


def launch_official_server(
    folder: str | Path, *, operator_authorized_side_effects: bool = False
) -> subprocess.Popen:
    """Start the real official upstream only after explicit operator approval.

    uv offline avoids package installation, but upstream itself may modify
    config, initialize caches or download models. That must be authorized
    separately at the operator UI before even spawning the upstream process.
    Never infer authorization from the folder path or a previous session.
    """
    if operator_authorized_side_effects is not True:
        raise StageOneUnavailable(
            "공식 실행 시의 설정 변경·모델 다운로드 가능성에 대한 이번 실행 승인이 없습니다."
        )
    root = prepare_official_launch(folder)
    uv = shutil.which("uv")
    if not uv:
        raise StageOneUnavailable("uv가 설치되어 있지 않습니다. 자동 설치하지 않습니다.")
    env = os.environ.copy()
    env["UV_OFFLINE"] = "1"
    env["UV_NO_SYNC"] = "1"
    # A real upstream server may fail to start due to a missing model or
    # runtime dependency. Preserve actual stderr instead of swallowing it.
    fd, output_path = tempfile.mkstemp(prefix="aisting-real-upstream-", suffix=".log")
    try:
        with os.fdopen(fd, "wb") as output:
            child = subprocess.Popen(
                [uv, "run", "--offline", "--no-sync", "run_server.py"],
                cwd=str(root), env=env, stdin=subprocess.DEVNULL,
                stdout=output, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    except OSError as exc:
        Path(output_path).unlink(missing_ok=True)
        raise StageOneUnavailable("공식 Open-LLM-VTuber 서버 실행 실패") from exc
    child._aisting_log_path = output_path
    return child


def _quoted_yaml(value: str) -> str:
    if not value or "\n" in value or "\r" in value or any(ord(c) < 32 for c in value):
        raise ValueError("실제 캐릭터 설정에 허용되지 않는 제어 문자가 있습니다.")
    return "'" + value.replace("'", "''") + "'"


def update_official_persona(source: str, fields: dict[str, str]) -> str:
    """Change only official character_config fields, keep every other engine.

    Identifies the exact official character_config mapping. No model, voice,
    audio or OBS work takes place. Refuse unknown upstream config layouts.
    """
    lines = source.splitlines(keepends=True)
    nodes = [i for i, l in enumerate(lines) if re.match(r"^character_config:\s*(?:#.*)?$", l.strip("\r\n"))]
    if len(nodes) != 1:
        raise ValueError("공식 character_config가 하나가 아닙니다. 원본은 변경하지 않습니다.")
    first = nodes[0] + 1
    stop = next((i for i in range(first, len(lines)) if lines[i].strip() and
                 not lines[i].startswith((" ", "#", "\t"))), len(lines))
    def find(key):
        matches = [i for i in range(first, stop)
                   if re.match(r"^  " + re.escape(key) + r":(?:\s|$)", lines[i])]
        if len(matches) != 1:
            raise ValueError("공식 캐릭터 설정의 " + key + " 필드를 찾을 수 없습니다.")
        return matches[0]
    name_at = find("character_name")
    prompt_at = find("persona_prompt")
    if name_at >= prompt_at:
        raise ValueError("지원하지 않는 공식 캐릭터 설정 순서입니다.")
    # Preserve comments and blank lines that belong to the following key.
    # A preceding upstream comment is not part of the persona_prompt value.
    prompt_end = next((i for i in range(prompt_at + 1, stop)
                       if lines[i].strip() and lines[i].startswith("  ") and
                       not lines[i].startswith("    ")), stop)
    while prompt_end > prompt_at + 1 and (not lines[prompt_end - 1].strip()
                                               or lines[prompt_end - 1].startswith("  #")):
        prompt_end -= 1
    # Stored AISTING identity only; unsaved editor drafts never reach upstream.
    for key in ("name", "style", "character"):
        _quoted_yaml(fields[key])
    ending = "\r\n" if "\r\n" in source else "\n"
    lines[name_at] = "  character_name: " + _quoted_yaml(fields["name"]) + ending
    prompt = [
        "너는 AI 버추얼 방송인 " + fields["name"] + "이다.",
        "캐릭터 성격: " + fields["character"],
        "한국어 말투: " + fields["style"],
    ]
    replacement = ["  persona_prompt: |" + ending] + ["    " + l + ending for l in prompt]
    lines[prompt_at:prompt_end] = replacement
    return "".join(lines)


def inspect_saved_persona_alignment(folder: str | Path, fields: dict[str, str]) -> bool:
    """Read-only comparison of the committed AISTING persona and official config.

    The same conservative, byte-preserving transformer used by the explicit
    Apply button must be a no-op for an aligned config. A mismatch is NOT
    proof that the running server uses a different persona: this checks only
    the existing conf.yaml on disk. Never read unsaved editor fields here.
    """
    root = check_official_project(folder)
    config = root / "conf.yaml"
    if config.is_symlink() or not config.is_file():
        raise StageOneUnavailable("공식 conf.yaml 일반 파일을 찾을 수 없습니다.")
    data = config.read_bytes()
    if len(data) > 1_000_000:
        raise StageOneUnavailable("공식 conf.yaml 크기가 비정상적입니다.")
    from .original_plan_config_io import decode_official_utf8
    try:
        current, _bom = decode_official_utf8(data)
        expected = update_official_persona(current, fields)
    except (UnicodeError, ValueError, KeyError) as exc:
        raise StageOneUnavailable("공식 캐릭터 설정의 읽기 전용 비교를 중단했습니다: " + str(exc)) from exc
    return current == expected


def save_official_persona(folder: str | Path, fields: dict[str, str]) -> tuple[Path, Path | None]:
    """Explicit real project config write with full unique non-destructive backup."""
    root = check_official_project(folder)
    config = root / "conf.yaml"
    if config.is_symlink() or not config.is_file():
        raise StageOneUnavailable("공식 conf.yaml을 찾을 수 없습니다. 임의 파일을 만들지 않습니다.")
    original = config.read_bytes()
    if len(original) > 1_000_000:
        raise StageOneUnavailable("공식 conf.yaml 크기가 비정상적입니다.")
    from .original_plan_config_io import decode_official_utf8, replace_official_config_with_backup
    try:
        original_text, bom = decode_official_utf8(original)
        updated = update_official_persona(original_text, fields)
        backup = replace_official_config_with_backup(
            config, original, bom + updated.encode('utf-8'), label='aisting')
    except (UnicodeError, ValueError, KeyError, OSError, RuntimeError) as exc:
        raise StageOneUnavailable("공식 캐릭터 설정 변경을 중단했습니다: " + str(exc)) from exc
    return config, backup



class OriginalPlanStudio:
    """Attach a real upstream operational view to the existing AISTING GUI."""

    def __init__(self, parent: ttk.Frame, app) -> None:
        self.parent = parent
        self.app = app
        self.project_dir = tk.StringVar(master=parent)
        self.state = tk.StringVar(master=parent, value="미연결 · 공식 AI/음성/Live2D 작동 미확인")
        self.voice_state = tk.StringVar(master=parent, value="실제 모델과 실제 목소리는 공식 화면에서 확인")
        self.saved_persona = tk.StringVar(master=parent)
        self.persona_sync_status = tk.StringVar(master=parent, value="공식 캐릭터 설정 파일 반영 여부 미확인")
        self.tts_status = tk.StringVar(master=parent, value="2단계 한국어 음성 · GPT-SoVITS 연결 미설정")
        self.obs_status = tk.StringVar(master=parent, value="3단계 OBS · 실제 연결 미확인")
        self.core_file_status = tk.StringVar(master=parent, value="공식 코어·Live2D 파일은 아직 검사하지 않았습니다.")
        self.ws_status = tk.StringVar(master=parent, value="실제 WebSocket 초기화는 아직 확인하지 않았습니다.")
        self.real_ai_status = tk.StringVar(master=parent,
            value="실제 AI 텍스트 대화 미실행 · 음성/아바타 검증과 구별")
        self._real_ai_busy = False
        self._real_ai_session = None
        self._real_ai_generation = 0
        self._real_ai_window: tk.Toplevel | None = None
        self._real_ai_output: tk.Text | None = None
        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._child: subprocess.Popen | None = None
        self._obs_window: tk.Toplevel | None = None
        self._obs_panel_status: tk.StringVar | None = None
        self._obs_check_in_progress = False
        self._closed = False
        self._after_id: str | None = None
        self._render()
        self._refresh_persona()
        self._after_id = parent.after(180, self._consume_events)

    def _render(self) -> None:
        # Real studio stays usable on a 1366x768 laptop: scroll content
        # instead of cutting off GPT-SoVITS and OBS controls below the fold.
        viewport = ttk.Frame(self.parent)
        viewport.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        canvas = tk.Canvas(viewport, highlightthickness=0, borderwidth=0)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        wrapper = ttk.Frame(canvas, padding=16)
        handle = canvas.create_window((0, 0), window=wrapper, anchor="nw")
        wrapper.bind("<Configure>", lambda _event: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(
            handle, width=event.width))
        def scroll_studio(event):
            if event.delta:
                canvas.yview_scroll(-int(event.delta / 120) or (-1 if event.delta > 0 else 1), "units")
            return "break"
        canvas.bind("<MouseWheel>", scroll_studio)
        wrapper.bind("<MouseWheel>", scroll_studio)
        ttk.Label(
            wrapper, text="AISTING  ·  AI 방송인", font=("Malgun Gothic", 21, "bold")
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            wrapper,
            text="원본 기획안 1단계 — 실제 Open-LLM-VTuber 실행 · AI 대화, 한국어 음성, Live2D 확인",
            font=("Malgun Gothic", 11), wraplength=840,
        ).pack(anchor="w", pady=(0, 18))

        identity = ttk.LabelFrame(wrapper, text="내 AI 방송인 · 저장된 캐릭터", padding=12)
        identity.pack(fill="x", pady=(0, 12))
        ttk.Label(identity, textvariable=self.saved_persona,
                  font=("Malgun Gothic", 12, "bold"), wraplength=800).pack(anchor="w")
        ttk.Button(identity, text="저장된 캐릭터 정보 새로 고침",
                   command=self._refresh_persona).pack(anchor="w", pady=(8, 0))
        ttk.Button(identity, text="확정 캐릭터 ↔ 공식 conf.yaml 비교 (읽기 전용)",
                   command=self._inspect_persona_alignment).pack(anchor="w", pady=(8, 0))
        ttk.Label(identity, textvariable=self.persona_sync_status,
                  wraplength=800).pack(anchor="w", pady=(4, 0))

        screen = ttk.LabelFrame(wrapper, text="실제 아바타·음성 화면", padding=12)
        screen.pack(fill="both", expand=True, pady=(0, 12))
        ttk.Label(
            screen, text="설치된 Open-LLM-VTuber Live2D 렌더러 연결",
            font=("Malgun Gothic", 14, "bold"),
        ).pack(anchor="w", pady=(6, 6))
        ttk.Label(
            screen,
            text="임시 그림이나 가짜 답변으로 실제 작동을 대신하지 않습니다."
                 " 실제 렌더러는 AISTING Windows 창에서 실행되며 AI 텍스트 창과 자동 동기화하지 않습니다."
                 " 공식 프로그램과 모델이 준비되지 않으면 연결 실패로 표시합니다.",
            wraplength=780, justify="left",
        ).pack(anchor="w", pady=(0, 15))
        ttk.Label(screen, textvariable=self.state, wraplength=780,
                  font=("Malgun Gothic", 11)).pack(anchor="w", pady=(0, 10))
        ttk.Label(screen, textvariable=self.voice_state, wraplength=780).pack(anchor="w")

        picker = ttk.Frame(wrapper)
        picker.pack(fill="x", pady=(0, 9))
        ttk.Label(picker, text="공식 프로그램 폴더").pack(side="left")
        ttk.Entry(picker, textvariable=self.project_dir).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(picker, text="찾아보기", command=self._browse).pack(side="right")

        buttons = ttk.Frame(wrapper)
        buttons.pack(fill="x", pady=(0, 12))
        ttk.Button(buttons, text="기존 공식 프로그램 실행",
                   command=self._start).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="실제 로컬 서버 연결 확인",
                   command=self._check).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="공식 AI 대화 + Live2D Windows 창 (같은 세션 · 승인 필요)",
                   command=self._open).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="이 앱이 실행한 공식 서버 중지",
                   command=self._stop_own_server).pack(side="left")
        ttk.Button(
            wrapper, text="1단계 · 공식 AI 설정·Live2D 실제 파일 검사 (읽기 전용)",
            command=self._inspect_core_files,
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(wrapper, textvariable=self.core_file_status,
                  wraplength=820, justify="left").pack(anchor="w", pady=(0, 12))
        ttk.Button(
            wrapper, text="1단계 · 공식 WebSocket 초기화 확인 (대화·음성 요청 안 함)",
            command=self._check_official_ws,
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(wrapper, textvariable=self.ws_status,
                  wraplength=820, justify="left").pack(anchor="w", pady=(0, 12))
        ttk.Button(
            wrapper, text="1단계 · 기존 Live2D 모델 선택 (공식 파일 · 승인 후 설정 저장)",
            command=self._open_real_live2d_choice,
        ).pack(anchor="w", pady=(0, 8))
        # Actual Stage-1 LLM call to the official core. No stubbed responses.
        ttk.Button(
            wrapper, text="1단계 · 실제 AI 텍스트 대화 (승인 후 · 소리 재생 안 함)",
            command=self._open_real_ai_chat,
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(wrapper, textvariable=self.real_ai_status,
                  wraplength=820, justify="left").pack(anchor="w", pady=(0, 12))
        ttk.Button(
            wrapper, text="저장된 캐릭터를 공식 Open-LLM-VTuber에 적용 (백업 후)",
            command=self._apply_official_identity,
        ).pack(anchor="w", pady=(0, 10))
        ttk.Label(
            wrapper,
            text="이 단계에서는 방송 플랫폼 송출·자동 시작·외부 게시를 실행하지 않습니다. "
                 "실제 AI 말하기/아바타 립싱크는 운영자 PC에서 확인해야 합니다.",
            wraplength=830,
        ).pack(anchor="w")
        # Original plan 7-3: use official GPT-SoVITS engine configuration,
        # never fake audio or silently train a speaker model.
        step2 = ttk.Frame(wrapper)
        step2.pack(fill="x", pady=(6, 0))
        ttk.Button(
            step2, text="2단계 · 실제 GPT-SoVITS 한국어 음성 연결 설정",
            command=self._open_gpt_sovits_panel,
        ).pack(side="left", padx=(0, 9))
        ttk.Label(step2, textvariable=self.tts_status, wraplength=490).pack(side="left")
        step3 = ttk.Frame(wrapper)
        step3.pack(fill="x", pady=(5, 0))
        ttk.Button(
            step3, text="3단계 · 실제 OBS 연결 확인 (송출 안 함)",
            command=self._open_obs_panel,
        ).pack(side="left", padx=(0, 9))
        ttk.Label(step3, textvariable=self.obs_status, wraplength=485).pack(side="left")

    def _check_official_ws(self) -> None:
        """Confirm actual upstream WebSocket init, never ask AI to speak."""
        if not messagebox.askyesno(
            "공식 WebSocket 연결 승인",
            "실제 127.0.0.1:12393/client-ws에 접속하여 공식 초기화 메시지만 읽습니다. "
            "서버는 연결 시 세션/로그를 만들 수 있습니다. AI 대화·음성 생성·마이크·방송은 "
            "요청하지 않습니다. 이번 연결을 승인하시겠습니까?",
            parent=self.parent,
        ):
            self.ws_status.set("운영자 승인 없음 · 실제 WebSocket 접속하지 않음")
            return
        self.ws_status.set("실제 WebSocket 초기화 메시지 대기 중 · AI/음성/Live2D 미검증")
        def job():
            from .original_plan_ws import probe_official_ws_initialization
            try:
                result = probe_official_ws_initialization(operator_approved=True)
            except (OSError, RuntimeError, ValueError, PermissionError) as exc:
                self._events.put(("ws_error", str(exc)))
            else:
                self._events.put(("ws_init", result))
        threading.Thread(target=job, daemon=True).start()

    def _require_confirmed_persona_for_real_ai(self) -> dict[str, str]:
        """Fail closed before any real AI turn if confirmed disk identity is not aligned.

        Read the confirmed settings file, never unsaved form fields. This checks
        conf.yaml ON DISK; the running official server may still need restart.
        """
        fields = self._read_confirmed_persona_from_disk()
        if not inspect_saved_persona_alignment(self.project_dir.get(), fields):
            raise StageOneUnavailable(
                '확정 저장된 캐릭터와 공식 conf.yaml이 일치하지 않습니다. '
                '캐릭터 확정·저장 후 공식 설정 적용을 확인하세요. '
                '현재 서버가 예전 설정을 사용한다면 별도 재시작 확인이 필요합니다.'
            )
        return fields

    def _open_real_ai_chat(self) -> None:
        """Send a real user-entered prompt to the official core, only by consent."""
        if self._real_ai_window is not None and self._real_ai_window.winfo_exists():
            self._real_ai_window.lift()
            return
        win = tk.Toplevel(self.parent)
        win.title("AISTING · 공식 AI 실제 대화")
        win.geometry("710x525")
        self._real_ai_window = win
        self._real_ai_generation += 1
        current_generation = self._real_ai_generation
        from .original_plan_conversation import OfficialConversationSession
        self._real_ai_session = OfficialConversationSession()
        def close_chat():
            if self._real_ai_session is not None:
                self._real_ai_session.close()
                self._real_ai_session = None
            self._real_ai_generation += 1  # Ignore any late worker results.
            self._real_ai_busy = False
            self._real_ai_output = None
            self._real_ai_window = None
            win.destroy()
        win.protocol('WM_DELETE_WINDOW', close_chat)
        frame = ttk.Frame(win, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="공식 Open-LLM-VTuber 127.0.0.1:12393/client-ws에 실제 질문",
                  font=("Malgun Gothic", 11, "bold")).pack(anchor="w")
        ttk.Label(frame,
            text="한 대화 창에서 여러 질문을 보내도 같은 공식 서버 세션을 사용합니다. "
                 "창을 닫거나 연결 오류가 나면 서버의 기존 세션 기억은 이어진다고 보장하지 않습니다. "
                 "앱은 응답 오디오를 재생/저장하지 않습니다. "
                 "공식 서버는 대화 기록을 저장하거나 음성 데이터를 생성할 수 있습니다. "
                 "캐릭터 확정 저장과 공식 conf.yaml의 읽기 전용 일치 검사를 거쳐야만 전송됩니다. "
                 "실행 중인 공식 서버에 변경 사항이 반영됐는지는 별도 확인해야 합니다. "
                 "공식 conf.yaml의 LLM이 외부/유료 서비스로 연결돼 있지 않은지 먼저 확인하세요.",
            wraplength=660, justify="left").pack(anchor="w", pady=(8, 10))
        ttk.Label(frame, text="질문 (사용자가 직접 입력 · 실행마다 별도 승인)").pack(anchor="w")
        input_box = tk.Text(frame, height=4, wrap="word")
        input_box.pack(fill="x")
        ttk.Label(frame, text="공식 서버가 보내온 실제 응답 텍스트").pack(anchor="w", pady=(12, 3))
        output = tk.Text(frame, height=11, wrap="word", state="disabled")
        output.pack(fill="both", expand=True)
        self._real_ai_output = output
        # Only the Tk main thread mutates widgets. Worker sends actual upstream
        # segments via the existing event queue; generation gates stale events.
        self._real_ai_stream_started = False
        self._real_ai_stream_parts = []
        footer = ttk.Frame(frame)
        footer.pack(fill="x", pady=(10, 0))
        indicator = tk.StringVar(master=win, value="아직 실행하지 않았습니다")
        ttk.Label(footer, textvariable=indicator).pack(side="left", fill="x", expand=True)
        def send():
            if self._real_ai_busy:
                indicator.set("기존 실제 AI 응답을 기다리는 중입니다")
                return
            message = input_box.get("1.0", "end-1c").strip()
            if not message or len(message) > 4000:
                messagebox.showerror("질문 확인", "질문을 1~4000자로 입력하세요.", parent=win)
                return
            try:
                approved_identity = self._require_confirmed_persona_for_real_ai()
            except (StageOneUnavailable, ValueError, OSError, KeyError) as exc:
                indicator.set('실제 AI 전송 차단 · 확정 캐릭터/공식 설정 불일치')
                messagebox.showerror('확정 캐릭터 확인 실패', str(exc), parent=win)
                return
            if not messagebox.askyesno(
                "실제 AI 대화 실행 승인",
                "실제 공식 서버의 LLM에 질문을 전송합니다. 공식 설정에 따라 외부 API 접속, "
                "대화기록 저장, TTS 음성 데이터 생성이 발생할 수 있습니다. "
                "이 앱은 스피커로 재생하거나 OBS로 송출하지 않습니다. "
                "이 질문의 실행을 명시적으로 승인하십니까?",
                parent=win):
                indicator.set("운영자 승인 취소 · 요청을 보내지 않았습니다")
                return
            try:
                # Recheck after the approval dialog; another window may have
                # committed a different identity while that dialog was open.
                if self._require_confirmed_persona_for_real_ai() != approved_identity:
                    raise StageOneUnavailable(
                        '승인 도중 확정 캐릭터가 변경됐습니다. 확인 후 다시 전송하세요.'
                    )
            except (StageOneUnavailable, ValueError, OSError, KeyError) as exc:
                indicator.set('실제 AI 전송 차단 · 확정 캐릭터 변경 감지')
                messagebox.showerror('확정 캐릭터 재확인 실패', str(exc), parent=win)
                return
            self._real_ai_busy = True
            self._real_ai_stream_started = False
            self._real_ai_stream_parts = []
            session = self._real_ai_session
            if session is None:
                self._real_ai_busy = False
                return
            send_button.configure(state="disabled")
            indicator.set("공식 AI의 실제 응답을 기다리는 중 · 완료/미완료는 수신 후 표시")
            self.real_ai_status.set("실제 공식 AI에 질문 전송 · 답변 수신 대기")
            def worker():
                def progress(kind, value):
                    # No widget access from background thread. Raw audio is
                    # never queued or retained; only WAV byte count is sent.
                    self._events.put(('ai_progress', (current_generation, message, kind, value)))
                try:
                    outcome = session.ask(message, operator_approved=True, on_progress=progress)
                except Exception as exc:
                    self._events.put(("ai_error", (current_generation, message, str(exc))))
                else:
                    self._events.put(("ai_result", (current_generation, message, outcome)))
            threading.Thread(target=worker, name="aisting-official-ai-turn", daemon=True).start()
        send_button = ttk.Button(footer, text="실제 AI에 질문 전송", command=send)
        send_button.pack(side="right")

        def send_to_same_live2d_session():
            """One approved AI turn handled inside the official viewer's own WS."""
            from .original_plan_frontend import send_to_native_live2d_session
            message = input_box.get("1.0", "end-1c").strip()
            if not 1 <= len(message) <= 4000:
                messagebox.showerror("질문 확인", "질문을 1~4000자로 입력하세요.", parent=win)
                return
            try:
                approved_identity = self._require_confirmed_persona_for_real_ai()
            except (StageOneUnavailable, ValueError, OSError, KeyError) as exc:
                indicator.set("확정 캐릭터/공식 설정 불일치 · 전송하지 않음")
                messagebox.showerror("확정 캐릭터 확인 실패", str(exc), parent=win)
                return
            if not messagebox.askyesno(
                "같은 공식 Live2D·TTS 세션으로 실제 질문",
                "이미 AISTING에서 연 공식 Live2D Windows 창의 대화 입력에 "
                "질문을 전달합니다. 별도의 AI WebSocket 세션을 만들지 않고 "
                "공식 창에서 답변·GPT-SoVITS 음성·입모양을 처리하도록 요청합니다. "
                "공식 설정에 따라 유료/외부 AI 요청이나 음성 합성, 기록이 발생할 수 "
                "있지만 OBS 송출은 시작하지 않습니다. 이번 질문을 실행합니까?",
                parent=win,
            ):
                indicator.set("운영자 승인 취소 · 요청을 보내지 않았습니다")
                return
            try:
                if self._require_confirmed_persona_for_real_ai() != approved_identity:
                    raise StageOneUnavailable("승인 도중 확정 캐릭터가 변경됐습니다.")
                send_to_native_live2d_session(message, operator_approved=True)
            except (RuntimeError, OSError, ValueError, PermissionError) as exc:
                indicator.set("동일 Live2D 세션 전달 실패 · " + str(exc))
                return
            input_box.delete("1.0", "end")
            indicator.set("공식 Live2D 창 입력 전달 요청 · 실제 AI/음성/립싱크 결과는 창에서 확인")
            self.real_ai_status.set("공식 Live2D 한 세션으로 입력 전달 시도 · 실제 서버 수신/영상/오디오 미검증")
            output.configure(state="normal")
            output.insert(
                "end", "나 [공식 Live2D 창 동일 세션 전달 요청]: " + message +
                "\\n[실제 응답은 공식 Live2D 창에 표시됩니다. "
                "전송 수신과 음성·립싱크는 확인되지 않았습니다.]\\n\\n"
            )
            output.see("end")
            output.configure(state="disabled")

        ttk.Button(
            footer, text="공식 Live2D 창 같은 세션으로 전송",
            command=send_to_same_live2d_session,
        ).pack(side="right", padx=(0, 9))
        self._ai_submit_button = send_button
        self._ai_indicator = indicator

    def _inspect_core_files(self) -> None:
        """Read upstream real files; never certify live AI/TTS/avatar operation."""
        from .original_plan_readiness import inspect_existing_official_core
        try:
            result = inspect_existing_official_core(self.project_dir.get())
        except (OSError, ValueError, StageOneUnavailable) as exc:
            self.core_file_status.set("실제 파일 검사 실패: " + str(exc))
            return
        lines = [
            "현재 설정된 캐릭터: " + result.character_name,
            "공식 LLM 에이전트: " + result.agent_type + " / 연결 엔진: " + result.llm_backend,
            "설정된 음성 엔진: " + result.tts_engine,
            "선택된 Live2D: " + result.live2d_model_name +
            " / 로컬 Cubism 참조 파일 존재: " + str(result.live2d_asset_files) + "개",
        ]
        if result.issues:
            lines.extend("검토 필요: " + issue for issue in result.issues)
        lines.append("파일 존재 여부만 확인 · 실제 AI 응답·음성·Live2D 동작은 여전히 미검증")
        self.core_file_status.set("\n".join(lines))

    def _open_real_live2d_choice(self) -> None:
        """Select only real installed Cubism assets; no preview, fake avatar or launch."""
        from .original_plan_avatar import (
            inspect_official_live2d_options, apply_official_live2d_choice,
        )
        folder = self.project_dir.get()
        try:
            options = inspect_official_live2d_options(folder)
        except (OSError, ValueError, StageOneUnavailable) as exc:
            messagebox.showerror("공식 Live2D 모델 목록", str(exc), parent=self.parent)
            return
        window = tk.Toplevel(self.parent)
        window.title("1단계 · 실제 설치된 Live2D 선택")
        window.geometry("650x370")
        frame = ttk.Frame(window, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="공식 Open-LLM-VTuber model_dict.json의 기존 모델만 표시합니다.",
                  wraplength=600).pack(anchor="w", pady=(0, 8))
        ttk.Label(frame, text="현재 conf.yaml 설정: " + options.selected_name,
                  wraplength=590).pack(anchor="w", pady=(0, 10))
        names = [entry.name for entry in options.choices]
        selected = tk.StringVar(master=window, value=options.selected_name
                                if options.selected_name in names else '')
        box = ttk.Combobox(frame, textvariable=selected, values=names, state="readonly")
        box.pack(fill="x")
        detail = tk.StringVar(master=window)
        def refresh(_event=None):
            choice = next((a for a in options.choices if a.name == selected.get()), None)
            if choice is None:
                detail.set("사용자가 모델을 선택하지 않았습니다.")
            elif not choice.available:
                detail.set("선택 불가 · 필수 Live2D 파일 부족/오류: " + choice.issue)
            else:
                detail.set("공식 모델 참조: " + choice.url + "\n기존 Cubism 필수 파일 " +
                           str(choice.asset_files) + "개 확인 (실제 렌더링은 별도 검증)")
        box.bind('<<ComboboxSelected>>', refresh)
        ttk.Label(frame, textvariable=detail, wraplength=600, justify="left").pack(
            anchor="w", pady=(12, 12))
        refresh()
        ttk.Label(frame, text="선택한 모델은 공식 conf.yaml의 live2d_model_name만 변경합니다. "
                  "기존 모델 파일은 변경하지 않습니다. "
                  "이미 실행 중인 공식 서버/Live2D 화면은 별도로 다시 시작해야 반영될 수 있습니다. "
                  "서버 재시작·다운로드·방송은 자동 실행하지 않습니다.",
                  wraplength=600, justify="left").pack(anchor="w")
        def apply():
            chosen = next((a for a in options.choices if a.name == selected.get()), None)
            if chosen is None or not chosen.available:
                messagebox.showerror("Live2D 모델 검사", "기존 모델과 필수 파일이 확인된 항목을 선택하세요.", parent=window)
                return
            if not messagebox.askyesno(
                "기존 공식 Live2D 설정 변경 승인",
                "실제 공식 conf.yaml 파일을 백업하고 live2d_model_name을 '" + chosen.name +
                "'(으)로 저장합니다.\n이번 변경은 AI/음성/송출을 시작하지 않습니다. "
                "이 파일 변경을 승인하시겠습니까?", parent=window,
            ):
                return
            try:
                config, backup = apply_official_live2d_choice(
                    folder, chosen.name,
                    expected_config_sha256=options.config_sha256,
                    operator_approved=True)
            except (OSError, ValueError, RuntimeError, PermissionError) as exc:
                messagebox.showerror("Live2D 모델 변경 중단", str(exc), parent=window)
                return
            if backup is None:
                messagebox.showinfo("설정 유지", "현재 공식 conf.yaml의 모델 설정과 같습니다. 변경하지 않았습니다.", parent=window)
            else:
                messagebox.showinfo("Live2D 설정 저장", "기존 공식 설정을 백업한 후 모델 이름만 변경했습니다. "
                                    "실제 모델 표시/립싱크는 아직 검증되지 않았으며 "
                                    "공식 서버 재시작은 별도 승인으로 수행해야 합니다.", parent=window)
            window.destroy()
            self._inspect_core_files()
        ttk.Button(frame, text="기존 모델 선택 확정 (설정 파일 수정은 별도 승인)", command=apply).pack(
            anchor="w", pady=(14, 0))

    def _open_gpt_sovits_panel(self) -> None:
        """Real upstream config editor; no network/audio/training on open."""
        from .original_plan_tts import (VoiceConfigurationError,
                                         apply_official_gpt_sovits,
                                         synthesize_local_gpt_sovits,
                                         inspect_reference_audio_container,
                                         validate_local_gpt_sovits_url)
        window = tk.Toplevel(self.parent)
        window.title("원본 기획안 2단계 · GPT-SoVITS 실제 목소리 연결")
        window.geometry("720x515")
        window.minsize(610, 475)
        form = ttk.Frame(window, padding=17)
        form.pack(fill="both", expand=True)
        ttk.Label(form, text="이미 확보한 목소리의 GPT-SoVITS 연결 설정",
                  font=("Malgun Gothic", 14, "bold")).pack(anchor="w")
        ttk.Label(form, text="공식 Open-LLM-VTuber conf.yaml만 변경합니다. 새 음성 학습·설치·재생 없음.",
                  wraplength=670).pack(anchor="w", pady=(5, 11))
        selection = ttk.Frame(form)
        selection.pack(fill="x", pady=(0, 8))
        ttk.Label(selection, text="본인/동의/라이선스 확보된 참조 음성 WAV/FLAC").pack(anchor="w")
        path_var = tk.StringVar(master=window)
        ttk.Entry(selection, textvariable=path_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        def browse_voice():
            result = filedialog.askopenfilename(
                parent=window, title="권리 확인된 참조 음성 선택",
                filetypes=[("WAV 또는 FLAC", "*.wav *.flac")],
            )
            if result:
                path_var.set(result)
        ttk.Button(selection, text="찾아보기", command=browse_voice).pack(side="right")
        ttk.Label(form, text="참조 음성 파일에서 실제로 말한 문장").pack(anchor="w")
        prompt_var = tk.StringVar(master=window)
        ttk.Entry(form, textvariable=prompt_var).pack(fill="x", pady=(5, 10))
        ttk.Label(form, text="이미 실행 중인 무료·로컬 GPT-SoVITS API 주소 (설치/접속 안 함)").pack(anchor="w")
        endpoint_var = tk.StringVar(master=window, value="http://127.0.0.1:9880/tts")
        ttk.Entry(form, textvariable=endpoint_var).pack(fill="x", pady=(5, 10))
        ttk.Label(form, text="실제 한국어 합성 시험 문장 (재생/저장/송출 안 함)").pack(anchor="w")
        synthesis_text = tk.StringVar(master=window, value="안녕하세요. 반갑습니다.")
        ttk.Entry(form, textvariable=synthesis_text).pack(fill="x", pady=(5, 6))
        note = tk.StringVar(master=window, value="입력만으로 파일을 수정하지 않습니다.")
        ttk.Label(form, textvariable=note, wraplength=665).pack(anchor="w", pady=(0, 8))
        def apply():
            try:
                project = check_official_project(self.project_dir.get())
                audio_file = Path(path_var.get()).expanduser()
                if not audio_file.is_file():
                    raise VoiceConfigurationError("실제 참조 음성을 선택해야 합니다.")
                if not prompt_var.get().strip():
                    raise VoiceConfigurationError("참조 음성에 녹음된 문장을 입력하세요.")
                format_info = inspect_reference_audio_container(audio_file)
                endpoint = validate_local_gpt_sovits_url(endpoint_var.get())
            except (StageOneUnavailable, VoiceConfigurationError) as exc:
                note.set(str(exc))
                return
            if not messagebox.askyesno(
                "실제 GPT-SoVITS 설정 변경 확인",
                "선택한 음성은 본인/동의/라이선스 권리가 확보된 자료인가요? "
                "공식 Open-LLM-VTuber conf.yaml을 백업하고 GPT-SoVITS에 연결하겠습니까? "
                "참조 파일 형식: " + format_info + "\n로컬 API: " + endpoint + "\n"
                "모델 학습이나 실제 합성은 시작하지 않습니다.",
                parent=window,
            ):
                return
            try:
                output, backup = apply_official_gpt_sovits(
                    project, audio_file, prompt_var.get(), api_url=endpoint
                )
            except (VoiceConfigurationError, StageOneUnavailable, OSError) as exc:
                note.set("연결 설정 실패: " + str(exc))
                return
            result = ("GPT-SoVITS 설정 기록 완료 · 실제 목소리 작동은 미검증"
                      if backup else "GPT-SoVITS 설정 동일 · 실제 목소리 작동은 미검증")
            note.set(result)
            self.tts_status.set(result)
        synthesis_busy = {"running": False}

        def test_real_synthesis():
            if synthesis_busy["running"]:
                return
            try:
                audio_file = Path(path_var.get()).expanduser()
                if not audio_file.is_file():
                    raise VoiceConfigurationError("권리가 확보된 실제 WAV/FLAC 참조 음성을 선택하세요.")
                inspect_reference_audio_container(audio_file)
                reference_text = prompt_var.get()
                if not reference_text.strip():
                    raise VoiceConfigurationError("참조 음성에서 실제 발화된 문장을 입력하세요.")
                endpoint = validate_local_gpt_sovits_url(endpoint_var.get())
                sentence = synthesis_text.get().strip()
                if not 1 <= len(sentence) <= 200:
                    raise VoiceConfigurationError("시험 문장은 1~200글자로 입력하세요.")
            except (OSError, VoiceConfigurationError) as exc:
                note.set("합성 준비 실패: " + str(exc))
                return
            if not messagebox.askyesno(
                "이번 한 번만 실제 한국어 합성 실행",
                "선택한 참조 음성의 소유/동의/라이선스 권리를 확인했습니까?\\n"
                "기존 로컬 GPT-SoVITS 서버에 실제 음성 합성 요청을 1회 보냅니다. "
                "참조 음성 경로와 해당 녹음 문장은 로컬 서버로 전송됩니다. "
                "모델 학습·설치·소리 재생·파일 저장·OBS 송출은 하지 않습니다.\\n"
                "요청 주소: " + endpoint + "\\n실행할까요?",
                parent=window,
            ):
                return
            synthesis_busy["running"] = True
            synthesis_btn.configure(state="disabled")
            note.set("로컬 GPT-SoVITS 실제 합성 응답 확인 중… 소리는 재생하지 않습니다.")
            def synth_worker():
                try:
                    result = synthesize_local_gpt_sovits(
                        audio_file, reference_text, sentence, api_url=endpoint,
                        operator_approved=True, rights_confirmed=True,
                    )
                except Exception as exc:
                    message = "실제 합성 실패: " + str(exc)
                else:
                    message = (
                        f"실제 한국어 합성 WAV 수신: {result.sample_rate}Hz / "
                        f"{result.channels}채널 / {result.frame_count}프레임 / "
                        f"{result.wav_bytes}바이트. 재생·Live2D·OBS는 미검증"
                    )
                self._events.put(("gpt_synth_result", (window, note, synthesis_btn,
                                                        synthesis_busy, message)))
            threading.Thread(target=synth_worker, daemon=True).start()

        footer = ttk.Frame(form)
        footer.pack(fill="x", pady=(6, 0))
        synthesis_btn = ttk.Button(
            footer, text="실제 한국어 WAV 합성 확인", command=test_real_synthesis
        )
        synthesis_btn.pack(side="left", padx=(0, 8))
        ttk.Button(footer, text="취소 / 닫기", command=window.destroy).pack(side="right")
        ttk.Button(footer, text="공식 설정 백업 후 적용",
                   command=apply).pack(side="right", padx=(0, 10))

    def _open_obs_panel(self) -> None:
        """Actual OBS WebSocket status query; never trigger outgoing stream."""
        from .original_plan_obs import OfficialObsWebsocket, ObsConnectionError
        if self._obs_window is not None and self._obs_window.winfo_exists():
            self._obs_window.lift()
            return
        window = tk.Toplevel(self.parent)
        self._obs_window = window
        def close_window():
            self._obs_window = None
            self._obs_panel_status = None
            window.destroy()
        window.protocol('WM_DELETE_WINDOW', close_window)
        window.title("원본 기획안 3단계 · OBS 실제 연결 확인")
        window.geometry("700x440")
        form = ttk.Frame(window, padding=16)
        form.pack(fill="both", expand=True)
        ttk.Label(form, text="실제 OBS WebSocket 접속 확인",
                  font=("Malgun Gothic", 14, "bold")).pack(anchor="w")
        ttk.Label(
            form, text="현재 PC의 OBS WebSocket 5 (localhost)만 조회. 송출 시작/종료 안 함.",
            wraplength=620,
        ).pack(anchor="w", pady=(6, 12))
        row = ttk.Frame(form)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="OBS 포트").pack(side="left")
        port = tk.StringVar(master=window, value="4455")
        ttk.Entry(row, textvariable=port, width=8).pack(side="left", padx=(8, 18))
        ttk.Label(row, text="OBS 비밀번호").pack(side="left")
        secret = tk.StringVar(master=window)
        ttk.Entry(row, textvariable=secret, show="*", width=24).pack(
            side="left", fill="x", expand=True, padx=(8, 0),
        )
        status = tk.StringVar(master=window, value="실제 연결 전 · 비밀번호는 저장하지 않습니다.")
        self._obs_panel_status = status
        ttk.Label(form, textvariable=status, wraplength=625).pack(anchor="w", pady=(4, 10))

        def connect():
            if self._obs_check_in_progress:
                return
            try:
                actual_port = int(port.get())
                client = OfficialObsWebsocket(secret.get(), port=actual_port)
            except (ValueError, ObsConnectionError) as exc:
                status.set(str(exc))
                return
            self._obs_check_in_progress = True
            connect_btn.configure(state='disabled')
            status.set("실제 OBS 서버 접속 시도 중 · 응답 아직 확인 전")
            self.obs_status.set("실제 OBS 접속 시도 중")
            def job():
                try:
                    current = client.connect()
                    try:
                        inventory = client.read_scene_inventory()
                        sources = ('장면 화면 소스: ' +
                                   (', '.join(inventory.scene_items[:8]) or '없음') +
                                   ' / OBS 입력 소스: ' +
                                   (', '.join(inventory.input_sources[:8]) or '없음'))
                    except ObsConnectionError as exc:
                        # Connectivity can succeed when one read-only inventory
                        # endpoint is unavailable. Keep each result distinct.
                        sources = '소스 목록 별도 조회 실패: ' + str(exc)
                    try:
                        media = client.read_scene_media_path()
                        captures = "실제 OBS 캡처 후보: " + ("; ".join(media.capture_sources[:8]) or "없음")
                        audio_path = "실제 OBS 음량/음소거 조회: " + ("; ".join(media.audio_sources[:8]) or "없음")
                        problems = "상세 미확인: " + ("; ".join(media.problems[:8]) or "없음")
                        sources += "\\n" + captures + "\\n" + audio_path + "\\n" + problems
                    except ObsConnectionError as exc:
                        sources += "\\n실제 OBS 화면/오디오 경로 상세 조회 실패: " + str(exc)
                    self._events.put(("obs_connected", (current, sources)))
                except Exception as exc:
                    self._events.put(("obs_error", str(exc)))
            threading.Thread(target=job, daemon=True).start()
        actions = ttk.Frame(form)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="닫기", command=close_window).pack(side="right")
        connect_btn = ttk.Button(actions, text="실제 OBS 상태 읽기", command=connect)
        connect_btn.pack(side="right", padx=(0, 8))
        self._obs_connect_button = connect_btn

    def _read_confirmed_persona_from_disk(self) -> dict[str, str]:
        """Read the latest *persisted* character, never the unsaved GUI draft.

        Another AISTING window may have confirmed a different character after
        this window opened. Updating only the in-memory persona fields keeps
        its unrelated broadcast editor state intact. A missing/corrupt file
        must NOT silently turn into an apparently confirmed default identity.
        """
        from .offline_settings import active_persona, load_settings, settings_file
        target = settings_file()
        if (target.is_symlink() or target.parent.is_symlink()
                or not target.is_file()):
            raise StageOneUnavailable(
                "확정 저장된 캐릭터 설정 파일이 없습니다. 먼저 '캐릭터 확정·저장'을 사용하세요."
            )
        try:
            first_stat = target.stat(follow_symlinks=False)
            if first_stat.st_size > 1_000_000:
                raise StageOneUnavailable('저장된 캐릭터 설정 파일이 너무 큽니다.')
            first_bytes = target.read_bytes()
            saved = load_settings(target)  # Real legacy migrations and validation.
            fields = active_persona(saved)
            last_stat = target.stat(follow_symlinks=False)
            if (target.is_symlink()
                    or (first_stat.st_dev, first_stat.st_ino, first_stat.st_size,
                        first_stat.st_mtime_ns) !=
                       (last_stat.st_dev, last_stat.st_ino, last_stat.st_size,
                        last_stat.st_mtime_ns)
                    or target.read_bytes() != first_bytes):
                raise StageOneUnavailable(
                    '캐릭터 설정을 읽는 동안 파일이 변경되었습니다. 다시 확인해 주세요.'
                )
        except (OSError, ValueError, UnicodeError) as exc:
            raise StageOneUnavailable('확정 캐릭터 설정 파일을 읽거나 검증할 수 없습니다.') from exc
        self.app.settings['persona_mode'] = saved['persona_mode']
        self.app.settings['persona'] = saved['persona'].copy()
        return fields

    def _refresh_persona(self) -> None:
        try:
            fields = self._read_confirmed_persona_from_disk()
        except StageOneUnavailable as exc:
            self.saved_persona.set('확정 캐릭터 복원 불가 · ' + str(exc))
            self.persona_sync_status.set('캐릭터 미확정/복원 실패 · 공식 설정을 변경하지 않습니다.')
            return
        self.saved_persona.set(
            fields["name"] + "  |  말투: " + fields["style"] +
            "  |  성격: " + fields["character"]
        )
        self.persona_sync_status.set('실제 저장 파일에서 캐릭터 복원 · 공식 설정 반영 여부 미확인')

    def _inspect_persona_alignment(self) -> None:
        """Only compare the latest disk-confirmed identity; no writes."""
        try:
            saved = self._read_confirmed_persona_from_disk()
            aligned = inspect_saved_persona_alignment(self.project_dir.get(), saved)
        except (StageOneUnavailable, ValueError, OSError) as exc:
            self.persona_sync_status.set("공식 캐릭터 설정 비교 실패: " + str(exc))
            return
        if aligned:
            self.persona_sync_status.set(
                "확정 캐릭터와 공식 conf.yaml의 이름·페르소나 문구 일치 · "
                "실행 중 AI 반영·응답은 별도 실기기 확인 필요"
            )
        else:
            self.persona_sync_status.set(
                "확정 캐릭터와 공식 conf.yaml의 이름·페르소나 문구 불일치 · "
                "자동 변경하지 않았습니다. 명시적 승인 후 적용할 수 있습니다."
            )

    def _browse(self) -> None:
        selected = filedialog.askdirectory(
            parent=self.parent, title="이미 준비된 Open-LLM-VTuber 공식 폴더 선택"
        )
        if selected:
            self.project_dir.set(selected)

    def _start(self) -> None:
        if self._child is not None and self._child.poll() is None:
            self.state.set("공식 서버 프로세스 실행 중 · 실제 AI/Live2D 동작은 별도 확인 필요")
            return
        try:
            prepare_official_launch(self.project_dir.get())
        except StageOneUnavailable as exc:
            self.state.set("실행 차단: " + str(exc))
            return
        if not messagebox.askyesno(
            "공식 프로그램 실행 시 외부 영향 승인",
            "공식 Open-LLM-VTuber 원본 실행 코드는 설정 동기화·캐시 및 "
            "선택 모델의 자동 다운로드/네트워크 연결을 수행할 수 있습니다. "
            "무료·로컬 모델 및 기존 설정을 직접 확인했고, 이번 실행의 "
            "이런 동작을 승인합니까? 유료 서비스 이용이나 방송 송출 승인이 아닙니다. "
            "동의하지 않으면 서버를 실행하지 않습니다.",
            parent=self.parent,
        ):
            self.state.set("운영자 승인 없음 · 공식 서버 실행하지 않음")
            return
        try:
            self._child = launch_official_server(
                self.project_dir.get(), operator_authorized_side_effects=True
            )
        except StageOneUnavailable as exc:
            self.state.set("실행 실패: " + str(exc))
            return
        self.state.set("공식 서버 시작 요청됨 · 실제 동작 확인 전")
        self.parent.after(2000, self._observe_started_server)

    def _observe_started_server(self) -> None:
        if self._closed or self._child is None:
            return
        code = self._child.poll()
        if code is None:
            self.state.set("공식 서버 프로세스 실행 중 · 모델/Live2D/TTS 실제 작동 미검증")
            # A server may crash after initial launch. Keep observing ONLY
            # the process launched by this AISTING instance.
            self.parent.after(2000, self._observe_started_server)
        else:
            self.state.set(
                "공식 서버 실행 실패/종료 · 종료 코드 " + str(code) +
                " · 원인 로그: " + str(getattr(self._child, "_aisting_log_path", "없음"))
            )

    def _stop_own_server(self) -> None:
        """Only a separately confirmed shutdown of a child we launched."""
        child = self._child
        if child is None or child.poll() is not None:
            self.state.set('이 AISTING 창이 실행한 공식 서버가 현재 없습니다.')
            return
        if not messagebox.askyesno(
            '공식 프로그램 종료 확인',
            '이 AISTING 창에서 실행한 Open-LLM-VTuber 서버만 종료할까요? '
            'OBS 방송 종료나 다른 프로세스 종료는 수행하지 않습니다.',
            parent=self.parent,
        ):
            return
        try:
            child.terminate()
        except OSError as exc:
            self.state.set('이 앱이 실행한 서버 종료 실패: ' + str(exc))
            return
        self.state.set('이 앱이 실행한 공식 서버 종료 요청됨 · 실제 종료 확인 중')

    def _check(self) -> None:
        self.state.set("127.0.0.1 공식 서버 포트 확인 중 · 동작 성공 판정 아님")
        threading.Thread(
            target=self._probe_worker, args=('check',), daemon=True,
        ).start()

    def _open(self) -> None:
        """Use the real upstream renderer in a native Windows window after approval."""
        try:
            from .original_plan_frontend import inspect_installed_official_frontend
            inspect_installed_official_frontend(self.project_dir.get())
        except (OSError, RuntimeError, ValueError) as exc:
            self.state.set('공식 Live2D 파일 사전검사 실패: ' + str(exc))
            return
        if not messagebox.askyesno(
            '실제 공식 Live2D 화면 열기 승인',
            '설치된 Open-LLM-VTuber의 기존 WebGL/Live2D 화면을 AISTING Windows 네이티브 창에서 엽니다. '
            '공식 창 안의 AI 텍스트 입력과 Live2D·음성은 공식 프런트엔드의 같은 WebSocket 세션을 사용합니다. '
            '기존 AISTING의 별도 텍스트 AI 대화창과는 서로 동기화되지 않습니다. '
            '공식 프런트엔드는 공식 설정에 따라 '
            '대화 기록 저장, 외부 API 연결, 리소스 다운로드, TTS 음성 재생을 할 수 있습니다. '
            'AISTING의 텍스트 대화 창과 이 화면은 자동으로 동기화되지 않습니다. '
            '사용 전 공식 설정을 확인했으며 이번 로컬 서버 접속과 Windows 창 실행을 승인합니까?',
            parent=self.parent,
        ):
            self.state.set('사용자 승인 취소 · 프런트엔드 접속/실행하지 않음')
            return
        self.state.set('설치된 공식 프런트엔드 및 로컬 HTML 응답 확인 중')
        project = self.project_dir.get()
        def job():
            from .original_plan_frontend import probe_official_frontend
            try:
                result = probe_official_frontend(project, operator_approved=True)
            except (OSError, RuntimeError, ValueError, PermissionError) as exc:
                self._events.put(('official_frontend', ('error', str(exc))))
            else:
                self._events.put(('official_frontend', ('ready', result)))
        threading.Thread(target=job, name='aisting-official-live2d-preflight', daemon=True).start()

    def _probe_worker(self, action: str) -> None:
        try:
            status_code = official_frontend_http_status()
        except StageOneUnavailable as exc:
            self._events.put((action, ('error', str(exc))))
        else:
            self._events.put((action, ('http', status_code)))

    def _apply_official_identity(self) -> None:
        try:
            project = check_official_project(self.project_dir.get())
            identity = self._read_confirmed_persona_from_disk()
        except (StageOneUnavailable, ValueError, OSError) as exc:
            self.state.set("캐릭터 적용 실패: " + str(exc))
            return
        if not messagebox.askyesno(
            "공식 방송인 캐릭터 적용",
            "이미 저장한 캐릭터 이름·성격·말투만 공식 프로젝트 conf.yaml에 "
            "적용합니다. 변경 전 백업을 생성합니다. 계속할까요?",
            parent=self.parent,
        ):
            return
        try:
            # A second window could confirm a new character while the
            # approval dialog is open. Never apply an identity the operator
            # did not just approve; ask them to review and retry instead.
            latest = self._read_confirmed_persona_from_disk()
            if latest != identity:
                raise StageOneUnavailable(
                    '승인 창이 열린 동안 확정 캐릭터가 변경되었습니다. 다시 확인해 주세요.'
                )
            config, backup = save_official_persona(project, identity)
        except (StageOneUnavailable, ValueError, OSError) as exc:
            self.state.set("실제 공식 캐릭터 설정 실패: " + str(exc))
            return
        self.persona_sync_status.set("공식 캐릭터 설정 변경됨 · 읽기 전용 비교로 재확인 필요")
        self.state.set(
            "공식 캐릭터 설정 적용: " + str(config) +
            (" · 백업: " + str(backup) if backup else " · 기존 설정 동일") +
            " · 실제 AI 대화는 별도 확인 필요"
        )

    def _consume_events(self) -> None:
        if self._closed:
            return
        try:
            while True:
                kind, connected = self._events.get_nowait()
                if kind == 'gpt_synth_result':
                    window, note, button, busy, message = connected
                    busy["running"] = False
                    try:
                        if window.winfo_exists():
                            button.configure(state="normal")
                            note.set(message)
                            self.tts_status.set(message)
                    except tk.TclError:
                        pass
                    continue
                if kind == 'ai_progress':
                    generation, sent_text, progress_kind, value = connected
                    if generation != self._real_ai_generation or not self._real_ai_busy:
                        continue
                    if (self._real_ai_window is None or not self._real_ai_window.winfo_exists()
                            or self._real_ai_output is None):
                        continue
                    if progress_kind == 'text' and isinstance(value, str):
                        self._real_ai_output.configure(state='normal')
                        if not self._real_ai_stream_started:
                            self._real_ai_output.insert('end', '나: ' + sent_text + '\nAI: ')
                            self._real_ai_stream_started = True
                        self._real_ai_stream_parts.append(value)
                        self._real_ai_output.insert('end', value)
                        self._real_ai_output.see('end')
                        self._real_ai_output.configure(state='disabled')
                    elif progress_kind == 'official_expressions':
                        self._ai_indicator.set('공식 AI 표정 지시 수신: ' + str(value) +
                                               ' · 실제 Live2D 움직임 미확인')
                    elif progress_kind == 'official_lip_sync_samples':
                        self._ai_indicator.set('공식 AI 립싱크 진폭 ' + str(value) +
                                               '개 수신 · 실제 아바타 움직임 미확인')
                    elif progress_kind == 'audio_wav':
                        self._ai_indicator.set('실제 AI 응답 수신 중 · 공식 WAV 데이터 수신 (' +
                                               str(value) + '바이트) · 재생 안 함')
                    continue
                if kind in ('ai_result', 'ai_error'):
                    generation, sent_text, response = connected
                    if generation != self._real_ai_generation:
                        continue  # Closed/reopened chat; do not show old reply.
                    self._real_ai_busy = False
                    if self._real_ai_window is not None and self._real_ai_window.winfo_exists():
                        self._ai_submit_button.configure(state="normal")
                    if kind == 'ai_error':
                        if self._real_ai_output is not None and self._real_ai_window is not None and self._real_ai_window.winfo_exists():
                            self._real_ai_output.configure(state='normal')
                            if self._real_ai_stream_started:
                                self._real_ai_output.insert('end', '\n[응답 도중 오류 · 부분 출력은 완료된 대화가 아닙니다]\n\n')
                            else:
                                self._real_ai_output.insert('end', '나: ' + sent_text + '\n[전송 또는 응답 실패]\n\n')
                            self._real_ai_output.see('end')
                            self._real_ai_output.configure(state='disabled')
                        # The upstream connection is no longer trustworthy after failure.
                        if self._real_ai_session is not None:
                            self._real_ai_session.close()
                        from .original_plan_conversation import OfficialConversationSession
                        self._real_ai_session = OfficialConversationSession()
                        self.real_ai_status.set('실제 AI 대화 실패 · 다음 질문은 새 세션 · ' + str(response))
                        if self._real_ai_window is not None and self._real_ai_window.winfo_exists():
                            self._ai_indicator.set('오류 · 다음 전송 시 새 세션/기억으로 시작')
                    else:
                        audio_note = (
                            '공식 WAV 데이터 수신 ' + str(response.wav_packets) + '개 (' +
                            str(response.wav_audio_bytes) + '바이트)' if response.wav_packets
                            else '실제 WAV 음성 데이터 수신 확인되지 않음'
                        )
                        if response.invalid_audio_packets:
                            audio_note += ' · 유효하지 않은 음성 프레임 ' + str(response.invalid_audio_packets) + '개'
                        avatar_note = (
                            '공식 표정 지시 ' + str(response.live2d_expression_signals) + '개 · ' +
                            '립싱크 진폭 샘플 ' + str(response.lip_sync_volume_samples) + '개' +
                            (' · 신호 형식 오류 ' + str(response.malformed_visual_signals) + '개'
                             if response.malformed_visual_signals else '') +
                            ' · Live2D 동작 별도 미검증'
                        )
                        self.real_ai_status.set('실제 AI 응답 텍스트 수신 · 설정: ' +
                                                response.config_name +
                                                ' · 공식 Live2D 초기화 모델: ' + response.model_name +
                                                ' (' + response.model_url + ')' +
                                                ' · ' + audio_note + ' · ' + avatar_note +
                                                ' · 공식 Live2D 창과 데스크톱 AI 세션 분리 가능' +
                                                ' · 청취/송출 미검증')
                        if self._real_ai_window is not None and self._real_ai_window.winfo_exists():
                            self._ai_indicator.set('같은 서버 세션 ' + str(response.session_number) +
                                                   ' · 대화 ' + str(response.turn_number) + '회 · 소리 재생 안 함')
                            if self._real_ai_output is not None:
                                self._real_ai_output.configure(state='normal')
                                # If the queue already delivered real text chunks,
                                # append only missing trailing text. Never duplicate.
                                # If the callback was ignored, show the full result.
                                streamed = ''.join(self._real_ai_stream_parts)
                                if self._real_ai_stream_started and streamed.strip() == response.text:
                                    # Official final result strips edge whitespace;
                                    # do not duplicate faithfully streamed chunks.
                                    prefix = ''
                                elif self._real_ai_stream_started and response.text.startswith(streamed):
                                    prefix = response.text[len(streamed):]
                                else:
                                    prefix = ('\n[최종 응답] ' if self._real_ai_stream_started else
                                              '나: ' + sent_text + '\nAI: ') + response.text
                                self._real_ai_output.insert(
                                    'end', prefix + '\n[공식 음성 데이터] ' + audio_note +
                                    ' · 실제 소리/립싱크는 미확인\n\n')
                                self._real_ai_output.see('end')
                                self._real_ai_output.configure(state='disabled')
                elif kind in ('ws_init', 'ws_error'):
                    if kind == 'ws_error':
                        self.ws_status.set('실제 WebSocket 초기화 실패: ' + str(connected))
                    else:
                        self.ws_status.set(
                            '실제 WebSocket 초기화 메시지 수신 · 설정: ' + connected.config_name +
                            ' / 모델: ' + connected.model_name +
                            ' / 참조: ' + connected.model_url +
                            ' · 실제 AI 응답·TTS·Live2D 동작은 미검증'
                        )
                elif kind in ('obs_connected', 'obs_error'):
                    self._obs_check_in_progress = False
                    if (self._obs_window is not None and self._obs_window.winfo_exists()
                            and hasattr(self, '_obs_connect_button')):
                        self._obs_connect_button.configure(state='normal')
                    if kind == 'obs_connected':
                        current, source_names = connected
                        result = (
                            'OBS ' + current.version + ' / 장면 ' + current.scene +
                            (' / 실제 송출 중' if current.streaming else ' / 송출 중지') +
                            ' · 음성·채팅 실제 통합 미검증\n' + source_names +
                            '\n소스 목록 존재는 실제 화면·오디오 전달 성공을 의미하지 않습니다.'
                        )
                    else:
                        result = '실제 OBS 연결 실패: ' + str(connected)
                    self.obs_status.set(result)
                    if self._obs_panel_status is not None:
                        self._obs_panel_status.set(result)
                elif kind == 'official_frontend':
                    status, details = connected
                    if status != 'ready':
                        self.state.set('기존 공식 Live2D 화면 확인 실패: ' + str(details))
                    else:
                        from .original_plan_frontend import open_prechecked_frontend
                        try:
                            opened = open_prechecked_frontend(details, operator_approved=True)
                        except (RuntimeError, OSError, ValueError, PermissionError) as exc:
                            self.state.set('공식 Windows Live2D 창 실행 실패: ' + str(exc))
                        else:
                            self.state.set(
                                '기존 공식 Live2D Windows 창 ' + ('열기 요청됨' if opened else '실행 실패') +
                                ' · 별도 AI 대화 세션 · 실제 렌더링/립싱크/음성 미검증'
                            )
                elif kind == 'check':
                    result_type, result_value = connected
                    if result_type != 'http':
                        self.state.set('실제 로컬 서버 연결 실패: ' + str(result_value))
                    elif result_value != 200:
                        self.state.set('실제 공식 화면 HTTP 오류: ' + str(result_value) +
                                       ' · AI/음성/Live2D 미검증')
                    else:
                        self.state.set('로컬 12393 HTTP 200 응답 · '
                                       '실제 AI/음성/Live2D는 미검증')
        except queue.Empty:
            pass
        self._after_id = self.parent.after(180, self._consume_events)

    def close(self) -> None:
        self._closed = True
        if self._real_ai_session is not None:
            self._real_ai_session.close()
            self._real_ai_session = None
        self._real_ai_generation += 1
        if self._after_id is not None:
            try:
                self.parent.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        # A process explicitly launched by the operator is left running; its
        # ownership and shutdown should be a deliberate operator action.
