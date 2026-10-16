"""Real Open-LLM-VTuber text exchange over its official localhost WebSocket.

This is NOT an alternative LLM or synthetic broadcaster. The upstream core
performs the actual inference and (when configured) TTS. The application only
reads the returned transcript; it does not play decoded audio or stream it.

Only call from a GUI action after the operator expressly accepts that the
upstream core may save conversation history and generate voice data. No network
connection is attempted while importing this module. Uses Python stdlib only.

Protocol reference: Open-LLM-VTuber/websocket_handler.py and
conversations/conversation_handler.py, conversation_utils.py, stream_audio.py
as checked against upstream main on 2026-10-16.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import os
import socket
import time
import threading
from typing import Callable

from .original_plan_ws import (
    HOST, PORT, PATH, _GUID, _read_http_upgrade, _extract_initialization,
    OfficialWsProbeError,
)

MAX_INCOMING_FRAME = 24 * 1024 * 1024  # Bound real TTS base64 payloads
MAX_FRAMES = 2048
MAX_INPUT = 4000


class RealConversationError(RuntimeError):
    """A real upstream exchange could not complete (never synthesize a reply)."""


@dataclass(frozen=True)
class RealConversationResult:
    """An actual upstream result, not evidence of TTS/playback/avatar motion."""
    text: str
    config_name: str
    model_name: str
    segments: int
    frames_received: int
    session_number: int = 1
    turn_number: int = 1
    wav_packets: int = 0
    wav_audio_bytes: int = 0
    invalid_audio_packets: int = 0
    silent_audio_packets: int = 0
    model_url: str = ''  # Actual upstream initialization metadata, NOT animation proof


def inspect_upstream_audio_event(msg: dict) -> tuple[str, int] | None:
    """Classify actual upstream audio frames without playing, saving or exposing them.

    The official stream_audio.prepare_audio_payload() serializes audio as
    base64-encoded WAV. Validate the container including both fmt and data chunks.
    A container can be valid while the speech, GPT-SoVITS voice, or lip sync
    are completely unverified. This function does NOT certify sound quality.
    """
    if msg.get('type') != 'audio':
        return None
    encoded = msg.get('audio')
    if encoded is None:
        return ('silent', 0)
    if not isinstance(encoded, str) or not encoded or len(encoded) > MAX_INCOMING_FRAME:
        return ('invalid', 0)
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error):
        return ('invalid', 0)
    # Exported pydub WAV: RIFF length, WAVE, fmt and nonempty data chunks.
    if (len(raw) < 44 or raw[:4] != b'RIFF' or raw[8:12] != b'WAVE'
            or int.from_bytes(raw[4:8], 'little') + 8 != len(raw)):
        return ('invalid', 0)
    offset = 12
    found_fmt = False
    found_data = False
    while offset + 8 <= len(raw):
        kind = raw[offset:offset + 4]
        length = int.from_bytes(raw[offset + 4:offset + 8], 'little')
        content = offset + 8
        end = content + length
        if end > len(raw):
            return ('invalid', 0)
        if kind == b'fmt ':
            if found_fmt or length < 16:
                return ('invalid', 0)
            audio_format = int.from_bytes(raw[content:content + 2], 'little')
            channels = int.from_bytes(raw[content + 2:content + 4], 'little')
            sample_rate = int.from_bytes(raw[content + 4:content + 8], 'little')
            if audio_format not in (1, 3) or channels < 1 or sample_rate < 1:
                return ('invalid', 0)
            found_fmt = True
        elif kind == b'data':
            if found_data or length == 0:
                return ('invalid', 0)
            found_data = True
        offset = end + (length & 1)
    if offset != len(raw) or not found_fmt or not found_data:
        return ('invalid', 0)
    return ('wav', len(raw))


def _exact(sock: socket.socket, count: int, pending: bytearray,
           deadline: float) -> bytes:
    if count < 0 or count > MAX_INCOMING_FRAME:
        raise RealConversationError('서버 응답 프레임이 너무 큽니다.')
    while len(pending) < count:
        left = deadline - time.monotonic()
        if left <= 0:
            raise RealConversationError('실제 AI 응답 시간 초과')
        sock.settimeout(left)
        incoming = sock.recv(min(65536, count - len(pending)))
        if not incoming:
            raise RealConversationError('공식 서버가 대화 중 연결을 종료했습니다.')
        pending.extend(incoming)
    payload = bytes(pending[:count])
    del pending[:count]
    return payload


def _send_masked(sock: socket.socket, opcode: int, payload: bytes) -> None:
    """Client frames MUST be masked under RFC 6455."""
    if len(payload) > 32 * 1024:
        raise ValueError('WebSocket 입력이 허용 크기를 초과했습니다.')
    mask = os.urandom(4)
    size = len(payload)
    length = bytes([size]) if size < 126 else (
        bytes([126]) + size.to_bytes(2, 'big') if size < 65536 else
        bytes([127]) + size.to_bytes(8, 'big')
    )
    framed = bytes([0x80 | opcode, 0x80 | length[0]]) + length[1:] + mask
    framed += bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    sock.sendall(framed)


def _read_message(sock: socket.socket, pending: bytearray, deadline: float) -> str | None:
    """Receive one UTF-8 JSON message; discard ping/pong, never play audio."""
    fragments: list[bytes] = []
    total = 0
    text_message = False
    while True:
        h = _exact(sock, 2, pending, deadline)
        if h[0] & 0x70 or h[1] & 0x80:
            raise RealConversationError('지원하지 않는 WebSocket 확장/마스킹 응답')
        fin = bool(h[0] & 0x80)
        op = h[0] & 0x0F
        length = h[1] & 0x7F
        if length == 126:
            length = int.from_bytes(_exact(sock, 2, pending, deadline), 'big')
        elif length == 127:
            length = int.from_bytes(_exact(sock, 8, pending, deadline), 'big')
        if length > MAX_INCOMING_FRAME or total + length > MAX_INCOMING_FRAME:
            raise RealConversationError('공식 서버 응답이 최대 크기를 초과했습니다.')
        if op in (8, 9, 10) and (length > 125 or not fin):
            raise RealConversationError('잘못된 WebSocket 제어 프레임')
        payload = _exact(sock, length, pending, deadline)
        if op == 9:
            _send_masked(sock, 10, payload)
            continue
        if op == 10:
            continue
        if op == 8:
            raise RealConversationError('공식 서버가 대화 응답 전에 연결을 닫았습니다.')
        if op == 1 and not fragments:
            text_message = True
        elif op == 0 and fragments:
            pass
        else:
            raise RealConversationError('공식 대화 데이터가 예상한 텍스트 프레임 형식이 아닙니다.')
        fragments.append(payload)
        total += len(payload)
        if fin:
            if not text_message:
                raise RealConversationError('서버가 예상하지 않은 바이너리 응답을 보냈습니다.')
            try:
                return b''.join(fragments).decode('utf-8', errors='strict')
            except UnicodeDecodeError as exc:
                raise RealConversationError('공식 응답이 올바른 UTF-8이 아닙니다.') from exc


def _read_upstream_json(sock: socket.socket, pending: bytearray,
                        deadline: float) -> dict | None:
    raw = _read_message(sock, pending, deadline)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise RealConversationError('공식 AI 응답이 JSON 형식이 아닙니다.') from exc
    if not isinstance(data, dict) or not isinstance(data.get('type'), str):
        raise RealConversationError('공식 AI 응답의 메시지 형식이 올바르지 않습니다.')
    return data


def extract_reply_segment(msg: dict) -> str | None:
    """Official output text accompanies an `audio` event even with audio=None.

    Ignores binary/base64 audio and status messages. Never guesses a response
    from 'Thinking...' or an initial 'Connection established' event.
    """
    if msg.get('type') != 'audio':
        return None
    display = msg.get('display_text')
    if not isinstance(display, dict):
        return None
    content = display.get('text')
    return content if isinstance(content, str) and content else None


class OfficialConversationSession:
    """Reuse one real upstream WebSocket across successive operator-approved turns.

    The upstream session owns its memory/history and answer generation. AISTING
    does not invent or replay history. A lost connection is *not* transparently
    retried: resending a prompt could duplicate an upstream action/response.
    The UI must separately explain when a *new* upstream session is created.
    """

    def __init__(self) -> None:
        self._sock: socket.socket | None = None
        self._pending = bytearray()
        self._initialization = None
        self._busy = threading.Lock()
        self._shutdown = threading.Event()
        self._turns = 0
        self._session_number = 0

    @property
    def connected(self) -> bool:
        return self._sock is not None and not self._shutdown.is_set()

    @property
    def turns_completed(self) -> int:
        return self._turns

    def _connect(self, deadline: float) -> None:
        if self._sock is not None:
            return
        if self._shutdown.is_set():
            raise RealConversationError('대화 창이 종료되었습니다.')
        key = base64.b64encode(os.urandom(16)).decode('ascii')
        request = (f'GET {PATH} HTTP/1.1\r\nHost: {HOST}:{PORT}\r\n'
                   'Upgrade: websocket\r\nConnection: Upgrade\r\n'
                   f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RealConversationError('서버 연결 제한 시간이 지났습니다.')
        sock = socket.create_connection((HOST, PORT), timeout=min(remaining, 10.0))
        self._sock = sock  # Expose immediately so GUI close() can interrupt recv.
        try:
            if self._shutdown.is_set():
                raise RealConversationError('대화 창이 종료되었습니다.')
            sock.sendall(request.encode('ascii'))
            self._pending = _read_http_upgrade(sock, key, deadline)
            for observed in range(1, 33):
                if self._shutdown.is_set():
                    raise RealConversationError('대화 창이 종료되었습니다.')
                evt = _read_upstream_json(sock, self._pending, deadline)
                if evt is None:
                    continue
                if evt.get('type') == 'error':
                    raise RealConversationError('공식 AI 초기화 실패: ' + str(evt.get('message', 'unknown'))[:200])
                init = _extract_initialization(evt, observed)
                if init is not None:
                    self._initialization = init
                    self._session_number += 1
                    return
            raise RealConversationError('공식 AI 초기화 메시지를 받지 못했습니다.')
        except BaseException:
            self._discard_connection()
            raise

    def _discard_connection(self) -> None:
        sock = self._sock
        self._sock = None
        self._pending = bytearray()
        self._initialization = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()

    def ask(self, message: str, *, operator_approved: bool = False,
            timeout: float = 120.0,
            on_progress: Callable[[str, str | int], None] | None = None) -> RealConversationResult:
        """Send one approved prompt in order over the SAME upstream session.

        The lock is only for turn ordering, not arbitrary artificial delay or
        selection: all calls made by the caller get one request if they are
        explicitly approved. No automatic retry after an uncertain send.
        """
        if operator_approved is not True:
            raise PermissionError('실제 AI 실행·대화기록·TTS 생성에는 이번 질문의 명시 승인이 필요합니다.')
        if not isinstance(message, str) or not message.strip() or len(message) > MAX_INPUT:
            raise ValueError('실제 AI에 보낼 문장은 1~4000자여야 합니다.')
        if type(timeout) not in (float, int) or not 10 <= timeout <= 300:
            raise ValueError('응답 제한 시간은 10~300초여야 합니다.')
        if self._shutdown.is_set():
            raise RealConversationError('종료한 세션을 다시 실행하지 않습니다.')
        if on_progress is not None and not callable(on_progress):
            raise TypeError('on_progress must be callable or None')
        with self._busy:
            deadline = time.monotonic() + float(timeout)
            try:
                if self._sock is None:
                    self._connect(deadline)
                if self._shutdown.is_set():
                    raise RealConversationError('대화 창이 종료되어 전송하지 않았습니다.')
                sock = self._sock
                assert sock is not None
                # The official server processes text-input in this connection's context.
                _send_masked(sock, 1, json.dumps({'type': 'text-input', 'text': message.strip()},
                                                 ensure_ascii=False).encode('utf-8'))
                segments: list[str] = []
                wav_packets = 0
                wav_audio_bytes = 0
                invalid_audio_packets = 0
                silent_audio_packets = 0
                for observed in range(1, MAX_FRAMES + 1):
                    if self._shutdown.is_set():
                        raise RealConversationError('대화 창이 종료되었습니다.')
                    evt = _read_upstream_json(sock, self._pending, deadline)
                    if evt is None:
                        continue
                    kind = evt['type']
                    if kind == 'error':
                        raise RealConversationError('공식 AI 응답 실패: ' + str(evt.get('message', 'unknown'))[:200])
                    segment = extract_reply_segment(evt)
                    if segment is not None:
                        segments.append(segment)
                        # Only genuine upstream segments; never echo a fake AI answer.
                        if on_progress is not None:
                            try:
                                on_progress('text', segment)
                            except Exception:
                                # Display failure must not interrupt the real LLM/TTS
                                # turn or cause the prompt to be resent.
                                pass
                    audio_result = inspect_upstream_audio_event(evt)
                    if audio_result is not None:
                        audio_status, audio_bytes = audio_result
                        if audio_status == 'wav':
                            wav_packets += 1
                            wav_audio_bytes += audio_bytes
                        elif audio_status == 'silent':
                            silent_audio_packets += 1
                        else:
                            invalid_audio_packets += 1
                        if on_progress is not None:
                            try:
                                on_progress('audio_' + audio_status, audio_bytes)
                            except Exception:
                                pass
                    if kind == 'control' and evt.get('text') == 'conversation-chain-end':
                        answer = ''.join(segments).strip()
                        if not answer:
                            raise RealConversationError('공식 AI 대화가 종료됐지만 응답 문장이 없었습니다.')
                        self._turns += 1
                        return RealConversationResult(
                            text=answer, config_name=self._initialization.config_name,
                            model_name=self._initialization.model_name,
                            segments=len(segments), frames_received=observed,
                            session_number=self._session_number,
                            turn_number=self._turns,
                            wav_packets=wav_packets,
                            wav_audio_bytes=wav_audio_bytes,
                            invalid_audio_packets=invalid_audio_packets,
                            silent_audio_packets=silent_audio_packets,
                            model_url=self._initialization.model_url,
                        )
                raise RealConversationError('공식 AI 응답 프레임 한도를 초과했습니다.')
            except (OfficialWsProbeError, OSError, TimeoutError, RealConversationError) as exc:
                # Never reuse half-consumed buffers or claim the conversation finished.
                self._discard_connection()
                if isinstance(exc, RealConversationError):
                    raise
                raise RealConversationError('실제 공식 서버 연결 또는 응답 실패: ' + str(exc)) from exc

    def close(self) -> None:
        """Stop only this client socket; never terminate official server/OBS."""
        self._shutdown.set()
        self._discard_connection()

    def __enter__(self):
        return self

    def __exit__(self, _typ, _value, _traceback) -> None:
        self.close()


def ask_real_official_ai(message: str, *, operator_approved: bool = False,
                         timeout: float = 120.0) -> RealConversationResult:
    """Compatibility one-shot API; use OfficialConversationSession for multi-turn."""
    if operator_approved is not True:
        raise PermissionError('실제 AI 실행·대화기록·TTS 생성에는 이번 질문의 명시 승인이 필요합니다.')
    if not isinstance(message, str) or not message.strip() or len(message) > MAX_INPUT:
        raise ValueError('실제 AI에 보낼 문장은 1~4000자여야 합니다.')
    with OfficialConversationSession() as session:
        return session.ask(message, operator_approved=True, timeout=timeout)
