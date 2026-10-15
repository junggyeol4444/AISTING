"""외부 의존성 없는 간단 실행기."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))
from ai_broadcaster.__main__ import main
if __name__ == '__main__':
    raise SystemExit(main())
