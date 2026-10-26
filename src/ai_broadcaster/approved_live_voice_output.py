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
import sys
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
from .approved_live_voice_journal import ApprovedLiveVoiceJournal, voice_turn_key
from .approved_live_voice_outbox import ApprovedLiveVoiceOutbox
from .approved_live_voice_stream_lease import ApprovedVoiceStreamLease
from .approved_live_voice_causal_journal import ApprovedVoiceCausalJournal
from .approved_live_voice_sync_receipts import ApprovedLiveVoiceSyncReceipts
from .approved_live_voice_media_receipts import ApprovedLiveVoiceMediaReceipts
from .approved_live_voice_playback_watch import ApprovedLiveVoicePlaybackWatch
from .approved_live_voice_prefetch import ApprovedVoiceSegmentPrefetch


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
        journal: ApprovedLiveVoiceJournal | None = None,
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
        if journal is not None and not isinstance(journal, ApprovedLiveVoiceJournal):
            raise TypeError("실제 음성 영구 장부가 올바르지 않습니다.")
        self._journal = journal if journal is not None else ApprovedLiveVoiceJournal()
        self._session_id = secrets.token_hex(16)
        # 실제 배포 대상인 Windows에서는 AI 답변을 현재 사용자 DPAPI로
        # 암호화해 SQLite에 먼저 영구 확정. 이전 방송의 대기는 자동 재생 금지.
        self._outbox = ApprovedLiveVoiceOutbox() if sys.platform == "win32" else None
        self._outbox_wakeup = threading.Event()
        self._stream_lease = ApprovedVoiceStreamLease()
        self._causal_journal = ApprovedVoiceCausalJournal()
        self._sync_receipts = ApprovedLiveVoiceSyncReceipts()
        self._media_receipts = ApprovedLiveVoiceMediaReceipts()
        self._playback_watch = ApprovedLiveVoicePlaybackWatch()
        self._stop = threading.Event()
        self._inbox: queue.Queue[tuple[str, str]] = queue.Queue(
            maxsize=_MAX_SPEECH_QUEUE)
        self._worker: threading.Thread | None = None
        self._submitted = 0
        self._finished = 0

    def start(self) -> None:
        if self._worker is not None:
            raise RuntimeError("실제 방송용 음성 작업자가 이미 시작되었습니다.")
        if self._stop.is_set():
            raise RuntimeError("중지된 실제 방송용 음성 작업자를 재사용하지 않습니다.")
        self._worker = threading.Thread(
            target=self._run_persisted if self._outbox is not None else self._run,
            name="AISTING-approved-live-voice", daemon=True)
        self._worker.start()

    def enqueue(
        self, reply: str, *, platform: str = "twitch",
        channel: str = "직접선택", event_id: str | None = None,
    ) -> int:
        """완성된 기존 AI 답변 한 건을 원순서 그대로 추가한다.

        초과 시 답변을 성공으로 위장하거나 기존 대기열을 버리지 않는다.
        발화 완료 여부는 별도 결과 이벤트로만 알린다.
        """
        if self._worker is None or self._stop.is_set():
            raise RuntimeError("실제 방송용 음성 연결이 실행 중이지 않습니다.")
        korean_voice_segments(reply)
        # 실제 서버 이벤트 ID가 없는 서로 다른 메시지는 절대 본문으로
        # 합치지 않는다. 원문은 메모리 FIFO에만 두고 DB에는 SHA만 기록.
        turn_key = voice_turn_key(
            platform, channel, event_id, nonce=secrets.token_hex(16))
        if self._outbox is not None:
            seq, is_new = self._outbox.enqueue(self._session_id, turn_key, reply)
            if not is_new:
                self._publish("발화중복차단", turn_key[:12])
                return seq
            self._submitted += 1
            self._outbox_wakeup.set()
            return seq
        try:
            self._inbox.put_nowait((turn_key, reply))
        except queue.Full as exc:
            raise RuntimeError(
                "실제 방송 음성 대기열 512건 초과 · 임의 발화 삭제 없음 · "
                "운영자 확인 필요") from exc
        self._submitted += 1
        return self._submitted

    def stop(self) -> None:
        """새 음성 시작 차단, 진행 중 발화 종료 요청. OBS 방송은 중지 안 함."""
        self._stop.set()
        self._outbox_wakeup.set()

    @property
    def pending(self) -> int:
        if self._outbox is not None:
            return self._outbox.pending(self._session_id)
        return self._inbox.qsize()

    @property
    def previous_unresolved(self) -> tuple[int, int]:
        if self._outbox is None:
            return (0, 0)
        return self._outbox.previous_unresolved(self._session_id)

    def previous_sessions_for_review(self) -> tuple[tuple[str, int, int, str], ...]:
        """운영자 수동 선택을 위한 이전 세션 건수·식별자만 제공."""
        if self._outbox is None:
            return ()
        return self._outbox.previous_sessions(self._session_id)

    def adopt_previous_pending(
        self, old_session_id: str, *, operator_approved: bool = False,
        same_broadcast_confirmed: bool = False,
    ) -> int:
        """운영자가 동일 방송을 확인하고 두 번 승인한 과거 미발화만 인계.

        SQLite에는 과거 OBS 출력 식별 정보가 없으므로 앱 단독으로
        동일 방송 여부를 입증하지 못한다. 현재 OBS 활성 출력·공식
        Live2D 장면을 확인하고 운영자가 과거 방송 동일성을 확인해야 한다.
        시도/불명 항목은 이동하지 않으며 새 송출을 시작하지 않는다.
        """
        if operator_approved is not True or same_broadcast_confirmed is not True:
            raise PermissionError("이전 발화 수동 인계에는 운영자 이중 확인이 필요합니다.")
        if self._worker is None or self._stop.is_set() or self._outbox is None:
            raise RuntimeError("Windows 실제 방송 음성 작업자가 실행 중이어야 합니다.")
        obs = OfficialObsWebsocket(self._obs_password, port=self._obs_port)
        status = obs.connect()
        self._stream_lease.check(obs)
        if not status.streaming:
            raise RuntimeError("현재 OBS 송출이 종료되어 과거 발화를 인계하지 않습니다.")
        media = obs.read_scene_media_path()
        if not active_official_window_capture(media.capture_sources):
            raise RuntimeError("현재 OBS 장면에서 공식 Live2D 창 캡처가 확인되지 않습니다.")
        if self._stop.is_set():
            raise RuntimeError("운영자 중지 후 과거 음성 인계 금지")
        count = self._outbox.adopt_previous_pending(
            old_session_id, self._session_id,
            operator_approved=True, same_broadcast_confirmed=True)
        if count:
            self._submitted += count
            self._outbox_wakeup.set()
            self._publish("과거대기수동인계", count)
        return count

    def _publish(self, kind: str, value: object) -> None:
        if self._on_event is not None:
            self._on_event(kind, value)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                turn_key, text = self._inbox.get(timeout=0.2)
            except queue.Empty:
                continue
            claimed = False
            try:
                # 실제 GPT-SoVITS 합성·Cubism·OBS 입력 전에 SQLite에
                # 발화 시도를 커밋. 응답 유실/재시작 후 자동 이중발화 금지.
                if not self._journal.claim(turn_key, text):
                    self._publish("발화중복차단", turn_key[:12])
                    continue
                claimed = True
                completed = 0
                duration = 0.0
                segments = korean_voice_segments(text)
                self._publish("발화시작", len(segments))
                completed, duration = self._speak_turn_segments(
                    segments, turn_key=turn_key)
                if self._stop.is_set() or completed != len(segments):
                    self._journal.finish(turn_key, "중단")
                    self._publish("발화중단", (completed, len(segments)))
                    break
                # 이 완료는 실제 OBS 재생 요청 경로의 반환이며,
                # 플랫폼 최종 시청자 음성 수신을 증명하지 않는다.
                self._journal.finish(turn_key, "재생요청완료")
                self._finished += 1
                self._publish("발화완료", ApprovedVoiceTurn(
                    completed, len(segments), duration, True, True))
            except Exception as exc:
                if claimed:
                    try:
                        self._journal.finish(turn_key, "불명")
                    except Exception:
                        # 기존 시도 행은 삭제하지 않으며 자동 재전송도 없음.
                        pass
                # 이미 Cubism·OBS에 일부 소리가 나갔을 수 있으므로
                # 불확실한 문장을 자동 재전송해 두 번 읽지 않는다.
                self._publish("발화오류", type(exc).__name__)
                self._stop.set()
                break
            finally:
                self._inbox.task_done()

    def _run_persisted(self) -> None:
        """Windows 실제 방송: SQLite 대기 원문을 먼저 시도로 고정한 후 송출.

        앱이 중단되어도 다른 방송 세션의 남은 문장을 자동으로 읽지
        않으며, 출력 여부가 불명확한 시도는 다시 합성하지 않는다.
        """
        outbox = self._outbox
        if outbox is None:
            raise RuntimeError("Windows 영구 음성 대기함이 없습니다.")
        while not self._stop.is_set():
            try:
                turn = outbox.claim_next(self._session_id)
            except Exception as exc:
                self._publish("발화오류", type(exc).__name__)
                self._stop.set()
                break
            if turn is None:
                self._outbox_wakeup.wait(0.2)
                self._outbox_wakeup.clear()
                continue
            seq, turn_key, text = turn
            claimed = False
            try:
                if self._stop.is_set():
                    outbox.finish(seq, "중단")
                    break
                if not self._journal.claim(turn_key, text):
                    outbox.finish(seq, "중복")
                    self._publish("발화중복차단", turn_key[:12])
                    continue
                claimed = True
                completed = 0
                duration = 0.0
                segments = korean_voice_segments(text)
                self._publish("발화시작", len(segments))
                completed, duration = self._speak_turn_segments(
                    segments, turn_key=turn_key)
                if self._stop.is_set() or completed != len(segments):
                    self._journal.finish(turn_key, "중단")
                    outbox.finish(seq, "중단")
                    self._publish("발화중단", (completed, len(segments)))
                    break
                self._journal.finish(turn_key, "재생요청완료")
                outbox.finish(seq, "완료")
                self._finished += 1
                self._publish("발화완료", ApprovedVoiceTurn(
                    completed, len(segments), duration, True, True))
            except Exception as exc:
                if claimed:
                    try:
                        self._journal.finish(turn_key, "불명")
                    except Exception:
                        pass
                try:
                    outbox.finish(seq, "불명")
                except Exception:
                    pass
                self._publish("발화오류", type(exc).__name__)
                self._stop.set()
                break

    def _synthesize_segment(self, text: str):
        """기존 권리 확인 모델만 사용하며 음성·OBS 자동 송출은 하지 않음."""
        if self._stop.is_set():
            raise RuntimeError("운영자 중지 후 한국어 음성 합성을 시작하지 않습니다.")
        actual = synthesize_local_gpt_sovits(
            self.reference_audio, self.reference_text, text,
            api_url=self.api_url, operator_approved=True,
            rights_confirmed=True, play_to_speaker=False,
            return_audio_bytes=True, timeout=120,
        )
        if self._stop.is_set():
            raise RuntimeError("한국어 음성 합성 중 운영자가 중지했습니다.")
        return actual

    def _speak_turn_segments(
        self, segments: tuple[str, ...], *, turn_key: str,
    ) -> tuple[int, float]:
        """다음 한 WAV 합성과 현재 WAV 방송을 겹치되 출력은 원래 FIFO."""
        completed = 0
        duration = 0.0
        prefetch = ApprovedVoiceSegmentPrefetch(
            self._synthesize_segment, self._stop)
        try:
            for index, segment in enumerate(segments):
                if self._stop.is_set():
                    break
                prepared = prefetch.take(segment)
                upcoming = segments[index + 1] if index + 1 < len(segments) else None
                start_next = (
                    (lambda next_text=upcoming: prefetch.start_next(next_text))
                    if upcoming is not None else None)
                duration += self._speak_segment(
                    segment, turn_key=turn_key, part_id=str(index + 1),
                    prepared_audio=prepared, prefetch_next=start_next)
                completed += 1
                self._publish("구간완료", (completed, len(segments)))
        finally:
            prefetch.close()
        return completed, duration

    def _speak_segment(
        self, text: str, *, depth: int = 0,
        turn_key: str | None = None, part_id: str = "1",
        prepared_audio: object | None = None,
        prefetch_next: Callable[[], None] | None = None,
    ) -> float:
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
        self._stream_lease.check(obs)
        if not original.streaming:
            raise RuntimeError("현재 OBS가 송출 중이지 않아 음성 방송을 시작하지 않습니다.")
        media_path = obs.read_scene_media_path()
        if not active_official_window_capture(media_path.capture_sources):
            raise RuntimeError("현재 OBS 장면에 공식 Live2D 활성 창 캡처가 없습니다.")

        # 내부 직접 발화에서 호출자가 turn_key를 제공하지 않아도
        # 같은 물리 WAV의 기존 인과·입 관측 두 독립 장부가 반드시
        # 똑같은 식별자를 사용하게 한다. 원문/채팅 ID 영구 저장 없음.
        effective_turn_key = turn_key or secrets.token_hex(32)
        actual = (prepared_audio if prepared_audio is not None
                  else self._synthesize_segment(text))
        if self._stop.is_set():
            raise RuntimeError("한국어 음성 합성 중 사용자가 중지했습니다.")
        raw = actual.wav_data
        if not raw or actual.sample_rate <= 0 or actual.frame_count <= 0:
            raise RuntimeError("실제 한국어 음성 PCM이 반환되지 않았습니다.")
        wav_seconds = actual.frame_count / actual.sample_rate
        if wav_seconds > 8.0:
            # 실제 GPT-SoVITS가 문장 길이를 오래 읽으면 무단
            # 배속/누락 대신 같은 원문의 더 작은 문장 둘로 다시 합성.
            # 원래 8초 제한은 공식 Cubism PCM 구동 범위이므로 유지.
            if len(text) < 15 or depth >= 5:
                raise RuntimeError(
                    "공식 Cubism 8초 제한을 만족하도록 더 분절할 수 없습니다.")
            middle = len(text) // 2
            boundary = text.rfind(" ", 8, middle + 1)
            if boundary <= 0:
                boundary = middle
            left = text[:boundary].strip()
            right = text[boundary:].strip()
            if not left or not right or self._stop.is_set():
                raise RuntimeError("한국어 음성 문장 재분절을 중단했습니다.")
            # 원래 문장의 각 글자를 순서대로 읽고 매번 같은 권리 모델 사용.
            return (self._speak_segment(
                        left, depth=depth + 1, turn_key=turn_key,
                        part_id=part_id + ".1",
                        prefetch_next=prefetch_next)
                    + self._speak_segment(
                        right, depth=depth + 1, turn_key=turn_key,
                        part_id=part_id + ".2"))
        if wav_seconds < 0.4:
            raise RuntimeError("공식 Cubism 최소 0.4초 미만의 실제 음성입니다.")
        envelope = authorized_pcm_envelope(raw)
        client = obs._client
        if "ffmpeg_source" not in client.get_input_kind_list(False).input_kinds:
            raise RuntimeError("OBS 실제 미디어 음성 입력이 지원되지 않습니다.")
        name = "AISTING-live-voice-" + secrets.token_hex(12)
        uuid = None
        created = False
        mouth_token = None
        causal_row = None
        sync_causal_row = None
        obs_request_confirmed = False

        def source_is_owned() -> bool:
            values = client.get_input_list().inputs
            matches = [x for x in values if isinstance(x, dict)
                       and x.get("inputName") == name
                       and x.get("inputKind") == "ffmpeg_source"]
            return (len(matches) == 1
                    and type(matches[0].get("inputUuid")) is str
                    and matches[0]["inputUuid"] == uuid)

        def current_obs_media_status() -> tuple[str, int | None]:
            """실제 같은 임시 음성 UUID의 OBS 미디어 상태/재생 커서만 조회."""
            if not source_is_owned():
                raise RuntimeError("OBS 재생 상태를 읽을 임시 음성 입력 소유권 상실")
            status = client.get_media_input_status(name)
            state = getattr(status, "media_state", None)
            cursor = getattr(status, "media_cursor", None)
            if type(cursor) is float:
                if not cursor.is_integer() or cursor < 0:
                    raise RuntimeError("OBS 실제 재생 커서 형식 오류")
                cursor = int(cursor)
            return state, cursor

        with tempfile.TemporaryDirectory(prefix="AISTING_live_voice_") as td:
            wav_path = Path(td) / "current_authorized.wav"
            wav_path.write_bytes(raw)
            try:
                self._stream_lease.check(obs)
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
                self._stream_lease.check(obs)
                if self._stop.is_set() or not obs.status().streaming:
                    raise RuntimeError("사용자 중지 또는 OBS 송출 종료")
                # 동일 WAV의 OBS 임시 음성 소스를 활성화한 뒤에만
                # Cubism PCM 입 구동을 시작한다. 과거에는 선행 TTS
                # 작업 제출과 OBS 소스 활성화가 공식 입 시작과
                # OBS 재생 요청 사이에 끼어 시간 오차가 커졌다.
                client.set_scene_item_enabled(original.scene, scene_item_id, True)
                self._stream_lease.check(obs)
                mouth_token = frontend.start_authorized_pcm_live2d_mouth(
                    envelope, operator_approved=True, rights_confirmed=True)
                causal_row = self._causal_journal.mouth_started(
                    turn_key=effective_turn_key,
                    part_id=part_id, wav_data=raw,
                    wav_seconds=wav_seconds, obs_scene=original.scene,
                    obs_source_uuid=uuid)
                sync_causal_row = causal_row
                # 둘 사이에 추가 합성이나 TTS 기다림을 끼워 넣지 않는다.
                self._stream_lease.check(obs)
                client.trigger_media_input_action(
                    name, "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART")
                self._causal_journal.obs_triggered(causal_row)
                obs_request_confirmed = True
                # OBS 재생 요청이 기록된 뒤에만 다음 WAV 합성을
                # 시작해 현재 구간 시작 시간의 영향을 줄인다.
                if prefetch_next is not None:
                    prefetch_next()
                # 한 WAV 재생 중에도 실제 송출/입/임시 소스가 유지되는지
                # 주기적으로 읽는다. 관측 불명 시 후속 구간 재발화 금지.
                playback = self._playback_watch.wait_for_current_wav(
                    seconds=wav_seconds, stop=self._stop, obs=obs,
                    lease=self._stream_lease, expected_scene=original.scene,
                    source_is_owned=source_is_owned,
                    cubism_is_alive=lambda: (
                        child.poll() is None
                        and frontend._native_viewer is child
                        and frontend._native_bridge is not None),
                    media_status=current_obs_media_status)
                # OBS의 실제 PLAYING·커서 전진을 같은 물리 WAV의 해시/
                # 소스 UUID에 묶어 별도 SQLite에 보존한 후에만 완료로 진행.
                # 이 증거는 시청자 전달/인코더 오디오 믹스 성공은 아님.
                media_receipt = self._media_receipts.record(
                    turn_key=effective_turn_key, part_id=part_id,
                    wav_data=raw, source_uuid=uuid, observation=playback)
                self._publish("OBS미디어재생관측", media_receipt)
                self._causal_journal.finish(causal_row, completed=True)
                causal_row = None
                return wav_seconds
            finally:
                if causal_row is not None:
                    try:
                        self._causal_journal.finish(causal_row, completed=False)
                    except Exception:
                        # 불명 원본 행은 유지. 재발화하지 않는다.
                        pass
                restore_error = None
                mouth_observation = None
                if mouth_token is not None:
                    try:
                        mouth_observation = frontend.finish_authorized_pcm_live2d_mouth(
                            mouth_token, operator_approved=True)
                    except Exception as exc:
                        restore_error = exc
                # OBS에 실제 재생 요청을 한 WAV와 공식 Cubism 모델
                # 실제 매개변수 변화 결과를 영구 연결. 같은 음성 원문,
                # 닉네임·WAV 본문·토큰을 새 장부에 저장하지 않는다.
                evidence_error = None
                if mouth_observation is not None and sync_causal_row is not None:
                    try:
                        gap = self._causal_journal.actual_obs_request_gap(
                            sync_causal_row)
                        evidence = self._sync_receipts.record(
                            turn_key=effective_turn_key,
                            part_id=part_id, wav_data=raw,
                            obs_source_uuid=uuid,
                            obs_request_gap_seconds=gap,
                            observation=mouth_observation,
                            obs_triggered=obs_request_confirmed)
                        self._publish("실제입OBS관측", evidence)
                    except Exception as exc:
                        # 방금 재생한 구간을 다시 실행하지 않는다.
                        evidence_error = exc
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
                if evidence_error is not None:
                    raise RuntimeError(
                        "실제 입·OBS 동일 WAV 관측 영구 기록 실패 · 재발화 차단")
