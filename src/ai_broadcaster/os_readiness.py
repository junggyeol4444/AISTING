"""11단계 준비: 운영자가 직접 입력한 OS 종류의 로컬 호환성 안내.

실제 PC의 OS/CPU/RAM/GPU를 전혀 조회하지 않는다. OS 정보는 자가 입력이며
Windows EXE가 해당 PC에서 작동한다는 검증 또는 외부 업로드를 뜻하지 않는다.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir

OS_LABELS = {
    "확인하지 않음": "unknown",
    "Windows 11 (직접 입력)": "windows_11",
    "Windows 10 (직접 입력)": "windows_10",
    "그 외 Windows (직접 입력)": "windows_other",
    "Windows 외 운영체제 (직접 입력)": "non_windows",
}
ARCH_LABELS = {
    "확인하지 않음": "unknown",
    "64비트 x64 (직접 입력)": "x64",
    "ARM64 (직접 입력)": "arm64",
    "32비트 x86 (직접 입력)": "x86",
    "기타 (직접 입력)": "other",
}
RECORD_NAME = "os_operator_note.json"
MAX_RECORD_BYTES = 4096


@dataclass(frozen=True)
class ManualOsChoice:
    os_code: str
    architecture: str

    def __post_init__(self) -> None:
        if type(self.os_code) is not str or self.os_code not in OS_LABELS.values():
            raise ValueError("지원하지 않는 운영체제 입력입니다.")
        if type(self.architecture) is not str or self.architecture not in ARCH_LABELS.values():
            raise ValueError("지원하지 않는 시스템 종류 입력입니다.")


@dataclass(frozen=True)
class OsReadiness:
    choice: ManualOsChoice
    candidate: bool
    description: str
    machine_verified: bool = False


def assess_manual_os(choice: ManualOsChoice) -> OsReadiness:
    """입력값만 판정. sys/platform/winreg/subprocess 등을 호출하지 않는다."""
    if not isinstance(choice, ManualOsChoice):
        raise TypeError("ManualOsChoice가 필요합니다.")
    if choice.os_code == "unknown" or choice.architecture == "unknown":
        detail = "운영체제 또는 시스템 종류가 미확인입니다. PC 확인 이후 정보를 직접 입력해 주세요."
        candidate = False
    elif choice.os_code in ("windows_10", "windows_11") and choice.architecture == "x64":
        detail = ("현재 제공하는 Windows x64 빌드 방식의 검토 후보입니다. "
                  "실제 AISTING.exe 설치·실행·음성·OBS 동작 여부는 확인되지 않았습니다.")
        candidate = True
    elif choice.architecture == "x86":
        detail = "현재 준비된 x64 EXE 빌드 방식과 32비트 Windows는 맞지 않습니다. 별도 검토가 필요합니다."
        candidate = False
    elif choice.os_code == "non_windows":
        detail = "AISTING은 Windows PC용 프로그램입니다. 현재 EXE 방식과 호환이 확인되지 않았습니다."
        candidate = False
    elif choice.architecture == "arm64":
        detail = "ARM64에서의 x64 호환 실행은 검증하지 않았습니다. Windows PC에서 별도 검증이 필요합니다."
        candidate = False
    else:
        detail = "현재 Windows x64 EXE 방식의 지원 여부가 확인되지 않았습니다. PC에서 별도 검토가 필요합니다."
        candidate = False
    return OsReadiness(
        choice=choice, candidate=candidate,
        description=("사용자 직접 입력 기반 참고 결과입니다. 자동 PC 조회·실기기 검증 없음.\n" + detail),
    )


def os_note_path(storage_dir: Path | None = None) -> Path:
    return (Path(storage_dir) if storage_dir is not None else data_dir()) / RECORD_NAME


def load_os_note(path: Path) -> ManualOsChoice | None:
    """운영자 요청 시에만 이전 입력 기록을 불러온다. 손상 파일은 변경하지 않는다."""
    try:
        with Path(path).open("rb") as reader:
            raw = reader.read(MAX_RECORD_BYTES + 1)
        if len(raw) > MAX_RECORD_BYTES:
            raise ValueError("입력 기록이 허용 크기를 초과했습니다.")
        value = json.loads(raw.decode("utf-8"))
        if (not isinstance(value, dict) or set(value) != {"schema_version", "source", "os_code", "architecture"}
                or type(value["schema_version"]) is not int or value["schema_version"] != 1
                or value["source"] != "operator_self_report"):
            raise ValueError("저장된 운영체제 입력 기록 형식이 잘못됐습니다.")
        return ManualOsChoice(value["os_code"], value["architecture"])
    except FileNotFoundError:
        return None


def save_os_note(choice: ManualOsChoice, path: Path, *, operator_confirmed: bool = False) -> Path:
    """운영자의 명시적 확인 후에만 입력 내용을 별도 파일에 안전하게 기록한다."""
    if not operator_confirmed:
        raise PermissionError("운영자의 명시적 저장 승인이 필요합니다.")
    if not isinstance(choice, ManualOsChoice):
        raise TypeError("ManualOsChoice가 필요합니다.")
    if choice.os_code == "unknown" or choice.architecture == "unknown":
        raise ValueError("확인하지 않은 항목은 PC에 저장하지 않습니다.")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {"schema_version": 1, "source": "operator_self_report",
              "os_code": choice.os_code, "architecture": choice.architecture}
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         prefix="aisting-os-note-", suffix=".tmp", delete=False) as output:
            temporary = output.name
            json.dump(record, output, ensure_ascii=False, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass
    return target


def delete_os_note(path: Path, *, operator_confirmed: bool = False) -> None:
    if not operator_confirmed:
        raise PermissionError("삭제하려면 운영자의 명시적 확인이 필요합니다.")
    Path(path).unlink(missing_ok=True)
