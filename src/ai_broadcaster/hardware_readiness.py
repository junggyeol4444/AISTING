"""12단계 준비: 운영자가 직접 적은 PC 하드웨어 참고 기록.

모든 함수는 입력된 문자열과 파일만 다룬다. 실제 사용자 PC의 CPU/RAM/GPU,
장치 목록, 드라이버 또는 네트워크를 탐색하지 않는다. 이것은 진단 결과가 아니다.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir

RECORD_NAME = "hardware_operator_note.json"
MAX_RECORD_BYTES = 4096
MAX_DEVICE_NAME_CHARS = 120


@dataclass(frozen=True)
class ManualHardwareChoice:
    cpu_name: str = ""
    cpu_cores: int | None = None
    ram_gb: int | None = None
    gpu_name: str = ""
    gpu_vram_gb: int | None = None

    def __post_init__(self) -> None:
        for label, name in (("CPU", self.cpu_name), ("GPU", self.gpu_name)):
            if not isinstance(name, str) or len(name) > MAX_DEVICE_NAME_CHARS:
                raise ValueError(f"{label} 모델명은 120자 이하로 입력해 주세요.")
            if any(ord(char) < 32 for char in name):
                raise ValueError(f"{label} 모델명에는 제어 문자를 넣을 수 없습니다.")
        for label, amount, low, high in (
            ("CPU 코어 수", self.cpu_cores, 1, 256),
            ("RAM 용량", self.ram_gb, 1, 4096),
            ("GPU VRAM 용량", self.gpu_vram_gb, 0, 1024),
        ):
            if amount is not None and (type(amount) is not int or not low <= amount <= high):
                raise ValueError(f"{label}는 {low}~{high} 범위의 정수 또는 미입력이어야 합니다.")


@dataclass(frozen=True)
class HardwareReview:
    summary: str
    missing: tuple[str, ...]
    machine_verified: bool = False
    performance_verified: bool = False


def review_manual_hardware(choice: ManualHardwareChoice) -> HardwareReview:
    """사용자 입력을 정리만 한다. 임의의 AI 모델 성능/호환성을 예측하지 않는다."""
    if not isinstance(choice, ManualHardwareChoice):
        raise TypeError("ManualHardwareChoice가 필요합니다.")
    missing = []
    if not choice.cpu_name.strip():
        missing.append("CPU 모델명")
    if choice.cpu_cores is None:
        missing.append("CPU 코어 수")
    if choice.ram_gb is None:
        missing.append("RAM 용량")
    if not choice.gpu_name.strip():
        missing.append("GPU 모델명 (없음/모름도 사용자가 직접 입력 가능)")
    # 통합 GPU/VRAM 미노출 등 정상적인 미입력 상황을 허용.
    lines = [
        "이 정보는 운영자 직접 입력값입니다. 실제 PC 사양 자동 조회/검증은 하지 않았습니다.",
        f"CPU: {choice.cpu_name.strip() or '미입력'} · 코어: {choice.cpu_cores if choice.cpu_cores is not None else '미입력'}",
        f"RAM: {str(choice.ram_gb) + ' GB' if choice.ram_gb is not None else '미입력'}",
        f"GPU: {choice.gpu_name.strip() or '미입력'} · VRAM: {str(choice.gpu_vram_gb) + ' GB' if choice.gpu_vram_gb is not None else '미입력'}",
    ]
    if missing:
        lines.append("추가 확인 참고 항목: " + ", ".join(missing))
    lines.append(
        "이 단계에서는 특정 로컬 AI/모델·2D/3D·방송 기능의 성능 또는 실행 가능 여부를 "
        "판정하지 않습니다. 실제 PC 측정과 선택한 프로그램의 요구사항 검토가 필요합니다."
    )
    return HardwareReview(summary="\n".join(lines), missing=tuple(missing))


def hardware_note_path(storage_dir: Path | None = None) -> Path:
    return (Path(storage_dir) if storage_dir is not None else data_dir()) / RECORD_NAME


def load_hardware_note(path: Path) -> ManualHardwareChoice | None:
    try:
        with Path(path).open("rb") as reader:
            raw = reader.read(MAX_RECORD_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(raw) > MAX_RECORD_BYTES:
        raise ValueError("PC 하드웨어 참고 기록의 크기 제한을 넘었습니다.")
    try:
        record = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("PC 하드웨어 참고 기록을 읽을 수 없습니다.") from exc
    expected = {"schema_version", "source", "cpu_name", "cpu_cores", "ram_gb", "gpu_name", "gpu_vram_gb"}
    if (not isinstance(record, dict) or set(record) != expected
            or type(record["schema_version"]) is not int or record["schema_version"] != 1
            or record["source"] != "operator_self_report"):
        raise ValueError("PC 하드웨어 참고 기록의 출처 또는 형식이 올바르지 않습니다.")
    return ManualHardwareChoice(
        cpu_name=record["cpu_name"], cpu_cores=record["cpu_cores"],
        ram_gb=record["ram_gb"], gpu_name=record["gpu_name"],
        gpu_vram_gb=record["gpu_vram_gb"],
    )


def save_hardware_note(choice: ManualHardwareChoice, path: Path, *, operator_confirmed: bool = False) -> Path:
    if not operator_confirmed:
        raise PermissionError("운영자가 직접 확인하기 전에는 기록할 수 없습니다.")
    if not isinstance(choice, ManualHardwareChoice):
        raise TypeError("ManualHardwareChoice가 필요합니다.")
    if not any((choice.cpu_name.strip(), choice.cpu_cores is not None,
                choice.ram_gb is not None, choice.gpu_name.strip(), choice.gpu_vram_gb is not None)):
        raise ValueError("입력한 사양 정보가 하나도 없습니다.")
    target = Path(path)
    document = {
        "schema_version": 1, "source": "operator_self_report",
        "cpu_name": choice.cpu_name.strip(), "cpu_cores": choice.cpu_cores,
        "ram_gb": choice.ram_gb, "gpu_name": choice.gpu_name.strip(),
        "gpu_vram_gb": choice.gpu_vram_gb,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix="aisting-hardware-note-", suffix=".tmp", delete=False,
        ) as writer:
            temporary = writer.name
            json.dump(document, writer, ensure_ascii=False, indent=2)
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass
    return target


def delete_hardware_note(path: Path, *, operator_confirmed: bool = False) -> None:
    if not operator_confirmed:
        raise PermissionError("운영자 확인이 필요합니다.")
    Path(path).unlink(missing_ok=True)
