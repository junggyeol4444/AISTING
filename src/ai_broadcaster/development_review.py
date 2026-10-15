"""10단계 준비: 개발 기준을 오프라인으로 검토하고 PC에서만 수동 승인 기록.

승인 기록은 프로그램 설계 기준에 대한 확인일 뿐 PC 설치/모델 다운로드/OBS 방송,
결제, 외부 계정 연결, 예약 실행에 대한 허가가 아니다. 단독으로 어떤 작업도 시작하지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .offline_settings import data_dir, validate_settings
from .requirements import validate as validate_requirements

SCHEMA_VERSION = 1
RECEIPT_FILENAME = "development_criteria_approval.json"


@dataclass(frozen=True)
class CriteriaCheck:
    code: str
    title: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CriteriaReview:
    fingerprint: str
    checks: tuple[CriteriaCheck, ...]
    completed_steps: int
    pending_step: int

    @property
    def ready(self) -> bool:
        return all(check.passed for check in self.checks)

    def describe(self) -> str:
        lines = [
            "10단계: 전체 개발 기준 최종 검토 (오프라인)",
            f"완료한 로드맵 단계: {self.completed_steps}/100",
            "검토만으로 방송·설치·결제·로그인이 허용되지 않습니다.",
            "",
        ]
        for item in self.checks:
            lines.append(f"{'[통과]' if item.passed else '[확인 필요]'} {item.title}\n  {item.detail}")
        lines.extend((
            "",
            "현재 단계는 사용자가 확인 기록을 직접 남기기 전까지 '승인 대기'입니다.",
            "Windows EXE 실기기/OBS/방송 플랫폼 연결은 아직 검증되지 않았습니다.",
        ))
        return "\n".join(lines)


def bundled_project_root() -> Path:
    """실행 중인 EXE에 같이 묶인 설정 파일 또는 실제 소스 트리.

    PyInstaller --onefile 실행에서는 임시 추출 디렉터리 안에 번들 자료가 있으며,
    GitHub나 인터넷 다운로드는 하지 않는다.
    """
    unpacked = getattr(sys, "_MEIPASS", None)
    return Path(unpacked) if unpacked else Path(__file__).resolve().parents[2]


def load_review_sources(root: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    base = Path(root) if root is not None else bundled_project_root()
    with (base / "config" / "requirements.json").open("r", encoding="utf-8") as source:
        requirements = json.load(source)
    with (base / "config" / "roadmap.json").open("r", encoding="utf-8") as source:
        roadmap = json.load(source)
    if not isinstance(requirements, dict) or not isinstance(roadmap, dict):
        raise ValueError("검토 자료 형식이 잘못됐습니다.")
    return requirements, roadmap


def evaluate_review(
    requirements: dict[str, Any], roadmap: dict[str, Any], settings: dict[str, Any],
) -> CriteriaReview:
    """오직 주어진 사본만 검사하며 어떤 파일/네트워크 작업도 하지 않는다."""
    # 설정 필드 등 구조적 오류를 별도로 포착하여 운영자가 확인하도록 보고.
    try:
        checked = validate_settings(settings)
        setting_error = ""
    except (ValueError, TypeError, KeyError) as exc:
        checked = None
        setting_error = str(exc)
    try:
        guard_errors = validate_requirements(requirements, roadmap)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        guard_errors = [f"기획안 검증 실패: {exc}"]
    steps = roadmap.get("steps") if isinstance(roadmap, dict) else None
    if not isinstance(steps, list):
        steps = []
    completed = sum(s.get("status") == "completed" for s in steps if isinstance(s, dict))
    prior = all(
        len(steps) > i and isinstance(steps[i], dict)
        and steps[i].get("number") == i + 1 and steps[i].get("status") == "completed"
        for i in range(9)
    )
    pending_ten = (
        len(steps) > 9 and isinstance(steps[9], dict)
        and steps[9].get("number") == 10 and steps[9].get("status") in ("pending", "review")
    )
    first_pending = next((s.get("number") for s in steps
                          if isinstance(s, dict) and s.get("status") != "completed"), 101)
    operator = requirements.get("control", {}) if isinstance(requirements, dict) else {}
    policy = requirements.get("development_policy", {}) if isinstance(requirements, dict) else {}
    decisions = requirements.get("operator_decisions", {}) if isinstance(requirements, dict) else {}
    no_unsafe_approval = (
        isinstance(operator, dict) and operator.get("operator_decisions_require_approval") is True
        and all(operator.get(k) is False for k in (
            "install_without_operator_approval", "charge_without_operator_approval",
            "publish_without_operator_approval", "broadcast_enabled_by_default",
            "clone_voice_without_permission",
        ))
    )
    choices_are_runtime = (
        decisions.get("broadcast_platform") == "runtime_multi_select_optional"
        and decisions.get("content_concept") == "runtime_select_chat_game_both"
        and decisions.get("persona") == "runtime_default_or_custom"
        and decisions.get("avatar_type_and_asset") == "runtime_choose_2d_or_3d_asset_use_requires_approval"
    ) if isinstance(decisions, dict) else False
    local_policy = (
        checked is not None and checked["host"] == "local_pc"
        and checked["budget"] == "free_only"
        and checked["scheduled_execution"] is False
        and checked["streaming_enabled"] is False
        and checked["external_publish_enabled"] is False
        and decisions.get("hosting_option") == "local_pc"
        and decisions.get("llm_provider_and_budget") == "free_only"
    )
    source_policy = (
        isinstance(policy, dict)
        and "파일" in policy.get("source_delivery", "")
        and "자동 커밋" in policy.get("external_automation", "")
        and "비활성" in policy.get("scheduled_work", "")
    )
    checks = (
        CriteriaCheck("requirements", "원본 기획 기준 및 정확히 100단계",
                      not guard_errors, "위반 없음" if not guard_errors else "; ".join(guard_errors)[:400]),
        CriteriaCheck("earlier_stages", "1~9단계 검증 결과 유지", prior,
                      "1~9단계가 모두 완료 상태" if prior else "완료되지 않은 선행 단계가 있습니다."),
        CriteriaCheck("approval_boundary", "10단계는 운영자 최종 확인 전", pending_ten,
                      "최종 승인 여부를 임의로 변경하지 않음" if pending_ten else "로드맵 10단계를 확인해 주세요."),
        CriteriaCheck("local_only", "내 PC · 무료 · 방송/예약/외부 게시 기본 OFF", local_policy,
                      "PC 내부 설정 검증 통과" if local_policy else setting_error or "실행 정책 설정 불일치"),
        CriteriaCheck("free_selection", "플랫폼/콘텐츠/캐릭터/아바타 선택형", choices_are_runtime,
                      "사전 확정 없이 프로그램에서 선택/변경" if choices_are_runtime else "기획안 선택 방식 불일치"),
        CriteriaCheck("operator_control", "설치·결제·송출·음성 복제는 별도 승인", no_unsafe_approval,
                      "사용자 승인 없이 실행 불가" if no_unsafe_approval else "안전 규칙 불일치"),
        CriteriaCheck("offline_workflow", "GitHub 업로드·앱 내부 예약 실행 없는 로컬 개발", source_policy,
                      "오프라인 소스 ZIP 전달 원칙" if source_policy else "개발 정책 확인 필요"),
        CriteriaCheck("roadmap_next", "현재 공식 단계 10 검토 중", first_pending == 10 and completed == 9,
                      "9/100 완료, 10단계 검토 중" if first_pending == 10 and completed == 9 else "로드맵 상태 확인 필요"),
    )
    content = json.dumps(
        {"requirements": requirements, "roadmap": roadmap, "settings": checked},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    fingerprint = hashlib.sha256(content).hexdigest()
    return CriteriaReview(fingerprint, checks, completed, int(first_pending))


def approval_path(storage_dir: Path | None = None) -> Path:
    return (Path(storage_dir) if storage_dir is not None else data_dir()) / RECEIPT_FILENAME


def approval_status(review: CriteriaReview, path: Path) -> tuple[bool, str]:
    """기존 파일만 읽기; 없음/손상/변경은 승인을 인정하지 않음."""
    if not path.exists():
        return False, "승인 기록 없음 · 최종 승인 대기"
    try:
        with path.open("r", encoding="utf-8") as file:
            receipt = json.load(file)
        if (not isinstance(receipt, dict) or receipt.get("schema_version") != SCHEMA_VERSION
                or receipt.get("decision") != "approved"
                or receipt.get("method") != "manual_operator_confirmed"
                or receipt.get("fingerprint") != review.fingerprint
                or receipt.get("checks") != [c.code for c in review.checks if c.passed]
                or not review.ready):
            return False, "이전 승인 기록과 현재 개발 기준이 다릅니다. 재검토가 필요합니다."
        return True, "현재 개발 기준의 수동 승인 기록이 PC에 있습니다. (방송·결제 승인 아님)"
    except (OSError, ValueError, TypeError, UnicodeError):
        return False, "승인 기록을 읽을 수 없습니다. 재검토가 필요합니다."


def record_approval(review: CriteriaReview, path: Path, *, operator_confirmed: bool = False) -> Path:
    """운영자 확인 없이 기록을 만들지 않으며 실패해도 기존 파일을 손상시키지 않는다."""
    if not operator_confirmed:
        raise PermissionError("명시적인 운영자 확인이 필요합니다.")
    if not review.ready:
        raise ValueError("검토 항목을 모두 통과해야 승인 기록을 남길 수 있습니다.")
    record = {
        "schema_version": SCHEMA_VERSION,
        "decision": "approved",
        "method": "manual_operator_confirmed",
        "fingerprint": review.fingerprint,
        "checks": [item.code for item in review.checks],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "development_criteria_only_not_streaming_installation_payment_or_accounts",
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix="aisting-approval-", suffix=".tmp",
            dir=target.parent, delete=False,
        ) as out:
            temp_name = out.name
            json.dump(record, out, ensure_ascii=False, indent=2)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp_name, target)
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass
    return target


def revoke_approval(path: Path, *, operator_confirmed: bool = False) -> None:
    if not operator_confirmed:
        raise PermissionError("승인 취소 역시 운영자 확인이 필요합니다.")
    Path(path).unlink(missing_ok=True)
