"""기존 OBS 게임 화면 인식에 연결되는 Windows 로컬 자율 게임 조작.

운영자가 현재 PC의 특정 게임 창 제목·목표·최대 행동 수를 지정하고
실제 키/마우스 조작을 별도 승인했을 때만 실행한다. 기존 로컬
시각 모델과 기존 Ollama 모델을 그대로 사용한다. 매 행동 전 실제
OBS 화면을 다시 보고 한 행동만 계획한다. 화면 분석 실패/모델의
비정형 출력/게임 창 포커스 상실/운영자 중지 시 즉시 중단한다.

사용자가 직접 허용하지 않은 OBS 송출/채팅/계정/공지 조작,
임의 외부 API/명령어 실행, Windows 시스템 단축키 입력은 없다.
"""
from __future__ import annotations

import ctypes
import json
import os
import threading
import time
from ctypes import wintypes
from dataclasses import asdict, dataclass
from typing import Callable
from uuid import uuid4

from .approved_local_game_vision import observe_game_scene_with_local_vision
from .approved_game_goal_journal import ApprovedGameGoalJournal
from .game_goal_evidence import assess_game_goal_from_two_observations
from .local_llm import LocalModelConfig, LocalOllamaReplyGenerator
from .offline_settings import active_persona, load_settings as load_gui_settings
from .operator_settings import load_settings as load_operator_settings
from .session import ChatMessage

_ALLOWED_KEYS = {
    "w": 0x57, "a": 0x41, "s": 0x53, "d": 0x44,
    "e": 0x45, "q": 0x51, "r": 0x52, "f": 0x46,
    "space": 0x20, "enter": 0x0D, "escape": 0x1B,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
}
_KEYUP = 0x0002
_MOUSE_LEFT_DOWN = 0x0002
_MOUSE_LEFT_UP = 0x0004
_INPUT_MOUSE = 0
_INPUT_KEYBOARD = 1


class _Point(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG), ("top", wintypes.LONG),
        ("right", wintypes.LONG), ("bottom", wintypes.LONG),
    ]


class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG), ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t),
    ]


class _KeyboardInput(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _InputUnion(ctypes.Union):
    _fields_ = [
        ("mi", _MouseInput), ("ki", _KeyboardInput),
        ("hi", _HardwareInput),
    ]


class _Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _InputUnion)]


@dataclass(frozen=True)
class GameAction:
    action: str
    key: str = ""
    duration_ms: int = 0
    x: float = 0.0
    y: float = 0.0


@dataclass(frozen=True)
class GameStep:
    number: int
    observation: str
    action: GameAction
    result: str


def parse_game_action(reply: str) -> GameAction:
    """자연어 지시를 실행하지 않고 엄격한 한 개 JSON 행동만 허용."""
    if type(reply) is not str or not 2 <= len(reply) <= 500:
        raise ValueError("게임 행동 JSON 길이가 올바르지 않습니다.")
    data = json.loads(reply)
    if type(data) is not dict:
        raise ValueError("게임 행동은 JSON 객체 한 개여야 합니다.")
    kind = data.get("action")
    if kind == "key":
        if set(data) != {"action", "key", "duration_ms"}:
            raise ValueError("게임 키 입력 JSON 필드가 다릅니다.")
        key = data["key"]
        ms = data["duration_ms"]
        if key not in _ALLOWED_KEYS or type(ms) is not int or not 50 <= ms <= 500:
            raise ValueError("허용된 게임 키 또는 50~500ms 범위가 아닙니다.")
        return GameAction(kind, key=key, duration_ms=ms)
    if kind == "click":
        if set(data) != {"action", "x", "y"}:
            raise ValueError("게임 클릭 JSON 필드가 다릅니다.")
        x, y = data["x"], data["y"]
        if (type(x) not in (int, float) or type(y) not in (int, float)
                or not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0):
            raise ValueError("클릭은 게임 창 내부 0~1 상대좌표만 허용됩니다.")
        return GameAction(kind, x=float(x), y=float(y))
    if kind in ("wait", "stop") and set(data) == {"action"}:
        return GameAction(kind)
    raise ValueError("게임 조작 JSON에 지원하지 않는 행동이 있습니다.")


class WindowsApprovedGameWindow:
    """지정된 단일 게임 창 HWND·PID가 유지될 때만 Win32 입력 전달."""

    def __init__(self, exact_title: str, *, operator_approved: bool) -> None:
        if operator_approved is not True:
            raise PermissionError("실제 Windows 게임 키·마우스 조작 승인이 필요합니다.")
        if os.name != "nt":
            raise OSError("실제 게임 조작은 Windows 10/11에서만 실행합니다.")
        if (type(exact_title) is not str or not 1 <= len(exact_title.strip()) <= 200
                or any(ord(c) < 32 for c in exact_title)):
            raise ValueError("정확한 게임 창 제목을 입력하세요.")
        self._api = ctypes.windll.user32
        self._api.FindWindowW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR)
        self._api.FindWindowW.restype = wintypes.HWND
        self._api.GetWindowThreadProcessId.argtypes = (
            wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
        self._api.GetWindowThreadProcessId.restype = wintypes.DWORD
        self._api.GetForegroundWindow.restype = wintypes.HWND
        self._api.SetForegroundWindow.argtypes = (wintypes.HWND,)
        self._api.SetForegroundWindow.restype = wintypes.BOOL
        self._api.IsWindow.argtypes = (wintypes.HWND,)
        self._api.IsWindow.restype = wintypes.BOOL
        self._api.IsWindowVisible.argtypes = (wintypes.HWND,)
        self._api.IsWindowVisible.restype = wintypes.BOOL
        self._api.IsIconic.argtypes = (wintypes.HWND,)
        self._api.IsIconic.restype = wintypes.BOOL
        self._api.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(_Rect))
        self._api.GetClientRect.restype = wintypes.BOOL
        self._api.ClientToScreen.argtypes = (wintypes.HWND, ctypes.POINTER(_Point))
        self._api.ClientToScreen.restype = wintypes.BOOL
        self._api.SendInput.argtypes = (
            wintypes.UINT, ctypes.POINTER(_Input), ctypes.c_int)
        self._api.SendInput.restype = wintypes.UINT
        self._api.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
        self._api.SetCursorPos.restype = wintypes.BOOL
        self._title = exact_title.strip()
        self._hwnd = self._api.FindWindowW(None, self._title)
        self._pid = wintypes.DWORD()
        if (not self._hwnd or not self._api.IsWindowVisible(self._hwnd)
                or self._api.IsIconic(self._hwnd)):
            raise RuntimeError("지정된 게임 창을 찾을 수 없거나 최소화되어 있습니다.")
        if not self._api.GetWindowThreadProcessId(
                self._hwnd, ctypes.byref(self._pid)):
            raise RuntimeError("게임 창의 프로세스를 확인할 수 없습니다.")
        if self._pid.value in (0, os.getpid()):
            raise PermissionError("프로그램 자체 창이나 시스템 창을 조작하지 않습니다.")
        self._api.SetForegroundWindow(self._hwnd)
        if self._api.GetForegroundWindow() != self._hwnd:
            raise RuntimeError("Windows가 게임 창 활성화를 허용하지 않았습니다.")

    def _ensure_focus(self) -> None:
        if (not self._api.IsWindow(self._hwnd)
                or not self._api.IsWindowVisible(self._hwnd)
                or self._api.IsIconic(self._hwnd)
                or self._api.GetForegroundWindow() != self._hwnd):
            raise RuntimeError("게임 창 포커스가 바뀌어 조작을 중단합니다.")
        current = wintypes.DWORD()
        self._api.GetWindowThreadProcessId(self._hwnd, ctypes.byref(current))
        if current.value != self._pid.value:
            raise RuntimeError("게임 창 소유 프로세스가 바뀌었습니다.")

    def _send(self, item: _Input) -> None:
        self._ensure_focus()
        if self._api.SendInput(1, ctypes.byref(item), ctypes.sizeof(_Input)) != 1:
            raise RuntimeError("Windows 게임 입력 전달에 실패했습니다.")

    def execute(self, action: GameAction, stop: threading.Event) -> str:
        if stop.is_set():
            return "운영자 중지"
        self._ensure_focus()
        if action.action == "stop":
            stop.set()
            return "AI 목표 종료 요청 · 결과는 미확인"
        if action.action == "wait":
            stop.wait(0.25)
            return "다음 실제 OBS 화면 관찰 대기"
        if action.action == "key":
            key = _ALLOWED_KEYS[action.key]
            down = _Input(type=_INPUT_KEYBOARD)
            down.union.ki = _KeyboardInput(wVk=key)
            up = _Input(type=_INPUT_KEYBOARD)
            up.union.ki = _KeyboardInput(wVk=key, dwFlags=_KEYUP)
            self._send(down)
            try:
                stop.wait(action.duration_ms / 1000.0)
            finally:
                # 사용자 중지·포커스 이탈 시에도 눌린 키 해제 시도.
                if self._api.SendInput(
                        1, ctypes.byref(up), ctypes.sizeof(_Input)) != 1:
                    raise RuntimeError("게임 키 해제 실패 · 직접 확인 필요")
            return f"게임 키 {action.key} {action.duration_ms}ms 전달 요청"
        if action.action == "click":
            bounds = _Rect()
            if not self._api.GetClientRect(self._hwnd, ctypes.byref(bounds)):
                raise RuntimeError("게임 창 내부 크기를 확인하지 못했습니다.")
            width = bounds.right - bounds.left
            height = bounds.bottom - bounds.top
            if width < 10 or height < 10:
                raise RuntimeError("게임 창의 조작 가능 화면이 너무 작습니다.")
            point = _Point(
                min(width - 1, max(0, int(action.x * width))),
                min(height - 1, max(0, int(action.y * height))))
            if not self._api.ClientToScreen(self._hwnd, ctypes.byref(point)):
                raise RuntimeError("게임 창의 실제 화면 좌표를 확인하지 못했습니다.")
            self._ensure_focus()
            if not self._api.SetCursorPos(point.x, point.y):
                raise RuntimeError("게임 내부 마우스 이동 실패")
            down = _Input(type=_INPUT_MOUSE)
            down.union.mi = _MouseInput(dwFlags=_MOUSE_LEFT_DOWN)
            up = _Input(type=_INPUT_MOUSE)
            up.union.mi = _MouseInput(dwFlags=_MOUSE_LEFT_UP)
            self._send(down)
            try:
                stop.wait(0.06)
            finally:
                if self._api.SendInput(
                        1, ctypes.byref(up), ctypes.sizeof(_Input)) != 1:
                    raise RuntimeError("게임 마우스 버튼 해제 실패 · 직접 확인 필요")
            return "지정한 게임 창 내부 클릭 전달 요청"
        raise ValueError("허용되지 않은 게임 조작")


class ApprovedLocalGameAutoplay:
    """운영자가 지정한 목표에 대해 화면→판단→한 행동을 제한 횟수 반복."""

    def __init__(
        self, *, obs_password: str, obs_port: int, model_name: str,
        game_window_title: str, goal: str, max_steps: int,
        operator_approved: bool = False,
        on_event: Callable[[str, object], None] | None = None,
        resume_run_id: str | None = None,
    ) -> None:
        if operator_approved is not True:
            raise PermissionError("게임 자동 조작 별도 승인이 필요합니다.")
        if (type(goal) is not str or not 1 <= len(goal.strip()) <= 300
                or any(ord(c) < 32 or ord(c) == 127 for c in goal)):
            raise ValueError("운영자 게임 목표는 1~300자여야 합니다.")
        if type(max_steps) is not int or not 1 <= max_steps <= 100:
            raise ValueError("한 번에 게임 행동 1~100회만 승인할 수 있습니다.")
        if on_event is not None and not callable(on_event):
            raise ValueError("게임 진행 결과 전달 함수가 올바르지 않습니다.")
        self._obs_password = obs_password
        self._obs_port = obs_port
        self._model = model_name
        self._title = game_window_title
        self._goal = goal.strip()
        self._max_steps = max_steps
        self._events = on_event
        self._resume_run_id = resume_run_id
        self._stop = threading.Event()

    def request_stop(self) -> None:
        self._stop.set()

    def _notify(self, kind: str, payload: object) -> None:
        if self._events is not None:
            self._events(kind, payload)

    def run(self) -> int:
        """기존 승인된 게임을 진행하고 새 목표 장부에 각 입력을 사전 기록."""
        if self._stop.is_set():
            return 0
        window = WindowsApprovedGameWindow(
            self._title, operator_approved=True)
        settings = load_operator_settings()
        persona = active_persona(load_gui_settings())
        settings["persona"]["name"] = persona["name"]
        settings["persona"]["traits"] = persona["character"]
        settings["persona"]["speech_style"] = persona["style"]
        generator = LocalOllamaReplyGenerator(
            LocalModelConfig(model=self._model), settings, memory=None)
        generator.system = (
            f"당신은 한국어 방송인 '{persona['name']}'의 게임 조작 담당입니다. "
            f"캐릭터 말투: {persona['style']}. "
            "실제 관찰 설명과 운영자 목표만 보고 다음 한 행동을 정하세요. "
            "게임 이름·조작법이 불확실하면 wait 또는 stop을 선택하세요. "
            "다음 중 JSON 객체 딱 하나만 출력: "
            '{"action":"key","key":"w","duration_ms":100}, '
            '{"action":"click","x":0.5,"y":0.5}, '
            '{"action":"wait"}, {"action":"stop"}. '
            "키 허용: w,a,s,d,e,q,r,f,space,enter,escape,up,down,left,right. "
            "키 누르는 시간 50~500ms. 절대 설명/마크다운/명령어를 덧붙이지 마세요."
        )
        journal = ApprovedGameGoalJournal()
        run = journal.begin(
            game_title=self._title, goal=self._goal, model=self._model,
            max_steps=self._max_steps, parent_run_id=self._resume_run_id,
            operator_approved=True)
        self._notify("기록시작", run)
        completed = 0
        reason = "횟수종료"
        previous_observation = None
        last_observation = None
        # 이전 실행의 기록은 새 승인에서 문맥으로만 읽는다.
        # 과거의 입력시도 기록은 실행 성공 여부가 불명확하므로 재생 금지.
        prior = (
            journal.history(self._resume_run_id, limit=10)
            if self._resume_run_id else ())
        prior_context = "\\n".join(
            f"{e.step_no}회 {e.phase}: {e.detail[:120]}"
            for e in prior)[:900]
        try:
            for index in range(1, self._max_steps + 1):
                if self._stop.is_set():
                    reason = "운영자중지"
                    break
                window._ensure_focus()
                observed = observe_game_scene_with_local_vision(
                    self._obs_password, self._obs_port, self._model,
                    operator_approved=True,
                    question="실제 게임 장면의 현재 상태와 목표 달성 여부를 보이는 사실만 한국어로 설명해.",
                )
                if self._stop.is_set():
                    reason = "운영자중지"
                    break
                if last_observation is not None:
                    journal.record(
                        run.run_id, index - 1, "후속관찰",
                        observed.description[:1200])
                previous_observation = last_observation
                last_observation = observed.description
                journal.record(
                    run.run_id, index, "관찰",
                    observed.description[:1200])
                history = journal.history(run.run_id, limit=8)
                context = "\\n".join(
                    f"{e.step_no}회 {e.phase}: {e.detail[:130]}"
                    for e in history)[:950]
                prompt = (
                    f"운영자 지정 목표: {self._goal}\\n"
                    f"현재 OBS 장면: {observed.scene}\\n"
                    f"현재 관찰: {observed.description[:2500]}\\n"
                    f"같은 승인 게임의 직전 행동/관찰 기록: {context}\\n"
                    f"이전 승인 회차의 기록(재실행 금지): {prior_context}\\n"
                    "현재 실제 화면과 기록을 보고 다음 한 번의 게임 행동 JSON만 출력하세요. "
                    "목표 달성이 실제 확인되지 않으면 성공이라고 단정하지 마세요."
                )
                answer = generator.generate(ChatMessage(
                    str(uuid4()), "실제 게임 화면", prompt))
                action = parse_game_action(answer)
                if self._stop.is_set():
                    reason = "운영자중지"
                    break
                serialized = json.dumps(
                    asdict(action), ensure_ascii=False, separators=(",", ":"))
                journal.record(run.run_id, index, "행동계획", serialized)
                # 실제 SendInput 이전에 입력 가능성을 영구 기록한다.
                # 강제 종료 뒤 이 행동을 다시 보내지 않는다.
                journal.record(run.run_id, index, "입력시도", serialized)
                result = window.execute(action, self._stop)
                journal.record(run.run_id, index, "입력반환", result)
                completed += 1
                self._notify("행동", GameStep(
                    index, observed.description[:800], action, result))
                if action.action == "stop":
                    reason = "AI종료"
                    break
                if self._stop.is_set():
                    reason = "운영자중지"
                    break

            # 마지막 입력도 후속 화면을 읽어 결과 근거를 남긴다.
            # AI stop은 입력이 아닌 종료 요청이므로 현재 프레임이 마지막 근거.
            if completed and not self._stop.is_set():
                window._ensure_focus()
                after = observe_game_scene_with_local_vision(
                    self._obs_password, self._obs_port, self._model,
                    operator_approved=True,
                    question="마지막 게임 행동 이후 화면에 실제로 표시된 결과만 한국어로 설명해.")
                journal.record(
                    run.run_id, completed, "후속관찰",
                    after.description[:1200])
                if last_observation is not None:
                    try:
                        evidence = assess_game_goal_from_two_observations(
                            goal=self._goal, before=last_observation,
                            after=after.description, model=self._model)
                        journal.record(
                            run.run_id, completed, "목표판정",
                            json.dumps(asdict(evidence), ensure_ascii=False)[:2000])
                        self._notify("목표판정", evidence)
                        if evidence.status == "달성후보":
                            reason = "목표후보"
                    except (ValueError, RuntimeError, OSError) as exc:
                        journal.record(
                            run.run_id, completed, "목표판정",
                            "불확실 · 로컬 목표 판정 불가 (" +
                            type(exc).__name__ + ")")
                        self._notify("목표판정불가", type(exc).__name__)
            elif completed and reason == "AI종료" and previous_observation:
                # AI의 'stop'은 목표 달성 증명이 아니다. 이전과 현재의
                # 두 실제 화면 관찰로만 보수적인 후보 판정을 요청한다.
                try:
                    evidence = assess_game_goal_from_two_observations(
                        goal=self._goal, before=previous_observation,
                        after=last_observation, model=self._model)
                    journal.record(
                        run.run_id, completed, "목표판정",
                        json.dumps(asdict(evidence), ensure_ascii=False)[:2000])
                    self._notify("목표판정", evidence)
                    if evidence.status == "달성후보":
                        reason = "목표후보"
                except (ValueError, RuntimeError, OSError) as exc:
                    journal.record(
                        run.run_id, completed, "목표판정",
                        "불확실 · 로컬 목표 판정 불가 (" +
                        type(exc).__name__ + ")")
                    self._notify("목표판정불가", type(exc).__name__)
            if self._stop.is_set() and reason != "AI종료":
                reason = "운영자중지"
            journal.finish(run.run_id, reason)
            self._notify("종료", completed)
            self._notify("기록종료", (run.run_id, reason))
            return completed
        except Exception:
            # 실제 게임 조작 도중 중단/실패해도 과거 입력시도는 보존.
            # 재시작 후에는 사용자에게 새 승인 없이 입력 재생하지 않음.
            try:
                journal.finish(run.run_id, "실행실패")
            except Exception:
                pass
            raise
