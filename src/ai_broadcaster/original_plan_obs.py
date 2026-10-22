"""Original plan section 7-4: real OBS WebSocket v5 connector.

Uses the installed OBS WebSocket client directly, not simulated OBS state.
No external broadcast is started by module import, construction or read-only
status query. Outgoing stream actions require a separate, explicit approval.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from copy import deepcopy
import base64
import binascii
import math
import os
import threading
import time
import zlib
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
    # Exact, unformatted names returned by OBS GetInputList. The Windows
    # operator must be able to select an input without copying a display
    # string containing the source kind (which is not part of its name).
    input_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActualObsMediaPath:
    """Read-only OBS routing candidates, NOT confirmed captured pictures/sound."""
    capture_sources: tuple[str, ...]
    audio_sources: tuple[str, ...]
    problems: tuple[str, ...]


@dataclass(frozen=True)
class ActualObsFrame:
    """An OBS-rendered PNG scene frame. No motion/audio/stream proof."""
    scene: str
    width: int
    height: int
    png_data: bytes


@dataclass(frozen=True)
class ActualObsAudioMeters:
    """Read-only OBS input meter evidence, not proof of broadcast output."""
    event_count: int
    input_peaks: tuple[tuple[str, float], ...]
    selected_input: str | None = None
    selected_muted: bool | None = None
    selected_volume: float | None = None
    selected_meter_events: int = 0
    selected_route_changed: bool = False
    first_selected_signal_monotonic: float = 0.0
    last_selected_signal_monotonic: float = 0.0

    @property
    def any_signal(self) -> bool:
        return any(peak > 0.001 for _, peak in self.input_peaks)

    @property
    def selected_signal(self) -> bool:
        return (self.selected_input is not None and any(
            name == self.selected_input and peak > 0.001
            for name, peak in self.input_peaks
        ))

    @property
    def usable_output_candidate(self) -> bool:
        return (self.selected_input is not None and self.selected_meter_events > 0
                and self.selected_signal and self.selected_muted is False
                and self.selected_volume is not None and self.selected_volume > 0.001
                and not self.selected_route_changed)


@dataclass(frozen=True)
class ActualObsAudioRoute:
    """Read-only candidate evidence for an OBS program audio input.

    Direct scene-item and OBS global-audio routing are checked separately,
    together with monitor mode and enabled mix tracks. Even an enabled track
    does not prove the encoder selected that track or viewers hear speech.
    """
    scene: str
    input_name: str
    origin: str
    identity: tuple[str, ...]
    # Real OBS v5 GetInputAudioTracks evidence (1..6). A meter can be active
    # even when no audio track is enabled, so identity alone is insufficient.
    enabled_tracks: tuple[int, ...] = ()

    @property
    def confirmed(self) -> bool:
        return bool(self.identity) and bool(self.enabled_tracks)


@dataclass(frozen=True)
class ActualObsProgramMediaObservation:
    """Two read-only OBS media observations in one operator-approved check.

    A scene image and an input meter are separate OBS data sources. Matching
    program-scene snapshots only rule out an observed scene/stream switch;
    they cannot prove TTS audio reaches the broadcast encoder or audience.
    """
    before: ActualObsState
    after_frame: ActualObsState
    after_meter: ActualObsState
    frame: ActualObsFrame
    audio: ActualObsAudioMeters
    before_audio_route: ActualObsAudioRoute
    after_audio_route: ActualObsAudioRoute
    # A final OBS status snapshot must follow the last route query: a scene
    # may change while GetSceneItemList/GetSpecialInputs is in flight.
    after_route: ActualObsState | None = None
    # 승인받은 현재 OBS 프로그램 장면을 음성 미터 관찰 전후에
    # 각각 읽는다. 영상 프레임 원본은 저장하지 않고 메모리만 사용한다.
    after_audio_frame: ActualObsFrame | None = None

    @property
    def program_video_change_candidate(self) -> bool:
        """OBS 프로그램 화면의 서로 다른 두 PNG 관측 후보.

        변경이 보이더라도 원인이 Cubism 입인지 장면의 다른 요소인지
        이 결과 하나로는 구분할 수 없고, 실제 방송 출력 증거도 아니다.
        """
        other = self.after_audio_frame
        return bool(
            other is not None and self.stable_program_scene
            and self.frame.scene == other.scene
            and self.frame.width == other.width
            and self.frame.height == other.height
            and bool(self.frame.png_data) and bool(other.png_data)
            and self.frame.png_data != other.png_data
        )

    @property
    def selected_audio_route_stable(self) -> bool:
        return (self.before_audio_route.confirmed
                and self.before_audio_route == self.after_audio_route
                and self.before_audio_route.scene == self.frame.scene
                and self.before_audio_route.input_name == self.audio.selected_input)

    @property
    def stable_program_scene(self) -> bool:
        states = (self.before, self.after_frame, self.after_meter)
        if self.after_route is not None:
            states += (self.after_route,)
        return (all(state.scene == self.frame.scene for state in states)
                and all(state.streaming == self.before.streaming for state in states))

    @property
    def coherent_media_candidate(self) -> bool:
        # A final OBS status read and the exact selected audio input must
        # both agree before these separate observations form one candidate.
        # This still does not prove encoder or audience delivery.
        return (self.after_route is not None and self.stable_program_scene
                and self.audio.usable_output_candidate
                and self.selected_audio_route_stable)


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
            input_names = []
            for item in inputs:
                if not isinstance(item, dict):
                    raise ValueError('OBS 오디오 입력 형식이 올바르지 않습니다.')
                input_kind = item.get('inputKind', '')
                input_name = item.get('inputName')
                if not isinstance(input_kind, str) or not isinstance(input_name, str):
                    raise ValueError('OBS 오디오 입력 형식이 올바르지 않습니다.')
                # List all input names, not just those heuristically identified
                # as audio; the operator must decide if a TTS input exists.
                if (not input_name or input_name != input_name.strip()
                        or any(ord(char) < 32 for char in input_name)
                        or input_name in input_names):
                    raise ValueError('OBS 입력 이름이 비어 있거나 중복·손상되었습니다.')
                audios.append(input_name + ' (' + input_kind + ')')
                input_names.append(input_name)
            # The scene can change while OBS enumerates items and inputs.
            # Do not populate the operator's exact-input picker from an
            # inventory labeled with an earlier program scene.
            observed_after = self.status()
            if (observed_after.scene != actual.scene
                    or observed_after.streaming != actual.streaming):
                raise ValueError('OBS 입력 목록 조회 도중 장면/송출 상태가 변경되었습니다.')
            return ActualObsInventory(
                actual.scene, tuple(names), tuple(audios), tuple(input_names)
            )
        except ObsConnectionError:
            raise
        except Exception as exc:
            raise ObsConnectionError('실제 OBS 장면/입력 소스 조회 실패') from exc


    def _read_nested_scene_items(self, scene: str, root_items: list[dict]):
        """Read enabled OBS v5 nested scenes AND groups without OBS writes.

        A group is not included in GetSceneList: OBS exposes it through
        GetGroupList/GetGroupSceneItemList. Retain the parent source UUID in
        each path, so replacing a group cannot look like a stable audio route.
        Missing/invalid identities never become confirmed routing evidence.
        """
        nested_types = ('OBS_SOURCE_TYPE_SCENE', 'OBS_SOURCE_TYPE_GROUP')
        if not any(isinstance(item, dict) and
                   item.get('sourceType') in nested_types for item in root_items):
            return ()
        known_scenes: dict[str, str] | None = None
        known_groups: frozenset[str] | None = None

        def scene_uuid(name: str) -> str | None:
            nonlocal known_scenes
            if known_scenes is None:
                scene_list = self._client.get_scene_list().scenes
                if not isinstance(scene_list, list):
                    raise ValueError('OBS 장면 목록 형식이 올바르지 않습니다.')
                known_scenes = {}
                for entry in scene_list:
                    if not isinstance(entry, dict):
                        raise ValueError('OBS 장면 식별자 형식이 올바르지 않습니다.')
                    entry_name, uuid = entry.get('sceneName'), entry.get('sceneUuid')
                    if (not isinstance(entry_name, str) or not entry_name
                            or not isinstance(uuid, str) or not uuid
                            or entry_name in known_scenes):
                        raise ValueError('OBS 장면 이름/UUID가 중복되거나 유효하지 않습니다.')
                    known_scenes[entry_name] = uuid
            return known_scenes.get(name)

        def group_exists(name: str) -> bool:
            nonlocal known_groups
            if known_groups is None:
                groups = self._client.get_group_list().groups
                if (not isinstance(groups, list)
                        or any(not isinstance(n, str) or not n for n in groups)
                        or len(set(groups)) != len(groups)):
                    raise ValueError('OBS 그룹 목록이 중복되거나 유효하지 않습니다.')
                known_groups = frozenset(groups)
            return name in known_groups

        found = []
        budget = 0

        def visit(items, parents, path, depth):
            nonlocal budget
            if not isinstance(items, list):
                raise ValueError('OBS 중첩 장면/그룹 항목 형식이 올바르지 않습니다.')
            for item in items:
                budget += 1
                if budget > 400:
                    raise ValueError('OBS 중첩 장면/그룹 항목이 검사 한도를 초과했습니다.')
                if not isinstance(item, dict):
                    raise ValueError('OBS 중첩 장면/그룹 소스 형식이 올바르지 않습니다.')
                if item.get('sceneItemEnabled') is not True:
                    continue
                item_id = item.get('sceneItemId')
                name = item.get('sourceName')
                if type(item_id) is not int or item_id < 0 or not isinstance(name, str):
                    continue
                source_uuid = item.get('sourceUuid')
                current = path + ((name, item_id, source_uuid),)
                if path:
                    found.append((current, item))
                kind = item.get('sourceType')
                if depth >= 6 or name in parents:
                    continue
                if kind == 'OBS_SOURCE_TYPE_SCENE':
                    if scene_uuid(name) != source_uuid:
                        continue
                    children = self._client.get_scene_item_list(name).scene_items
                elif kind == 'OBS_SOURCE_TYPE_GROUP':
                    # GetGroupList returns names, not UUIDs. The parent
                    # scene-item UUID is therefore required and included in
                    # the before/after route identity comparison.
                    if (not isinstance(source_uuid, str) or not source_uuid
                            or not group_exists(name)):
                        continue
                    children = self._client.get_group_scene_item_list(name).scene_items
                else:
                    continue
                visit(children, parents | {name}, current, depth + 1)

        visit(root_items, frozenset({scene}), (), 0)
        return tuple(found)

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
            # Keep immutable identity snapshots before any later OBS request.
            # OBS can replace a nested group/input while settings are read,
            # without changing the current program scene or stream status.
            def source_identity(rows):
                return tuple((row.get('sourceName'), row.get('sourceUuid'),
                              row.get('sceneItemId'), row.get('sourceType'),
                              row.get('sceneItemEnabled')) for row in rows)

            def input_identity(rows):
                return tuple((row.get('inputName'), row.get('inputUuid'),
                              row.get('inputKind')) for row in rows)

            if any(not isinstance(row, dict) for row in scene_items + inputs):
                raise ValueError('OBS 장면/입력 소스 항목 형식이 올바르지 않습니다.')
            scene_before = source_identity(scene_items)
            inputs_before = input_identity(inputs)
            captures: list[str] = []
            audio: list[str] = []
            problems: list[str] = []
            # OBS can retarget an existing window/game capture without
            # changing the scene item or input UUID. Preserve a deep copy of
            # the settings observed for each enabled capture candidate.
            capture_settings_before: dict[str, dict[str, Any]] = {}
            # Mute and gain are part of the reported OBS audio path, too.
            # Recheck these exact read-only controls after inspecting the
            # other sources; an input can be muted without changing its UUID.
            audio_controls_before: dict[str, tuple[bool, float]] = {}
            # Official OBS WebSocket v5 GetSceneItemList does NOT include
            # inputKind. GetInputList contains inputKind and inputUuid;
            # resolve the scene source against that real input identity.
            # Matching a name alone can mislabel a replaced scene source.
            input_by_name: dict[str, list[dict[str, Any]]] = {}
            for entry in inputs:
                if isinstance(entry, dict) and isinstance(entry.get('inputName'), str):
                    input_by_name.setdefault(entry['inputName'], []).append(entry)
            capture_kinds = ('window_capture', 'game_capture', 'monitor_capture')
            for item in scene_items[:100]:
                if not isinstance(item, dict):
                    raise ValueError('OBS 장면 소스 형식이 올바르지 않습니다.')
                name = item.get('sourceName')
                item_kind = item.get('inputKind', '')
                if not isinstance(name, str) or not isinstance(item_kind, str):
                    raise ValueError('OBS 장면 소스 필드가 올바르지 않습니다.')
                matched = input_by_name.get(name, [])
                source_uuid = item.get('sourceUuid')
                if len(matched) == 1:
                    source = matched[0]
                    actual_kind = source.get('inputKind', '')
                    input_uuid = source.get('inputUuid')
                    if not isinstance(actual_kind, str):
                        raise ValueError('OBS 입력 종류가 올바르지 않습니다.')
                    if (isinstance(source_uuid, str) and source_uuid
                            and isinstance(input_uuid, str) and input_uuid
                            and source_uuid == input_uuid):
                        kind = actual_kind
                    else:
                        # A scene item and an input with the same name are
                        # not necessarily the same OBS source. Fail closed.
                        kind = ''
                elif (not matched and not source_uuid
                      and item_kind in capture_kinds):
                    # Preserve the existing legacy/plugin scene-item display
                    # when it explicitly supplies inputKind but no UUID. This
                    # is only a capture candidate, never verified OBS routing.
                    kind = item_kind
                else:
                    kind = ''
                if kind not in capture_kinds:
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
                        capture_settings_before[name] = deepcopy(settings)
                        window = settings.get('window', '')
                        if isinstance(window, str) and window:
                            configured = ' / 선택된 창 ' + window[:140]
                    else:
                        problems.append(name + ': 창 설정 형식을 확인할 수 없음')
                except Exception:
                    problems.append(name + ': 창 설정 세부 정보 조회 불가')
                captures.append(name + ' (' + kind + ', 활성)' + configured)
            # A Live2D capture may be inside an enabled nested OBS scene.
            # The nested scene itself is a scene source, not an input, and
            # its source UUID must match the actual GetSceneList scene UUID.
            nested_before = self._read_nested_scene_items(actual.scene, scene_items)
            # Paths are immutable, unlike the dicts returned by a client.
            # Include each child's enabled/type state in the snapshot.
            nested_identity_before = tuple((path, item.get('sourceType'),
                                            item.get('sceneItemEnabled'))
                                           for path, item in nested_before)
            for path, item in nested_before:
                name = item.get('sourceName')
                source_uuid = item.get('sourceUuid')
                matches = input_by_name.get(name, [])
                if len(matches) != 1:
                    continue
                entry = matches[0]
                kind = entry.get('inputKind')
                if (not isinstance(kind, str) or kind not in capture_kinds
                        or not isinstance(source_uuid, str) or not source_uuid
                        or source_uuid != entry.get('inputUuid')):
                    continue
                # Every parent in path was enabled and UUID-checked.
                # An OBS scene-item name alone never certifies a capture.
                path_name = ' / '.join(part[0] for part in path)
                configured = ''
                try:
                    settings = self._client.get_input_settings(name).input_settings
                    if isinstance(settings, dict):
                        capture_settings_before[name] = deepcopy(settings)
                        window = settings.get('window', '')
                        if isinstance(window, str) and window:
                            configured = ' / 선택된 창 ' + window[:140]
                    else:
                        problems.append(path_name + ': 창 설정 형식을 확인할 수 없음')
                except Exception:
                    problems.append(path_name + ': 창 설정 세부 정보 조회 불가')
                captures.append(path_name + ' (' + kind + ', 활성)' + configured)
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
                    if (type(muted) is not bool or type(gain) not in (float, int)
                            or not math.isfinite(gain) or not 0 <= gain <= 1000):
                        raise ValueError('OBS 음소거/볼륨 데이터 오류')
                    audio_controls_before[name] = (muted, float(gain))
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
            # OBS may replace a group, its child capture, or an input while
            # the program scene/stream stays unchanged. Re-read the real v5
            # source identities after settings/mute/volume reads. A stale
            # capture candidate must never be labeled as the current path.
            current_scene = self._client.get_scene_item_list(actual.scene).scene_items
            current_inputs = self._client.get_input_list().inputs
            if (not isinstance(current_scene, list) or not isinstance(current_inputs, list)
                    or any(not isinstance(row, dict)
                           for row in current_scene + current_inputs)
                    or source_identity(current_scene) != scene_before
                    or input_identity(current_inputs) != inputs_before):
                raise ValueError('OBS 경로 검사 도중 장면 항목/입력 UUID가 변경되었습니다.')
            nested_after = self._read_nested_scene_items(actual.scene, current_scene)
            nested_identity_after = tuple((path, item.get('sourceType'),
                                           item.get('sceneItemEnabled'))
                                          for path, item in nested_after)
            if nested_identity_before != nested_identity_after:
                raise ValueError('OBS 경로 검사 도중 중첩 장면/그룹 경로가 변경되었습니다.')
            # A capture can switch its selected window, capture mode or
            # plugin settings while its OBS input UUID remains unchanged.
            # Re-read only the captures we actually inspected. Never report
            # the earlier window selection as a stable current path.
            for name, before_settings in capture_settings_before.items():
                after_settings = self._client.get_input_settings(name).input_settings
                if (not isinstance(after_settings, dict)
                        or after_settings != before_settings):
                    raise ValueError('OBS 경로 검사 도중 캡처 설정이 변경되었습니다: ' + name)
            # Mute and volume can change without any OBS scene, input UUID,
            # or capture setting change. Never display an obsolete "unmuted"
            # audio route as if it were the current program configuration.
            for name, (before_muted, before_gain) in audio_controls_before.items():
                after_muted = self._client.get_input_mute(name).input_muted
                after_gain = self._client.get_input_volume(name).input_volume_mul
                if (type(after_muted) is not bool
                        or type(after_gain) not in (int, float)
                        or not math.isfinite(after_gain)
                        or not 0 <= after_gain <= 1000
                        or after_muted != before_muted
                        or not math.isclose(float(after_gain), before_gain,
                                            rel_tol=1e-6, abs_tol=1e-9)):
                    raise ValueError('OBS 경로 검사 도중 오디오 음소거/음량이 변경되었습니다: ' + name)
            # GetSceneItemList, GetInputList, mute, volume and input settings
            # are separate real OBS requests. A scene or stream transition
            # during those reads must not be presented as one program path.
            observed_after = self.status()
            if (observed_after.scene != actual.scene
                    or observed_after.streaming != actual.streaming):
                raise ValueError('OBS 경로 검사 도중 장면/송출 상태가 변경되었습니다.')
            return ActualObsMediaPath(tuple(captures), tuple(audio), tuple(problems))
        except Exception as exc:
            raise ObsConnectionError('OBS 화면 캡처/오디오 경로 상세 읽기 실패') from exc


    def read_current_scene_frame(self, *, operator_approved: bool = False) -> ActualObsFrame:
        """Obtain a REAL current program scene image directly from OBS.

        Read-only GetSourceScreenshot; does not save to disk, change an OBS
        scene, enable capture sources, record video, or start broadcasting.
        The operator must approve exposing potentially private desktop pixels
        inside this local AISTING application for this particular request.
        """
        if operator_approved is not True:
            raise PermissionError('현재 OBS 실제 화면 프레임 검사 승인이 필요합니다.')
        actual = self.status()
        if self._client is None:
            raise ObsConnectionError('실제 OBS에 먼저 연결해야 합니다.')
        try:
            result = self._client.get_source_screenshot(
                actual.scene, 'png', 640, 360, -1
            )
            encoded = result.image_data
            if (not isinstance(encoded, str)
                    or not encoded.startswith('data:image/png;base64,')
                    or len(encoded) > 4_000_000):
                raise ValueError('OBS가 실제 PNG 영상 프레임을 반환하지 않았습니다.')
            binary = base64.b64decode(
                encoded[len('data:image/png;base64,'):], validate=True
            )
            if len(binary) < 45 or len(binary) > 2_500_000:
                raise ValueError('OBS 화면 프레임 용량이 유효하지 않습니다.')
            if (binary[:8] != b'\x89PNG\r\n\x1a\n'
                    or binary[12:16] != b'IHDR'):
                raise ValueError('OBS 영상 프레임의 PNG 헤더가 유효하지 않습니다.')
            width = int.from_bytes(binary[16:20], 'big')
            height = int.from_bytes(binary[20:24], 'big')
            if not 1 <= width <= 640 or not 1 <= height <= 360:
                raise ValueError('OBS 영상 크기가 비정상적입니다.')
            # Validate actual PNG chunk boundaries and CRCs. A correct IHDR
            # alone can be followed by truncated/corrupt image data; that is
            # not an OBS-rendered frame we can reliably show to the operator.
            offset, idat_seen, iend_seen = 8, False, False
            idat_ended, palette_seen = False, False
            idat_parts = []
            while offset + 12 <= len(binary):
                chunk_size = int.from_bytes(binary[offset:offset + 4], 'big')
                chunk_end = offset + 12 + chunk_size
                if chunk_end > len(binary):
                    raise ValueError('OBS PNG 청크 데이터가 잘렸습니다.')
                chunk_type = binary[offset + 4:offset + 8]
                actual_crc = int.from_bytes(binary[chunk_end - 4:chunk_end], 'big')
                expected_crc = zlib.crc32(binary[offset + 4:chunk_end - 4]) & 0xffffffff
                if actual_crc != expected_crc:
                    raise ValueError('OBS PNG 이미지 데이터 무결성(CRC) 오류')
                # A decodable zlib payload alone is not a valid PNG: the
                # critical chunks must follow the PNG-defined ordering.
                if (len(chunk_type) != 4 or any(
                        not (65 <= byte <= 90 or 97 <= byte <= 122)
                        for byte in chunk_type)):
                    raise ValueError('OBS PNG 청크 이름이 유효하지 않습니다.')
                if chunk_type == b'IHDR':
                    if offset != 8 or chunk_size != 13:
                        raise ValueError('OBS PNG 헤더가 중복되거나 손상되었습니다.')
                elif chunk_type == b'PLTE':
                    color_type = binary[25]
                    depth = binary[24]
                    if (palette_seen or idat_seen or color_type in (0, 4)
                            or chunk_size == 0 or chunk_size % 3 != 0
                            or chunk_size > 768
                            or (color_type == 3 and chunk_size // 3 > (1 << depth))):
                        raise ValueError('OBS PNG 색상 팔레트 순서/형식 오류')
                    palette_seen = True
                elif chunk_type == b'IDAT':
                    if idat_ended or (binary[25] == 3 and not palette_seen):
                        raise ValueError('OBS PNG 이미지 데이터 청크 순서 오류')
                    idat_seen = True
                    idat_parts.append(binary[offset + 8:chunk_end - 4])
                elif chunk_type not in (b'IEND',):
                    # Unrecognized critical chunks cannot be safely ignored.
                    if not (chunk_type[0] & 0x20):
                        raise ValueError('OBS PNG 알 수 없는 필수 청크가 있습니다.')
                if idat_seen and chunk_type not in (b'IDAT', b'IEND'):
                    idat_ended = True
                if chunk_type == b'IEND':
                    if chunk_size != 0 or chunk_end != len(binary):
                        raise ValueError('OBS PNG 종료 청크 형식이 올바르지 않습니다.')
                    iend_seen = True
                    break
                offset = chunk_end
            if not idat_seen or not iend_seen:
                raise ValueError('OBS PNG 영상 데이터 또는 종료 청크가 없습니다.')
            # Chunk CRC alone does not establish that PNG image data can be
            # decoded. Check the actual bounded zlib stream before passing
            # the frame to Tk's PhotoImage (which otherwise may raise).
            inflater = zlib.decompressobj()
            try:
                pixels = inflater.decompress(b''.join(idat_parts), 2_500_001)
            except zlib.error as exc:
                raise ValueError('OBS PNG 압축 영상 데이터가 손상되었습니다.') from exc
            if (not pixels or len(pixels) > 2_500_000 or not inflater.eof
                    or inflater.unused_data or inflater.unconsumed_tail):
                raise ValueError('OBS PNG 압축 영상 데이터가 손상되었습니다.')
            # Check the actual scanline layout for non-interlaced PNG frames.
            # This rejects valid-zlib-but-incomplete pixel data that Tk cannot
            # display, without installing an image decoder or changing OBS.
            depth, color, compression, filter_method, interlace = binary[24:29]
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
            depths = {0: (1, 2, 4, 8, 16), 2: (8, 16),
                      3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
            if (channels is None or depth not in depths[color]
                    or int.from_bytes(binary[8:12], 'big') != 13
                    or compression != 0 or filter_method != 0
                    or interlace not in (0, 1)):
                raise ValueError('OBS PNG 픽셀 형식이 올바르지 않습니다.')
            if interlace == 0:
                row_bytes = (width * channels * depth + 7) // 8
                stride = row_bytes + 1
                if (len(pixels) != stride * height
                        or any(pixels[row * stride] > 4 for row in range(height))):
                    raise ValueError('OBS PNG 실제 픽셀 행 데이터가 손상되었습니다.')
            else:
                # Adam7 interlacing has seven separately filtered passes.
                # Previously any nonempty decompressed data was accepted when
                # IHDR declared interlace=1, even if its rows were missing.
                # Validate the exact scanline layout before Tk receives it.
                passes = (
                    (0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8),
                    (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2),
                    (0, 1, 1, 2),
                )
                offset = 0
                for x0, y0, dx, dy in passes:
                    pass_width = max(0, (width - x0 + dx - 1) // dx)
                    pass_height = max(0, (height - y0 + dy - 1) // dy)
                    if not pass_width or not pass_height:
                        continue
                    row_bytes = (pass_width * channels * depth + 7) // 8
                    stride = row_bytes + 1
                    end = offset + stride * pass_height
                    if end > len(pixels):
                        raise ValueError('OBS PNG Adam7 픽셀 행 데이터가 잘렸습니다.')
                    if any(pixels[offset + row * stride] > 4
                           for row in range(pass_height)):
                        raise ValueError('OBS PNG Adam7 픽셀 필터가 손상되었습니다.')
                    offset = end
                if offset != len(pixels):
                    raise ValueError('OBS PNG Adam7 픽셀 데이터 길이가 일치하지 않습니다.')
            # The OBS program scene can change while GetSourceScreenshot is
            # in flight. Never label an image as the old program scene if a
            # second real OBS status read already shows a different scene.
            # A screenshot remains image evidence only, not stream evidence.
            observed_after = self.status()
            if observed_after.scene != actual.scene:
                raise ValueError('OBS PNG 요청 도중 프로그램 장면이 변경되었습니다.')
            return ActualObsFrame(actual.scene, width, height, binary)
        except (OSError, ValueError, TypeError, binascii.Error) as exc:
            raise ObsConnectionError('실제 OBS PNG 화면 읽기·검증 실패: ' + str(exc)) from exc
        except Exception as exc:
            raise ObsConnectionError('실제 OBS에서 화면 프레임을 가져오지 못했습니다.') from exc

    def read_actual_audio_meters(self, *, operator_approved: bool = False,
                                 duration: float = 3.0,
                                 input_name: str | None = None,
                                 start_action=None) -> ActualObsAudioMeters:
        """Observe selected OBS input events without recording or changing OBS.

        Meter peaks are not proof of GPT-SoVITS speech or stream delivery.
        The selected input's identity, mute and gain are checked before and
        after the observation, so stale meter events do not certify a new path.
        A supplied operator-authorized start_action is invoked ONLY after
        the meter subscription is registered; by default NO OBS input changes
        are made. The caller owns all source-identity and stream safety checks.
        """
        if operator_approved is not True:
            raise PermissionError('실제 OBS 오디오 미터 관찰 승인이 필요합니다.')
        if start_action is not None and (input_name is None or not callable(start_action)):
            raise ValueError('실제 지정 음성 입력과 승인된 재생 작업이 필요합니다.')
        if type(duration) not in (int, float) or not 1 <= duration <= 8:
            raise ValueError('OBS 미터 관찰 기간은 1~8초여야 합니다.')
        if input_name is not None and (
                not isinstance(input_name, str) or not 1 <= len(input_name) <= 128
                or input_name != input_name.strip()
                or any(ord(char) < 32 for char in input_name)):
            raise ValueError('OBS 오디오 입력 이름을 정확히 지정해야 합니다.')
        if self._client is None:
            raise ObsConnectionError('실제 OBS에 먼저 연결해야 합니다.')
        selected_muted = None
        selected_volume = None
        selected_uuid = None
        if input_name is not None:
            try:
                inventory = self._client.get_input_list().inputs
                if not isinstance(inventory, list):
                    raise ValueError('OBS 입력 목록 응답이 올바르지 않습니다.')
                matches = [item for item in inventory
                           if isinstance(item, dict)
                           and item.get('inputName') == input_name]
                if len(matches) != 1:
                    raise ObsConnectionError(
                        '선택한 OBS 오디오 입력을 유일하게 확인하지 못했습니다.'
                    )
                value = matches[0].get('inputUuid')
                if not isinstance(value, str) or not value.strip():
                    raise ObsConnectionError(
                        '선택 OBS 입력의 UUID를 확인하지 못해 동일 이름 재생성 여부를 검증할 수 없습니다.'
                    )
                selected_uuid = value
            except ObsConnectionError:
                raise
            except Exception as exc:
                raise ObsConnectionError('실제 OBS 오디오 입력 목록 조회 실패') from exc
            try:
                muted = self._client.get_input_mute(input_name).input_muted
                volume = self._client.get_input_volume(input_name).input_volume_mul
                if (type(muted) is not bool or type(volume) not in (int, float)
                        or not math.isfinite(volume) or not 0 <= volume <= 1000):
                    raise ValueError('선택 OBS 입력의 음소거/음량 응답 오류')
                selected_muted, selected_volume = muted, float(volume)
            except Exception as exc:
                raise ObsConnectionError('선택 OBS 오디오 입력의 음소거/음량 조회 실패') from exc
        try:
            import obsws_python
        except ImportError as exc:
            raise ObsConnectionError('OBS WebSocket 오디오 이벤트 패키지가 없습니다.') from exc
        lock = threading.Lock()
        peaks: dict[str, float] = {}
        count = 0
        selected_meter_events = 0
        first_selected_signal_monotonic = 0.0
        last_selected_signal_monotonic = 0.0

        def on_input_volume_meters(data: object) -> None:
            nonlocal count, selected_meter_events
            nonlocal first_selected_signal_monotonic, last_selected_signal_monotonic
            inputs = getattr(data, 'inputs', None)
            if not isinstance(inputs, list):
                return
            with lock:
                count += 1
                for item in inputs[:100]:
                    if not isinstance(item, dict):
                        continue
                    name = item.get('inputName')
                    levels = item.get('inputLevelsMul')
                    if input_name is not None and name != input_name:
                        continue
                    if (not isinstance(name, str) or not name.strip()
                            or not isinstance(levels, list)):
                        continue
                    channel_peaks = []
                    for channel in levels[:8]:
                        if not isinstance(channel, list):
                            continue
                        channel_peaks.extend(float(v) for v in channel[:3]
                                             if type(v) in (int, float)
                                             and 0 <= v <= 20 and math.isfinite(v))
                    if channel_peaks:
                        peaks[name] = max(peaks.get(name, 0.0), max(channel_peaks))
                        if input_name is not None and name == input_name:
                            selected_meter_events += 1
                            if max(channel_peaks) > 0.001:
                                sampled_at = time.monotonic()
                                if not first_selected_signal_monotonic:
                                    first_selected_signal_monotonic = sampled_at
                                last_selected_signal_monotonic = sampled_at

        events = None
        try:
            events = obsws_python.EventClient(
                host='127.0.0.1', port=self._port, password=self._password,
                subs=obsws_python.Subs.INPUTVOLUMEMETERS, timeout=5,
            )
            events.callback.register(on_input_volume_meters)
            # Register FIRST, then optionally restart the caller's freshly
            # created temporary OBS media source. Otherwise the beginning
            # (or all) of a short generated Korean utterance is missed.
            if start_action is not None:
                start_action()
            threading.Event().wait(float(duration))
        except Exception as exc:
            raise ObsConnectionError('실제 OBS 오디오 미터 이벤트 관찰 실패') from exc
        finally:
            if events is not None:
                try:
                    events.disconnect()
                except Exception as exc:
                    raise ObsConnectionError('OBS 오디오 미터 이벤트 연결 종료 실패') from exc
        route_changed = False
        if input_name is not None:
            try:
                current = self._client.get_input_list().inputs
                if not isinstance(current, list):
                    raise ValueError('OBS 입력 목록 응답 형식 오류')
                current_matches = [item for item in current
                                   if isinstance(item, dict)
                                   and item.get('inputName') == input_name]
                if len(current_matches) != 1:
                    route_changed = True
                else:
                    if current_matches[0].get('inputUuid') != selected_uuid:
                        route_changed = True
                    after_muted = self._client.get_input_mute(input_name).input_muted
                    after_volume = self._client.get_input_volume(input_name).input_volume_mul
                    if (type(after_muted) is not bool or
                            type(after_volume) not in (int, float) or
                            not math.isfinite(after_volume) or
                            not 0 <= after_volume <= 1000):
                        raise ValueError('OBS 최종 음량 응답 형식 오류')
                    route_changed = route_changed or (selected_muted != after_muted or
                        not math.isclose(selected_volume, float(after_volume),
                                         rel_tol=1e-6, abs_tol=1e-9))
            except Exception as exc:
                raise ObsConnectionError('OBS 미터 관찰 후 입력 상태 재확인 실패') from exc
        with lock:
            return ActualObsAudioMeters(
                count, tuple(sorted(peaks.items())), input_name,
                selected_muted, selected_volume, selected_meter_events,
                route_changed,
                first_selected_signal_monotonic,
                last_selected_signal_monotonic,
            )


    def read_program_audio_route(self, *, input_name: str,
                                 scene: str) -> ActualObsAudioRoute:
        """Inspect OBS scene/global routing without altering audio or stream.

        OBS audio meters may be active even for inputs that do not reach the
        current program scene. Only a uniquely identifiable enabled scene
        item, or an OBS global audio device, counts as route evidence. Nested
        scenes and plugin-defined routing remain unconfirmed, not successful.
        """
        if self._client is None:
            raise ObsConnectionError('실제 OBS에 먼저 연결해야 합니다.')
        if (not isinstance(input_name, str) or not input_name.strip()
                or not isinstance(scene, str) or not scene.strip()):
            raise ValueError('OBS 장면과 입력 이름이 필요합니다.')
        try:
            # Scene-item names are not OBS input identities. Compare the
            # actual input UUID to the scene source UUID, and preserve that
            # identity even for OBS global audio (not a scene item).
            inputs = self._client.get_input_list().inputs
            if not isinstance(inputs, list):
                raise ValueError('OBS 입력 목록이 올바르지 않습니다.')
            matches = [entry for entry in inputs
                       if isinstance(entry, dict)
                       and entry.get('inputName') == input_name]
            if len(matches) != 1:
                raise ValueError('선택한 OBS 입력 이름이 유일하지 않거나 존재하지 않습니다.')
            input_uuid = matches[0].get('inputUuid')
            if not isinstance(input_uuid, str) or not input_uuid.strip():
                raise ValueError('선택한 OBS 입력 UUID가 없습니다.')
            # A meter can show sound even when monitoring is ONLY or every
            # OBS mix track is disabled. Use the actual OBS v5 read-only
            # GetInputAudioMonitorType + GetInputAudioTracks responses. Both
            # must be available before describing a program route as a
            # candidate; neither proves the selected stream encoder track.
            try:
                monitor_type = self._client.get_input_audio_monitor_type(
                    input_name).monitor_type
            except Exception:
                return ActualObsAudioRoute(scene, input_name, 'monitor-unconfirmed', ())
            if monitor_type not in (
                    'OBS_MONITORING_TYPE_NONE',
                    'OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT'):
                return ActualObsAudioRoute(scene, input_name, 'monitor-only-or-unknown', ())
            try:
                tracks = self._client.get_input_audio_tracks(
                    input_name).input_audio_tracks
            except Exception:
                return ActualObsAudioRoute(scene, input_name, 'tracks-unconfirmed', ())
            if (not isinstance(tracks, dict)
                    or set(tracks) != {str(i) for i in range(1, 7)}
                    or any(type(value) is not bool for value in tracks.values())):
                return ActualObsAudioRoute(scene, input_name, 'tracks-invalid', ())
            enabled_tracks = tuple(i for i in range(1, 7)
                                   if tracks[str(i)] is True)
            if not enabled_tracks:
                return ActualObsAudioRoute(scene, input_name, 'tracks-disabled', ())
            items = self._client.get_scene_item_list(scene).scene_items
            if not isinstance(items, list):
                raise ValueError('OBS 장면 항목 목록이 올바르지 않습니다.')
            identities = []
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError('OBS 장면 항목 형식이 올바르지 않습니다.')
                if item.get('sourceName') != input_name:
                    continue
                if item.get('sceneItemEnabled') is not True:
                    continue
                item_id = item.get('sceneItemId')
                if type(item_id) is not int or item_id < 0:
                    # Do not call a name-only match verified routing.
                    continue
                uuid = item.get('sourceUuid')
                if uuid != input_uuid:
                    # Same-name scene source can be a different input.
                    # Missing UUID must not become a verified audio route.
                    continue
                identities.append(str(item_id) + ':' + input_uuid)
            direct = bool(identities)
            # OBS commonly nests a dedicated avatar/audio scene inside the
            # program scene. Resolve only enabled, UUID-verified scene chains.
            for path, item in self._read_nested_scene_items(scene, items):
                if (item.get('sourceName') == input_name
                        and item.get('sourceUuid') == input_uuid):
                    # Retain the UUID of *each* nested scene as well as
                    # its item ID. Equality of before/after route snapshots
                    # must fail if OBS replaces an intermediate scene.
                    identities.append('/'.join(
                        str(part[1]) + '@' + str(part[2]) for part in path
                    ))
            if identities:
                return ActualObsAudioRoute(
                    scene, input_name,
                    'enabled-scene-item' if direct else 'enabled-nested-scene-item',
                    tuple(sorted(identities)), enabled_tracks
                )
            # Global Desktop Audio/Mic inputs are not listed as scene items.
            # OBS WebSocket GetSpecialInputs is a read-only v5 request.
            try:
                special = self._client.get_special_inputs()
            except Exception:
                special = None
            if special is not None:
                # obsws-python GetSpecialInputs exposes desktop1/desktop2,
                # not desktop_audio1/desktop_audio2. Match real OBS v5 fields.
                keys = ('desktop1', 'desktop2', 'mic1', 'mic2', 'mic3', 'mic4')
                matched = tuple(key for key in keys
                                if getattr(special, key, None) == input_name)
                if matched:
                    return ActualObsAudioRoute(
                        scene, input_name, 'global-audio',
                        tuple(key + ':' + input_uuid for key in matched), enabled_tracks,
                    )
            return ActualObsAudioRoute(scene, input_name, 'unconfirmed', ())
        except ObsConnectionError:
            raise
        except Exception as exc:
            raise ObsConnectionError('OBS 실제 장면의 선택 오디오 입력 경로 조회 실패') from exc


    def inspect_program_media(self, *, operator_approved: bool = False,
                              input_name: str, duration: float = 3.0,
                              observe_program_motion: bool = False
                              ) -> ActualObsProgramMediaObservation:
        """Read one real OBS scene frame and the selected input's meter.

        Never starts/stops a stream, changes OBS routing, records samples, or
        sends media anywhere. Requires the same operator approval as each
        constituent read. Detects observed scene or stream changes between
        the two reads so they are not presented as one stable media path.
        """
        if operator_approved is not True:
            raise PermissionError('OBS 실제 화면·오디오 통합 관찰 승인이 필요합니다.')
        if type(observe_program_motion) is not bool:
            raise ValueError('OBS 영상 변화 관찰 선택값이 잘못되었습니다.')
        if (not isinstance(input_name, str) or not 1 <= len(input_name) <= 128
                or input_name != input_name.strip()
                or any(ord(char) < 32 for char in input_name)):
            raise ValueError('실제 OBS 오디오 입력 이름을 정확히 지정해야 합니다.')
        if (type(duration) not in (int, float) or not math.isfinite(duration)
                or not 1 <= duration <= 8):
            raise ValueError('OBS 미터 관찰 기간은 1~8초여야 합니다.')
        if self._client is None:
            raise ObsConnectionError('실제 OBS에 먼저 연결해야 합니다.')
        before = self.status()
        before_audio_route = self.read_program_audio_route(
            input_name=input_name, scene=before.scene,
        )
        frame = self.read_current_scene_frame(operator_approved=True)
        after_frame = self.status()
        # If the scene switched while capturing the image, do not attach
        # subsequent audio evidence to a different program scene.
        if (before.scene != frame.scene or after_frame.scene != frame.scene
                or before.streaming != after_frame.streaming):
            raise ObsConnectionError(
                'OBS 영상 검사 도중 장면/송출 상태가 변경되어 오디오 경로 결합을 중단했습니다.'
            )
        audio = self.read_actual_audio_meters(
            operator_approved=True, duration=duration, input_name=input_name,
        )
        # 기존 장면·오디오 읽기 흐름은 보존한다. 운영자가 위 통합 검사로
        # 요청한 경우에만 두 번째 실제 프로그램 영상 프레임을 가져온다.
        after_audio_frame = (
            self.read_current_scene_frame(operator_approved=True)
            if observe_program_motion else None
        )
        after_meter = self.status()
        if (after_audio_frame is not None
                and after_audio_frame.scene != frame.scene):
            raise ObsConnectionError(
                'OBS 후속 영상 프레임이 원래 프로그램 장면과 일치하지 않습니다.'
            )
        after_audio_route = self.read_program_audio_route(
            input_name=input_name, scene=after_meter.scene,
        )
        # Route inspection itself takes time. A selected OBS input can also
        # be muted or turned down *after* the meter observation while the
        # final route is queried, without changing its UUID or mix tracks.
        preliminary = ActualObsProgramMediaObservation(
            before=before, after_frame=after_frame, after_meter=after_meter,
            frame=frame, audio=audio,
            before_audio_route=before_audio_route,
            after_audio_route=after_audio_route,
            after_audio_frame=after_audio_frame,
        )
        # The final status read has not happened yet. Check the provisional
        # path explicitly here, then require the final OBS state in the
        # returned observation before reporting a coherent candidate.
        if (preliminary.stable_program_scene
                and preliminary.audio.usable_output_candidate
                and preliminary.selected_audio_route_stable):
            try:
                final_muted = self._client.get_input_mute(input_name).input_muted
                final_gain = self._client.get_input_volume(input_name).input_volume_mul
                if (type(final_muted) is not bool
                        or type(final_gain) not in (int, float)
                        or not math.isfinite(final_gain)
                        or not 0 <= final_gain <= 1000):
                    raise ValueError('OBS 최종 오디오 제어 응답 형식 오류')
            except Exception as exc:
                raise ObsConnectionError(
                    'OBS 최종 음소거/음량 상태를 확인하지 못해 통합 경로 검증을 중단했습니다.'
                ) from exc
            if (final_muted != audio.selected_muted
                    or not math.isclose(float(final_gain), audio.selected_volume,
                                        rel_tol=1e-6, abs_tol=1e-9)):
                audio = replace(audio, selected_route_changed=True)
        # Keep the last read as OBS program/stream state, so a scene switch
        # during the final audio-control reads is also detected. A single
        # PNG and meter still do NOT prove actual broadcast audio/video.
        after_route = self.status()
        return replace(preliminary, audio=audio, after_route=after_route)

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
