"""18단계: 사용자가 직접 선택해 실행하는 로컬 기획안·설정 사본 보관.

실행 전 자동 조회/백업/복원 없음. 원본을 변경하지 않고, 새 ZIP만 생성한다.
19단계의 정기 백업·복구 기능이나 사용자 PC 승인으로 간주하지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .development_review import bundled_project_root
from .offline_settings import settings_file, validate_settings, _migrate_legacy_voice, _migrate_legacy_v05
from .runtime_profile import load_profile, profile_path

MAX_SOURCE_BYTES = 1_048_576
MAX_ARCHIVE_BYTES = 5_242_880
MANIFEST = "manifest.json"
# Archive member names are fixed, not derived from external paths.
PROJECT_ITEMS = (
    ("기획안 원본", "docs/ORIGINAL_PLAN.txt"),
    ("요구사항", "config/requirements.json"),
    ("개발 로드맵", "config/roadmap.json"),
)
USER_ITEMS = (
    ("방송 선택 설정", "settings.json"),
    ("수동 실행 환경", "runtime_operator_profile.json"),
)


@dataclass(frozen=True)
class ArchivePlan:
    sources: tuple[tuple[str, Path], ...]

    def describe(self) -> str:
        return (
            "18단계 · 기획안과 설정 파일 보관 (수동, 오프라인)\n"
            + "\n".join("- " + name for name, _ in self.sources)
            + "\n\n새 ZIP 생성은 '보관 ZIP 만들기' 클릭과 확인 후에만 수행합니다.\n"
              "원본은 수정/삭제하지 않으며, 기존 ZIP도 덮어쓰지 않습니다.\n"
              "설정 파일은 사용자가 체크한 경우에만 포함합니다.\n"
              "채팅/SQLite 기억·PC 사양·계정 정보는 자동 포함하지 않습니다.\n"
              "압축파일에는 선택 설정이 포함될 수 있으니 공유에 주의하세요.\n"
              "복구·정기 백업·승인 완료·설치·방송 실행을 의미하지 않습니다."
        )


def plan_archive(*, project_root: Path | None = None, settings: Path | None = None,
                 runtime: Path | None = None, include_settings: bool = False,
                 include_runtime: bool = False) -> ArchivePlan:
    """Pure plan: no file read, stat, network, installation or PC probe."""
    root = Path(project_root) if project_root is not None else bundled_project_root()
    items = [(label, root / rel) for label, rel in PROJECT_ITEMS]
    if include_settings:
        items.append((USER_ITEMS[0][0], Path(settings) if settings is not None else settings_file()))
    if include_runtime:
        items.append((USER_ITEMS[1][0], Path(runtime) if runtime is not None else profile_path()))
    return ArchivePlan(tuple(items))


def _safe_path(path: Path) -> None:
    for item in (path, *path.parents):
        if item.is_symlink() or bool(getattr(item, "is_junction", lambda: False)()):
            raise ValueError("심볼릭 링크/정션 경로는 사용하지 않습니다.")
        try:
            info = item.lstat()
        except (FileNotFoundError, NotADirectoryError):
            continue
        if getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError("재분석 지점 경로는 사용하지 않습니다.")


def _read_source(label: str, source: Path) -> bytes:
    _safe_path(source)
    if not source.is_file():
        raise ValueError(f"{label}: 일반 파일이 없거나 접근할 수 없습니다.")
    if source.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError(f"{label}: 허용 크기를 초과했습니다.")
    with source.open("rb") as stream:
        data = stream.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError(f"{label}: 허용 크기를 초과했습니다.")
    if label == "기획안 원본":
        data.decode("utf-8")
    elif label in ("요구사항", "개발 로드맵"):
        if not isinstance(json.loads(data.decode("utf-8")), dict):
            raise ValueError(f"{label}: JSON 객체가 아닙니다.")
    elif label == "방송 선택 설정":
        validate_settings(_migrate_legacy_voice(_migrate_legacy_v05(json.loads(data.decode("utf-8")))))
    elif label == "수동 실행 환경":
        # Existing validator rejects foreign/remote/automatic runtime profiles.
        if load_profile(source) is None:
            raise ValueError("수동 실행 환경 파일이 없습니다.")
    return data


def _member(label: str) -> str:
    if label == "기획안 원본":
        return "project/docs/ORIGINAL_PLAN.txt"
    if label == "요구사항":
        return "project/config/requirements.json"
    if label == "개발 로드맵":
        return "project/config/roadmap.json"
    if label == "방송 선택 설정":
        return "operator/settings.json"
    if label == "수동 실행 환경":
        return "operator/runtime_operator_profile.json"
    raise ValueError("알 수 없는 보관 항목")


def create_archive(plan: ArchivePlan, destination: Path, *, confirmed: bool = False) -> Path:
    if not confirmed:
        raise PermissionError("사용자 확인 없이 ZIP을 생성하지 않습니다.")
    if not isinstance(plan, ArchivePlan):
        raise TypeError("보관 계획이 올바르지 않습니다.")
    labels = tuple(label for label, _ in plan.sources)
    allowed = {label for label, _ in PROJECT_ITEMS + USER_ITEMS}
    if len(labels) != len(set(labels)) or labels[:3] != tuple(label for label, _ in PROJECT_ITEMS) or not set(labels) <= allowed:
        raise ValueError("보관 항목 구성이 올바르지 않습니다.")
    target = Path(destination)
    _safe_path(target)
    if target.suffix.lower() != ".zip" or not target.name.strip() or not target.parent.is_dir():
        raise ValueError("존재하는 폴더 안의 새 .zip 파일을 선택해 주세요.")
    if target.exists() or target.is_symlink():
        raise FileExistsError("기존 ZIP은 덮어쓰지 않습니다. 새 이름을 선택해 주세요.")
    snapshots = []
    total = 0
    for label, source in plan.sources:
        raw = _read_source(label, Path(source))
        total += len(raw)
        if total > MAX_ARCHIVE_BYTES:
            raise ValueError("보관 자료의 총 크기가 허용 범위를 넘었습니다.")
        snapshots.append((_member(label), raw))
    manifest = {
        "schema_version": 1,
        "purpose": "manual_offline_archive_not_restore_or_approval",
        "entries": [{"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                    for name, raw in snapshots],
    }
    # O_EXCL avoids overwriting an archive even if it appears between validation and opening.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as output:
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, raw in snapshots:
                    archive.writestr(name, raw)
                archive.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        verify_archive(target)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target


def verify_archive(path: Path) -> dict:
    """Read-only bounded ZIP validation: fixed members, sizes, hashes and CRC.

    Never extract ZIP paths or trust uncompressed size claims without a read limit.
    """
    _safe_path(Path(path))
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or MANIFEST not in names or not 4 <= len(names) <= 6:
            raise ValueError("ZIP 항목 구성이 올바르지 않습니다.")
        allowed = {_member(label) for label, _ in PROJECT_ITEMS + USER_ITEMS}
        required = {_member(label) for label, _ in PROJECT_ITEMS}
        if not required <= set(names) or not set(names) <= allowed | {MANIFEST}:
            raise ValueError("ZIP에 필수 자료가 없거나 허용되지 않은 항목이 있습니다.")
        total_size = 0
        for info in infos:
            # ZIP external attributes can mark an entry as a symbolic link.
            if (info.flag_bits & 1 or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                    or ((info.external_attr >> 16) & 0o170000) == 0o120000
                    or info.is_dir()):
                raise ValueError("ZIP에 암호화/링크/허용되지 않은 항목이 있습니다.")
            limit = 4096 if info.filename == MANIFEST else MAX_SOURCE_BYTES
            if info.file_size > limit or info.file_size < 0:
                raise ValueError("ZIP 파일 크기가 허용 범위를 넘었습니다.")
            total_size += info.file_size
        if total_size > MAX_ARCHIVE_BYTES:
            raise ValueError("ZIP 전체 크기가 허용 범위를 넘었습니다.")
        with archive.open(MANIFEST) as stream:
            raw_manifest = stream.read(4097)
        if len(raw_manifest) > 4096:
            raise ValueError("ZIP 목록이 너무 큽니다.")
        manifest = json.loads(raw_manifest.decode("utf-8"))
        if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1
                or manifest.get("purpose") != "manual_offline_archive_not_restore_or_approval"
                or not isinstance(manifest.get("entries"), list)):
            raise ValueError("ZIP 목록 형식이 올바르지 않습니다.")
        entries = manifest["entries"]
        if not all(isinstance(entry, dict) and set(entry) == {"name", "bytes", "sha256"}
                   and isinstance(entry["name"], str) and type(entry["bytes"]) is int
                   and isinstance(entry["sha256"], str) and len(entry["sha256"]) == 64
                   and all(char in "0123456789abcdef" for char in entry["sha256"])
                   for entry in entries):
            raise ValueError("ZIP 목록 항목이 올바르지 않습니다.")
        expected = [entry["name"] for entry in entries]
        if len(expected) != len(set(expected)) or set(names) != set(expected) | {MANIFEST}:
            raise ValueError("ZIP 목록과 실제 파일이 다릅니다.")
        for entry in entries:
            if entry["name"] not in allowed or entry["bytes"] < 0 or entry["bytes"] > MAX_SOURCE_BYTES:
                raise ValueError("ZIP 파일 크기/경로가 허용 범위를 넘었습니다.")
            with archive.open(entry["name"]) as stream:
                data = stream.read(MAX_SOURCE_BYTES + 1)
            # Reading through the end checks ZIP CRC as well as our own SHA256.
            if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError("ZIP 파일 내용 또는 SHA256이 일치하지 않습니다.")
    return manifest
