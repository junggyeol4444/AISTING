"""16단계: 사용자가 직접 지정·확인한 위치에만 로컬 개발 작업 폴더를 구성한다.

미리보기는 순수 계산이며, 명시적 확인 없는 생성/설치/백업/PC 검색은 없다.
기존 파일을 덮어쓰지 않고, 다른 프로그램 폴더를 작업 공간으로 오인하지 않는다.
"""
from __future__ import annotations

import json
import stat
from dataclasses import dataclass
from pathlib import Path


WORKSPACE_NAME = "AISTING_Workspace"
SUBFOLDERS = ("source", "backups", "exports", "logs", "notes")
MANIFEST_NAME = "workspace_manifest.json"
MANIFEST = {
    "app": "AISTING",
    "schema_version": 1,
    "purpose": "local_development_workspace",
    "folders": list(SUBFOLDERS),
}


@dataclass(frozen=True)
class WorkspacePlan:
    parent: Path
    root: Path
    subfolders: tuple[str, ...] = SUBFOLDERS

    def describe(self) -> str:
        return (
            "16단계 · 로컬 개발용 작업 공간 계획 (미리보기)\n"
            f"선택한 상위 폴더: {self.parent}\n"
            f"생성할 작업 공간: {self.root}\n"
            "내부 폴더: " + ", ".join(self.subfolders) + "\n"
            f"식별 파일: {MANIFEST_NAME}\n\n"
            "미리보기는 PC 파일을 읽거나 생성하지 않습니다.\n"
            "[작업 공간 생성]을 누르고 별도로 확인해야 폴더를 만듭니다.\n"
            "기존 파일을 덮어쓰거나 삭제하지 않습니다.\n"
            "backups 폴더는 백업을 담을 자리일 뿐, 실제 백업은 아직 하지 않습니다.\n"
            "프로그램 설치·외부 서버 연결·방송 시작·10/15단계 승인과 무관합니다."
        )


def workspace_plan(parent_text: str) -> WorkspacePlan:
    """I/O 없이 사용자 입력을 경로 계획으로 변환한다."""
    if not isinstance(parent_text, str) or not parent_text.strip():
        raise ValueError("먼저 작업 공간을 둘 상위 폴더를 직접 선택해 주세요.")
    if len(parent_text) > 4096 or any(ord(c) < 32 for c in parent_text):
        raise ValueError("경로에 사용할 수 없는 문자가 있습니다.")
    raw = parent_text.strip()
    parent = Path(raw)
    if not parent.is_absolute() or ".." in parent.parts:
        raise ValueError("상위 폴더는 '..'가 없는 절대 경로여야 합니다.")
    if parent == Path(parent.anchor):
        raise ValueError("드라이브/파일시스템 루트는 상위 폴더로 선택할 수 없습니다.")
    return WorkspacePlan(parent=parent, root=parent / WORKSPACE_NAME)


def _is_link_or_junction(path: Path) -> bool:
    if path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)()):
        return True
    # Python 3.11 on Windows does not expose Path.is_junction().
    # Reject other reparse points as well rather than traversing them.
    try:
        info = path.lstat()
    except (FileNotFoundError, NotADirectoryError):
        return False
    return bool(getattr(info, "st_file_attributes", 0) &
                getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _assert_no_link_ancestors(path: Path) -> None:
    for candidate in (path, *path.parents):
        if _is_link_or_junction(candidate):
            raise ValueError(f"심볼릭 링크/정션 경로는 작업 공간에 사용할 수 없습니다: {candidate}")


def create_workspace(plan: WorkspacePlan, *, confirmed: bool = False) -> Path:
    """확인한 사용자의 선택 경로만 생성. 기존 폴더·파일·설정을 보존한다.

    식별 파일이 없는 비어 있지 않은 동명 폴더에는 절대 손대지 않는다.
    식별 파일이 있으면 내용을 검증하고 누락된 작업 폴더만 보충한다.
    """
    if not confirmed:
        raise PermissionError("사용자 명시적 확인 없이는 작업 공간을 만들지 않습니다.")
    if not isinstance(plan, WorkspacePlan) or plan != workspace_plan(str(plan.parent)):
        raise ValueError("작업 공간 계획이 유효하지 않습니다.")
    parent, root = plan.parent, plan.root
    _assert_no_link_ancestors(parent)
    if not parent.is_dir():
        raise ValueError("선택한 상위 폴더가 존재하지 않거나 폴더가 아닙니다.")
    if _is_link_or_junction(root):
        raise ValueError("동명 작업 공간이 링크/정션이므로 사용하지 않습니다.")
    if root.exists() and not root.is_dir():
        raise ValueError("동명 파일이 있어 작업 공간을 만들 수 없습니다.")

    marker = root / MANIFEST_NAME
    if root.exists():
        if _is_link_or_junction(marker):
            raise ValueError("식별 파일이 링크이므로 사용하지 않습니다.")
        if marker.exists():
            if not marker.is_file() or marker.stat().st_size > 4096:
                raise ValueError("기존 작업 공간 식별 파일이 유효하지 않습니다.")
            try:
                existing = json.loads(marker.read_text(encoding="utf-8"))
            except (UnicodeError, ValueError, OSError) as exc:
                raise ValueError("기존 작업 공간 식별 파일을 읽을 수 없습니다.") from exc
            if existing != MANIFEST:
                raise ValueError("다른 작업 공간이므로 기존 내용을 변경하지 않습니다.")
        elif any(root.iterdir()):
            raise ValueError("동명 폴더에 기존 파일이 있습니다. 덮어쓰지 않습니다.")
        for name in SUBFOLDERS:
            child = root / name
            if _is_link_or_junction(child) or (child.exists() and not child.is_dir()):
                raise ValueError(f"기존 항목과 충돌하여 중단합니다: {name}")

    # 모든 기존 항목을 먼저 검증한 후에만 쓰기를 시작한다.
    root.mkdir(exist_ok=True)
    for name in SUBFOLDERS:
        (root / name).mkdir(exist_ok=True)
    if not marker.exists():
        # 'x' 모드: 같은 이름의 기존 파일을 절대 덮어쓰지 않는다.
        with marker.open("x", encoding="utf-8") as stream:
            json.dump(MANIFEST, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    return root
