"""이미 승인되어 송출 중인 OBS에 로컬 AI의 실제 한국어 음성을 연결.

기존 검증 전용 WAV→OBS 코드를 갈아엎지 않고, 운영자가 선택한 실제
4플랫폼 AI 답변을 한국어 GPT-SoVITS로 합성한 뒤 같은 WAV 하나로
공식 Windows Live2D Cubism 입과 OBS 음성 소스를 함께 구동한다.
별도 승인 전에는 어떤 합성/송출/OBS 변경도 하지 않는다.

이 기능은 실제 방송 중 발화 경로이며 관측 전용 도구가 아니다.
기존 OBS 방송 시작/종료, 녹화, 장면/다른 소스, 캐릭터·기억,
모델 학습/다운로드·외부 채팅은 제어하지 않는다. 시청자 최종 수신이나
1~3초 지연은 이 코드만으로 보증하지 않는다.
"""
from __future__ import annotations

import queue
import re
import secrets
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .original_plan_obs import OfficialObsWebsocket
from .original_plan_tts import synthesize_local_gpt_sovits
from .same_wav_cubism_driver import authorized_pcm_envelope
from .obs_live2d_frame_link import active_official_window_capture


_MAX_SEGMENT_CHARS = 64
_MAX_REPLY_CHARS = 6000
_MAX_SPEECH_QUEUE = 512


def korean_voice_segments(reply: str) -> tuple[str, ...]:
    """내용 누락 없이 응답을 64자 이내의 실제 합성 문장으로 분절."""
    if type(reply) is not str or not 1 <= len(reply.strip()) <= _MAX_REPLY_CHARS:
        raise ValueError("실제 한국어 AI 답변 길이가 1~6000자가 아닙니다.")
    if any(ord(c) < 32 and c not in "\n\t\r" for c in reply):
        raise ValueError("실제 한국어 AI 답변에 제어 문자가 있습니다.")
    normalized = re.sub(r"\s+", " ", reply).strip()
    parts: list[str] = []
    remaining = normalized
    while remaining:
        if len(remaining) <= _MAX_SEGMENT_CHARS:
            parts.append(remaining)
            break
        window = remaining[:_MAX_SEGMENT_CHARS + 1]
        # 마침표/띄어쓰기를 우선하되 긴 단어도 잘라 무단 생략 금지.
        cut = max(window.rfind(ch, 15, _MAX_SEGMENT_CHARS + 1)
                  for ch in (" ", ".", "!", "?", "。"))
        if cut <= 0:
            cut = _MAX_SEGMENT_CHARS
        elif window[cut] != " ":
            cut += 1
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].lstrip()
    if not parts or any(not item or len(item) > _MAX_SEGMENT_CHARS for item in parts):
        raise ValueError("한국어 발화 문장 분절 범위가 올바르지 않습니다.")
    return tuple(parts)


@dataclass(frozen=True)
class ApprovedVoiceTurn:
    segments_completed: int
    segments_total: int
    wav_seconds: float
    obs_stream_was_active: bool
    cubism_started: bool


class ApprovedLiveVoiceOutput:
    """승인된 단일 채팅 세션에 귀속된 실제 방송용 음성 FIFO."""

    def __init__(
        self, *,
        reference_audio: Path,
        reference_text: str,
        api_url: str,
        obs_password: str,
        obs_port: int = 4455,
        operator_approved: bool = False,
        rights_confirmed: bool = False,
        on_event: Callable[[str, object], None] | None = None,
    ) -> None:
        if operator_approved is not True or rights_confirmed is not True:
            raise PermissionError("기존 OBS 방송 중 음성 사용과 실제 권리 별도 승인이 필요합니다.")
        if type(obs_password) is not str or not obs_password:
            raise ValueError("로컬 OBS 인증 암호가 필요합니다.")
        if type(obs_port) is not int or not 1 <= obs_port <= 65535:
            raise ValueError("로컬 OBS 포트가 잘못되었습니다.")
        if type(reference_text) is not str or not reference_text.strip():
            raise ValueError("권리가 확인된 참조 음성의 녹음 문구가 없습니다.")
        if type(api_url) is not str:
            raise ValueError("기존 한국어 음성 모델 주소가 올바르지 않습니다.")
        if on_event is not None and not callable(on_event):
            raise TypeError("방송 음성 결과 수신 함수가 올바르지 않습니다.")
        self.reference_audio = Path(reference_audio)
        self.reference_text = reference_text
        self.api_url = api_url
        self._obs_password = obs_password
        self._obs_port = obs_port
        self._on_event = on_event
        self._stop = threading.Event()
        self._inbox: queue.Queue[str] = queue.Queue(maxsize=_MAX_SPEECH_QUEUE)
        self._worker: threading.Thread | None = None
        self._submitted = 0
        self._finished = 0

    def start(self) -> None:
        if self._worker is not None:
            raise RuntimeError("실제 방송용 음성 작업자가 이미 시작되었습니다.")
        if self._stop.is_set():
            raise RuntimeError("중지된 실제 방송용 음성 작업자를 재사용하지 않습니다.")
        self._worker = threading.Thread(
            target=self._run, name="AISTING-approved-live-voice", daemon=True)
        self._worker.start()

    def enqueue(self, reply: str) -> int:
        """완성된 기존 AI 답변 한 건을 원순서 그대로 추가한다.

        초과 시 답변을 성공으로 위장하거나 기존 대기열을 버리지 않는다.
        발화 완료 여부는 별도 결과 이벤트로만 알린다.
        """
        if self._worker is None or self._stop.is_set():
            raise RuntimeError("실제 방송용 음성 연결이 실행 중이지 않습니다.")
        korean_voice_segments(reply)
        try:
            self._inbox.put_nowait(reply)
        except queue.Full as exc:
            raise RuntimeError(
                "실제 방송 음성 대기열 512건 초과 · 임의 발화 삭제 없음 · "
                "운영자 확인 필요") from exc
        self._submitted += 1
        return self._submitted

    def stop(self) -> None:
        """새 음성 시작 차단, 진행 중 발화 종료 요청. OBS 방송은 중지 안 함."""
        self._stop.set()

    @property
    def pending(self) -> int:
        return self._inbox.qsize()

    def _publish(self, kind: str, value: object) -> None:
        if self._on_event is not None:
            self._on_event(kind, value)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                text = self._inbox.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                completed = 0
                duration = 0.0
                segments = korean_voice_segments(text)
                self._publish("발화시작", len(segments))
                for segment in segments:
                    if self._stop.is_set():
                        break
                    duration += self._speak_segment(segment)
                    completed += 1
                    self._publish("구간완료", (completed, len(segments)))
                if self._stop.is_set() or completed != len(segments):
                    self._publish("발화중단", (completed, len(segments)))
                    break
                self._finished += 1
                self._publish("발화완료", ApprovedVoiceTurn(
                    completed, len(segments), duration, True, True))
            except Exception as exc:
                # 이미 Cubism·OBS에 일부 소리가 나갔을 수 있으므로
                # 불확실한 문장을 자동 재전송해 두 번 읽지 않는다.
                self._publish("발화오류", type(exc).__name__)
                self._stop.set()
                break
            finally:
                self._inbox.task_done()

    def _speak_segment(self, text: str) -> float:
        """실제 OBS의 '이미 송출 중' 상태에서만 동일 PCM을 재생·입 구동."""
        from . import original_plan_frontend as frontend
        if self._stop.is_set():
            raise RuntimeError("운영자가 음성 출력을 중지했습니다.")
        child = frontend._native_viewer
        if (child is None or child.poll() is not None
                or frontend._native_bridge is None):
            raise RuntimeError("실제 공식 Windows Live2D Cubism 창이 닫혔습니다.")

        obs = OfficialObsWebsocket(self._obs_password, port=self._obs_port)
        original = obs.connect()
        if not original.streaming:
            raise RuntimeError("현재 OBS가 송출 중이지 않아 음성 방송을 시작하지 않습니다.")
        media_path = obs.read_scene_media_path()
        if not active_official_window_capture(media_path.capture_sources):
            raise RuntimeError("현재 OBS 장면에 공식 Live2D 활성 창 캡처가 없습니다.")

        actual = synthesize_local_gpt_sovits(
            self.reference_audio, self.reference_text, text,
            api_url=self.api_url, operator_approved=True,
            rights_confirmed=True, play_to_speaker=False,
            return_audio_bytes=True, timeout=120,
        )
        if self._stop.is_set():
            raise RuntimeError("한국어 음성 합성 중 사용자가 중지했습니다.")
        raw = actual.wav_data
        if not raw or actual.sample_rate <= 0 or actual.frame_count <= 0:
            raise RuntimeError("실제 한국어 음성 PCM이 반환되지 않았습니다.")
        wav_seconds = actual.frame_count / actual.sample_rate
        if not 0.4 <= wav_seconds <= 8:
            # 임의 시간 배속·원문 생략 없이 실제 WAV 길이 그대로 판단.
            raise RuntimeError("공식 Cubism 동일 PCM 구동 길이 0.4~8초를 초과했습니다.")
        envelope = authorized_pcm_envelope(raw)
        client = obs._client
        if "ffmpeg_source" not in client.get_input_kind_list(False).input_kinds:
            raise RuntimeError("OBS 실제 미디어 음성 입력이 지원되지 않습니다.")
        name = "AISTING-live-voice-" + secrets.token_hex(12)
        uuid = None
        created = False
        mouth_token = None

        def source_is_owned() -> bool:
            values = client.get_input_list().inputs
            matches = [x for x in values if isinstance(x, dict)
                       and x.get("inputName") == name
                       and x.get("inputKind") == "ffmpeg_source"]
            return (len(matches) == 1
                    and type(matches[0].get("inputUuid")) is str
                    and matches[0]["inputUuid"] == uuid)

        with tempfile.TemporaryDirectory(prefix="AISTING_live_voice_") as td:
            wav_path = Path(td) / "current_authorized.wav"
            wav_path.write_bytes(raw)
            try:
                latest = obs.status()
                if (self._stop.is_set() or not latest.streaming
                        or latest.scene != original.scene):
                    raise RuntimeError("음성 시작 전 OBS 송출·장면 상태가 변경됐습니다.")
                creation = client.create_input(
                    original.scene, name, "ffmpeg_source",
                    {"is_local_file": True, "local_file": str(wav_path),
                     "looping": False, "restart_on_activate": False,
                     "close_when_inactive": True}, False)
                created = True
                uuid = getattr(creation, "input_uuid", None)
                scene_item_id = getattr(creation, "scene_item_id", None)
                if (type(uuid) is not str or not uuid
                        or type(scene_item_id) is not int
                        or not source_is_owned()):
                    raise RuntimeError("OBS 전용 한국어 음성 소스 동일성 확인 실패")
                if self._stop.is_set() or not obs.status().streaming:
                    raise RuntimeError("사용자 중지 또는 OBS 송출 종료")
                # 하나의 WAV로 공식 Cubism 입과 OBS 오디오를 함께 구동.
                mouth_token = frontend.start_authorized_pcm_live2d_mouth(
                    envelope, operator_approved=True, rights_confirmed=True)
                client.set_scene_item_enabled(original.scene, scene_item_id, True)
                client.trigger_media_input_action(
                    name, "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART")
                if self._stop.wait(wav_seconds + 0.2):
                    raise RuntimeError("운영자가 실제 방송 음성 출력을 중지했습니다.")
                if not obs.status().streaming:
                    raise RuntimeError("실제 발화 도중 OBS 송출이 종료되었습니다.")
                return wav_seconds
            finally:
                restore_error = None
                if mouth_token is not None:
                    try:
                        frontend.finish_authorized_pcm_live2d_mouth(
                            mouth_token, operator_approved=True)
                    except Exception as exc:
                        restore_error = exc
                remove_error = None
                if created:
                    try:
                        if source_is_owned():
                            client.remove_input(name)
                        else:
                            raise RuntimeError("OBS 음성 소스의 소유권이 달라졌습니다.")
                    except Exception as exc:
                        remove_error = exc
                if restore_error is not None or remove_error is not None:
                    raise RuntimeError(
                        "공식 Cubism 원상복귀 또는 방송 음성 소스 정리 실패")
