"""20단계: 사용자가 명시적으로 실행하는 오프라인 개발 환경 자가점검.

검사 대상은 동봉된 개발 기준과 *격리된 샘플 데이터*뿐이다.
실제 사용자 PC 사양/설치 프로그램/계정/설정/기억을 조회하지 않는다.
실제 Windows 호환성, EXE 빌드, 방송, AI 모델 연결을 검증했다고 주장하지 않는다.
"""
from __future__ import annotations

import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .development_review import load_review_sources
from .local_runtime import local_operation_plan
from .offline_chat import ChatRehearsal, LocalMemory, MockReplyGenerator
from .offline_settings import DEFAULTS, VOICES, validate_settings, load_settings, save_settings
from .requirements import validate as validate_requirements


@dataclass(frozen=True)
class ExecutionCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ExecutionReport:
    checks: tuple[ExecutionCheck, ...]

    @property
    def passed(self) -> bool:
        return len(self.checks) == 5 and all(item.passed for item in self.checks)

    def describe(self) -> str:
        lines = [
            "20단계 · 오프라인 개발 환경 수동 자가점검",
            f"검사 결과: {sum(item.passed for item in self.checks)}/{len(self.checks)} 항목 통과",
            "", 
        ]
        lines.extend(
            f"{'[통과]' if item.passed else '[실패]'} {item.name}: {item.detail}"
            for item in self.checks
        )
        lines.extend((
            "", "점검은 동봉된 기획/설정 기준과 임시 샘플 데이터만 사용합니다.",
            "기존 사용자 설정·SQLite 기억·선택값은 읽거나 변경하지 않습니다.",
            "외부 네트워크·GitHub·Ollama·OBS·방송·설치·PC 사양 조회 없음.",
            "임시 샘플 데이터는 점검 종료 시 삭제를 시도하며 실패하면 오류로 보고합니다.",
            "Windows 실기기 실행·EXE 빌드·OS/하드웨어 적합성 검증은 별도로 필요합니다.",
            "10단계 최종 승인과 11~20단계 실제 PC 확인은 계속 승인 대기입니다.",
        ))
        return "\n".join(lines)


def _bundled_criteria(root: Path | None) -> str:
    requirements, roadmap = load_review_sources(root)
    errors = validate_requirements(requirements, roadmap)
    if errors:
        raise ValueError("기획 기준 불일치: " + "; ".join(errors[:3]))
    steps = roadmap["steps"]
    if sum(step["status"] == "completed" for step in steps) != 9:
        raise ValueError("기존 9개 완료 상태와 다릅니다. 승인 대기 단계를 자동 완료할 수 없습니다.")
    if any(step["status"] == "completed" for step in steps[9:20]):
        raise ValueError("사용자 승인/PC 확인 대기 단계를 완료로 표시할 수 없습니다.")
    return "동봉된 기준 100단계 및 승인 대기 상태 일치"


def _selection_policy() -> str:
    """All combinations are in-memory; do not load operator settings."""
    combinations = 0
    for platforms in ([], ["chzzk"], ["youtube", "twitch"], ["chzzk", "youtube", "twitch"]):
        for content in ("undecided", "chat", "game", "both"):
            for avatar in ("undecided", "2d", "3d"):
                for voice in VOICES.values():
                    sample = deepcopy(DEFAULTS)
                    sample["platforms"] = platforms.copy()
                    sample["content"] = content
                    sample["avatar"] = avatar
                    sample["voice"] = voice
                    sample["persona_mode"] = "custom"
                    sample["persona"]["name"] = "수동 선택 샘플"
                    checked = validate_settings(sample)
                    if checked != sample:
                        raise AssertionError("선택형 설정을 보존하지 못했습니다.")
                    plan = local_operation_plan(checked, storage_dir=Path("AISTING_SAMPLE_ONLY"))
                    if plan.github_required or plan.external_publish_enabled or plan.scheduled_execution:
                        raise AssertionError("로컬 운영 정책 위반")
                    combinations += 1
    return f"선택형 플랫폼·콘텐츠·아바타·목소리 {combinations}개 조합 및 로컬 정책 확인"


def _temporary_settings(base: Path) -> str:
    sample = deepcopy(DEFAULTS)
    sample["platforms"] = ["youtube", "chzzk"]
    sample["content"] = "both"
    sample["avatar"] = "3d"
    sample["voice"] = "windows_system"
    sample["voice_profile"]["installed_voice_name"] = "예시 이름"
    sample["persona_mode"] = "custom"
    sample["persona"]["name"] = "샘플"
    path = base / "sample" / "settings.json"
    save_settings(sample, path)
    if load_settings(path) != sample:
        raise AssertionError("임시 설정 저장·재읽기 불일치")
    return "임시 설정 저장·불러오기와 사용자 선택값 유지 확인"


def _mock_chat_fifo() -> str:
    rehearsal = ChatRehearsal(generator=MockReplyGenerator())
    rehearsal.add_script("가: 안녕\n나: 안녕\n가: 안녕")
    delivered = []
    while rehearsal.pending:
        rehearsal.process_next(delivered.append)
    if [answer.original.sender for answer in delivered] != ["가", "나", "가"]:
        raise AssertionError("채팅 순서/중복 응답 손실")
    if len(delivered) != 3 or len(rehearsal.completed) != 3 or rehearsal.pending:
        raise AssertionError("모의 채팅 응답 누락")
    return "모의 채팅 3건 FIFO 처리·중복 보존 (모델 연결 없음)"


def _temporary_memory(base: Path) -> str:
    db_path = base / "sample" / "memory.sqlite3"
    memory = LocalMemory(db_path)
    rehearsal = ChatRehearsal(generator=MockReplyGenerator(), memory=memory)
    rehearsal.add_script("테스트: 기억 점검\n테스트: 두 번째")
    while rehearsal.pending:
        rehearsal.process_next(lambda _answer: None)
    history = memory.recent(8)
    if [answer.original.text for answer in history] != ["기억 점검", "두 번째"]:
        raise AssertionError("임시 SQLite 기억 순서 불일치")
    if rehearsal.memory_errors:
        raise AssertionError("임시 SQLite 저장 실패")
    return "임시 SQLite 기억 2건 저장·재조회 확인"


def run_execution_selfcheck(*, project_root: Path | None = None,
                            scratch_parent: Path | None = None) -> ExecutionReport:
    """Called ONLY from an explicit button/CLI action; never at GUI initialization.

    Reads bundled project criteria; creates only disposable sample files in a
    TemporaryDirectory. Does not inspect OS, hardware, installed apps or user data.
    Each failure is reported, not converted into a successful check.
    """
    checks: list[ExecutionCheck] = []

    def check(name: str, action: Callable[[], str]) -> None:
        try:
            detail = action()
        except Exception as exc:
            checks.append(ExecutionCheck(name, False, f"{type(exc).__name__}: {exc}"))
        else:
            checks.append(ExecutionCheck(name, True, detail))

    check("동봉된 개발 기준", lambda: _bundled_criteria(project_root))
    check("선택형 설정·로컬 정책", _selection_policy)
    # Never fall back to the operator's persistent data folder on temp failure.
    try:
        with tempfile.TemporaryDirectory(prefix="aisting-selfcheck-", dir=scratch_parent) as tmp:
            scratch = Path(tmp)
            check("격리된 설정 저장", lambda: _temporary_settings(scratch))
            check("모의 대화 실행", _mock_chat_fifo)
            check("격리된 SQLite 기억", lambda: _temporary_memory(scratch))
    except (OSError, ValueError, PermissionError) as exc:
        # If a temp directory is unavailable, still test in-memory mock chat.
        if len(checks) == 2:
            checks.append(ExecutionCheck("격리된 설정 저장", False, f"임시 공간 생성 실패: {exc}"))
            check("모의 대화 실행", _mock_chat_fifo)
            checks.append(ExecutionCheck("격리된 SQLite 기억", False, "임시 공간을 만들 수 없습니다."))
        else:
            # Cleanup failure must not be misreported as a full success.
            checks.append(ExecutionCheck("임시 공간 정리", False, str(exc)))
    return ExecutionReport(tuple(checks))
