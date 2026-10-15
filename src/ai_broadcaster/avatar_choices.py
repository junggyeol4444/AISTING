"""8단계: 런타임 아바타 형태 선택. 외부 3D 엔진, 모델 다운로드 없음.

여기서 완료된 것은 *선택/저장/정확한 상태 표시*뿐이다.
실제 Live2D나 VRM 모델을 만들어 구동했다고 주장하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_settings import AVATARS


@dataclass(frozen=True)
class AvatarChoice:
    code: str
    description: str
    sample_2d_visible: bool
    can_open_sample_window: bool


_CHOICES: dict[str, AvatarChoice] = {
    "undecided": AvatarChoice(
        "undecided", "아바타 형태 미정 · 아래는 선택과 무관한 무료 2D 샘플입니다. 언제든 변경할 수 있습니다.",
        True, True,
    ),
    "2d": AvatarChoice(
        "2d", "2D 선택 · 무료 Tk 샘플만 제공. 실제 Live2D 모델·정밀 립싱크는 미구현입니다.",
        True, True,
    ),
    "3d": AvatarChoice(
        "3d", "3D(VRM) 선택 기록 완료 · VRM 파일·3D 렌더러 미설치. 2D를 3D처럼 표시하지 않습니다.",
        False, False,
    ),
}


def avatar_choice(code: str) -> AvatarChoice:
    """선택되지 않은 코드에 자동으로 다른 모드를 적용하지 않는다."""
    if not isinstance(code, str) or code not in AVATARS.values():
        raise ValueError("지원하지 않는 아바타 형태입니다 (미정/2D/3D).")
    return _CHOICES[code]
