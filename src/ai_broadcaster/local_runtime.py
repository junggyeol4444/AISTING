"""9단계: 내 PC 실행 방식 확인용 순수 로컬 모듈.

진단/리포트 생성을 위해 네트워크, 클라우드, GitHub, OBS, AI 모델에 접속하지 않는다.
운영자의 수동 '저장 공간 검사' 명령에서만 전용 임시 파일을 쓰고 즉시 삭제한다.
PC 사양 감지, 프로그램 설치, 송출, 예약 실행을 하지 않는다.
"""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .offline_settings import DEFAULTS, data_dir, validate_settings


@dataclass(frozen=True)
class LocalOperationPlan:
    """실제로 구현된 것과 아직 구현하지 않은 기능의 경계를 명확하게 보고."""

    settings_path: Path
    memory_path: Path
    operating_mode: str = "내 Windows PC에서 독립 실행"
    default_chat_mode: str = "네트워크 없는 모의 답변"
    optional_ai: str = "운영자가 수동 선택한 경우에만 같은 PC의 127.0.0.1 Ollama"
    tts_mode: str = "PC에 이미 설치된 Windows 시스템 음성(수동 재생)"
    avatar_mode: str = "PC의 Tkinter 2D 샘플(3D 렌더러 미구현)"
    broadcasts: str = "실제 채팅 수집·OBS 송출·플랫폼 로그인은 미구현"
    github_required: bool = False
    scheduled_execution: bool = False
    external_publish_enabled: bool = False

    def describe(self) -> str:
        return (
            f"실행: {self.operating_mode}\n"
            f"기본 답변: {self.default_chat_mode}\n"
            f"선택적 AI: {self.optional_ai}\n"
            f"음성: {self.tts_mode}\n"
            f"아바타: {self.avatar_mode}\n"
            f"설정 파일: {self.settings_path}\n"
            f"로컬 대화 기억: {self.memory_path}\n"
            "GitHub·외부 실행 서버 필요: 없음\n"
            "자동 예약·외부 송출: 꺼짐\n"
            f"아직 미구현: {self.broadcasts}\n"
            "PC 사양 수집·모델 자동 설치·서버 접속 진단은 하지 않습니다."
        )


def local_operation_plan(
    settings: dict[str, Any] | None = None, *, storage_dir: Path | None = None,
) -> LocalOperationPlan:
    """설정의 로컬 운용 불변 조건만 확인. 파일/네트워크 I/O 없음."""
    checked = validate_settings(DEFAULTS if settings is None else settings)
    if checked["host"] != "local_pc" or checked["budget"] != "free_only":
        raise ValueError("로컬 무료 운용 정책을 위반한 설정입니다.")
    home = Path(storage_dir) if storage_dir is not None else data_dir()
    return LocalOperationPlan(home / "settings.json", home / "conversation.sqlite3")


@dataclass(frozen=True)
class StorageCheck:
    success: bool
    message: str


def check_local_storage(directory: Path) -> StorageCheck:
    """버튼 클릭 시에만 데이터 폴더에 임시 파일을 쓰고 지워 접근권한 점검.

    기존 사용자 설정/대화 DB를 열거나 수정하지 않으며, 오류는 반환만 한다.
    Windows에서 이미 열린 파일 삭제 문제를 피하려고 닫힌 후 제거한다.
    """
    try:
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w+b", prefix="aisting-check-", suffix=".tmp", dir=destination, delete=True,
        ) as tmp:
            tmp.write(b"AISTING_LOCAL_OK")
            tmp.flush()
            tmp.seek(0)
            if tmp.read() != b"AISTING_LOCAL_OK":
                raise OSError("임시 저장 파일을 다시 읽지 못했습니다.")
    except (OSError, ValueError, TypeError) as exc:
        return StorageCheck(False, f"PC 로컬 데이터 폴더를 사용할 수 없습니다: {exc}")
    return StorageCheck(True, "PC 로컬 폴더 읽기·쓰기 점검 통과. 기존 설정/기억 파일은 변경하지 않았습니다.")
