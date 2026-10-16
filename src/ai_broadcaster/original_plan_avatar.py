"""Explicit selection of REAL, already-present upstream Live2D models (stage 1).

AISTING is the existing desktop GUI; this module edits only the official
Open-LLM-VTuber conf.yaml the operator explicitly chooses. It never draws a
fake model, downloads anything, starts an upstream server, plays sound, or
claims that a running frontend has loaded/animated the selected model.

The upstream's model_dict.json and Cubism model3.json are inspected via the
existing stage-1 readiness code. No dependency installation is required.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re

from .original_plan_studio import StageOneUnavailable, check_official_project
from .original_plan_config_io import (
    decode_official_utf8, replace_official_config_with_backup,
)
from .original_plan_readiness import (
    _contained_regular_file, _live2d_assets, _read_utf8, _scalar, _select_block,
)


@dataclass(frozen=True)
class OfficialLive2DChoice:
    name: str
    url: str
    asset_files: int
    issue: str = ''

    @property
    def available(self) -> bool:
        return not self.issue


@dataclass(frozen=True)
class OfficialLive2DOptions:
    selected_name: str
    config_sha256: str
    choices: tuple[OfficialLive2DChoice, ...]


def _official_model_rel(url: str) -> Path:
    if not isinstance(url, str) or not url.startswith('/live2d-models/') or not url.endswith('.model3.json'):
        raise StageOneUnavailable('공식 Live2D 모델 경로가 아닙니다.')
    relative = Path(url[1:])
    if (relative.is_absolute() or any(part in ('..', '.') for part in url[1:].split('/'))
            or '\\' in url or '\x00' in url or '//' in url or ':' in url):
        raise StageOneUnavailable('잘못된 Live2D 모델 경로입니다.')
    return relative


def _read_config(root: Path) -> bytes:
    config = root / 'conf.yaml'
    if config.is_symlink() or not config.is_file() or config.stat().st_size > 1_000_000:
        raise StageOneUnavailable('공식 conf.yaml 기존 일반 파일이 필요합니다.')
    return config.read_bytes()


def _character_range(source: str) -> tuple[list[str], tuple[int, int]]:
    lines = source.splitlines(keepends=True)
    region = _select_block(lines, (0, len(lines)), 'character_config', 0)
    return lines, region


def _active_model(source: str) -> str:
    lines, region = _character_range(source)
    return _scalar(lines, region, 'live2d_model_name', 2)


def inspect_official_live2d_options(folder: str | Path) -> OfficialLive2DOptions:
    """Only list real models and their local Cubism references; NO write/network."""
    root = check_official_project(folder)
    current = _read_config(root)
    try:
        source, _ = decode_official_utf8(current)
        selected = _active_model(source)
        index = json.loads(_read_utf8(root / 'model_dict.json'))
        if not isinstance(index, list):
            raise StageOneUnavailable('공식 model_dict.json이 목록이 아닙니다.')
        names: set[str] = set()
        choices: list[OfficialLive2DChoice] = []
        for item in index:
            if not isinstance(item, dict) or not isinstance(item.get('name'), str):
                raise StageOneUnavailable('공식 Live2D 모델 목록 항목이 유효하지 않습니다.')
            name = item['name']
            if not name.strip() or name in names:
                raise StageOneUnavailable('중복되거나 빈 Live2D 모델 이름이 있습니다.')
            names.add(name)
            url = item.get('url')
            if not isinstance(url, str):
                choices.append(OfficialLive2DChoice(name, '', 0, '모델 URL이 없습니다.'))
                continue
            try:
                scale = item.get('kScale')
                # Upstream frontend requires name, url and positive kScale.
                if type(scale) not in (int, float) or not math.isfinite(scale) or scale <= 0:
                    raise StageOneUnavailable('공식 모델 항목의 필수 kScale이 없습니다/유효하지 않습니다.')
                relative = _official_model_rel(url)
                definition = _contained_regular_file(root, relative)
                payload = json.loads(_read_utf8(definition))
                if not isinstance(payload, dict):
                    raise StageOneUnavailable('Cubism 모델 정의 형식 오류')
                count = _live2d_assets(payload, root, relative)
            except (StageOneUnavailable, OSError, ValueError, UnicodeError) as exc:
                choices.append(OfficialLive2DChoice(name, url, 0, str(exc)))
            else:
                choices.append(OfficialLive2DChoice(name, url, count))
        if not choices:
            raise StageOneUnavailable('공식 Live2D 모델 목록이 비어 있습니다.')
        return OfficialLive2DOptions(
            selected, hashlib.sha256(current).hexdigest(), tuple(choices))
    except (UnicodeError, ValueError, KeyError) as exc:
        raise StageOneUnavailable('공식 Live2D 설정을 읽을 수 없습니다.') from exc


def _split_inline_comment(value: str) -> tuple[str, str]:
    """Split an inline YAML comment while respecting single/double quotes."""
    quote = ''
    escaped = False
    index = 0
    while index < len(value):
        ch = value[index]
        if quote == '"':
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                quote = ''
        elif quote == "'":
            if ch == "'" and index + 1 < len(value) and value[index + 1] == "'":
                index += 1
            elif ch == "'":
                quote = ''
        elif ch in ("'", '"'):
            quote = ch
        elif ch == '#' and index > 0 and value[index - 1].isspace():
            begin = index - 1
            while begin and value[begin - 1].isspace():
                begin -= 1
            return value[:begin], value[begin:]
        index += 1
    return value, ''


def _change_model_scalar(source: str, name: str) -> str:
    lines, (start, end) = _character_range(source)
    # Validate the existing scalar layout; no unsafe generic YAML regex rewrite.
    _scalar(lines, (start, end), 'live2d_model_name', 2)
    matches = [i for i in range(start, end)
               if re.match(r'^  live2d_model_name:\s*', lines[i])]
    if len(matches) != 1 or '\n' in name or '\r' in name or any(ord(c) < 32 for c in name):
        raise StageOneUnavailable('공식 아바타 항목 형식을 확인할 수 없습니다.')
    i = matches[0]
    ending = '\r\n' if lines[i].endswith('\r\n') else '\n' if lines[i].endswith('\n') else ''
    line = lines[i][:-len(ending)] if ending else lines[i]
    old_value = line.split(':', 1)[1]
    _value, comment = _split_inline_comment(old_value)
    lines[i] = "  live2d_model_name: '" + name.replace("'", "''") + "'" + comment + ending
    return ''.join(lines)


def apply_official_live2d_choice(
    folder: str | Path, name: str, *, expected_config_sha256: str,
    operator_approved: bool = False,
) -> tuple[Path, Path | None]:
    """Change only the explicitly selected official model, with private backup.

    The running upstream's model is NOT switched here. Restart/reload of
    official upstream may be necessary and always needs separate approval.
    """
    if operator_approved is not True:
        raise PermissionError('공식 Live2D 설정 변경은 사용자 명시 승인이 필요합니다.')
    if not isinstance(name, str) or not isinstance(expected_config_sha256, str):
        raise ValueError('아바타 선택 입력이 올바르지 않습니다.')
    options = inspect_official_live2d_options(folder)
    if options.config_sha256 != expected_config_sha256:
        raise StageOneUnavailable('다른 창에서 공식 conf.yaml이 변경됐습니다. 목록을 새로 읽으세요.')
    matches = [choice for choice in options.choices if choice.name == name]
    if len(matches) != 1 or not matches[0].available:
        raise StageOneUnavailable('모델 목록에 없거나 Cubism 필수 파일이 부족합니다.')
    root = check_official_project(folder)
    config = root / 'conf.yaml'
    old = _read_config(root)
    if hashlib.sha256(old).hexdigest() != expected_config_sha256:
        raise StageOneUnavailable('공식 conf.yaml이 선택 후 변경되었습니다.')
    if options.selected_name == name:
        # Same semantic selection: never churn quotes/comments or create a backup.
        return config, None
    source, bom = decode_official_utf8(old)
    updated = _change_model_scalar(source, name)
    after = bom + updated.encode('utf-8')
    backup = replace_official_config_with_backup(config, old, after, label='live2d')
    return config, backup
