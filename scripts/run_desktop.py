"""Windows native GUI entry point. No browser/server."""
import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop import main

if __name__ == "__main__":
    if sys.argv[1:] == ["--aisting-live2d-viewer"]:
        # The same Windows EXE hosts official Live2D in its own WebView2 window.
        # The original Tk application remains the default launch path.
        from ai_broadcaster.original_plan_frontend import run_native_live2d_window
        run_native_live2d_window(operator_approved=True)
    else:
        main()
