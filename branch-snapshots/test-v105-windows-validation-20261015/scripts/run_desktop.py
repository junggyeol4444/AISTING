"""Windows native GUI entry point. No browser/server."""
import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop import main

def _verify_bundled_resources() -> int:
    """Safe, explicit offline check of the six files packaged with the EXE."""
    from ai_broadcaster.development_review import bundled_project_root
    from ai_broadcaster.offline_final_acceptance import ALLOWED_FILES, inspect_bundled_project

    reviewed, approval_pending = inspect_bundled_project(bundled_project_root())
    return 0 if (
        approval_pending
        and len(reviewed) == len(ALLOWED_FILES)
        and all(item.digest and item.status.startswith("보관 파일 존재") for item in reviewed)
    ) else 2


if __name__ == "__main__":
    if sys.argv[1:] == ["--verify-bundled-resources"]:
        raise SystemExit(_verify_bundled_resources())
    main()
