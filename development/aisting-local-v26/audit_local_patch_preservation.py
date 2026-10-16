"""Read-only post-apply audit of the EXISTING AISTING source copy.

Compares every pre-copy file with the recorded SHA-256. The only permitted
changes are the exact desktop.py and offline_settings.py patches, their two
byte-identical private backups, and the integration modules in this package. This is a
source/data preservation audit, NOT evidence of actual AI/voice/live broadcast.

Never touches GitHub, executes the application, writes files or reads user
settings into logs. The provenance file is an accident-prevention marker,
not a cryptographic attestation against a malicious local editor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

from apply_to_existing_aisting import (
    BASELINE_DESKTOP_SHA, BASELINE_OFFLINE_SHA, SOURCE_REL, OFFLINE_SETTINGS_REL,
    MODULE_REL, EXTRA_MODULES, git_blob_sha, modify_existing_desktop,
    modify_existing_offline_settings,
)
from prepare_local_source_copy import PROVENANCE

PACKAGE = Path(__file__).resolve().parent
MODULES = (MODULE_REL, *EXTRA_MODULES)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inventory(root: Path) -> tuple[dict[str, str], set[str]]:
    found: dict[str, str] = {}
    directories: set[str] = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            file = Path(directory) / name
            rel = file.relative_to(root).as_posix()
            mode = file.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ValueError('로컬 사본에 링크 또는 특수 파일이 있습니다: ' + rel)
            if stat.S_ISDIR(mode):
                directories.add(rel)
            if stat.S_ISREG(mode):
                found[rel] = _sha(file.read_bytes())
    return found, directories


def audit_applied_copy(root: Path) -> dict[str, object]:
    """Return verified counts or raise; never modify the provided source copy."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError('실제 로컬 사본 폴더가 아닙니다.')
    root = root.resolve(strict=True)
    if (root / '.git').exists() or (root / '.git').is_symlink():
        raise ValueError('Git 작업 폴더는 감사 대상이 아닙니다.')
    marker = root / PROVENANCE
    if marker.is_symlink() or not marker.is_file():
        raise ValueError('검증된 사본 출처 기록이 없습니다.')
    record = json.loads(marker.read_text(encoding='utf-8'))
    if not isinstance(record, dict) or record.get('purpose') != 'local copy of EXISTING AISTING, no github write':
        raise ValueError('기존 AISTING 사본 기록이 아닙니다.')
    baseline = record.get('original_all_sha256')
    if not isinstance(baseline, dict) or not baseline or record.get('all_existing_files_verified') != len(baseline):
        raise ValueError('전체 기존 파일의 해시 기록이 없습니다.')
    for rel, digest in baseline.items():
        if (not isinstance(rel, str) or not rel or '\\' in rel or '\x00' in rel
                or PurePosixPath(rel).is_absolute()
                or any(p in ('', '.', '..') for p in rel.split('/'))
                or rel.startswith('.git/') or rel == PROVENANCE
                or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)):
            raise ValueError('사본 기록의 파일 이름/해시가 올바르지 않습니다.')
    if record.get('desktop_git_blob_sha') != BASELINE_DESKTOP_SHA:
        raise ValueError('검증된 원본 desktop.py 버전이 다릅니다.')
    desktop = SOURCE_REL.as_posix()
    offline = OFFLINE_SETTINGS_REL.as_posix()
    if desktop not in baseline or offline not in baseline:
        raise ValueError('원본 desktop.py/offline_settings.py 파일 해시가 없습니다.')
    for module in MODULES:
        if module.as_posix() in baseline:
            raise ValueError('원본에 이미 존재하는 모듈을 덮어쓴 것으로 기록되었습니다.')
    original_dirs = record.get('original_all_directories')
    if (not isinstance(original_dirs, list)
            or record.get('all_existing_directories_verified') != len(original_dirs)
            or len(set(original_dirs)) != len(original_dirs)):
        raise ValueError('전체 기존 폴더 기록이 없습니다.')
    for rel in original_dirs:
        if (not isinstance(rel, str) or not rel or '\\' in rel or '\x00' in rel
                or PurePosixPath(rel).is_absolute()
                or any(p in ('', '.', '..') for p in rel.split('/'))
                or rel == '.git' or rel.startswith('.git/')):
            raise ValueError('사본 기록의 폴더 이름이 올바르지 않습니다.')
    inventory, current_dirs = _inventory(root)
    if current_dirs != set(original_dirs):
        raise ValueError('기존 프로그램의 폴더 구조가 변경되었습니다.')
    backups: dict[str, str] = {}
    for name, expected_blob, modifier in (
        (desktop, BASELINE_DESKTOP_SHA, modify_existing_desktop),
        (offline, BASELINE_OFFLINE_SHA, modify_existing_offline_settings),
    ):
        prefix = name + '.before-original-plan-'
        found = [rel for rel in inventory if rel.startswith(prefix) and rel.endswith('.bak')
                 and re.fullmatch(r'\d{8}T\d{12}Z', rel[len(prefix):-4])]
        if len(found) != 1:
            raise ValueError('검증 가능한 원본 백업이 정확히 하나여야 합니다: ' + name)
        backup = found[0]
        original = (root / backup).read_bytes()
        if _sha(original) != baseline[name] or git_blob_sha(original) != expected_blob:
            raise ValueError('원본 백업이 기록과 다릅니다: ' + name)
        expected = modifier(original.decode('utf-8')).encode('utf-8')
        if inventory.get(name) != _sha(expected):
            raise ValueError('수정된 소스가 검증된 수정안과 다릅니다: ' + name)
        backups[name] = backup
    allowed_new = {PROVENANCE, *backups.values()} | {module.as_posix() for module in MODULES}
    if set(inventory) != set(baseline) | allowed_new:
        missing = sorted((set(baseline) | allowed_new) - set(inventory))
        unexpected = sorted(set(inventory) - (set(baseline) | allowed_new))
        raise ValueError('사본 파일 누락/추가: missing=' + repr(missing[:3]) + ', extra=' + repr(unexpected[:3]))
    for rel, digest in baseline.items():
        if rel not in (desktop, offline) and inventory[rel] != digest:
            raise ValueError('기존 파일이 변경되었습니다: ' + rel)
    for module in MODULES:
        rel = module.as_posix()
        payload = PACKAGE / 'payload' / module
        if not payload.is_file() or inventory[rel] != _sha(payload.read_bytes()):
            raise ValueError('추가 연결 모듈의 바이트가 패키지와 다릅니다: ' + rel)
    return {
        'baseline_existing_files_preserved': len(baseline) - 2,
        'baseline_directories_preserved': len(original_dirs),
        'desktop_patch_exact_match': True,
        'offline_settings_patch_exact_match': True,
        'original_desktop_backup_verified': True,
        'original_offline_settings_backup_verified': True,
        'integration_modules_verified': len(MODULES),
        'user_data_changed': False,
        'real_ai_tts_live2d_obs_verified': False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='AISTING 기존 전체 사본 패치 후 읽기 전용 보존 감사')
    parser.add_argument('--source', type=Path, required=True, help='패치가 적용된 검증된 로컬 사본')
    args = parser.parse_args()
    try:
        result = audit_applied_copy(args.source)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print('사본 보존 감사 실패:', exc, file=sys.stderr)
        return 1
    print('PASS 로컬 사본 코드·기존 파일 보존 검사:', json.dumps(result, ensure_ascii=False))
    print('실제 AI·한국어 음성·Live2D·OBS·방송 기능은 이 검사로 검증되지 않습니다.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
