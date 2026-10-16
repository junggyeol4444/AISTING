"""Read the REAL Open-LLM-VTuber WebSocket initialization handshake.

This is a Stage-1 *connection diagnostic*, not an LLM/TTS/Live2D acceptance
check.  It never sends a text-input, mic-audio, ai-speak or TTS request.
The official server may create session state when a client connects, so the
operator must approve each connection in the GUI. No package installation.

Protocol cross-checked read-only against upstream Open-LLM-VTuber:
  src/open_llm_vtuber/routes.py: /client-ws
  src/open_llm_vtuber/websocket_handler.py: set-model-and-conf
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
import os
import socket
import time

HOST = '127.0.0.1'
PORT = 12393
PATH = '/client-ws'
_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
_MAX_HEADER = 16384
_MAX_MESSAGE = 512 * 1024


class OfficialWsProbeError(RuntimeError):
    """Cannot confirm the official server's initial WebSocket protocol."""


@dataclass(frozen=True)
class OfficialWsInitialization:
    """Upstream initialization metadata; NOT evidence of AI or avatar action."""
    config_name: str
    model_name: str
    model_url: str
    messages_observed: int


def _read_exact(sock: socket.socket, count: int, pending: bytearray, deadline: float) -> bytes:
    if count < 0 or count > _MAX_MESSAGE:
        raise OfficialWsProbeError('WebSocket 응답 크기가 허용 범위를 벗어났습니다.')
    while len(pending) < count:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OfficialWsProbeError('공식 WebSocket 초기화 응답 시간 초과')
        sock.settimeout(remaining)
        data = sock.recv(min(65536, count - len(pending)))
        if not data:
            raise OfficialWsProbeError('공식 WebSocket이 초기화 전에 연결을 닫았습니다.')
        pending.extend(data)
    result = bytes(pending[:count])
    del pending[:count]
    return result


def _read_http_upgrade(sock: socket.socket, key: str, deadline: float) -> bytearray:
    pending = bytearray()
    while b'\r\n\r\n' not in pending:
        if len(pending) > _MAX_HEADER:
            raise OfficialWsProbeError('WebSocket 업그레이드 헤더가 너무 큽니다.')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OfficialWsProbeError('WebSocket 업그레이드 시간 초과')
        sock.settimeout(remaining)
        chunk = sock.recv(4096)
        if not chunk:
            raise OfficialWsProbeError('WebSocket 업그레이드 응답이 없습니다.')
        pending.extend(chunk)
    head, body = bytes(pending).split(b'\r\n\r\n', 1)
    if len(head) > _MAX_HEADER:
        raise OfficialWsProbeError('WebSocket 업그레이드 헤더가 너무 큽니다.')
    try:
        rows = head.decode('ascii').split('\r\n')
    except UnicodeDecodeError as exc:
        raise OfficialWsProbeError('WebSocket 응답 헤더가 유효하지 않습니다.') from exc
    if not rows[0].startswith('HTTP/1.1 101 '):
        raise OfficialWsProbeError('실제 WebSocket 업그레이드(HTTP 101)가 확인되지 않았습니다.')
    headers: dict[str, str] = {}
    for row in rows[1:]:
        if ':' not in row:
            raise OfficialWsProbeError('WebSocket 헤더 형식이 유효하지 않습니다.')
        k, v = row.split(':', 1)
        name = k.lower().strip()
        if name in headers:
            raise OfficialWsProbeError('중복 WebSocket 헤더: ' + name)
        headers[name] = v.strip()
    expected = base64.b64encode(hashlib.sha1((key + _GUID).encode('ascii')).digest()).decode('ascii')
    if (headers.get('sec-websocket-accept') != expected
            or headers.get('upgrade', '').lower() != 'websocket'
            or 'upgrade' not in [v.strip().lower() for v in headers.get('connection', '').split(',')]):
        raise OfficialWsProbeError('WebSocket 서버의 프로토콜 확인값이 올바르지 않습니다.')
    if headers.get('sec-websocket-extensions'):
        raise OfficialWsProbeError('요청하지 않은 WebSocket 확장 프로토콜입니다.')
    return bytearray(body)


def _send_control(sock: socket.socket, opcode: int, payload: bytes) -> None:
    """WebSocket masked protocol pong/close only; never application messages."""
    if len(payload) > 125:
        raise OfficialWsProbeError('WebSocket 제어 프레임이 비정상적으로 큽니다.')
    mask = os.urandom(4)
    frame = bytes([0x80 | opcode, 0x80 | len(payload)]) + mask
    frame += bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
    sock.sendall(frame)


def _next_text_frame(sock: socket.socket, pending: bytearray, deadline: float) -> str | None:
    head = _read_exact(sock, 2, pending, deadline)
    fin = bool(head[0] & 0x80)
    opcode = head[0] & 0x0F
    if head[0] & 0x70 or not fin:
        raise OfficialWsProbeError('지원하지 않는 WebSocket 분할/확장 프레임입니다.')
    if head[1] & 0x80:
        raise OfficialWsProbeError('서버가 마스킹된 WebSocket 프레임을 보냈습니다.')
    size = head[1] & 0x7F
    if size == 126:
        size = int.from_bytes(_read_exact(sock, 2, pending, deadline), 'big')
    elif size == 127:
        size = int.from_bytes(_read_exact(sock, 8, pending, deadline), 'big')
    if size > _MAX_MESSAGE or (opcode in (8, 9, 10) and size > 125):
        raise OfficialWsProbeError('WebSocket 프레임 크기가 비정상적입니다.')
    payload = _read_exact(sock, size, pending, deadline)
    if opcode == 9:  # ping: protocol-level pong, not AI text or audio
        _send_control(sock, 10, payload)
        return None
    if opcode == 10:
        return None
    if opcode == 8:
        raise OfficialWsProbeError('공식 WebSocket이 초기화 메시지 전에 종료되었습니다.')
    if opcode != 1:
        raise OfficialWsProbeError('공식 초기화 단계에서 예상하지 않은 바이너리 프레임입니다.')
    try:
        return payload.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise OfficialWsProbeError('WebSocket 텍스트가 UTF-8이 아닙니다.') from exc


def _extract_initialization(message: object, observed: int) -> OfficialWsInitialization | None:
    if not isinstance(message, dict) or message.get('type') != 'set-model-and-conf':
        return None
    model = message.get('model_info')
    conf = message.get('conf_name')
    uid = message.get('client_uid')
    if not isinstance(model, dict) or not isinstance(conf, str) or not isinstance(uid, str):
        raise OfficialWsProbeError('공식 초기화 메시지 필드가 불완전합니다.')
    name = model.get('name')
    url = model.get('url')
    if (not isinstance(name, str) or not name.strip() or not isinstance(url, str)
            or not url.startswith('/live2d-models/') or not url.endswith('.model3.json')):
        raise OfficialWsProbeError('공식 Live2D 모델 초기화 정보가 유효하지 않습니다.')
    return OfficialWsInitialization(conf, name, url, observed)


def probe_official_ws_initialization(*, operator_approved: bool = False,
                                     timeout: float = 8.0) -> OfficialWsInitialization:
    """Observe only real localhost upstream startup metadata after consent.

    A successful result proves an HTTP WebSocket upgrade and the matching
    upstream initialization *message format*. It does not authenticate the
    server binary or demonstrate a generated response, voice or animation.
    """
    if operator_approved is not True:
        raise PermissionError('실제 서버 세션 생성은 운영자의 이번 실행 승인이 필요합니다.')
    if not 1.0 <= timeout <= 30.0:
        raise ValueError('검사 제한 시간이 올바르지 않습니다.')
    key = base64.b64encode(os.urandom(16)).decode('ascii')
    deadline = time.monotonic() + timeout
    request = (f'GET {PATH} HTTP/1.1\r\nHost: {HOST}:{PORT}\r\n'
               'Upgrade: websocket\r\nConnection: Upgrade\r\n'
               f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n')
    try:
        with socket.create_connection((HOST, PORT), timeout=timeout) as sock:
            sock.sendall(request.encode('ascii'))
            pending = _read_http_upgrade(sock, key, deadline)
            for observed in range(1, 25):
                text = _next_text_frame(sock, pending, deadline)
                if text is None:
                    continue
                try:
                    message = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise OfficialWsProbeError('공식 초기화 응답이 JSON이 아닙니다.') from exc
                result = _extract_initialization(message, observed)
                if result is not None:
                    return result
            raise OfficialWsProbeError('공식 set-model-and-conf 초기화 메시지를 받지 못했습니다.')
    except (OSError, TimeoutError) as exc:
        raise OfficialWsProbeError('실제 로컬 WebSocket 연결 또는 초기화에 실패했습니다.') from exc
