"""Existing AISTING Windows native entry point (never a web-app launcher)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def _verify_frozen_bundle() -> bool:
    """Read-only, GUI-free smoke check of THIS built Windows EXE.

    It checks bundled program modules and original plan/roadmap, but does not
    launch Tk, create user settings, contact upstream servers, play audio, or
    pretend that actual AI/Live2D/OBS has been validated.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False
    root_arg = getattr(sys, "_MEIPASS", None)
    if not isinstance(root_arg, str) or not root_arg:
        return False
    try:
        root = Path(root_arg)
        required = (
            root / "docs" / "ORIGINAL_PLAN.txt",
            root / "docs" / "ROADMAP_100.md",
            root / "config" / "roadmap.json",
        )
        for path in required:
            if (path.is_symlink() or not path.is_file()
                    or not 0 < path.stat().st_size <= 2_000_000):
                return False
        roadmap = json.loads(required[-1].read_text(encoding="utf-8"))
        steps = roadmap.get("steps")
        if (roadmap.get("total_steps") != 100 or not isinstance(steps, list)
                or len(steps) != 100
                or {step.get("number") for step in steps if isinstance(step, dict)}
                   != set(range(1, 101))):
            return False
        from ai_broadcaster.desktop import main
        from ai_broadcaster.original_plan_frontend import run_native_live2d_window
        from ai_broadcaster.original_plan_obs import OfficialObsWebsocket
        import obsws_python
        import websocket
        import winsound
        if (not callable(main) or not callable(run_native_live2d_window)
                or not callable(OfficialObsWebsocket)
                or not callable(obsws_python.ReqClient)
                or not callable(websocket.create_connection)
                or not callable(winsound.PlaySound)):
            return False
        return importlib.util.find_spec("webview") is not None
    except (OSError, ValueError, ImportError, AttributeError, TypeError):
        return False



def _verify_frozen_gui() -> bool:
    """Run real Tk command callbacks and restart with isolated Windows CI data.

    These are actual widgets from the existing AISTING.exe, not a replica UI.
    All writes stay beneath RUNNER_TEMP; real accounts, audio, OBS, AI and
    streaming are never touched. This does not certify live integration.
    """
    if (sys.platform != "win32" or not getattr(sys, "frozen", False)
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("AISTING_GUI_SELFTEST") != "approved_ci_only"):
        return False
    local = os.environ.get("LOCALAPPDATA")
    runner = os.environ.get("RUNNER_TEMP")
    if not local or not runner:
        return False
    # Never run this state-writing journey against a real Windows profile.
    try:
        local_root = Path(local).resolve()
        runner_root = Path(runner).resolve()
        if not local_root.is_relative_to(runner_root):
            return False
        target = local_root / "AISTING" / "settings.json"
        if target.exists():
            return False
    except (OSError, ValueError):
        return False

    from tkinter import ttk
    from ai_broadcaster.desktop import AistingApp
    from ai_broadcaster.offline_settings import load_settings

    def button(parent, caption):
        found = []
        def search(widget):
            if isinstance(widget, ttk.Button) and widget.cget("text") == caption:
                found.append(widget)
            for child in widget.winfo_children():
                search(child)
        search(parent)
        if len(found) != 1:
            raise AssertionError("Real Tk control missing or ambiguous: " + caption)
        return found[0]

    app = None
    try:
        app = AistingApp()
        app.withdraw()
        app.update_idletasks()
        names = {app._tabs.tab(tab, "text") for tab in app._tabs.tabs()}
        if not (app.title().startswith("AISTING") and
                {"방송인 홈", "내 캐릭터", "방송 설정",
                 "시청자 채팅 연습", "아바타 미리보기"}.issubset(names)):
            return False
        # Verify live chat GUI is actually reachable inside packaged EXE.
        button(app, "실제 채팅·AI").invoke()
        if (app._tabs.tab(app._tabs.select(), "text") != "실제 채팅·AI"
                or not app._real_chat_tab.winfo_exists()):
            return False
        names = []
        def visit(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button):
                    names.append(child.cget("text"))
                visit(child)
        visit(app._real_chat_tab)
        if not {"텍스트 전송", "읽기 전용 연결", "읽기 중지"}.issubset(names):
            return False
        button(app, "내 캐릭터").invoke()
        if app._tabs.tab(app._tabs.select(), "text") != "내 캐릭터":
            return False

        # Use the original character-confirm button, not an internal setter.
        confirmed = {"name": "CI검증캐릭터", "style": "또렷한 한국어",
                     "character": "저장 검증용 성격"}
        app._persona_mode.set("직접 만들기")
        for key, value in confirmed.items():
            entry = app._persona[key]
            entry.delete(0, "end")
            entry.insert(0, value)
        button(app, "캐릭터 확정·저장").invoke()
        if (not target.is_file()
                or load_settings(target)["persona"] != confirmed
                or app.settings["persona_mode"] != "custom"):
            return False

        # Editing an unconfirmed draft must not change the saved identity,
        # even when the operator clicks the OTHER, broadcast-settings button.
        app._persona["name"].delete(0, "end")
        app._persona["name"].insert(0, "미확정초안")
        button(app, "방송 설정").invoke()
        app._platforms["chzzk"].set(True)
        app._content.set("수다")
        button(app, "방송 설정 저장 (캐릭터 제외)").invoke()
        disk = load_settings(target)
        if (disk["persona"] != confirmed
                or disk["persona_mode"] != "custom"
                or disk["platforms"] != ["chzzk"]
                or disk["content"] != "chat"
                or disk["streaming_enabled"] or disk["scheduled_execution"]
                or disk["external_publish_enabled"]):
            return False

        # Start a second actual Windows GUI instance after closing the first.
        app.destroy()
        app = None
        app = AistingApp()
        app.withdraw()
        app.update_idletasks()
        if (app.settings["persona"] != confirmed
                or app.settings["persona_mode"] != "custom"
                or app._persona["name"].get() != confirmed["name"]
                or "CI검증캐릭터" not in app._original_studio.saved_persona.get()):
            return False

        # Open actual existing integration panels without pressing the
        # audio/network/model/OBS/streaming controls or using mock services.
        button(app, "2단계 · 실제 GPT-SoVITS 한국어 음성 연결 설정").invoke()
        def top_levels(root):
            result = []
            def walk(node):
                for child in node.winfo_children():
                    if child.winfo_class() == "Toplevel":
                        result.append(child)
                    walk(child)
            walk(root)
            return result
        voice = [item for item in top_levels(app)
                 if "GPT-SoVITS" in item.title()]
        if len(voice) != 1:
            return False
        button(voice[0], "취소 / 닫기").invoke()
        button(app, "3단계 · 실제 OBS 연결 확인 (송출 안 함)").invoke()
        obs = app._original_studio._obs_window
        if (obs is None or not obs.winfo_exists()
                or "OBS" not in obs.title()):
            return False
        button(obs, "닫기").invoke()
        app.update_idletasks()
        # A Windows GUI integration rehearsal is not live broadcasting.
        return (app._original_studio._obs_window is None
                and load_settings(target)["persona"] == confirmed)
    except Exception:
        return False
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass


def _run(argv: list[str] | None = None) -> int:
    """Dispatch the original Tk window, a native child, or an offline EXE check."""
    args = sys.argv[1:] if argv is None else argv
    if args == ["--aisting-selftest"]:
        return 0 if _verify_frozen_bundle() else 2
    if args == ["--aisting-gui-selftest"]:
        return 0 if _verify_frozen_gui() else 2
    if (len(args) == 5 and args[0] == "--aisting-live2d-viewer"
            and args[2] == "--aisting-ipc"):
        from ai_broadcaster.original_plan_frontend import run_native_live2d_window
        import re
        # Only the same AISTING.exe's Windows named-pipe relay is accepted.
        # This is a child of a one-shot operator-approved official viewer.
        if (sys.platform != 'win32'
                or not re.fullmatch(r'\\\\\.\\pipe\\aisting-live2d-[0-9a-f]{32}',
                                    args[3])
                or not re.fullmatch(r'[0-9a-f]{64}', args[4])):
            return 2
        try:
            run_native_live2d_window(
                args[1], operator_approved=True,
                ipc_address=args[3], ipc_auth=args[4],
            )
        except (OSError, RuntimeError, ValueError, ImportError) as exc:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            try:
                messagebox.showerror("AISTING Live2D 시작 실패", str(exc), parent=root)
            finally:
                root.destroy()
            return 2
        return 0
    if len(args) == 2 and args[0] == "--aisting-live2d-viewer":
        # An explicit user-approved AISTING UI action spawns this same EXE.
        from ai_broadcaster.original_plan_frontend import run_native_live2d_window
        try:
            run_native_live2d_window(args[1], operator_approved=True)
        except (OSError, RuntimeError, ValueError, ImportError) as exc:
            # A --windowed executable has no console to display this failure.
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            try:
                messagebox.showerror("AISTING Live2D 시작 실패", str(exc), parent=root)
            finally:
                root.destroy()
            return 2
        return 0
    if "--aisting-live2d-viewer" in args or any(
        arg.startswith("--aisting-") for arg in args
    ):
        return 2  # Never launch the wrong GUI on invalid internal arguments.
    from ai_broadcaster.desktop import main
    main()
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())
