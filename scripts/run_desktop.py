"""Windows native GUI entry point. No browser/server."""
import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop import main

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--aisting-live2d-viewer":
        # Child of the same AISTING.exe. Verify the explicitly selected
        # installed official project again before creating the native window.
        from ai_broadcaster.original_plan_frontend import run_native_live2d_window
        try:
            run_native_live2d_window(sys.argv[2], operator_approved=True)
        except (OSError, RuntimeError, ValueError, ImportError) as exc:
            # --windowed EXE has no terminal: show actual startup failure,
            # not a silently blank WebView or false success in the operator UI.
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            try:
                messagebox.showerror("AISTING Live2D 시작 실패", str(exc), parent=root)
            finally:
                root.destroy()
            raise SystemExit(2)
    elif "--aisting-live2d-viewer" in sys.argv[1:]:
        raise SystemExit(2)  # Missing/extra project argument: never guess.
    else:
        main()
