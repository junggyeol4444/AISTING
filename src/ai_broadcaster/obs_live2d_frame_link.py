"""실제 OBS 현재 장면의 공식 Live2D 창 캡처와 오디오 구간 영상 관측 후보.

OBS 설정의 임의 화면 캡처·게임 캡처·타인 창을 공식 Live2D로 간주하지
않는다. 프로그램 장면 PNG의 변화는 Cubism 입 변화의 인과성 증명이
아니며, 실제 시청자에게 송출되었다는 뜻도 아니다.
"""
from __future__ import annotations

import math

OFFICIAL_WINDOW_TITLE = "AISTING | 공식 Live2D 및 AI 대화"


def active_official_window_capture(captures: tuple[str, ...]) -> bool:
    """실제 OBS가 보고한 활성 창 캡처의 대상 창 제목을 확인한다.

    기존 OBS 장면/소스 이름을 변경하지 않고, OBS WebSocket이 반환한
    읽기 전용 입력 설정의 창 제목을 엄격히 대조한다.
    """
    if not isinstance(captures, tuple):
        return False
    return any(
        isinstance(item, str)
        and "(window_capture, 활성)" in item
        and " / 선택된 창 " + OFFICIAL_WINDOW_TITLE in item
        and ": 비활성" not in item
        for item in captures
    )


def program_motion_near_audio(
    frames: tuple[tuple[float, str, str], ...],
    positive_audio_times: tuple[float, ...],
    *,
    restart_at: float,
    wav_seconds: float,
) -> bool:
    """실제 WAV 구간의 OBS 프레임 변화와 양성 오디오 시각 근접 후보.

    frames: (실제 프레임 취득 완료 단조시각, 장면 이름, PNG SHA256).
    PNG 데이터 자체를 저장하거나 외부로 보내지 않는다. PNG 해시
    차이는 화면 변화의 약한 후보이지 입술 움직임 판별이 아니다.
    """
    if (len(frames) < 3 or not isinstance(restart_at, (int, float))
            or not math.isfinite(restart_at) or restart_at <= 0
            or not isinstance(wav_seconds, (int, float))
            or not math.isfinite(wav_seconds) or not 0 < wav_seconds <= 8):
        return False
    if any(
        not isinstance(sample, tuple) or len(sample) != 3
        or type(sample[0]) not in (int, float)
        or not math.isfinite(sample[0])
        or not isinstance(sample[1], str) or not sample[1]
        or not isinstance(sample[2], str) or len(sample[2]) != 64
        for sample in frames
    ):
        return False
    if len({sample[1] for sample in frames}) != 1:
        return False
    if any(frames[i][0] >= frames[i + 1][0]
           for i in range(len(frames) - 1)):
        return False
    baseline = frames[0][2]
    if frames[0][0] >= restart_at:
        return False
    upper = restart_at + wav_seconds
    valid_audio = tuple(
        moment for moment in positive_audio_times
        if type(moment) in (float, int) and math.isfinite(moment)
        and restart_at <= moment <= upper + 0.5
    )
    if not valid_audio:
        return False
    return any(
        restart_at < when <= upper
        and digest != baseline
        and any(abs(when - audio_when) <= 0.6
                for audio_when in valid_audio)
        for when, _scene, digest in frames[1:-1]
    )


class OfficialProgramFrameSampler:
    """동일 실제 발화 재생 중 OBS 프로그램 영상의 변화만 읽기 전용 관찰.

    WebSocket 연결은 별도 작업자 소유이고 영상은 즉시 SHA-256으로 축약해
    폐기한다. 외부 송출·녹화·장면 변경·기존 소스 수정·화면 저장은 없다.
    이 화면 변화는 공식 Cubism '입' 픽셀을 식별하는 검사가 아니므로
    오디오·영상 최종 인과성의 후보로만 표시해야 한다.
    """

    def __init__(self, password: str, *, port: int, scene: str,
                 interval_seconds: float = 0.35):
        import threading
        if (type(password) is not str or not password
                or type(port) is not int or not 1 <= port <= 65535
                or type(scene) is not str or not scene.strip()
                or type(interval_seconds) not in (int, float)
                or not 0.2 <= interval_seconds <= 1.0):
            raise ValueError("공식 Live2D OBS 영상 관측 연결 조건 오류")
        self._password = password
        self._port = port
        self._scene = scene
        self._interval = float(interval_seconds)
        self._ready = threading.Event()
        self._begin = threading.Event()
        self._stop = threading.Event()
        self._worker = None
        self._frames: list[tuple[float, str, str]] = []
        self._error: str | None = None
        self._capture_before: tuple[str, ...] | None = None
        self._capture_after: tuple[str, ...] | None = None

    def start(self) -> None:
        """실제 방송/녹화 중지와 공식 창 캡처를 확인하고 기준 프레임 확보."""
        import threading
        if self._worker is not None:
            raise RuntimeError("OBS 영상 관측 작업은 한 번만 시작할 수 있습니다.")
        self._worker = threading.Thread(
            target=self._sample, name="AISTING-OBS-공식영상관측", daemon=True)
        self._worker.start()
        if not self._ready.wait(12):
            self._stop.set()
            raise RuntimeError("실제 OBS 공식 Live2D 캡처 준비 시간 초과")
        if self._error is not None:
            self._stop.set()
            raise RuntimeError("실제 OBS 공식 캡처 준비 실패 (" + self._error + ")")

    def begin(self) -> None:
        """실제 OBS 임시 WAV 재생 시작 직전에만 영상 후속 관측 시작."""
        if not self._ready.is_set() or self._error is not None or self._stop.is_set():
            raise RuntimeError("공식 Live2D OBS 프로그램 영상 관측 준비 미완료")
        self._begin.set()

    def finish(self) -> tuple[tuple[float, str, str], ...]:
        """이미지 저장 없이 시간·장면·SHA-256 목록만 반환."""
        self._stop.set()
        worker = self._worker
        if worker is None:
            return ()
        worker.join(timeout=12)
        if worker.is_alive():
            raise RuntimeError("실제 OBS 프로그램 영상 관측 종료 미확인")
        if self._error:
            raise RuntimeError("실제 OBS 공식 영상 관측 실패 (" + self._error + ")")
        if (self._capture_before is None or self._capture_after is None
                or self._capture_before != self._capture_after):
            raise RuntimeError("OBS 공식 Live2D 창 캡처 입력이 관측 중 변경됨")
        return tuple(self._frames)

    def _sample(self) -> None:
        import hashlib
        import time
        from .original_plan_obs import OfficialObsWebsocket

        try:
            obs = OfficialObsWebsocket(self._password, port=self._port)
            start = obs.connect()
            if start.streaming or start.scene != self._scene:
                raise RuntimeError("OBS 송출/현재 프로그램 장면 상태 불일치")
            # 방송 출력을 건드리지 않고 실제 OBS 녹화 상태도 점검.
            recorded = obs._client.get_record_status().output_active
            if type(recorded) is not bool or recorded:
                raise RuntimeError("OBS 녹화 중 또는 녹화 상태 미확인")
            media = obs.read_scene_media_path()
            if not active_official_window_capture(media.capture_sources):
                raise RuntimeError("공식 Live2D 네이티브 창을 캡처하는 입력 미확인")
            self._capture_before = media.capture_sources

            def snapshot():
                state = obs.status()
                if state.streaming or state.scene != self._scene:
                    raise RuntimeError("OBS 관측 중 송출/프로그램 장면 변경")
                actual = obs.read_current_scene_frame(operator_approved=True)
                if actual.scene != self._scene:
                    raise RuntimeError("OBS 현재 프레임 장면 변경")
                at = time.monotonic()
                digest = hashlib.sha256(actual.png_data).hexdigest()
                self._frames.append((at, actual.scene, digest))

            snapshot()  # Only a pre-WAV baseline, never claimed as mouth video.
            self._ready.set()
            # Stop immediately if the user cancels before the WAV starts.
            while not self._stop.is_set() and not self._begin.is_set():
                self._stop.wait(0.05)
            if not self._stop.is_set():
                while not self._stop.is_set() and len(self._frames) < 33:
                    snapshot()
                    self._stop.wait(self._interval)
            # Verify routing AFTER playback too; source may have been retargeted.
            final_media = obs.read_scene_media_path()
            self._capture_after = final_media.capture_sources
        except Exception as exc:
            # Never log raw OBS tokens, pixels, addresses, credentials.
            self._error = type(exc).__name__
        finally:
            self._ready.set()
