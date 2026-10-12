"""Windows용 AISTING.exe 진입점. 브라우저를 사용하지 않음."""
import sys
from pathlib import Path
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop import main

if __name__ == "__main__":
    main()
