"""13단계 준비: 운영자가 직접 제공한 OS·하드웨어 입력을 이용한 오프라인 개발 범위표.

시스템 정보 탐색, 파일 읽기/쓰기, 네트워크, 외부 실행, 성능 추정은 하지 않는다.
기능이 소스에 구현되어 있다는 사실과 사용자 PC에서 실행 검증됐다는 사실을 구분한다.
"""
from __future__ import annotations

from dataclasses import dataclass

from .hardware_readiness import ManualHardwareChoice, review_manual_hardware
from .os_readiness import ManualOsChoice, assess_manual_os


@dataclass(frozen=True)
class ScopeItem:
    name: str
    source_status: str
    conditions: str


@dataclass(frozen=True)
class DevelopmentScope:
    os_reference_candidate: bool
    hardware_missing: tuple[str, ...]
    items: tuple[ScopeItem, ...]
    notes: tuple[str, ...]
    machine_verified: bool = False
    performance_verified: bool = False
    windows_exe_verified: bool = False

    def describe(self) -> str:
        lines = [
            "13단계 · 현재 PC에서 검토할 개발 범위 (사용자 직접 입력 기반)",
            "주의: 자동 PC 조회/실행/설치/성능 측정 없음. 실제 호환성은 검증하지 않았습니다.",
            "",
        ]
        for item in self.items:
            lines.append(f"■ {item.name} — {item.source_status}")
            lines.append(f"  확인 사항: {item.conditions}")
        lines.extend(["", "추가 확인 및 제한:"])
        lines.extend("- " + note for note in self.notes)
        lines.append("판정: 실제 PC 실행 가능 여부·모델 처리 속도·방송 가능 여부 모두 미검증.")
        return "\n".join(lines)


def review_development_scope(os_choice: ManualOsChoice, hardware: ManualHardwareChoice) -> DevelopmentScope:
    """명시적으로 전달받은 입력만 사용한다. 성능 임계치나 기기 지원을 지어내지 않는다."""
    if not isinstance(os_choice, ManualOsChoice):
        raise TypeError("ManualOsChoice가 필요합니다.")
    if not isinstance(hardware, ManualHardwareChoice):
        raise TypeError("ManualHardwareChoice가 필요합니다.")

    os_result = assess_manual_os(os_choice)
    hw_result = review_manual_hardware(hardware)
    if os_choice.os_code == "unknown" or os_choice.architecture == "unknown":
        os_note = "운영체제/시스템 종류가 미입력입니다. Windows x64 대상 여부부터 확인해야 합니다."
    elif os_result.candidate:
        os_note = "직접 입력한 OS는 Windows 10/11 x64 빌드 검토 후보입니다. 실제 실행은 검증되지 않았습니다."
    else:
        os_note = "직접 입력한 OS/시스템 종류는 현재 Windows x64 빌드 대상과 일치하지 않거나 확인되지 않았습니다."

    items = (
        ScopeItem(
            "설정·모의 채팅·SQLite 대화 기억", "로컬 소스 구현됨",
            "Python/Tkinter 실행 환경 및 저장 권한을 사용자 PC에서 직접 검증해야 함",
        ),
        ScopeItem(
            "2D 샘플 아바타·별도 창", "로컬 소스 구현됨",
            "실제 Windows 그래픽 표시/장시간 동작은 아직 검증하지 않음",
        ),
        ScopeItem(
            "Windows 한국어 시스템 음성", "기본 음성 연동 소스 구현됨",
            "PC에 이미 설치된 한국어 음성 및 Windows 실행 상태 확인 필요; 자동 설치 없음",
        ),
        ScopeItem(
            "로컬 Ollama 텍스트 AI", "선택형 localhost 연동 소스 구현됨",
            "사용자가 직접 준비한 로컬 모델 필요; 모델별 CPU/RAM/VRAM 요구사항과 속도 미검증",
        ),
        ScopeItem(
            "Windows EXE 생성·실행", "Windows 빌드 스크립트 제공",
            "PyInstaller 설치 여부와 실제 Windows x64 빌드·실행을 확인해야 함; 자동 설치 없음",
        ),
        ScopeItem(
            "실제 3D VRM·방송 플랫폼 채팅·OBS 송출", "미구현",
            "PC 사양과 무관하게 현재 소스만으로 실제 방송 기능을 사용할 수 없음",
        ),
    )
    notes = [os_note]
    if hw_result.missing:
        notes.append("직접 입력이 부족한 항목: " + ", ".join(hw_result.missing))
    else:
        notes.append("CPU·RAM·GPU 값은 입력됐지만 자가 신고값이므로 실측된 사양으로 간주하지 않습니다.")
    notes.append("RAM/VRAM 수치만으로 모델 실행 가능 여부나 FPS·응답 속도를 예측하지 않습니다.")
    notes.append("10단계 운영자 최종 승인, 11·12단계 PC 실확인, 13단계 실기기 범위 검증은 미완료입니다.")
    return DevelopmentScope(
        os_reference_candidate=os_result.candidate,
        hardware_missing=hw_result.missing,
        items=items,
        notes=tuple(notes),
    )
