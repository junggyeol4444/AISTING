"""수동 실행 전용: 동봉된 자료와 임시 샘플만 오프라인 검사 (20단계)."""
from __future__ import annotations

import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_broadcaster.execution_selfcheck import run_execution_selfcheck


def main() -> int:
    report = run_execution_selfcheck()
    print(report.describe())
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
