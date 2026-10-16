"""Prepare a private local COPY of the existing AISTING source (not a new app).

No network, GitHub write, installation, streaming or user-data mutation.
Preview by default. --copy is a separate, explicit filesystem action.
Refuses links and special files to avoid copying outside the selected tree.
The .git metadata directory is deliberately excluded; all existing program
files, including user configuration and 100-step records, are copied intact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from contextlib import contextmanager
import stat
import sys

from apply_to_existing_aisting import BASELINE_DESKTOP_SHA, SOURCE_REL, git_blob_sha

REQUIRED = (
    SOURCE_REL,
    Path('scripts/run_desktop.py'),
    Path('docs/ORIGINAL_PLAN.txt'),
    Path('docs/ROADMAP_100.md'),
    Path('config/roadmap.json'),
    Path('docs/REQUIREMENTS.md'),
    Path('docs/STATUS.md'),
)
PROVENANCE = '.aisting_local_copy_provenance.json'


@contextmanager
def _safe_regular_source(root: Path, relative: Path):
    """Read one existing file without following symlinks on POSIX.

    On Windows, Python does not expose equivalent portable directory handles;
    inspect every ancestor and the opened file and recheck the full tree.
    """
    pieces = relative.parts
    if not pieces or any(p in ('.', '..', '') for p in pieces):
        raise ValueError('원본 파일의 상대 경로가 올바르지 않습니다.')
    if os.name == 'posix' and hasattr(os, 'O_NOFOLLOW'):
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in pieces[:-1]:
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            file_fd = os.open(pieces[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        finally:
            os.close(fd)
        with os.fdopen(file_fd, 'rb') as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise ValueError('원본 파일이 일반 파일이 아닙니다: ' + relative.as_posix())
            yield handle
    else:
        candidate = root
        for part in pieces:
            candidate = candidate / part
            if candidate.is_symlink():
                raise ValueError('원본 파일 경로에 링크가 있습니다: ' + relative.as_posix())
        with candidate.open('rb') as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise ValueError('원본 파일이 일반 파일이 아닙니다: ' + relative.as_posix())
            yield handle


def _sha_stream(handle) -> str:
    digest = hashlib.sha256()
    for block in iter(lambda: handle.read(1024 * 1024), b''):
        digest.update(block)
    return digest.hexdigest()


def _check_source(source: Path) -> tuple[Path, dict[str, str], dict[str, str], list[str]]:
    if source.is_symlink() or not source.is_dir():
        raise ValueError('기존 AISTING 소스 폴더는 실제 디렉터리여야 합니다.')
    root = source.resolve(strict=True)
    inventory: dict[str, str] = {}
    directories: list[str] = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        here = Path(directory)
        # Git metadata is deliberately excluded from the private copy.
        if here == root:
            dirs[:] = [name for name in dirs if name != '.git']
            files = [name for name in files if name != '.git']
        for name in dirs + files:
            item = here / name
            relative = item.relative_to(root)
            mode = item.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ValueError('링크/특수 파일이 있어 안전한 복사를 중단합니다: ' + str(relative))
            if stat.S_ISDIR(mode):
                directories.append(relative.as_posix())
            else:
                with _safe_regular_source(root, relative) as handle:
                    inventory[relative.as_posix()] = _sha_stream(handle)
    checks: dict[str, str] = {}
    for rel in REQUIRED:
        key = rel.as_posix()
        if key not in inventory:
            raise ValueError('기존 프로그램 필수 파일이 없습니다: ' + key)
        checks[key] = inventory[key]
    with _safe_regular_source(root, SOURCE_REL) as handle:
        original = handle.read()
    if git_blob_sha(original) != BASELINE_DESKTOP_SHA:
        raise ValueError('기존 desktop.py의 Git blob SHA가 검증된 main 원본과 다릅니다.')
    return root, checks, inventory, sorted(directories)


def _copy_exact_inventory(root: Path, target: Path, files: dict[str, str], directories: list[str]) -> None:
    """Copy only the inventoried paths, never a newly introduced source link.

    No copytree traversal of a source that could have changed to a symlink
    between inspection and copy. The destination is a newly-created folder.
    """
    for rel in sorted(directories, key=lambda v: (v.count('/'), v)):
        dest = target / Path(rel)
        dest.mkdir(mode=0o700)
    for rel, expected in sorted(files.items()):
        relative = Path(rel)
        dest = target / relative
        with _safe_regular_source(root, relative) as source:
            source_stat = os.fstat(source.fileno())
            digest = hashlib.sha256()
            with dest.open('xb') as output:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    output.write(block)
                    digest.update(block)
                output.flush()
                os.fsync(output.fileno())
        if digest.hexdigest() != expected:
            raise RuntimeError('복사 중 원본 파일 내용이 변경되었습니다: ' + rel)
        os.chmod(dest, stat.S_IMODE(source_stat.st_mode))
    # Directory permissions can be restored after creating their children.
    for rel in sorted(directories, key=lambda v: (-v.count('/'), v)):
        directory = root / rel
        if directory.is_symlink() or not directory.is_dir():
            raise RuntimeError('복사 중 원본 폴더가 변경되었습니다: ' + rel)
        os.chmod(target / rel, stat.S_IMODE(directory.stat().st_mode))

def _discard_failed_copy(target: Path) -> None:
    """Remove only the new private destination, even if a copied folder is read-only."""
    def _make_writable_and_retry(func, name, _exc):
        if Path(name).is_symlink():
            raise RuntimeError('실패한 사본에 예상하지 못한 링크가 있습니다. 수동 확인 필요: ' + str(name))
        os.chmod(name, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        func(name)
    shutil.rmtree(target, onexc=_make_writable_and_retry)


def prepare_copy(source: Path, destination: Path, *, write: bool = False) -> Path:
    root, checks, inventory, directories = _check_source(source)
    if destination.is_symlink() or destination.exists():
        raise ValueError('복사 대상이 이미 존재합니다. 덮어쓰지 않습니다.')
    target = destination.expanduser().absolute()
    if target == root or root in target.parents or target in root.parents:
        raise ValueError('원본 내부/상위에는 사본을 만들 수 없습니다.')
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise ValueError('복사 대상의 상위 폴더가 실제로 존재해야 합니다.')
    print('확인된 기존 원본:', root)
    print('원본 desktop.py Git blob SHA:', BASELINE_DESKTOP_SHA)
    print('복사 대상:', target)
    print('기존 소스/설정/기억/100단계 기록 유지, .git 메타데이터만 제외')
    if not write:
        print('읽기 전용 검사 완료. --copy 없이는 파일을 생성하지 않습니다.')
        return target
    # 0700 prevents other users from traversing private settings or data.
    target.mkdir(mode=0o700)
    try:
        _copy_exact_inventory(root, target, inventory, directories)
        # copytree copies the original directory mode: reassert privacy.
        os.chmod(target, 0o700)
        # Detect file AND empty-directory changes during copying.
        _, _, source_after, dirs_after = _check_source(root)
        if source_after != inventory or dirs_after != directories:
            raise RuntimeError('복사 중 원본 파일/폴더가 변경되었습니다. 사본을 폐기합니다.')
        _, _, copied_after, copied_dirs = _check_source(target)
        if copied_after != inventory or copied_dirs != directories:
            raise RuntimeError('복제 후 파일/폴더 무결성이 다릅니다. 사본을 폐기합니다.')
        # v12: preserve a digest for EVERY existing file, not only seven
        # entry points. The patcher re-verifies this entire manifest before
        # writing, so changed memory, settings, and legacy modules fail closed.
        proof = {'purpose': 'local copy of EXISTING AISTING, no github write',
                 'desktop_git_blob_sha': BASELINE_DESKTOP_SHA,
                 'original_required_sha256': checks,
                 'original_all_sha256': inventory,
                 'original_all_directories': directories,
                 'all_existing_files_verified': len(inventory),
                 'all_existing_directories_verified': len(directories),
                 'github_metadata_copied': False,
                 'full_windows_exe_built': False,
                 'actual_ai_voice_avatar_obs_tested': False}
        proof_file = target / PROVENANCE
        fd = os.open(proof_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(proof, output, ensure_ascii=False, indent=2)
            output.flush()
            os.fsync(output.fileno())
        print('기존 프로그램 로컬 사본 준비 완료. 원본 파일 변경 없음.')
        return target
    except Exception:
        _discard_failed_copy(target)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description='기존 AISTING 로컬 개발 사본 생성 (기본 읽기 전용)')
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--copy', action='store_true', help='명시적으로 로컬 사본 생성')
    args = parser.parse_args()
    try:
        prepare_copy(args.source, args.destination, write=args.copy)
    except (OSError, ValueError, RuntimeError) as exc:
        print('로컬 사본 준비 중단:', exc, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
