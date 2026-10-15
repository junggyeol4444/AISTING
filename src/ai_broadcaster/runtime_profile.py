"""17단계: 오프라인 수동 실행 환경의 선택/검증/기록.

이 모듈은 PC 사양을 감지하거나 모델/프로그램을 실행하지 않는다. 저장한
프로필은 자동으로 실행되지 않으며 운영자가 GUI에서 명시적으로 적용한다.
"""
from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .offline_settings import data_dir

PROFILE_NAME = "runtime_operator_profile.json"
MAX_PROFILE_BYTES = 4096
MODES = {
    "모의 답변 (인터넷 불필요)": "mock",
    "로컬 Ollama (수동 선택)": "local_ollama",
}
MODEL_PATTERN = re.compile(r"[A-Za-z0-9_.:/-]{1,120}\Z")


@dataclass(frozen=True)
class RuntimeProfile:
    mode: str = "mock"
    model_name: str = ""

    def __post_init__(self) -> None:
        if type(self.mode) is not str or self.mode not in MODES.values():
            raise ValueError("지원하지 않는 응답 방식입니다.")
        if type(self.model_name) is not str:
            raise ValueError("로컬 모델 이름이 올바르지 않습니다.")
        if self.mode == "mock" and self.model_name:
            raise ValueError("모의 답변에는 모델 이름을 지정하지 않습니다.")
        if self.mode == "local_ollama" and (
            not MODEL_PATTERN.fullmatch(self.model_name)
            or "://" in self.model_name or self.model_name.startswith("/")
            or any(part in ("", ".", "..") for part in self.model_name.split("/"))
        ):
            raise ValueError("로컬 Ollama 모델 이름은 영문/숫자 및 _ . : / - 만 허용합니다 (1~120자).")

    def describe(self) -> str:
        label = next(name for name, code in MODES.items() if code == self.mode)
        return (
            "17단계 · 기본 실행 환경 계획 (사용자 선택값만, 실제 실행 아님)\n"
            f"채팅 연습 응답 방식: {label}\n"
            f"모델 이름: {self.model_name if self.mode == 'local_ollama' else '(불필요)'}\n"
            "AI 연결 범위: 로컬 Ollama 선택 시 127.0.0.1:11434만 (실제 요청은 '모두 답변' 클릭 시)\n"
            "앱 실행 시 자동 모델 연결: 없음\n"
            "앱 실행 시 자동 방송·자동 채팅 처리·자동 음성: 없음\n"
            "프로그램 설치·PC 사양 조회·외부 서버·GitHub·계정 연동: 없음\n"
            "미리보기는 PC 파일 읽기/쓰기 없이 수행됩니다.\n"
            "저장된 프로필도 자동 적용되지 않으며, 채팅 연습에 적용 버튼을 눌러야 반영됩니다.\n"
            "플랫폼/콘텐츠/캐릭터/음성/아바타 설정과 SQLite 기억은 변경하지 않습니다.\n"
            "이 화면은 실제 Windows 실행 환경 검증이나 10/15/17단계 승인 완료가 아닙니다."
        )


def profile_path(storage_dir: Path | None = None) -> Path:
    return (Path(storage_dir) if storage_dir is not None else data_dir()) / PROFILE_NAME


def _assert_safe_path(path: Path) -> None:
    """파일/상위 디렉터리의 심볼릭 링크·Windows 정션을 통한 우회 방지."""
    for item in (path, *path.parents):
        if item.is_symlink() or bool(getattr(item, "is_junction", lambda: False)()):
            raise ValueError("링크/정션 경로에는 실행 환경 기록을 저장·조회하지 않습니다.")
        try:
            info = item.lstat()
        except (FileNotFoundError, NotADirectoryError):
            continue
        if getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError("재분석 지점 경로는 사용할 수 없습니다.")


def load_profile(path: Path) -> RuntimeProfile | None:
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError("실행 환경 기록 경로가 일반 파일이 아닙니다.")
    try:
        with target.open("rb") as stream:
            raw = stream.read(MAX_PROFILE_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(raw) > MAX_PROFILE_BYTES:
        raise ValueError("실행 환경 기록 크기가 허용 범위를 넘었습니다.")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("실행 환경 기록 JSON을 읽을 수 없습니다.") from exc
    return validate_profile_record(data)


def validate_profile_record(data: object) -> RuntimeProfile:
    """Disk-independent validation also used for an operator-selected recovery ZIP."""
    if (type(data) is not dict or set(data) != {
        "schema_version", "source", "mode", "model_name", "host", "manual_start_only",
        "streaming_enabled", "external_publish_enabled",
    } or type(data["schema_version"]) is not int or data["schema_version"] != 1
        or data["source"] != "operator_choice" or data["host"] != "127.0.0.1"
        or data["manual_start_only"] is not True
        or data["streaming_enabled"] is not False
        or data["external_publish_enabled"] is not False):
        raise ValueError("저장된 실행 환경 기록이 로컬 수동 실행 정책에 맞지 않습니다.")
    return RuntimeProfile(data["mode"], data["model_name"])


def save_profile(profile: RuntimeProfile, path: Path, *, operator_confirmed: bool = False) -> Path:
    if not operator_confirmed:
        raise PermissionError("운영자가 저장을 명시적으로 확인해야 합니다.")
    if not isinstance(profile, RuntimeProfile):
        raise TypeError("RuntimeProfile이 필요합니다.")
    # frozen dataclass도 object.__setattr__으로 바뀔 수 있으므로 재검증한다.
    checked = RuntimeProfile(profile.mode, profile.model_name)
    target = Path(path)
    _assert_safe_path(target)
    if target.exists():
        if not target.is_file():
            raise ValueError("동명 항목이 파일이 아니므로 저장하지 않습니다.")
        # 알 수 없는 기존 내용을 프로필로 오인하여 덮어쓰지 않는다.
        load_profile(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 1, "source": "operator_choice",
        "mode": checked.mode, "model_name": checked.model_name,
        "host": "127.0.0.1", "manual_start_only": True,
        "streaming_enabled": False, "external_publish_enabled": False,
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix="aisting-runtime-", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        _assert_safe_path(target)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
    return target


def delete_profile(path: Path, *, operator_confirmed: bool = False) -> None:
    if not operator_confirmed:
        raise PermissionError("운영자가 삭제를 명시적으로 확인해야 합니다.")
    target = Path(path)
    _assert_safe_path(target)
    if target.exists():
        # 알 수 없는 파일이나 손상된 기록을 자동 삭제하지 않는다.
        load_profile(target)
    target.unlink(missing_ok=True)
