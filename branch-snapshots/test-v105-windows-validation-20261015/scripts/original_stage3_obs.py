"""Original plan [7-4] manual REAL OBS connection (user PC only).

Default action is strictly read-only. It talks to actual OBS WebSocket 5
on 127.0.0.1:4455 and DOES NOT create a synthetic OBS response.
Never installs OBS, audio cables, browser, plugins or OBS Python dependency.

Environment:
  OBS_WEBSOCKET_PASSWORD=<password from the user's OBS>

Examples (from AISTING project root):
  python scripts/original_stage3_obs.py --status
  python scripts/original_stage3_obs.py --scene "My Live2D Scene"

No auto start or schedule. Live stream commands are deliberately not exposed
in this script until the user separately authorizes a real broadcast test.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_broadcaster.real_obs_control import RealObsController


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Original plan stage 3: actual localhost OBS WebSocket control"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true")
    group.add_argument("--scene", help="switch an existing OBS program scene")
    parser.add_argument("--port", type=int, default=4455)
    args = parser.parse_args(argv)
    try:
        client = RealObsController(
            password=os.environ.get("OBS_WEBSOCKET_PASSWORD", ""),
            port=args.port,
        )
        report = client.connect()
        print(f"실제 OBS 연결 확인: {report.obs_version}")
        if args.scene:
            report = client.select_scene(args.scene)
        print("실제 OBS 장면:", report.active_scene)
        print("실제 OBS 송출 상태:", "송출 중" if report.is_streaming else "송출 안 함")
        print("로컬 AI 채팅·음성·아바타의 OBS 캡처 연결은 별도 실기기 확인이 필요합니다.")
        return 0
    except (ValueError, RuntimeError, PermissionError) as exc:
        print("실제 OBS 연결 실패: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
