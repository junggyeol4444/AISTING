"""19단계: 수동 ZIP 무결성 확인 및 비파괴적 복구 사본 준비.

18단계 ZIP만 수락한다. 기존 실행 중 설정/SQLite/프로젝트를 덮어쓰지 않는다.
버튼 클릭과 별도 확인 없이는 파일 읽기/쓰기/네트워크/PC 조회가 없다.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .manual_archive import (
    MANIFEST, MAX_ARCHIVE_BYTES, MAX_SOURCE_BYTES, PROJECT_ITEMS, USER_ITEMS,
    _member, _safe_path, verify_archive,
)
from .offline_settings import _migrate_legacy_v05, _migrate_legacy_voice, validate_settings
from .runtime_profile import validate_profile_record

STAGING_NAME = "AISTING_Recovery_Staging"
NOTE_NAME = "RECOVERY_NOTE.txt"
REQUIRED_MEMBERS = frozenset(_member(label) for label, _ in PROJECT_ITEMS)
ALLOWED_MEMBERS = frozenset(_member(label) for label, _ in PROJECT_ITEMS + USER_ITEMS)


@dataclass(frozen=True)
class BackupInspection:
    archive: Path
    members: tuple[tuple[str, int, str], ...]

    def describe(self) -> str:
        lines = [
            "19단계 · 로컬 백업 무결성 검사 (읽기 전용)",
            f"선택한 ZIP: {self.archive}",
            f"SHA256 검증 완료: {len(self.members)}개 파일",
            "",
        ]
        lines.extend(f"- {name} ({size}바이트, SHA256 {digest[:12]}…)" for name, size, digest in self.members)
        lines.extend((
            "", "복구 사본 생성은 별도 버튼과 확인을 거쳐야 합니다.",
            "복구 사본은 새 폴더에만 생성하며 실행 중인 설정/SQLite를 덮어쓰지 않습니다.",
            "SQLite 대화 기억, OS/PC 정보는 이 ZIP에 포함되지 않습니다.",
            "정기 자동 백업/자동 복원/사용자 승인/실기기 검증이 아닙니다.",
        ))
        return "\n".join(lines)


def _validated_snapshot(path: Path) -> tuple[BackupInspection, dict[str, bytes]]:
    """Read only an explicitly selected ZIP; verify hash and safe semantic content."""
    archive_path = Path(path)
    _safe_path(archive_path)
    if not archive_path.is_file():
        raise ValueError("선택한 ZIP이 일반 파일이 아닙니다.")
    try:
        manifest = verify_archive(archive_path)
        entries = manifest["entries"]
        names = {entry["name"] for entry in entries}
        if not REQUIRED_MEMBERS <= names or not names <= ALLOWED_MEMBERS or len(names) != len(entries):
            raise ValueError("필수 기획안/요구사항/로드맵이 없거나 중복 항목이 있습니다.")
        snapshots: dict[str, bytes] = {}
        total = 0
        with zipfile.ZipFile(archive_path, "r") as archive:
            if set(archive.namelist()) != names | {MANIFEST}:
                raise ValueError("검사 중 ZIP 구성 변경이 감지됐습니다.")
            for entry in entries:
                name = entry["name"]
                with archive.open(name) as stream:
                    raw = stream.read(MAX_SOURCE_BYTES + 1)
                total += len(raw)
                if (len(raw) != entry["bytes"] or len(raw) > MAX_SOURCE_BYTES
                        or total > MAX_ARCHIVE_BYTES
                        or hashlib.sha256(raw).hexdigest() != entry["sha256"]):
                    raise ValueError("검사 중 ZIP 내용 변경 또는 크기 초과가 감지됐습니다.")
                snapshots[name] = raw
        # Do not stage files that could activate unsafe settings if later copied manually.
        snapshots["project/docs/ORIGINAL_PLAN.txt"].decode("utf-8")
        for name in ("project/config/requirements.json", "project/config/roadmap.json"):
            if type(json.loads(snapshots[name].decode("utf-8"))) is not dict:
                raise ValueError(f"{name}: JSON 객체가 아닙니다.")
        if "operator/settings.json" in snapshots:
            value = json.loads(snapshots["operator/settings.json"].decode("utf-8"))
            validate_settings(_migrate_legacy_voice(_migrate_legacy_v05(value)))
        if "operator/runtime_operator_profile.json" in snapshots:
            value = json.loads(snapshots["operator/runtime_operator_profile.json"].decode("utf-8"))
            validate_profile_record(value)
        info = BackupInspection(archive_path, tuple(
            (entry["name"], entry["bytes"], entry["sha256"]) for entry in entries
        ))
        return info, snapshots
    except (zipfile.BadZipFile, zipfile.LargeZipFile, EOFError, RuntimeError,
            UnicodeError, KeyError, TypeError) as exc:
        raise ValueError("유효한 AISTING 수동 보관 ZIP이 아닙니다.") from exc


def inspect_backup(path: Path) -> BackupInspection:
    """Explicit operator request only. Never creates or changes files."""
    inspection, _ = _validated_snapshot(path)
    return inspection


def stage_recovery(path: Path, parent: Path, *, confirmed: bool = False) -> Path:
    """Copy verified files into a NEW staging folder; never touch live application data.

    On error, remove only the staging directory created by this call.
    No automatic restore, no SQLite copy, no scheduled work.
    """
    if not confirmed:
        raise PermissionError("사용자 확인 없이 복구 사본을 만들지 않습니다.")
    destination_parent = Path(parent)
    if (not destination_parent.is_absolute() or ".." in destination_parent.parts
            or destination_parent == Path(destination_parent.anchor)):
        raise ValueError("복구 사본 상위 폴더는 루트가 아닌 절대 경로여야 합니다.")
    target = destination_parent / STAGING_NAME
    _safe_path(destination_parent)
    _safe_path(target)
    if not destination_parent.is_dir():
        raise ValueError("이미 존재하는 로컬 상위 폴더를 선택해 주세요.")
    if target.exists() or target.is_symlink():
        raise FileExistsError("동명 복구 사본 폴더가 있습니다. 기존 내용을 덮어쓰지 않습니다.")
    inspection, snapshots = _validated_snapshot(path)
    # Everything is validated before the first write.
    _safe_path(target)
    target.mkdir(mode=0o700, exist_ok=False)
    try:
        for name, raw in snapshots.items():
            # name comes exclusively from a fixed allowlist, not arbitrary ZIP paths.
            if name not in ALLOWED_MEMBERS:
                raise ValueError("허용되지 않은 복구 파일 경로입니다.")
            output = target.joinpath(*name.split("/"))
            output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            _safe_path(output)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_BINARY"):
                flags |= os.O_BINARY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            with os.fdopen(os.open(output, flags, 0o600), "wb") as stream:
                stream.write(raw)
        note = (
            "AISTING 19단계 복구 준비 사본 (자동 복원 아님)\n"
            "이 폴더의 파일은 실행 중인 앱 설정/SQLite/기획안에 자동 적용되지 않습니다.\n"
            "필요한 파일을 직접 검토한 후 별도 사용자 승인 절차로 처리하세요.\n"
            "SQLite 기억/채팅 로그/PC 사양/승인 기록은 포함되지 않습니다.\n"
            f"검증한 파일 수: {len(inspection.members)}\n"
        ).encode("utf-8")
        with (target / NOTE_NAME).open("xb") as stream:
            stream.write(note)
    except BaseException:
        # No preexisting files were present: only clean up our own new folder.
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        raise
    return target
