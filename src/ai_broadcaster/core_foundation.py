"""21단계 방송 코어 *구조* 준비: 순수 메모리 구성도와 의존성 검증.

중요: 이 모듈은 실제 코어 실행/AI 연결/방송 송출을 구현하지 않는다.
사용자 PC 데이터 조회, 프로세스 실행, 네트워크, 파일 I/O가 전혀 없다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .offline_settings import (
    AVATARS, CONTENTS, PERSONA_MODES, PLATFORMS, VOICES, validate_settings,
)

CORE_SCHEMA_VERSION = 1
CORE_MODES = ("mock", "local_ollama")
STATES = frozenset(("implemented", "manual_only", "not_implemented"))


@dataclass(frozen=True)
class CoreComponent:
    key: str
    title: str
    state: str
    contract: str
    depends_on: tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class CoreBlueprint:
    schema_version: int
    runtime_mode: str
    platforms: tuple[str, ...]
    content: str
    persona_mode: str
    avatar: str
    voice: str
    components: tuple[CoreComponent, ...]
    streaming_enabled: bool = False
    auto_start_enabled: bool = False
    external_publish_enabled: bool = False

    def describe(self) -> str:
        """구성도만 표시. 연결 가능성/실제 작동을 증명하지 않는다."""
        validate_blueprint(self)
        status = {"implemented": "소스 존재", "manual_only": "수동 미리보기만",
                  "not_implemented": "미구현"}
        lines = [
            "21단계 · 방송 코어 기반 프로젝트 구성도 (실행 아님)",
            "방식: " + ("오프라인 모의 답변" if self.runtime_mode == "mock"
                     else "사용자 수동 로컬 Ollama 선택 (연결/설치 미검증)"),
            "선택 플랫폼: " + (", ".join(self.platforms) if self.platforms else "미선택"),
            f"콘텐츠: {self.content} · 캐릭터 방식: {self.persona_mode}",
            f"아바타: {self.avatar} · 목소리 확보 방식: {self.voice}",
            "", "연결 계약 / 구현 상태:",
        ]
        for part in self.components:
            dependencies = ", ".join(part.depends_on) if part.depends_on else "없음"
            lines.append(f"- {part.title} [{status[part.state]}] · 계약 {part.contract} · 선행 {dependencies}")
            if part.note:
                lines.append("  " + part.note)
        lines.extend((
            "", "방송/외부 발행/자동 시작: 모두 비활성", "플랫폼 선택은 계정 연결이 아닙니다.",
            "Windows 음성/2D 아바타는 로컬 미리보기 범위이며 방송 출력에 연결되지 않습니다.",
            "22단계 메모리 전용 모의 코어는 별도 수동 탭에서 실행합니다. 실제 통합 방송 코어·24단계 실제 AI 연결 시험·61~90단계 방송은 미구현입니다. 23단계 연결 방식 계획은 별도 탭에서 설정할 수 있습니다.",
            "외부 오픈소스 코어는 다운로드/설치/통합하지 않았습니다.",
            "10단계 최종 승인 및 11단계 이후 사용자 PC 확인은 대기, 공식 진행률 9/100 유지.",
        ))
        return "\n".join(lines)


def build_core_blueprint(settings: Mapping[str, object], runtime_mode: str = "mock") -> CoreBlueprint:
    """기존 설정값의 안전한 복사만 사용하며 설정/기억을 수정하지 않는다."""
    checked = validate_settings(settings)
    if type(runtime_mode) is not str or runtime_mode not in CORE_MODES:
        raise ValueError("지원하지 않는 방송 코어 응답 방식입니다.")

    components = (
        CoreComponent("input", "채팅 입력", "manual_only", "InputPort",
                      note="수동 대본만 지원, 실제 플랫폼 채팅 수신 미구현"),
        CoreComponent("reply", "답변 생성", "implemented" if runtime_mode == "mock" else "manual_only",
                      "ReplyPort", ("input",),
                      "기존 모의 답변 소스" if runtime_mode == "mock" else
                      "127.0.0.1 로컬 Ollama 수동 연습 소스만 존재; 실제 연결 미검증"),
        CoreComponent("memory", "대화 기억", "manual_only", "MemoryPort", ("reply",),
                      "기존 SQLite 저장은 선택적 채팅 연습에서만 사용; 자동 방송 기억 미구현"),
        CoreComponent("voice", "음성 출력", "manual_only" if checked["voice"] == "windows_system"
                      else "not_implemented", "VoicePort", ("reply",),
                      "기존 Windows 음성 수동 미리듣기만 가능" if checked["voice"] == "windows_system"
                      else "선택된 음성의 실제 방송용 합성 미구현"),
        CoreComponent("avatar", "아바타 출력", "manual_only" if checked["avatar"] == "2d"
                      else "not_implemented", "AvatarPort", ("reply",),
                      "기존 2D 샘플 미리보기만 가능" if checked["avatar"] == "2d"
                      else "선택된 아바타의 실제 방송 렌더링 미구현"),
        CoreComponent("broadcast", "실제 방송 송출", "not_implemented", "BroadcastPort",
                      ("reply", "voice", "avatar"), "OBS/플랫폼 로그인/실방송 연결 없음"),
        CoreComponent("orchestrator", "통합 방송 코어 실행", "not_implemented", "CoreCoordinator",
                      ("input", "reply", "memory", "voice", "avatar", "broadcast"),
                      "22단계 모의 실행은 별도 구현, 실제 통합 방송 코어는 미구현"),
    )
    blueprint = CoreBlueprint(
        CORE_SCHEMA_VERSION, runtime_mode, tuple(checked["platforms"]), checked["content"],
        checked["persona_mode"], checked["avatar"], checked["voice"], components,
    )
    validate_blueprint(blueprint)
    return blueprint


def validate_blueprint(plan: CoreBlueprint) -> None:
    """누락·순환 의존성·위험한 실행 플래그·미구현 상태 은폐를 거부한다."""
    if not isinstance(plan, CoreBlueprint) or type(plan.schema_version) is not int or plan.schema_version != CORE_SCHEMA_VERSION:
        raise ValueError("방송 코어 구성도 버전 오류")
    if type(plan.runtime_mode) is not str or plan.runtime_mode not in CORE_MODES:
        raise ValueError("코어 응답 방식 오류")
    if (type(plan.platforms) is not tuple or len(plan.platforms) != len(set(plan.platforms))
            or any(p not in PLATFORMS.values() for p in plan.platforms)
            or plan.content not in CONTENTS.values()
            or plan.persona_mode not in PERSONA_MODES.values()
            or plan.avatar not in AVATARS.values()
            or plan.voice not in VOICES.values()):
        raise ValueError("방송 코어 선택값 오류")
    if plan.streaming_enabled is not False or plan.auto_start_enabled is not False or plan.external_publish_enabled is not False:
        raise ValueError("승인받지 않은 방송/자동 실행 설정입니다.")
    expected = ("input", "reply", "memory", "voice", "avatar", "broadcast", "orchestrator")
    if (type(plan.components) is not tuple or any(not isinstance(part, CoreComponent) for part in plan.components)
            or tuple(part.key for part in plan.components) != expected):
        raise ValueError("필수 코어 연결 항목이 누락되거나 중복됐습니다.")
    known: set[str] = set()
    for part in plan.components:
        if not isinstance(part, CoreComponent) or part.state not in STATES or not part.contract:
            raise ValueError("코어 연결 계약 형식 오류")
        if not isinstance(part.depends_on, tuple) or any(dep not in known for dep in part.depends_on):
            raise ValueError("코어 의존성 누락·순환·순서 오류")
        known.add(part.key)
    if plan.components[5].state != "not_implemented" or plan.components[6].state != "not_implemented":
        raise ValueError("실제 방송/통합 코어를 구현 완료로 표시할 수 없습니다.")
    if plan.components[0].state != "manual_only" or plan.components[2].state != "manual_only":
        raise ValueError("입력/기억을 자동 방송 연결로 표시할 수 없습니다.")
    if plan.components[3].state != ("manual_only" if plan.voice == "windows_system" else "not_implemented"):
        raise ValueError("선택한 목소리의 실제 지원 범위를 잘못 표시했습니다.")
    if plan.components[4].state != ("manual_only" if plan.avatar == "2d" else "not_implemented"):
        raise ValueError("선택한 아바타의 실제 지원 범위를 잘못 표시했습니다.")
    if plan.runtime_mode == "mock" and plan.components[1].state != "implemented":
        raise ValueError("모의 답변 소스 상태가 올바르지 않습니다.")
    if plan.runtime_mode == "local_ollama" and plan.components[1].state != "manual_only":
        raise ValueError("로컬 AI 연결을 자동 실행 가능으로 표시할 수 없습니다.")
