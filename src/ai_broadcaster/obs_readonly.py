"""OBS Studio v5 WebSocket READ-ONLY client using Python's standard library.

Connections only to 127.0.0.1; methods restricted to version, scene list and
stream status and selected scene items. Never changes OBS or stores passwords.
User must click '연결 상태 확인' in Windows EXE to invoke this.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import socket
import struct
from dataclasses import dataclass


class ObsError(RuntimeError):
    """OBS 연결/인증/프로토콜 오류."""


ALLOWED_REQUESTS = frozenset({"GetVersion", "GetSceneList", "GetStreamStatus", "GetSceneItemList"})
MAX_FRAME = 1_000_000


@dataclass(frozen=True)
class SceneItem:
    source_name: str
    input_kind: str | None
    enabled: bool
    item_id: int


@dataclass(frozen=True)
class ObsSnapshot:
    obs_version: str
    websocket_version: str
    scenes: tuple[str, ...]
    streaming: bool
    inspected_scene: str | None = None
    scene_items: tuple[SceneItem, ...] = ()


def avatar_capture_diagnostic(snapshot: ObsSnapshot) -> str:
    """Only identify candidates: OBS input settings and actual captured window not checked."""
    if not isinstance(snapshot, ObsSnapshot):
        raise TypeError("OBS 상태가 필요합니다.")
    if snapshot.inspected_scene is None:
        return "장면을 선택한 뒤 '장면 소스 확인'을 누르세요."
    active_windows = [
        source for source in snapshot.scene_items
        if source.enabled and source.input_kind == "window_capture"
    ]
    if any("aisting" in source.source_name.casefold() for source in active_windows):
        return "AISTING 이름의 활성 창 캡처 후보 발견 · 실제 화면 연결은 OBS에서 직접 확인"
    if active_windows:
        return "활성 창 캡처 소스가 있지만 AISTING 창 연결 여부는 미확인"
    return "이 장면에서 활성 창 캡처 소스를 찾지 못했습니다. OBS에서 직접 추가해 주세요."


def _read_exact(sock: socket.socket, amount: int) -> bytes:
    if amount < 0 or amount > MAX_FRAME:
        raise ObsError("OBS 메시지가 너무 깁니다.")
    chunks = []
    while amount:
        part = sock.recv(amount)
        if not part:
            raise ObsError("OBS가 연결을 종료했습니다.")
        chunks.append(part)
        amount -= len(part)
    return b"".join(chunks)


def _send_frame(sock: socket.socket, payload: bytes, opcode: int = 1) -> None:
    if len(payload) > MAX_FRAME:
        raise ObsError("OBS 요청이 너무 큽니다.")
    mask = os.urandom(4)
    header = bytearray([0x80 | opcode])
    length = len(payload)
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header += struct.pack("!H", length)
    else:
        header.append(0x80 | 127)
        header += struct.pack("!Q", length)
    masked = bytes(b ^ mask[i % 4] for i,b in enumerate(payload))
    sock.sendall(bytes(header) + mask + masked)


def _read_json(sock: socket.socket) -> dict:
    assembled = bytearray()
    first = None
    while True:
        a,b = _read_exact(sock,2)
        opcode = a & 0x0f
        final = bool(a & 0x80)
        if a & 0x70 or b & 0x80:
            raise ObsError("OBS WebSocket 프레임 형식이 올바르지 않습니다.")
        length = b & 0x7f
        if length == 126:
            length = struct.unpack("!H", _read_exact(sock,2))[0]
        elif length == 127:
            length = struct.unpack("!Q", _read_exact(sock,8))[0]
        if length > MAX_FRAME or len(assembled)+length > MAX_FRAME:
            raise ObsError("OBS 메시지 제한을 초과했습니다.")
        if opcode in (8, 9, 10):
            if not final or length > 125:
                raise ObsError("OBS 제어 프레임 오류")
            data = _read_exact(sock,length)
            if opcode == 8:
                raise ObsError("OBS가 WebSocket 연결을 종료했습니다.")
            if opcode == 9:
                _send_frame(sock,data,opcode=10)
            continue
        if opcode == 1:
            if first is not None:
                raise ObsError("OBS 프레임 중복")
            first = 1
        elif opcode != 0 or first is None:
            raise ObsError("OBS 텍스트 응답이 아닙니다.")
        assembled += _read_exact(sock,length)
        if final:
            try:
                data = json.loads(assembled.decode("utf-8"))
            except (UnicodeError,ValueError) as exc:
                raise ObsError("OBS JSON 응답 오류") from exc
            if not isinstance(data,dict) or type(data.get("op")) is not int or not isinstance(data.get("d"),dict):
                raise ObsError("OBS 프로토콜 응답 오류")
            return data


def _handshake(sock: socket.socket) -> None:
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        "GET / HTTP/1.1\r\n"
        "Host: 127.0.0.1\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    ).encode("ascii")
    sock.sendall(request)
    header = bytearray()
    while not header.endswith(b"\r\n\r\n"):
        if len(header) >= 8192:
            raise ObsError("OBS WebSocket 응답 헤더가 너무 깁니다.")
        header += _read_exact(sock,1)
    try:
        lines = header.decode("latin1").split("\r\n")
        if not re.match(r"^HTTP/1\.[01] 101(?: |$)",lines[0]):
            raise ObsError("OBS WebSocket 업그레이드 실패")
        fields = {}
        for line in lines[1:]:
            if ":" in line:
                k,v = line.split(":",1)
                fields[k.strip().lower()] = v.strip()
        expected = base64.b64encode(
            hashlib.sha1((key+"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if fields.get("sec-websocket-accept") != expected:
            raise ObsError("OBS WebSocket 서버 인증 오류")
        if fields.get("upgrade","").lower() != "websocket":
            raise ObsError("OBS WebSocket 업그레이드 헤더 누락")
        if "upgrade" not in fields.get("connection","").lower():
            raise ObsError("OBS 연결 업그레이드 헤더 누락")
    except UnicodeError as exc:
        raise ObsError("OBS HTTP 응답 오류") from exc


def _authentication(password: str, challenge: str, salt: str) -> str:
    if not isinstance(password,str) or not isinstance(challenge,str) or not isinstance(salt,str):
        raise ObsError("OBS 인증 정보 형식 오류")
    secret = base64.b64encode(hashlib.sha256((password+salt).encode("utf-8")).digest())
    return base64.b64encode(hashlib.sha256(secret+challenge.encode("utf-8")).digest()).decode("ascii")


def _request(
    sock: socket.socket, name: str, seq: int, *,
    scene_name: str | None = None,
) -> dict:
    if name not in ALLOWED_REQUESTS:
        raise ObsError("OBS 읽기 전용 모드에서 허용되지 않은 요청입니다.")
    if type(seq) is not int or seq < 0:
        raise ObsError("OBS 요청 번호 오류")
    if name == "GetSceneItemList":
        if not isinstance(scene_name, str) or not 1 <= len(scene_name) <= 256 or not scene_name.strip():
            raise ObsError("장면 이름이 올바르지 않습니다.")
        request_data = {"sceneName": scene_name}
    elif scene_name is not None:
        raise ObsError("해당 조회에는 장면 이름을 지정할 수 없습니다.")
    else:
        request_data = None
    rid = f"aisting-read-{seq}"
    request = {"requestType": name, "requestId": rid}
    if request_data is not None:
        request["requestData"] = request_data
    _send_frame(sock,json.dumps({
        "op":6,"d":request
    },ensure_ascii=False,separators=(",",":")).encode("utf-8"))
    # OBS may emit events after Identify; skip bounded unrelated events only.
    for _ in range(20):
        data = _read_json(sock)
        if data["op"] != 7:
            continue
        reply = data["d"]
        if reply.get("requestId") != rid or reply.get("requestType") != name:
            raise ObsError("OBS 응답 ID가 일치하지 않습니다.")
        status = reply.get("requestStatus")
        if not isinstance(status,dict) or status.get("result") is not True:
            raise ObsError(f"OBS {name} 조회 실패")
        content = reply.get("responseData",{})
        if not isinstance(content,dict):
            raise ObsError("OBS 응답 데이터가 올바르지 않습니다.")
        return content
    raise ObsError("OBS에서 요청 응답을 확인할 수 없습니다.")


def get_obs_snapshot(
    *, port: int = 4455, password: str = "", timeout: float = 5.0,
    scene_name: str | None = None,
) -> ObsSnapshot:
    """Operator-triggered loopback-only OBS status snapshot; no write operations."""
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("OBS 포트는 1~65535 범위입니다.")
    if not isinstance(password,str) or len(password)>512:
        raise ValueError("OBS 암호가 너무 깁니다.")
    if type(timeout) not in (int,float) or not 0 < timeout <= 20:
        raise ValueError("OBS 연결 제한 시간은 0~20초 범위입니다.")
    if scene_name is not None and (
        not isinstance(scene_name, str) or not 1 <= len(scene_name) <= 256 or not scene_name.strip()
    ):
        raise ValueError("장면 이름은 1~256글자로 선택해야 합니다.")
    try:
        with socket.create_connection(("127.0.0.1",port),timeout=timeout) as sock:
            sock.settimeout(timeout)
            _handshake(sock)
            hello = _read_json(sock)
            if hello["op"] != 0:
                raise ObsError("OBS WebSocket 5.x Hello 응답이 아닙니다.")
            h=hello["d"]
            identify={"rpcVersion":1,"eventSubscriptions":0}
            auth=h.get("authentication")
            if auth is not None:
                if not isinstance(auth,dict) or not isinstance(auth.get("challenge"),str) or not isinstance(auth.get("salt"),str):
                    raise ObsError("OBS 인증 요청 형식 오류")
                if not password:
                    raise ObsError("OBS WebSocket 비밀번호가 필요합니다.")
                identify["authentication"]=_authentication(password,auth["challenge"],auth["salt"])
            _send_frame(sock,json.dumps({"op":1,"d":identify},separators=(",",":")).encode("utf-8"))
            identified=_read_json(sock)
            if identified["op"] != 2:
                raise ObsError("OBS 인증 실패 또는 WebSocket 버전 불일치")
            ver=_request(sock,"GetVersion",1)
            scenes=_request(sock,"GetSceneList",2)
            stream=_request(sock,"GetStreamStatus",3)
            entries=scenes.get("scenes",[])
            if not isinstance(entries,list) or len(entries)>500:
                raise ObsError("OBS 장면 목록 형식 오류")
            names=[]
            for item in entries:
                name=item.get("sceneName") if isinstance(item,dict) else None
                if not isinstance(name,str) or len(name)>256:
                    raise ObsError("OBS 장면 이름 형식 오류")
                names.append(name)
            streaming=stream.get("outputActive")
            if type(streaming) is not bool:
                raise ObsError("OBS 송출 상태 형식 오류")
            obs_version=ver.get("obsVersion")
            ws_version=ver.get("obsWebSocketVersion")
            if not isinstance(obs_version,str) or not isinstance(ws_version,str):
                raise ObsError("OBS 버전 확인 실패")
            if scene_name is None:
                return ObsSnapshot(obs_version,ws_version,tuple(names),streaming)
            if scene_name not in names:
                raise ObsError("선택한 OBS 장면이 현재 장면 목록에 없습니다.")
            scene_data=_request(sock,"GetSceneItemList",4,scene_name=scene_name)
            raw_items=scene_data.get("sceneItems")
            if not isinstance(raw_items,list) or len(raw_items)>500:
                raise ObsError("OBS 장면 소스 목록 형식 오류")
            items=[]
            for raw in raw_items:
                if not isinstance(raw,dict):
                    raise ObsError("OBS 장면 소스 데이터 오류")
                name=raw.get("sourceName")
                kind=raw.get("inputKind")
                enabled=raw.get("sceneItemEnabled")
                item_id=raw.get("sceneItemId")
                if (not isinstance(name,str) or not 1<=len(name)<=256
                    or (kind is not None and (not isinstance(kind,str) or len(kind)>128))
                    or type(enabled) is not bool or type(item_id) is not int or item_id<0):
                    raise ObsError("OBS 장면 소스 필드 오류")
                items.append(SceneItem(name,kind,enabled,item_id))
            return ObsSnapshot(obs_version,ws_version,tuple(names),streaming,scene_name,tuple(items))
    except (OSError,TimeoutError) as exc:
        raise ObsError("내 PC의 OBS(127.0.0.1)와 연결할 수 없습니다. OBS WebSocket 설정을 확인해 주세요.") from exc
