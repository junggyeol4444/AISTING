"""Stage 058: offline positioning for the bundled 2D *preview*, not an OBS scene.

All values are operator-chosen and local. No file access occurs until an explicit
save/load/delete request. No auto scanning, microphone, streaming or 3D fallback.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .avatar_renderer import AvatarFrame, BACKGROUND_COLORS, draw_avatar
from .offline_settings import data_dir
from .runtime_profile import _assert_safe_path

SCHEMA = 1
MAX_BYTES = 1024
FILE_NAME = 'avatar_layout_draft.json'
PREVIEW_WIDTH = 640
PREVIEW_HEIGHT = 360
# The sample drawing itself uses a 370 by 460 local coordinate system.
SOURCE_WIDTH = 370
SOURCE_HEIGHT = 460


@dataclass(frozen=True)
class AvatarLayout:
    avatar: str = '2d'
    horizontal: int = 75
    vertical: int = 100
    size: int = 70
    background: str = '남색 스튜디오'

    def __post_init__(self) -> None:
        if self.avatar != '2d' or type(self.avatar) is not str:
            raise ValueError('내장 2D 샘플에만 화면 배치를 설정할 수 있습니다. 3D 자동 대체 불가.')
        for key, val, lower, upper in (
            ('가로 위치', self.horizontal, 0, 100),
            ('세로 위치', self.vertical, 0, 100),
            ('크기', self.size, 40, 100),
        ):
            if type(val) is not int or not lower <= val <= upper:
                raise ValueError(f'{key}: {lower}~{upper} 사이의 정수만 허용합니다.')
        if type(self.background) is not str or self.background not in BACKGROUND_COLORS:
            raise ValueError('배경은 제공된 로컬 색상에서만 선택하세요.')

    def geometry(self, width: int = PREVIEW_WIDTH, height: int = PREVIEW_HEIGHT) -> tuple[float, float, float]:
        if type(width) is not int or type(height) is not int or width < 1 or height < 1:
            raise ValueError('올바른 양수 화면 크기가 필요합니다.')
        # Maximum figure height is 70% of preview; entire original bounding box fits.
        scale = min(width / SOURCE_WIDTH, height * 0.7 / SOURCE_HEIGHT) * self.size / 100
        dx = (width - SOURCE_WIDTH * scale) * self.horizontal / 100
        dy = (height - SOURCE_HEIGHT * scale) * self.vertical / 100
        return scale, dx, dy

    def describe(self) -> str:
        return (f'58단계 · 내장 2D 샘플의 가상 방송 화면 배치\n'
                f'가로 {self.horizontal}% · 세로 {self.vertical}% · 크기 {self.size}% · 배경 {self.background}\n'
                '미리보기 전용: OBS 장면 배치·외부 모델 표시·실제 방송·운영자 최종 승인 아님.')


def draw_layout_preview(canvas, layout: AvatarLayout, pose: AvatarFrame) -> None:
    """Render existing Tk 2D sample and reposition its Canvas objects in a mock scene."""
    if type(layout) is not AvatarLayout or type(pose) is not AvatarFrame:
        raise ValueError('아바타 배치와 프레임을 확인하세요.')
    if pose.background != layout.background:
        raise ValueError('선택 배경과 아바타 프레임이 일치해야 합니다.')
    draw_avatar(canvas, pose)
    scale, dx, dy = layout.geometry()
    canvas.scale('all', 0, 0, scale, scale)
    canvas.move('all', dx, dy)


def layout_path(directory: Path | None = None) -> Path:
    return (Path(directory) if directory is not None else data_dir()) / FILE_NAME


def _record(layout: AvatarLayout) -> dict:
    return dict(schema_version=SCHEMA, kind='builtin_2d_layout_preview',
                avatar=layout.avatar, horizontal=layout.horizontal,
                vertical=layout.vertical, size=layout.size, background=layout.background,
                obs_configured=False, external_model_loaded=False,
                broadcasting_authorized=False, final_approval=False)


def validate_layout_record(obj: object) -> AvatarLayout:
    if type(obj) is not dict or set(obj) != set(_record(AvatarLayout())):
        raise ValueError('아바타 배치 기록 형식이 잘못되었습니다.')
    if (type(obj['schema_version']) is not int or obj['schema_version'] != SCHEMA
            or obj['kind'] != 'builtin_2d_layout_preview'
            or any(obj[k] is not False for k in (
                'obs_configured', 'external_model_loaded',
                'broadcasting_authorized', 'final_approval'))):
        raise ValueError('배치 기록의 자동 승인 필드를 허용하지 않습니다.')
    return AvatarLayout(obj['avatar'], obj['horizontal'], obj['vertical'],
                        obj['size'], obj['background'])


def save_layout(path: Path, layout: AvatarLayout, *, operator_confirmed: bool = False) -> Path:
    if operator_confirmed is not True:
        raise PermissionError('운영자 확인 후에만 배치 초안을 저장합니다.')
    if type(layout) is not AvatarLayout:
        raise ValueError('아바타 배치 형식이 올바르지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 허용합니다.')
    raw = json.dumps(_record(layout), ensure_ascii=False, indent=2).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValueError('배치 기록 크기를 초과했습니다.')
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(target)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.avatar-layout-',
                                         suffix='.tmp', delete=False) as fp:
            temporary = Path(fp.name)
            fp.write(raw)
            fp.flush()
            os.fsync(fp.fileno())
        _assert_safe_path(target)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def load_layout(path: Path, *, selected_avatar: str) -> AvatarLayout | None:
    if selected_avatar != '2d':
        raise ValueError('2D가 아닌 선택에서는 2D 배치 기록을 재사용하지 않습니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 허용합니다.')
    try:
        with target.open('rb') as fp:
            raw = fp.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(raw) > MAX_BYTES:
        raise ValueError('배치 기록 크기를 초과했습니다.')
    try:
        obj = json.loads(raw.decode('utf-8'))
        return validate_layout_record(obj)
    except (UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise ValueError('배치 기록을 신뢰할 수 없어 불러오지 않습니다.') from exc


def delete_layout(path: Path, *, operator_confirmed: bool = False) -> bool:
    if operator_confirmed is not True:
        raise PermissionError('운영자 삭제 확인이 필요합니다.')
    target = Path(path)
    _assert_safe_path(target)
    if target.exists() and not target.is_file():
        raise ValueError('일반 파일만 허용합니다.')
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True
