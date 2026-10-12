"""프로젝트 루트에서 실행하는 진입점."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from ai_broadcaster.__main__ import main
if __name__ == "__main__":
    raise SystemExit(main())
