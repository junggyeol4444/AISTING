"""23단계: 방송 코어 AI 연결 *방식*의 오프라인 검증/선택 계약.

네트워크, 파일, 모델 목록 조회, 프로세스 실행을 하지 않는다. 실제 로컬 AI
연결 시험은 24단계의 별도 명시적 사용자 동작이 있어야 가능하다.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir
from .runtime_profile import RuntimeProfile, save_profile, load_profile, delete_profile

LOOPBACK_HOST = "127.0.0.1"
LOOPBACK_PORT = 11434
GENERATE_PATH = "/api/generate"
SCHEMA_VERSION = 1
CORE_AI_PROFILE_NAME = "core_ai_operator_profile.json"


@dataclass(frozen=True)
class CoreAIConnectionPlan:
    schema_version: int
    mode: str
    model_name: str
    transport: str
    host: str
    port: int
    request_path: str
    manual_only: bool = True
    network_enabled: bool = False
    auto_start_enabled: bool = False
    streaming_enabled: bool = False
    external_publish_enabled: bool = False

    def describe(self) -> str:
        validate_core_ai_plan(self)
        if self.mode == "mock":
            choice = "내장 모의 답변 · 외부 모델 불필요"
            route = "네트워크 없음 · 메모리 내 MockCoreReplyPort"
        else:
            choice = "같은 PC의 Ollama (향후 수동 연결 후보)"
            route = f"향후 허용 주소: http://{self.host}:{self.port}{self.request_path}"
        return "\n".join((
            "23단계 · AI 모델 연결 방식 설정 (계획/검증만, 실제 연결 아님)",
            f"선택 방식: {choice}",
            f"모델 이름: {self.model_name or '(없음)'}",
            f"경로: {route}",
            "연결 가능 여부·설치 여부·모델 존재 여부: 확인하지 않음",
            "자동 모델 연결·다운로드·설치·클라우드 API·외부 서버: 금지",
            "코어의 22단계 수동 실행은 연결 계획을 적용해도 모의 답변만 생성",
            "기존 채팅 연습의 수동 Ollama 설정과 독립된 코어 연결 계획",
            "실제 모델 연결 시험은 24단계에서 별도 사용자 승인 후 구현/검증 예정",
            "플랫폼·콘텐츠·캐릭터·목소리·아바타 선택과 SQLite 기억은 변경하지 않음",
            "10단계 최종 승인/11단계 이후 PC 확인은 보류 · 공식 9/100",
        ))


def build_core_ai_plan(mode: str = "mock", model_name: str = "") -> CoreAIConnectionPlan:
    """운영자 입력만 검증한다. 어떤 시스템 상태도 읽지 않는다."""
    profile = RuntimeProfile(mode, model_name)
    plan = CoreAIConnectionPlan(
        schema_version=SCHEMA_VERSION,
        mode=profile.mode,
        model_name=profile.model_name,
        transport="none" if profile.mode == "mock" else "loopback_http_candidate",
        host=LOOPBACK_HOST,
        port=LOOPBACK_PORT,
        request_path=GENERATE_PATH if profile.mode == "local_ollama" else "",
    )
    validate_core_ai_plan(plan)
    return plan


def validate_core_ai_plan(plan: CoreAIConnectionPlan) -> None:
    """변조/위험한 실행 플래그/원격 주소를 fail-closed로 거부한다."""
    if not isinstance(plan, CoreAIConnectionPlan):
        raise TypeError("코어 AI 연결 계획 형식이 아닙니다.")
    if type(plan.schema_version) is not int or plan.schema_version != SCHEMA_VERSION:
        raise ValueError("코어 AI 연결 계획 버전 오류")
    profile = RuntimeProfile(plan.mode, plan.model_name)
    expected_transport = "none" if profile.mode == "mock" else "loopback_http_candidate"
    expected_path = "" if profile.mode == "mock" else GENERATE_PATH
    if (type(plan.transport) is not str or plan.transport != expected_transport
            or type(plan.host) is not str or plan.host != LOOPBACK_HOST
            or type(plan.port) is not int or plan.port != LOOPBACK_PORT
            or type(plan.request_path) is not str or plan.request_path != expected_path):
        raise ValueError("외부/변경된 AI 연결 경로를 사용할 수 없습니다.")
    if (plan.manual_only is not True or plan.network_enabled is not False
            or plan.auto_start_enabled is not False or plan.streaming_enabled is not False
            or plan.external_publish_enabled is not False):
        raise ValueError("자동 AI 연결·외부 송출은 허용하지 않습니다.")


def core_ai_profile_path(storage_dir: Path | None = None) -> Path:
    """17단계 채팅 연습 프로필과 분리된 코어 AI 계획 기록."""
    return (Path(storage_dir) if storage_dir is not None else data_dir()) / CORE_AI_PROFILE_NAME


def save_core_ai_plan(plan: CoreAIConnectionPlan, path: Path, *, operator_confirmed: bool = False) -> Path:
    """기존 17단계의 안전한 원자적 로컬 저장 기능 재사용."""
    validate_core_ai_plan(plan)
    return save_profile(RuntimeProfile(plan.mode, plan.model_name), path,
                        operator_confirmed=operator_confirmed)


def load_core_ai_plan(path: Path) -> CoreAIConnectionPlan | None:
    """명시적 불러오기 전에는 어떤 파일도 읽지 않는다."""
    profile = load_profile(path)
    return None if profile is None else build_core_ai_plan(profile.mode, profile.model_name)


def delete_core_ai_plan(path: Path, *, operator_confirmed: bool = False) -> None:
    """코어 계획 기록 하나만 수동 삭제. 기존 설정/기억에는 접근하지 않음."""
    delete_profile(path, operator_confirmed=operator_confirmed)
