"""사용자가 지정한 Windows 게임의 실제 행동 직전 OBS 장면 동일성 확인.

기존 approved_local_game_control을 위한 읽기 전용 OBS 소유 장면 검사.
매 게임 행동에 새 스크린샷을 찍거나 LLM에게 새 목표를 만들게 하지
않으며 게임/OBS/녹화/방송 상태는 절대로 변경하지 않는다.
게임 창 HWND/PID/포커스는 기존 WindowsApprovedGameWindow가 별도로 확인한다.
"""
from __future__ import annotations

from .original_plan_obs import OfficialObsWebsocket


def require_approved_game_scene(
    obs_password: str, obs_port: int, expected_scene: str,
) -> None:
    """기존 OBS에서 관측하던 바로 그 장면에서만 다음 실제 입력 허용."""
    if type(obs_password) is not str or not obs_password:
        raise PermissionError("게임 OBS 장면을 확인할 수 있는 승인된 암호가 없습니다.")
    if type(obs_port) is not int or not 1 <= obs_port <= 65535:
        raise ValueError("OBS 장면 확인 포트가 올바르지 않습니다.")
    if (type(expected_scene) is not str or not expected_scene.strip()
            or len(expected_scene) > 300):
        raise ValueError("이번 승인 게임의 최초 OBS 장면이 확정되지 않았습니다.")
    obs = OfficialObsWebsocket(obs_password, port=obs_port)
    try:
        connected = obs.connect()
        status = obs.status()
        if (getattr(connected, "scene", None) != expected_scene
                or getattr(status, "scene", None) != expected_scene):
            raise RuntimeError(
                "운영자가 승인한 최초 OBS 게임 장면이 달라졌으므로 "
                "추가 게임 키보드·마우스 조작을 중단합니다.")
    finally:
        inner = getattr(obs, "_client", None)
        disconnect = getattr(inner, "disconnect", None)
        if callable(disconnect):
            try:
                disconnect()
            except Exception:
                pass
