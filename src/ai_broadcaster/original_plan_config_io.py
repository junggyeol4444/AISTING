"""Loss-preserving local edits of an EXISTING official conf.yaml.

Only called after an explicit per-action GUI approval. No network, model
operations, audio or broadcast. This does not authenticate the upstream app.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import stat
import tempfile


class ExistingConfigChangedError(RuntimeError):
    """The official config is missing, unsafe or changed during editing."""


def decode_official_utf8(data: bytes) -> tuple[str, bytes]:
    """Preserve the source's UTF-8 BOM, if present, across a surgical edit."""
    bom = b'\xef\xbb\xbf' if data.startswith(b'\xef\xbb\xbf') else b''
    return data.decode('utf-8-sig'), bom


def replace_official_config_with_backup(config: Path, before: bytes, after: bytes,
                                        *, label: str) -> Path | None:
    """Back up and replace only the already-inspected regular config file.

    Refuses symlinks, rechecks bytes and inode before replacement, and
    fsyncs/validates the private backup before touching the existing file.
    A filesystem concurrent writer can still race the final check; this is
    not a cross-process locking protocol.
    """
    config = Path(config)
    if not isinstance(before, bytes) or not isinstance(after, bytes):
        raise TypeError('설정 원본과 수정안은 바이트여야 합니다.')
    if len(before) > 1_000_000 or len(after) > 1_000_000:
        raise ExistingConfigChangedError('공식 conf.yaml 크기가 비정상적입니다.')
    if (not label or not label.replace('-', '').isascii()
            or not label.replace('-', '').isalnum()):
        raise ValueError('설정 백업 구분자가 올바르지 않습니다.')
    if config.is_symlink() or not config.is_file() or config.parent.is_symlink():
        raise ExistingConfigChangedError('공식 conf.yaml이 일반 파일이 아니거나 링크입니다.')
    original_stat = config.stat()
    if not stat.S_ISREG(original_stat.st_mode) or config.read_bytes() != before:
        raise ExistingConfigChangedError('공식 conf.yaml이 검사 후 변경되었습니다.')
    if before == after:
        return None
    nonce = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = config.with_name('conf.yaml.before-' + label + '-' + nonce + '.bak')
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(before)
        stream.flush()
        os.fsync(stream.fileno())
    if backup.read_bytes() != before:
        raise ExistingConfigChangedError('원본 백업 검증 실패. 기존 설정을 변경하지 않았습니다.')
    temp = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=config.parent, prefix='.aisting-conf-',
                                         suffix='.tmp', delete=False) as stream:
            temp = Path(stream.name)
            stream.write(after)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, stat.S_IMODE(original_stat.st_mode))
        current_stat = config.stat(follow_symlinks=False)
        if (config.is_symlink() or not stat.S_ISREG(current_stat.st_mode)
                or (current_stat.st_dev, current_stat.st_ino, current_stat.st_size,
                    current_stat.st_mtime_ns) !=
                   (original_stat.st_dev, original_stat.st_ino, original_stat.st_size,
                    original_stat.st_mtime_ns)
                or config.read_bytes() != before):
            raise ExistingConfigChangedError('공식 conf.yaml이 적용 직전 변경되어 덮어쓰지 않았습니다.')
        os.replace(temp, config)
        temp = None
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return backup
