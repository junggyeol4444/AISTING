"""Original plan section 7-2, stage 1.

Run the ACTUAL Open-LLM-VTuber project that the operator has already installed.
This is NOT a substitute core or a mock. It does not download dependencies,
install models, access streaming accounts, or start OBS. It invokes precisely
the upstream quick-start command: 'uv run run_server.py'.

Upstream: https://github.com/Open-LLM-VTuber/Open-LLM-VTuber
Guide: https://docs.llmvtuber.com/en/docs/quick-start/
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

UPSTREAM_COMMAND = ("uv", "run", "run_server.py")
UPSTREAM_UI = "http://localhost:12393"


def start_existing_open_llm_vtuber(project_dir: Path) -> int:
    """Run an explicitly selected, existing upstream folder in the foreground.

    Never fabricate a successful result from process start. Success of this
    function alone does NOT verify live AI voice, Live2D or model loading.
    """
    root = Path(project_dir).expanduser().resolve(strict=True)
    if not root.is_dir() or not (root / "run_server.py").is_file():
        raise ValueError("Open-LLM-VTuber 폴더의 run_server.py가 필요합니다.")
    if not (root / "pyproject.toml").is_file():
        raise ValueError("Open-LLM-VTuber 공식 프로젝트의 pyproject.toml이 필요합니다.")
    if not (root / "frontend").is_dir():
        raise ValueError(
            "공식 프런트엔드 폴더가 없습니다. 원본 설치 가이드의 "
            "Release ZIP 또는 git clone --recursive 경로를 확인하세요."
        )
    # uv run can auto-resolve / install dependencies. Respect the operator's
    # explicit no-install-unapproved constraint: never invoke uv's resolver.
    executable = shutil.which("uv")
    if executable is None:
        raise RuntimeError("이미 설치된 uv 실행 파일을 찾지 못했습니다. 자동 설치하지 않습니다.")
    env = dict(os.environ)
    env["UV_OFFLINE"] = "1"
    env["UV_NO_SYNC"] = "1"
    print("원본 기획안 1단계: 기존 Open-LLM-VTuber 실제 서버 실행")
    print("기반:", root)
    print("실행:", "uv run --offline --no-sync run_server.py")
    print("화면:", UPSTREAM_UI)
    print("설치·다운로드 없음. 모델·소리·Live2D가 실제 작동하는지는 별도로 확인해야 합니다.")
    cmd = [executable, "run", "--offline", "--no-sync", "run_server.py"]
    try:
        return subprocess.call(cmd, cwd=root, env=env)
    except OSError as exc:
        raise RuntimeError("공식 서버 프로세스를 실행하지 못했습니다.") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run existing official Open-LLM-VTuber for original-plan stage 1"
    )
    parser.add_argument(
        "--project-dir", type=Path, required=True,
        help="이미 준비된 원본 Open-LLM-VTuber 폴더 (설치·다운로드 수행 안 함)",
    )
    args = parser.parse_args(argv)
    try:
        return start_existing_open_llm_vtuber(args.project_dir)
    except (ValueError, RuntimeError, OSError) as exc:
        print("원본 1단계 실행 실패: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
