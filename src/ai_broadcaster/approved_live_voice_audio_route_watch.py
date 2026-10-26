"""승인된 실제 WAV OBS 임시 입력의 출력 경로를 변경 없이 관측한다.

OBS v5 GetInputAudioTracks/MonitorType, Mute, Volume 및 현재 프로그램
장면의 UUID 검증된 항목을 함께 확인한다. 출력 트랙 후보를 확인할
뿐 실제 스트림 인코더 선택 트랙/시청자 수신은 증명하지 않는다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from .original_plan_obs import OfficialObsWebsocket


@dataclass(frozen=True)
class LiveVoiceAudioRouteSample:
    scene: str
    source_uuid: str
    origin: str
    identities: tuple[str, ...]
    enabled_tracks: tuple[int, ...]
    volume_mul: float
    muted: bool


class ApprovedLiveVoiceAudioRouteGuard:
    """한 승인 WAV 재생 동안 오디오 출력 후보가 바뀌지 않았는지 관측."""

    def __init__(self, *, obs: OfficialObsWebsocket, scene: str,
                 input_name: str, source_uuid: str,
                 source_is_owned: Callable[[], bool]) -> None:
        if (not isinstance(obs, OfficialObsWebsocket)
                or type(scene) is not str or not scene
                or type(input_name) is not str or not input_name
                or type(source_uuid) is not str or not source_uuid
                or not callable(source_is_owned)):
            raise TypeError("OBS 한국어 음성 오디오 경로 감시 대상 오류")
        self._obs = obs
        self._scene = scene
        self._input_name = input_name
        self._uuid = source_uuid
        self._source_is_owned = source_is_owned
        self._baseline: LiveVoiceAudioRouteSample | None = None
        self._samples = 0
        self._minimum_volume = float("inf")

    def sample(self) -> LiveVoiceAudioRouteSample:
        """OBS를 읽기만 하며 mute/volume/scene UUID/트랙을 동시에 확인."""
        if self._source_is_owned() is not True:
            raise RuntimeError("OBS 임시 음성 입력 UUID 소유권 상실")
        route = self._obs.read_program_audio_route(
            input_name=self._input_name, scene=self._scene)
        if (route.confirmed is not True or route.scene != self._scene
                or route.input_name != self._input_name
                or not any(identity.endswith(":" + self._uuid)
                           or identity.endswith("@" + self._uuid)
                           for identity in route.identity)):
            raise RuntimeError(
                "OBS 한국어 음성 입력이 현재 프로그램 장면/출력 트랙에 "
                "연결되었다는 근거가 없습니다.")
        client = self._obs._client
        if client is None:
            raise RuntimeError("OBS 음성 입력 오디오 조회 연결이 끊겼습니다.")
        try:
            muted = client.get_input_mute(self._input_name).input_muted
            volume = client.get_input_volume(self._input_name).input_volume_mul
        except Exception as exc:
            raise RuntimeError("OBS 실제 음성 mute/volume 조회 실패") from exc
        if (type(muted) is not bool
                or type(volume) not in (int, float)
                or not math.isfinite(volume)):
            raise RuntimeError("OBS 실제 음성 mute/volume 응답 형식 오류")
        if muted or volume <= 0.001:
            raise RuntimeError("OBS 한국어 음성 입력이 음소거 또는 무음 볼륨입니다.")
        sample = LiveVoiceAudioRouteSample(
            self._scene, self._uuid, route.origin,
            tuple(route.identity), tuple(route.enabled_tracks),
            float(volume), muted)
        baseline = self._baseline
        if baseline is not None and (
                sample.origin != baseline.origin
                or sample.identities != baseline.identities
                or sample.enabled_tracks != baseline.enabled_tracks):
            raise RuntimeError("OBS WAV 재생 중 장면 오디오 경로/트랙이 변경됐습니다.")
        if baseline is None:
            self._baseline = sample
        self._minimum_volume = min(self._minimum_volume, sample.volume_mul)
        self._samples += 1
        return sample

    @property
    def baseline(self) -> LiveVoiceAudioRouteSample:
        if self._baseline is None:
            raise RuntimeError("OBS WAV 오디오 경로의 최초 관측이 없습니다.")
        return self._baseline

    @property
    def samples(self) -> int:
        return self._samples

    @property
    def minimum_volume(self) -> float:
        if not self._samples:
            raise RuntimeError("OBS WAV 오디오 볼륨 관측이 없습니다.")
        return self._minimum_volume
