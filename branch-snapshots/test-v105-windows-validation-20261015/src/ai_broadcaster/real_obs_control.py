"""Original plan [7-4] OBS WebSocket v5 REAL control boundary.

Not a simulator: every method calls the official OBS WebSocket client.
Nothing connects, switches scene, records or streams on import.
No broadcasting occurs merely because this class is constructed.

The caller must supply existing OBS host/password; localhost only.
Do NOT report original 3rd stage complete until real OBS video, actual TTS
audio and real platform chat are verified together on the user's PC.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ObsBroadcastStatus:
    connected: bool
    is_streaming: bool
    obs_version: str
    active_scene: str
    duration_ms: int


class RealObsController:
    """OBS Studio v28+ WebSocket 5, optional obsws-python library."""

    def __init__(self, *, password: str, port: int = 4455) -> None:
        if not isinstance(password, str) or not password:
            raise ValueError("OBS WebSocket 비밀번호가 필요합니다.")
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("OBS WebSocket 포트는 1~65535 범위여야 합니다.")
        self._port = port
        self._password = password
        self._client: Any | None = None

    def connect(self) -> ObsBroadcastStatus:
        if self._client is not None:
            return self.status()
        try:
            import obsws_python as obs
        except ImportError as exc:
            raise RuntimeError(
                "실제 OBS WebSocket Python 클라이언트가 설치되지 않았습니다. "
                "모의 연결로 대체하지 않습니다."
            ) from exc
        try:
            client = obs.ReqClient(
                host="127.0.0.1", port=self._port,
                password=self._password, timeout=4,
            )
        except Exception as exc:
            raise RuntimeError("실제 OBS 서버 접속 또는 인증 실패") from exc
        self._client = client
        try:
            return self.status()
        except Exception:
            self._client = None
            raise

    def status(self) -> ObsBroadcastStatus:
        client = self._require_connection()
        try:
            version = client.get_version()
            scene = client.get_current_program_scene()
            stream = client.get_stream_status()
            return ObsBroadcastStatus(
                connected=True,
                is_streaming=bool(stream.output_active),
                obs_version=str(version.obs_version),
                active_scene=str(scene.current_program_scene_name),
                duration_ms=int(getattr(stream, "output_duration", 0)),
            )
        except Exception as exc:
            raise RuntimeError("실제 OBS 상태 조회 실패") from exc

    def select_scene(self, scene_name: str) -> ObsBroadcastStatus:
        if not isinstance(scene_name, str) or not scene_name.strip() or len(scene_name) > 120:
            raise ValueError("OBS 장면 이름이 올바르지 않습니다.")
        if any(ord(ch) < 32 for ch in scene_name):
            raise ValueError("OBS 장면 이름에 제어 문자를 사용할 수 없습니다.")
        client = self._require_connection()
        try:
            client.set_current_program_scene(scene_name.strip())
        except Exception as exc:
            raise RuntimeError("실제 OBS 장면 전환 실패") from exc
        return self.status()

    def start_stream(self, *, operator_approved: bool = False) -> ObsBroadcastStatus:
        """Real outgoing stream operation, never implicit."""
        if operator_approved is not True:
            raise PermissionError("실제 방송 시작은 운영자 명시적 승인이 필요합니다.")
        self._start_guard()
        client = self._require_connection()
        try:
            client.start_stream()
        except Exception as exc:
            raise RuntimeError("OBS 실제 방송 시작 실패") from exc
        result = self.status()
        if not result.is_streaming:
            raise RuntimeError("OBS에 방송 시작 명령을 보냈지만 실제 송출이 확인되지 않았습니다.")
        return result

    def stop_stream(self, *, operator_approved: bool = False) -> ObsBroadcastStatus:
        """Real outgoing stream termination, never implicit."""
        if operator_approved is not True:
            raise PermissionError("실제 방송 종료는 운영자 명시적 승인이 필요합니다.")
        current = self.status()
        if not current.is_streaming:
            raise RuntimeError("현재 OBS에서 실제 송출 중이 아닙니다.")
        try:
            self._require_connection().stop_stream()
        except Exception as exc:
            raise RuntimeError("OBS 실제 방송 종료 실패") from exc
        result = self.status()
        if result.is_streaming:
            raise RuntimeError("OBS에 방송 종료 명령을 보냈지만 실제 종료가 확인되지 않았습니다.")
        return result

    def _start_guard(self) -> None:
        if os.environ.get("AISTING_OPERATOR_APPROVED_REAL_STREAM") != "I_APPROVE":
            raise PermissionError(
                "실제 외부 방송은 별도 운영자 승인 후 "
                "AISTING_OPERATOR_APPROVED_REAL_STREAM=I_APPROVE 필요"
            )
        current = self.status()
        if current.is_streaming:
            raise RuntimeError("OBS는 이미 송출 중입니다. 중복 시작하지 않습니다.")

    def _require_connection(self):
        if self._client is None:
            raise RuntimeError("실제 OBS 서버에 먼저 연결해야 합니다.")
        return self._client
