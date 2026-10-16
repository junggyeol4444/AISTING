"""Commit ONLY a user-confirmed AISTING character to existing local settings.

This is called by the dedicated character-confirm button, never by the
ordinary broadcast-settings save. It preserves newer on-disk non-character
settings and makes a private, verified backup before replacing existing data.
No network, model, microphone, TTS, OBS or publishing operations occur here.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import tempfile


class CharacterCommitConflict(RuntimeError):
    """The local settings file cannot safely be updated in this operation."""


@contextmanager
def _exclusive_settings_save(target: Path):
    """Nonblocking per-settings OS lock shared by both explicit save actions.

    The lock file is intentionally retained: deleting a lock file after use
    would let two processes lock different inodes and both write at once.
    This protects cooperating AISTING windows using this module; older code
    that writes settings.json directly does not honor the lock, so the
    existing byte-level before/replace checks remain mandatory.
    """
    parent = target.parent
    if parent.is_symlink():
        raise CharacterCommitConflict('설정 폴더가 심볼릭 링크입니다.')
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink():
        raise CharacterCommitConflict('설정 폴더가 링크로 변경되어 저장하지 않습니다.')
    lock = parent / ('.' + target.name + '.aisting-write.lock')
    if lock.is_symlink():
        raise CharacterCommitConflict('설정 잠금 파일이 링크이므로 저장하지 않습니다.')
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    fd = None
    acquired = False
    try:
        fd = os.open(lock, flags, 0o600)
        actual = os.fstat(fd)
        path_stat = lock.lstat()
        if (not stat.S_ISREG(actual.st_mode)
                or not stat.S_ISREG(path_stat.st_mode)
                or (actual.st_dev, actual.st_ino) != (path_stat.st_dev, path_stat.st_ino)
                or actual.st_size > 1
                or getattr(actual, 'st_nlink', 1) != 1):
            raise CharacterCommitConflict('설정 잠금 파일의 형식이 안전하지 않습니다.')
        if os.name != 'nt' and stat.S_IMODE(actual.st_mode) & 0o077:
            raise CharacterCommitConflict('설정 잠금 파일 권한이 비공개가 아닙니다.')
        if actual.st_size == 1:
            os.lseek(fd, 0, os.SEEK_SET)
            if os.read(fd, 1) != b'\0':
                raise CharacterCommitConflict('설정 잠금 파일의 내용이 올바르지 않습니다.')
        if os.name == 'nt':
            import msvcrt
            # Windows byte-range locks require a byte in the lock file.
            if actual.st_size == 0:
                os.write(fd, b'\0')
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise CharacterCommitConflict('다른 AISTING 창에서 설정을 저장 중입니다.') from exc
        else:
            import fcntl
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (OSError, BlockingIOError) as exc:
                raise CharacterCommitConflict('다른 AISTING 창에서 설정을 저장 중입니다.') from exc
        acquired = True
        yield
    finally:
        if fd is not None:
            try:
                if acquired:
                    if os.name == 'nt':
                        import msvcrt
                        os.lseek(fd, 0, os.SEEK_SET)
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)


def commit_character_identity(current: dict, mode: str, draft: dict[str, str],
                              *, path: Path | None = None) -> dict:
    """Explicitly commit name/style/personality, leaving other settings intact.

    If another application instance has saved non-character settings since
    this window opened, merge with the latest valid on-disk settings rather
    than overwriting them from stale GUI memory. The final compare is not a
    cross-process lock: simultaneous writers must still be avoided.
    """
    from .offline_settings import load_settings, settings_file, validate_settings

    current = validate_settings(current)
    if mode not in ('default', 'custom') or not isinstance(draft, dict):
        raise ValueError('캐릭터 확정 저장 형식이 올바르지 않습니다.')
    candidate = deepcopy(current)
    candidate['persona_mode'] = mode
    candidate['persona'] = deepcopy(draft)
    validate_settings(candidate)  # Reject invalid text before touching disk.

    target = Path(path) if path is not None else settings_file()
    with _exclusive_settings_save(target):
        parent = target.parent
        if parent.is_symlink() or target.is_symlink():
            raise CharacterCommitConflict('설정 경로가 심볼릭 링크이므로 저장하지 않습니다.')
        if target.exists() and not target.is_file():
            raise CharacterCommitConflict('설정 파일이 일반 파일이 아닙니다.')

        existed = target.exists()
        before = None
        original_stat = None
        if existed:
            original_stat = target.stat(follow_symlinks=False)
            if not stat.S_ISREG(original_stat.st_mode) or original_stat.st_size > 1_000_000:
                raise CharacterCommitConflict('기존 설정 파일의 형식 또는 크기가 올바르지 않습니다.')
            before = target.read_bytes()
            if len(before) > 1_000_000:
                raise CharacterCommitConflict('기존 설정 파일이 너무 큽니다.')
            # The original loader also performs the existing legacy migrations.
            merged = load_settings(target)
        else:
            merged = current
        merged = deepcopy(merged)
        merged['persona_mode'] = mode
        merged['persona'] = deepcopy(draft)
        merged = validate_settings(merged)
        if existed and merged == load_settings(target):
            return merged
        return _write_merged_settings(target, merged, existed, before, original_stat,
                                      backup_label='character')


def save_broadcast_without_persona(current: dict, proposed: dict,
                                   *, path: Path | None = None) -> dict:
    """Save operator-selected BROADCAST settings without ever committing a draft.

    The existing desktop builds `proposed` from its broadcast editor. Its
    persona keys are ignored. The latest on-disk confirmed persona wins even
    when a different AISTING window confirmed it after this GUI was opened.
    Refuse to overwrite unrelated external broadcast edits from a stale GUI.
    No external service, audio, model, OBS or network action is performed.
    """
    from .offline_settings import load_settings, settings_file, validate_settings

    current = validate_settings(current)
    # A broadcast-only save must not even *validate* the unsaved character
    # draft: its fields are intentionally outside this operation. Validate
    # every other proposed field against the actual existing settings schema.
    if not isinstance(proposed, dict):
        raise ValueError('방송 설정은 JSON 객체여야 합니다.')
    broadcast_only = deepcopy(proposed)
    broadcast_only['persona_mode'] = deepcopy(current['persona_mode'])
    broadcast_only['persona'] = deepcopy(current['persona'])
    proposed = validate_settings(broadcast_only)
    target = Path(path) if path is not None else settings_file()
    with _exclusive_settings_save(target):
        if target.is_symlink() or target.parent.is_symlink():
            raise CharacterCommitConflict('방송 설정 저장 경로에 심볼릭 링크가 있습니다.')
        if target.exists() and not target.is_file():
            raise CharacterCommitConflict('방송 설정 파일이 일반 파일이 아닙니다.')
        existed = target.exists()
        before = None
        original_stat = None
        if existed:
            original_stat = target.stat(follow_symlinks=False)
            if not stat.S_ISREG(original_stat.st_mode) or original_stat.st_size > 1_000_000:
                raise CharacterCommitConflict('기존 방송 설정 파일 형식 또는 크기가 올바르지 않습니다.')
            before = target.read_bytes()
            if len(before) > 1_000_000:
                raise CharacterCommitConflict('기존 방송 설정 파일이 너무 큽니다.')
            disk = load_settings(target)  # includes the real existing legacy migrations
        else:
            disk = current
        # A second window may have explicitly confirmed a new character: preserve
        # that newer confirmation. For OTHER fields, stale saves are a conflict.
        non_persona = set(current) - {'persona_mode', 'persona'}
        if any(disk[key] != current[key] for key in non_persona):
            raise CharacterCommitConflict(
                '다른 창에서 방송 설정이 변경되었습니다. 현재 창을 다시 열어 확인한 뒤 저장하세요.')
        merged = deepcopy(proposed)
        merged['persona_mode'] = deepcopy(disk['persona_mode'])
        merged['persona'] = deepcopy(disk['persona'])
        merged = validate_settings(merged)
        if existed and merged == disk:
            return merged  # Semantic no-op: preserve original formatting and mtime.
        return _write_merged_settings(target, merged, existed, before, original_stat,
                                      backup_label='broadcast')


def _write_merged_settings(target: Path, merged: dict, existed: bool,
                           before: bytes | None, original_stat,
                           *, backup_label: str) -> dict:
    """Private, checked backup and atomic replace shared by both save buttons.

    This is not a cross-process lock: an external writer can race after the
    final check. It avoids silent stale writes in ordinary operation.
    """
    output = (json.dumps(merged, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if len(output) > 1_000_000:
        raise CharacterCommitConflict('저장할 설정 파일이 너무 큽니다.')
    parent = target.parent
    if parent.is_symlink():
        raise CharacterCommitConflict('설정 폴더가 심볼릭 링크입니다.')
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink():
        raise CharacterCommitConflict('설정 폴더가 링크로 변경되어 저장하지 않습니다.')

    def unchanged() -> bool:
        if target.is_symlink() or target.exists() != existed:
            return False
        if not existed:
            return True
        try:
            now = target.stat(follow_symlinks=False)
            return (stat.S_ISREG(now.st_mode) and
                    (now.st_dev, now.st_ino, now.st_size, now.st_mtime_ns) ==
                    (original_stat.st_dev, original_stat.st_ino,
                     original_stat.st_size, original_stat.st_mtime_ns) and
                    target.read_bytes() == before)
        except OSError:
            return False

    if not unchanged():
        raise CharacterCommitConflict('설정 파일이 변경되었습니다. 다시 확인한 뒤 저장하세요.')
    if existed and before == output:
        return merged
    if existed:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = target.with_name(target.name + '.before-' + backup_label + '-' + stamp + '.bak')
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(before)
            handle.flush()
            os.fsync(handle.fileno())
        if backup.read_bytes() != before:
            raise CharacterCommitConflict('기존 설정 백업 검증 실패. 파일을 변경하지 않았습니다.')

    temporary = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=parent, prefix='.' + target.name + '.',
                                         suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            os.chmod(temporary, 0o600)
            handle.write(output)
            handle.flush()
            os.fsync(handle.fileno())
        if not unchanged():
            raise CharacterCommitConflict('설정이 저장 직전 변경되어 덮어쓰지 않았습니다.')
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return merged
