"""Standalone real-AI stage launch. Does not import the legacy 100-page UI."""
import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_broadcaster.stage1_live import main

if __name__ == "__main__":
    main()
