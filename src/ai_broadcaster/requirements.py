"""원본 기획안 원칙 및 단계 상태 검증 (외부 패키지 불필요)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def validate(config: dict[str, Any], roadmap: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    defaults = config.get("defaults", {})
    for key, expected in {
        "respond_to_all_chats": True,
        "forced_response_delay": False,
        "preemptively_skip_chats": False,
        "operator_judges_naturalness": True,
    }.items():
        if defaults.get(key) is not expected:
            errors.append(f"핵심 원칙 위반: defaults.{key}는 {expected!r} 필요")
    controls = config.get("control", {})
    for key in (
        "install_without_operator_approval",
        "charge_without_operator_approval",
        "publish_without_operator_approval",
        "broadcast_enabled_by_default",
        "clone_voice_without_permission",
    ):
        if controls.get(key) is not False:
            errors.append(f"운영자 승인 원칙 위반: control.{key}는 false 필수")
    if controls.get("operator_decisions_require_approval") is not True:
        errors.append("운영자 결정 승인이 필요합니다.")
    steps = roadmap.get("steps", [])
    if roadmap.get("total_steps") != 100 or len(steps) != 100:
        errors.append("로드맵은 정확히 100단계여야 합니다.")
    if [s.get("number") for s in steps] != list(range(1, 101)):
        errors.append("단계 번호는 1~100까지 연속이어야 합니다.")
    allowed = {"pending", "in_progress", "blocked", "review", "completed"}
    for s in steps:
        if not s.get("title") or s.get("status") not in allowed:
            errors.append(f"단계 내용 또는 상태 오류: {s.get('number')}")
    return errors

def validate_features(data: dict[str, Any]) -> list[str]:
    errors = []
    required = data.get("required", [])
    optional = data.get("optional", [])
    required_ids = {x.get("id") for x in required}
    expected = {"conversation","chat","tts","avatar","broadcast","lifecycle","notices","memory","operations"}
    if not expected.issubset(required_ids):
        errors.append("필수 기능 누락: " + ", ".join(sorted(expected-required_ids)))
    if not all(x.get("name") and x.get("acceptance") for x in required):
        errors.append("필수 기능 이름/수용 기준 누락")
    if any(x.get("id") in required_ids for x in optional):
        errors.append("선택 기능이 필수 기능과 중복")
    if any(x.get("enabled_by_default", False) is True for x in optional):
        errors.append("선택 기능을 기본 활성화할 수 없음")
    if len(data.get("no_default_actions", [])) == 0:
        errors.append("운영자 승인 이전 제한 목록 없음")
    return errors

def status(roadmap: dict[str, Any]) -> dict[str, Any]:
    steps = roadmap["steps"]
    completed = sum(x["status"] == "completed" for x in steps)
    current = next((x for x in steps if x["status"] != "completed"), None)
    return {"completed": completed, "total": len(steps), "current": current}
