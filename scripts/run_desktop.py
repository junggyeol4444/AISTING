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
        if (not callable(main) or not callable(run_native_live2d_window)
                or not callable(OfficialObsWebsocket)
                or not callable(obsws_python.ReqClient)):
            return False
        return importlib.util.find_spec("webview") is not None
    except (OSError, ValueError, ImportError, AttributeError, TypeError):
        return False



def _verify_frozen_gui() -> bool:
    """Actually construct the ORIGINAL Tkinter Windows UI in disposable CI.

    This runs only in a Windows GitHub Actions runner, with an isolated
    LOCALAPPDATA supplied by the build step. It does not enter mainloop,
    connect to AI/OBS, play audio, or operate on the user's PC.
    """
    if (sys.platform != "win32" or not getattr(sys, "frozen", False)
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("AISTING_GUI_SELFTEST") != "approved_ci_only"):
        return False
    app = None
    try:
        from ai_broadcaster.desktop import AistingApp
        app = AistingApp()
        app.withdraw()
        app.update_idletasks()
        names = {app._tabs.tab(t, "text") for t in app._tabs.tabs()}
        return (app.title().startswith("AISTING")
                and {"방송인 홈", "내 캐릭터", "방송 설정",
                     "시청자 채팅 연습", "아바타 미리보기"}.issubset(names))
    except Exception:
        # No false positives from a window that failed to construct.
        return False
    finally:
        if app is not None:
            try:
                # No broadcaster shutdown actions or TTS stop call; the test
                # never started playback. Tk cancels callbacks on destroy.
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
