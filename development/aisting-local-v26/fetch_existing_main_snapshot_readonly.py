"""Fetch a PINNED snapshot of the EXISTING AISTING main source, read-only.

This is a source-retrieval helper, NOT a replacement project or an installer.
Only public HTTPS GET to the known GitHub codeload host; never uses GitHub
write APIs, credentials, models, pip, git clone, OBS or broadcast platforms.

The default --check does NOT contact the network or create files. --fetch is
an explicit source-copy operation and fails closed on any mismatch. The
result is a *snapshot*; use prepare_local_source_copy.py to create a separate
editable development copy before applying the v9 patch.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
from urllib.error import URLError, HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile

from apply_to_existing_aisting import BASELINE_DESKTOP_SHA, git_blob_sha
from prepare_local_source_copy import REQUIRED

PINNED_MAIN_COMMIT = '2269205998201165e024a22d0adef576e6cac0c6'
REPO = 'junggyeol4444/AISTING'
ARCHIVE_URL = f'https://codeload.github.com/{REPO}/zip/{PINNED_MAIN_COMMIT}'
MAX_ARCHIVE_BYTES = 80 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 350 * 1024 * 1024
MAX_SINGLE_FILE_BYTES = 80 * 1024 * 1024
MAX_FILE_COUNT = 6000
SNAPSHOT_RECORD = '.aisting_readonly_main_snapshot.json'


class SnapshotError(RuntimeError):
    """Source snapshot could not be verified; no partial copy is retained."""


class _ApprovedGitHubRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != 'https' or parsed.hostname not in ('codeload.github.com',):
            raise SnapshotError('허용되지 않은 GitHub 다운로드 리다이렉트: ' + parsed.hostname.__str__())
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_pinned_archive() -> bytes:
    """Read only a bounded public GitHub source ZIP; no GitHub writes."""
    request = Request(ARCHIVE_URL, headers={
        'User-Agent': 'AISTING-existing-main-local-readonly-source-snapshot',
        'Accept': 'application/zip',
    }, method='GET')
    opener = build_opener(_ApprovedGitHubRedirect())
    with opener.open(request, timeout=30) as response:
        if response.status != 200:
            raise SnapshotError('공개 GitHub 소스 응답 HTTP ' + str(response.status))
        content = response.read(MAX_ARCHIVE_BYTES + 1)
    if len(content) > MAX_ARCHIVE_BYTES:
        raise SnapshotError('기존 소스 ZIP 크기 제한 초과')
    if not content.startswith(b'PK\x03\x04'):
        raise SnapshotError('GitHub가 ZIP 파일을 반환하지 않았습니다.')
    return content


def _safe_member(info: zipfile.ZipInfo, expected_root: str) -> tuple[str, bool]:
    name = info.filename
    if (not name or '\\' in name or '\x00' in name or any(ord(c) < 32 for c in name)
            or name.startswith('/') or '//' in name):
        raise SnapshotError('위험한 ZIP 파일 이름을 거부했습니다.')
    parts = name.rstrip('/').split('/')
    if (not parts or parts[0] != expected_root
            or any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in parts)):
        raise SnapshotError('GitHub 소스 ZIP 경로/커밋 루트가 예상과 다릅니다.')
    if len(parts) == 1:
        if not info.is_dir():
            raise SnapshotError('소스 ZIP 루트가 디렉터리가 아닙니다.')
        return '', True
    rel = '/'.join(parts[1:])
    # Prevent Windows path aliases/ADS/reserved device names, too.
    for p in parts[1:]:
        if ':' in p or p.split('.')[0].casefold() in {
            'con', 'prn', 'aux', 'nul', *('com' + str(i) for i in range(1, 10)),
            *('lpt' + str(i) for i in range(1, 10))
        }:
            raise SnapshotError('Windows에서 위험한 소스 파일 이름: ' + rel)
    if PurePosixPath(rel).is_absolute() or '.git' in parts[1:]:
        raise SnapshotError('소스 ZIP에서 허용하지 않는 경로: ' + rel)
    mode = (info.external_attr >> 16) & 0xffff
    filetype = stat.S_IFMT(mode)
    if filetype not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise SnapshotError('링크 또는 특수 파일을 거부했습니다: ' + rel)
    if info.flag_bits & 1:
        raise SnapshotError('암호화된 ZIP 항목은 허용하지 않습니다.')
    if info.is_dir() != (filetype == stat.S_IFDIR) and filetype != 0:
        raise SnapshotError('ZIP 파일 유형이 일치하지 않습니다: ' + rel)
    return rel, info.is_dir()


def extract_pinned_snapshot(archive: bytes, destination: Path, *,
                            commit: str = PINNED_MAIN_COMMIT,
                            expected_desktop_sha: str = BASELINE_DESKTOP_SHA) -> Path:
    """Verify ZIP before writes; atomically reject and clean partial snapshots.

    This function can also be tested with a small synthetic archive, which
    does NOT constitute real AISTING integration validation.
    """
    if not isinstance(archive, bytes) or len(archive) > MAX_ARCHIVE_BYTES:
        raise SnapshotError('압축 원본 크기가 허용 범위를 벗어났습니다.')
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise SnapshotError('고정 커밋 식별자가 올바르지 않습니다.')
    if destination.is_symlink() or destination.exists():
        raise SnapshotError('원본/기존 파일을 덮어쓰지 않습니다. 새 사본 경로를 선택하세요.')
    target = destination.expanduser().absolute()
    if (not target.parent.is_dir() or target.parent.is_symlink()
            or any(parent.is_symlink() for parent in target.parents)):
        raise SnapshotError('사본 상위 경로에 링크가 있거나 실제 디렉터리가 없습니다.')
    root_name = 'AISTING-' + commit
    try:
        z = zipfile.ZipFile(io.BytesIO(archive))
    except (zipfile.BadZipFile, OSError) as exc:
        raise SnapshotError('기존 AISTING 소스 ZIP을 열 수 없습니다.') from exc
    with z:
        files: dict[str, zipfile.ZipInfo] = {}
        directories: set[str] = set()
        seen: set[str] = set()
        canonical_paths: dict[str, str] = {}
        total = 0
        for info in z.infolist():
            rel, isdir = _safe_member(info, root_name)
            if not rel:
                continue
            # Windows folds directory names too, even if the ZIP omitted
            # explicit directory entries. Refuse silently merged folders.
            pieces = rel.split('/')
            for i in range(1, len(pieces) + 1):
                segment = '/'.join(pieces[:i])
                folded = segment.casefold()
                old = canonical_paths.setdefault(folded, segment)
                if old != segment:
                    raise SnapshotError('ZIP 경로의 Windows 대소문자 충돌: ' + rel)
            alias = rel.casefold()
            if alias in seen:
                raise SnapshotError('ZIP 중복 또는 Windows 대소문자 충돌: ' + rel)
            seen.add(alias)
            if isdir:
                directories.add(rel)
                continue
            if info.file_size > MAX_SINGLE_FILE_BYTES:
                raise SnapshotError('단일 파일 크기 제한 초과: ' + rel)
            total += info.file_size
            if total > MAX_UNCOMPRESSED_BYTES or len(files) >= MAX_FILE_COUNT:
                raise SnapshotError('전체 파일 크기 또는 개수 제한 초과')
            files[rel] = info
        missing = [p.as_posix() for p in REQUIRED if p.as_posix() not in files]
        if missing:
            raise SnapshotError('기존 AISTING 필수 파일 누락: ' + ', '.join(missing))
        if SNAPSHOT_RECORD in files:
            raise SnapshotError('소스에 기존 사본 기록과 충돌하는 파일이 있습니다.')
        # Validate directory/file collisions before creating the target.
        for rel in files:
            if rel in directories:
                raise SnapshotError('동일한 경로가 파일과 디렉터리로 등록됨: ' + rel)
            parent = PurePosixPath(rel).parent
            while str(parent) != '.':
                if str(parent) in files:
                    raise SnapshotError('파일 아래에 다른 ZIP 항목이 존재함: ' + rel)
                parent = parent.parent
        target.mkdir(mode=0o700)
        try:
            digests: dict[str, str] = {}
            for rel, info in files.items():
                output = target.joinpath(*PurePosixPath(rel).parts)
                output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                digest = hashlib.sha256()
                length = 0
                with z.open(info, 'r') as source, output.open('xb') as sink:
                    while True:
                        chunk = source.read(128 * 1024)
                        if not chunk:
                            break
                        length += len(chunk)
                        if length > info.file_size or length > MAX_SINGLE_FILE_BYTES:
                            raise SnapshotError('압축 해제 중 파일 크기 제한 초과: ' + rel)
                        sink.write(chunk)
                        digest.update(chunk)
                    sink.flush()
                    os.fsync(sink.fileno())
                if length != info.file_size:
                    raise SnapshotError('압축 해제 파일 크기가 다릅니다: ' + rel)
                digests[rel] = digest.hexdigest()
            desktop = (target / 'src/ai_broadcaster/desktop.py').read_bytes()
            if git_blob_sha(desktop) != expected_desktop_sha:
                raise SnapshotError('GitHub main의 기존 desktop.py SHA 불일치. 새 코드로 대체하지 않습니다.')
            record = {
                'purpose': 'READ-ONLY public GitHub main source snapshot of EXISTING AISTING',
                'repository': REPO,
                'pinned_main_commit': commit,
                'desktop_git_blob_sha': expected_desktop_sha,
                'archive_sha256': hashlib.sha256(archive).hexdigest(),
                'files': digests,
                'github_write': False,
                'installed_or_broadcast': False,
                'full_windows_exe_built': False,
            }
            path = target / SNAPSHOT_RECORD
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                json.dump(record, out, ensure_ascii=False, indent=2)
                out.flush()
                os.fsync(out.fileno())
            return target
        except Exception:
            shutil.rmtree(target)
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description='기존 AISTING main 소스 읽기 전용 로컬 사본 확보')
    parser.add_argument('--destination', type=Path, required=True,
                        help='기존 원본과 다른 새 로컬 폴더 (기존 파일 덮어쓰기 금지)')
    parser.add_argument('--fetch', action='store_true',
                        help='명시적으로 공개 GitHub 소스 ZIP을 읽기 전용 GET으로 받아 새 폴더에 복제')
    args = parser.parse_args()
    print('기존 AISTING main 고정 커밋:', PINNED_MAIN_COMMIT)
    print('기존 desktop.py Git blob SHA:', BASELINE_DESKTOP_SHA)
    print('조회 대상(읽기 전용):', ARCHIVE_URL)
    print('로컬 사본 대상:', args.destination)
    if not args.fetch:
        print('검토 모드: 네트워크 요청·파일 변경 없음. --fetch 없이는 다운로드하지 않습니다.')
        return 0
    try:
        archive = fetch_pinned_archive()
        result = extract_pinned_snapshot(archive, args.destination)
        print('기존 프로그램 소스 사본 확보:', result)
        print('이 폴더는 수정하지 말고 prepare_local_source_copy.py로 별도 개발 사본을 만드세요.')
        return 0
    except (OSError, URLError, HTTPError, SnapshotError, zipfile.BadZipFile) as exc:
        print('원본 소스 확보 실패:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
