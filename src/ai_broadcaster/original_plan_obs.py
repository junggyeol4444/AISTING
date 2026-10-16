"""Original plan section 7-4: real OBS WebSocket v5 connector.

Uses the installed OBS WebSocket client directly, not simulated OBS state.
No external broadcast is started by module import, construction or read-only
status query. Outgoing stream actions require a separate, explicit approval.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any


class ObsConnectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ActualObsState:
    version: str
    scene: str
    streaming: bool


@dataclass(frozen=True)
class ActualObsInventory:
    """Names returned by actual OBS, not an assertion of video/audio delivery."""
    scene: str
    scene_items: tuple[str, ...]
    input_sources: tuple[str, ...]


@dataclass(frozen=True)
class ActualObsMediaPath:
    """Read-only OBS routing candidates, NOT confirmed captured pictures/sound."""
    capture_sources: tuple[str, ...]
    audio_sources: tuple[str, ...]
    problems: tuple[str, ...]


class OfficialObsWebsocket:
    def __init__(self, password: str, *, port: int = 4455) -> None:
        if not isinstance(password, str) or not password:
            raise ValueError('OBS WebSocket 비밀번호가 필요합니다.')
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('OBS 포트가 올바르지 않습니다.')
        self._password = password
        self._port = port
        self._client: Any | None = None

    def connect(self) -> ActualObsState:
        # obsws-python is an actual OBS WebSocket 5 API client, not a mock.
        try:
            import obsws_python
        except ImportError as exc:
            raise ObsConnectionError('실제 OBS WebSocket 연결 패키지가 설치되어 있지 않습니다.') from exc
        try:
            self._client = obsws_python.ReqClient(
                host='127.0.0.1', port=self._port, password=self._password,
                timeout=5,
            )
            return self.status()
        except Exception as exc:
            self._client = None
            raise ObsConnectionError('실제 OBS 서버 접속·인증에 실패했습니다.') from exc

    def status(self) -> ActualObsState:
        if self._client is None:
            raise ObsConnectionError('먼저 실제 OBS에 연결해야 합니다.')
        try:
            ver = self._client.get_version()
            scene = self._client.get_current_program_scene()
            stream = self._client.get_stream_status()
        except Exception as exc:
            raise ObsConnectionError('실제 OBS의 장면/방송 상태 읽기 실패') from exc
        return ActualObsState(
            version=str(ver.obs_version),
            scene=str(scene.current_program_scene_name),
            streaming=bool(stream.output_active),
        )

    def read_scene_inventory(self) -> ActualObsInventory:
        """Read actual OBS program-scene sources and audio inputs, no writes.

        Source discovery is a prerequisite to validating the plan's avatar
        scene and actual TTS audio routing, not proof the routing works.
        """
        if self._client is None:
            raise ObsConnectionError('실제 OBS에 먼저 연결해야 합니다.')
        actual = self.status()
        try:
            scene_result = self._client.get_scene_item_list(actual.scene)
            inputs_result = self._client.get_input_list()
            scene_items = scene_result.scene_items
            inputs = inputs_result.inputs
            if not isinstance(scene_items, list) or not isinstance(inputs, list):
                raise ValueError('OBS 응답 목록 형식이 올바르지 않습니다.')
            names = []
            for item in scene_items:
                if not isinstance(item, dict) or not isinstance(item.get('sourceName'), str):
                    raise ValueError('OBS 장면 소스 형식이 올바르지 않습니다.')
                names.append(item['sourceName'])
            audios = []
            for item in inputs:
                if not isinstance(item, dict):
                    raise ValueError('OBS 오디오 입력 형식이 올바르지 않습니다.')
                input_kind = item.get('inputKind', '')
                input_name = item.get('inputName')
                if not isinstance(input_kind, str) or not isinstance(input_name, str):
                    raise ValueError('OBS 오디오 입력 형식이 올바르지 않습니다.')
                # List all input names, not just those heuristically identified
                # as audio; the operator must decide if a TTS input exists.
                audios.append(input_name + ' (' + input_kind + ')')
            return ActualObsInventory(actual.scene, tuple(names), tuple(audios))
        except ObsConnectionError:
            raise
        except Exception as exc:
            raise ObsConnectionError('실제 OBS 장면/입력 소스 조회 실패') from exc


    def read_scene_media_path(self) -> ActualObsMediaPath:
        """Inspect actual current-scene capture settings and local audio routing.

        Reading OBS input mute and volume does NOT prove the operating system
        actually delivers samples or that a configured window is visible.
        Never change the scene, enable a source, adjust volume or start stream.
        """
        if self._client is None:
            raise ObsConnectionError('실제 OBS에 먼저 연결해야 합니다.')
        actual = self.status()
        try:
            scene_items = self._client.get_scene_item_list(actual.scene).scene_items
            inputs = self._client.get_input_list().inputs
            if not isinstance(scene_items, list) or not isinstance(inputs, list):
                raise ValueError('OBS 장면 또는 입력 소스 목록이 올바르지 않습니다.')
            captures: list[str] = []
            audio: list[str] = []
            problems: list[str] = []
            for item in scene_items[:100]:
                if not isinstance(item, dict):
                    raise ValueError('OBS 장면 소스 형식이 올바르지 않습니다.')
                name, kind = item.get('sourceName'), item.get('inputKind', '')
                if not isinstance(name, str) or not isinstance(kind, str):
                    raise ValueError('OBS 장면 소스 필드가 올바르지 않습니다.')
                if kind not in ('window_capture', 'game_capture', 'monitor_capture'):
                    continue
                enabled = item.get('sceneItemEnabled')
                if type(enabled) is not bool:
                    problems.append(name + ': 활성 상태를 확인할 수 없음')
                    continue
                if not enabled:
                    captures.append(name + ': 비활성')
                    continue
                configured = ''
                try:
                    settings = self._client.get_input_settings(name).input_settings
                    if isinstance(settings, dict):
                        window = settings.get('window', '')
                        if isinstance(window, str) and window:
                            configured = ' / 선택된 창 ' + window[:140]
                except Exception:
                    problems.append(name + ': 창 설정 세부 정보 조회 불가')
                captures.append(name + ' (' + kind + ', 활성)' + configured)
            # Input kinds are OBS-version/plugin-dependent. Probe each input
            # for actual audio controls instead of presuming naming conventions.
            for item in inputs[:100]:
                if not isinstance(item, dict):
                    raise ValueError('OBS 입력 소스 형식이 올바르지 않습니다.')
                name = item.get('inputName')
                kind = item.get('inputKind', '')
                if not isinstance(name, str) or not isinstance(kind, str):
                    raise ValueError('OBS 입력 소스 항목이 올바르지 않습니다.')
                try:
                    mute_result = self._client.get_input_mute(name)
                    volume_result = self._client.get_input_volume(name)
                    muted = mute_result.input_muted
                    gain = volume_result.input_volume_mul
                    if type(muted) is not bool or not isinstance(gain, (float, int)):
                        raise ValueError('OBS 음소거/볼륨 데이터 오류')
                    audio.append(
                        name + ' (' + kind + ')' +
                        (' / 음소거' if muted else ' / 음소거 아님') +
                        ' / OBS 볼륨 ' + str(round(float(gain), 3))
                    )
                except Exception:
                    # Video-only sources legitimately reject audio controls.
                    # Audio-capable plugins might reject them too: record unknown,
                    # never declare the sound path valid in either case.
                    if any(part in kind.lower() for part in (
                            'audio', 'wasapi', 'pulse', 'coreaudio', 'alsa',
                            'browser_source', 'ffmpeg', 'vlc', 'application')):
                        problems.append(name + ': 오디오 상태 조회 불가 (' + kind + ')')
            if len(scene_items) > 100 or len(inputs) > 100:
                problems.append('대규모 OBS 소스 목록은 앞쪽 100개만 검사')
            if not captures:
                problems.append('현재 장면에서 창/게임/모니터 캡처 소스를 찾지 못함')
            if not audio:
                problems.append('OBS에서 음소거/음량을 확인할 수 있는 입력을 찾지 못함')
            return ActualObsMediaPath(tuple(captures), tuple(audio), tuple(problems))
        except Exception as exc:
            raise ObsConnectionError('OBS 화면 캡처/오디오 경로 상세 읽기 실패') from exc

    def set_scene(self, name: str, *, operator_confirmed: bool = False) -> ActualObsState:
        # Changing the on-air scene is an actual OBS control action. Require
        # the same separate permission as stream start/stop; this method is
        # not exposed by the read-only operator-inspection UI.
        if operator_confirmed is not True or os.environ.get('AISTING_APPROVED_OBS_OUTGOING') != 'YES':
            raise PermissionError('실제 OBS 장면 변경은 운영자의 별도 명시적 승인이 필요합니다.')
        if not isinstance(name, str) or not name.strip() or len(name) > 128:
            raise ValueError('OBS 장면 이름이 올바르지 않습니다.')
        if any(ord(c) < 32 for c in name):
            raise ValueError('OBS 장면 이름에 줄바꿈·제어 문자를 사용할 수 없습니다.')
        if self._client is None:
            raise ObsConnectionError('실제 OBS에 먼저 연결해야 합니다.')
        try:
            self._client.set_current_program_scene(name.strip())
        except Exception as exc:
            raise ObsConnectionError('실제 OBS 장면 전환 실패') from exc
        return self.status()

    def start_stream(self, *, operator_confirmed: bool = False) -> ActualObsState:
        """Only after an authorized outbound broadcast test. Not called by GUI."""
        if operator_confirmed is not True or os.environ.get('AISTING_APPROVED_OBS_OUTGOING') != 'YES':
            raise PermissionError('실제 송출은 운영자의 별도 명시적 승인 없이 실행할 수 없습니다.')
        state = self.status()
        if state.streaming:
            raise ObsConnectionError('실제 OBS가 이미 송출 중입니다.')
        try:
            self._client.start_stream()
        except Exception as exc:
            raise ObsConnectionError('실제 OBS 송출 시작 요청 실패') from exc
        state = self.status()
        if not state.streaming:
            raise ObsConnectionError('OBS가 송출을 시작했다고 확인되지 않았습니다.')
        return state

    def stop_stream(self, *, operator_confirmed: bool = False) -> ActualObsState:
        if operator_confirmed is not True or os.environ.get('AISTING_APPROVED_OBS_OUTGOING') != 'YES':
            raise PermissionError('실제 송출 중지는 운영자의 별도 명시적 승인이 필요합니다.')
        state = self.status()
        if not state.streaming:
            raise ObsConnectionError('OBS가 실제 송출 중이 아닙니다.')
        try:
            self._client.stop_stream()
        except Exception as exc:
            raise ObsConnectionError('실제 OBS 송출 종료 요청 실패') from exc
        state = self.status()
        if state.streaming:
            raise ObsConnectionError('송출 종료가 실제 OBS에서 확인되지 않았습니다.')
        return state
