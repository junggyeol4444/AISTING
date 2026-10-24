"""Operator-selected, read-only CHZZK / SOOP / YouTube live chat transports.

No platform chat posting, OAuth login, account scraping, credential persistence,
startup connections or stream start. Each adapter is an explicit, stoppable reader.
Unofficial CHZZK/SOOP protocols may change; connection errors are surfaced.
"""
from __future__ import annotations

import json
import math
from collections import deque
import re
import ssl
import threading
import time
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError


@dataclass(frozen=True)
class PlatformChat:
    channel: str
    sender: str
    text: str
    platform: str
    # 서버가 제공한 실제 이벤트 ID만 재연결 중복 수신 확인에 사용한다.
    # 동일한 본문·작성자의 별개 채팅은 절대 합치지 않는다.
    event_id: str | None = field(default=None, compare=False, repr=False)


def _json_get(url: str, *, timeout: float = 10, headers: dict | None = None) -> dict:
    # Authentication, when explicitly supplied, travels only via HTTPS
    # Authorization headers, never an API URL, print, saved file or log.
    request_headers = {"User-Agent": "AISTING/1.0 (read-only chat)",
                       "Accept": "application/json"}
    if headers is not None:
        if not url.startswith("https://www.googleapis.com/youtube/v3/"):
            raise ValueError("인증된 유튜브 읽기 주소가 올바르지 않습니다.")
        request_headers.update(headers)
    request = Request(url, headers=request_headers)
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError("공개 방송 메타정보 HTTP 오류")
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("방송 메타정보 크기 초과")
    result = json.loads(raw.decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("방송 메타정보 형식 오류")
    return result


def parse_chzzk_frame(raw: str, channel: str) -> list[PlatformChat]:
    """Parse all normal chat records, not a selected subset."""
    frame = json.loads(raw)
    if not isinstance(frame, dict) or frame.get("cmd") not in (93101, 15101):
        return []
    body = frame.get("bdy")
    if isinstance(body, dict):
        body = body.get("messageList")
    if not isinstance(body, list):
        raise ValueError("치지직 채팅 목록 형식 오류")
    out = []
    for item in body:
        # 실제 채팅 명령의 형식 오류를 조용히 건너뛰면 이 프레임의
        # 서버 채팅 수와 로컬 FIFO 전달 건수가 달라도 알아챌 수 없다.
        # 전달 전 전체 프레임 파싱을 실패시켜 재연결·운영자 경고로 남긴다.
        if not isinstance(item, dict):
            raise ValueError("치지직 채팅 항목 형식 오류 · 프레임 전달 미확정")
        if not isinstance(item.get("msg"), str):
            raise ValueError("치지직 채팅 본문 형식 오류 · 프레임 전달 미확정")
        profile = item.get("profile") or {}
        if isinstance(profile, str):
            try:
                profile = json.loads(profile)
            except ValueError:
                profile = {}
        nick = profile.get("nickname") if isinstance(profile, dict) else None
        nick = nick or item.get("uid") or "anonymous"
        if item["msg"]:
            # 실제 서버 이벤트 ID가 있는 경우에만 재연결 중복 판별에 사용.
            # ID가 없거나 유효하지 않으면 동일 문장도 모두 전달한다.
            raw_id = item.get("msgId")
            event_id = (str(raw_id) if type(raw_id) is int and raw_id >= 0
                        else raw_id if type(raw_id) is str else None)
            if (event_id is not None
                    and (not 1 <= len(event_id) <= 256
                         or any(ord(ch) < 33 or ord(ch) > 126 for ch in event_id))):
                event_id = None
            out.append(PlatformChat(
                channel, str(nick), item["msg"], "chzzk", event_id))
    return out


def parse_soop_frame(raw: bytes | str, channel: str) -> list[PlatformChat]:
    """Parse SOOP form-feed chat packets, excluding control/entry/donation."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    if not isinstance(raw, str) or not raw.startswith("\x1b\t"):
        return []
    # A single WebSocket message may contain more than one 0x1b-09 packet.
    # Only chat command 0005 is forwarded. Preserve duplicates and order.
    result = []
    for frame in raw.split("\x1b\t")[1:]:
        if frame[:4] != "0005":
            continue
        # SOOP의 0005는 실제 채팅 명령이다. 짧거나 필드가
        # 잘린 채팅을 무시하고 프레임 처리를 성공으로 표시하지 않는다.
        if len(frame) < 12:
            raise ValueError("SOOP 채팅 프레임 길이 오류 · 전달 미확정")
        fields = frame[12:].split("\x0c")
        if len(fields) < 3:
            raise ValueError("SOOP 채팅 필드 형식 오류 · 전달 미확정")
        content, uid = fields[1], fields[2]
        # 0005 means an actual chat message. Never filter messages by
        # viewer-entered words like "1", "-1", "fw=", or whitespace.
        nick = (fields[6] if len(fields) > 6 and fields[6] not in ("0", "-1", "")
                else fields[3] if len(fields) > 3 and fields[3] else uid or "anonymous")
        result.append(PlatformChat(channel, nick, content, "soop"))
    return result


def parse_youtube_page(page: dict, channel: str) -> list[PlatformChat]:
    if not isinstance(page, dict) or not isinstance(page.get("items", []), list):
        raise ValueError("유튜브 채팅 응답 형식 오류")
    result = []
    for item in page.get("items", []):
        # 이미 API에서 수신한 항목이 손상됐다면 페이지를 완료로
        # 표시하지 않는다. 상위 수신기는 이 페이지를 FIFO에 넣기
        # 전에 전체 파싱하므로 잘못된 커서 확정을 피할 수 있다.
        if not isinstance(item, dict):
            raise ValueError("유튜브 채팅 페이지 항목 형식 오류 · 페이지 미확정")
        snippet = item.get("snippet")
        if not isinstance(snippet, dict):
            raise ValueError("유튜브 채팅 페이지 내용 형식 오류 · 페이지 미확정")
        # 기존 비채팅 제어 이벤트는 계속 제외한다.
        if snippet.get("type") not in ("textMessageEvent", "superChatEvent",
                                       "superStickerEvent", "memberMilestoneChatEvent"):
            continue
        author = item.get("authorDetails") or {}
        if not isinstance(author, dict):
            raise ValueError("유튜브 채팅 작성자 형식 오류 · 페이지 미확정")
        text = snippet.get("displayMessage")
        if not isinstance(text, str) or not text:
            raise ValueError("유튜브 채팅 본문 형식 오류 · 페이지 미확정")
        raw_id = item.get("id")
        event_id = (raw_id if isinstance(raw_id, str)
                    and 1 <= len(raw_id) <= 256 else None)
        result.append(PlatformChat(
            channel, str(author.get("displayName") or "YouTube 시청자"),
            text, "youtube", event_id))
    return result


class PreJoinChatResumeState:
    """승인 전 수신된 치지직·SOOP 채팅을 재연결 중 메모리에서 보존한다.

    서버 채팅방 식별자가 바뀌면 이전 방송의 미전달 사건을 새 방송에
    섞지 않는다. 프로세스 재시작·서버 미전송 사건의 복구는 보장하지 않는다.
    """

    def __init__(self) -> None:
        self.room_id: str | None = None
        self.pending: deque[PlatformChat] = deque()
        self._pending_ids: set[str] = set()
        self.duplicate_server_ids = 0

    def bind_room(self, room_id: str, *, accepted_pending: bool = False) -> None:
        if not isinstance(room_id, str) or not room_id.strip():
            raise ValueError("입장 전 채팅방 식별자 오류")
        if self.room_id is not None and self.room_id != room_id:
            if self.pending or accepted_pending:
                raise RuntimeError(
                    "채팅방이 변경되어 이전 방송의 미전달 채팅을 보존 중입니다. "
                    "운영자 확인 없이 다른 방송에 전달하지 않습니다.")
            self._pending_ids.clear()
        self.room_id = room_id

    def stage(self, chats: list[PlatformChat]) -> None:
        """서버 ID가 같은 재전송만 중복 차단하고 본문/닉네임은 구별한다."""
        if not isinstance(chats, list) or any(
                not isinstance(item, PlatformChat) for item in chats):
            raise ValueError("입장 전 채팅 임시 보관 형식 오류")
        new_items: list[PlatformChat] = []
        batch_ids: set[str] = set()
        duplicates = 0
        for item in chats:
            event_id = item.event_id
            if event_id is not None and (
                    event_id in self._pending_ids or event_id in batch_ids):
                duplicates += 1
                continue
            new_items.append(item)
            if event_id is not None:
                batch_ids.add(event_id)
        if len(self.pending) + len(new_items) > 4096:
            raise RuntimeError("JOIN 승인 전 채팅 임시 보관 한도 초과 · 누락 위험")
        self.pending.extend(new_items)
        self._pending_ids.update(batch_ids)
        self.duplicate_server_ids += duplicates

    def release_to(self, accepted_queue: deque[PlatformChat]) -> None:
        """JOIN 승인 뒤 이전 미수용 FIFO 앞쪽에만 안전하게 이어붙인다."""
        accepted_queue.extend(self.pending)
        self.pending.clear()
        self._pending_ids.clear()


class ReadOnlySession:
    def __init__(self, channel: str, emit):
        if not isinstance(channel, str) or not channel.strip() or len(channel) > 130:
            raise ValueError("채널 식별자가 올바르지 않습니다.")
        self.channel, self.emit = channel.strip(), emit
        self._stop = threading.Event()
        self._socket = None
        # 읽기 전용 WebSocket 프레임 안의 채팅은 로컬 FIFO가
        # 수용하기 전까지 메모리에만 보류한다. 재연결 시 상위
        # 세션에서 같은 deque를 연결해 미수용 프레임을 이어받는다.
        # 본문을 디스크·로그에 저장하거나 외부로 발신하지 않는다.
        self._pending_chats: deque[PlatformChat] = deque()
        self._chat_room_ready = False

    def _queue_received_chats(self, chats) -> None:
        """프레임 전체를 수용 확정 전에 보류해 뒤쪽 채팅도 보존한다."""
        self._pending_chats.extend(chats)

    def _flush_pending_chats(self) -> None:
        """실제 방 입장 뒤에만 이전 프레임부터 FIFO 순서로 전달한다.

        콜백이 False를 반환하거나 예외가 나면 미수용 선두 사건과
        나머지 사건을 pop하지 않는다. 다음 수신기에서 재시도한다.
        """
        if not self._chat_room_ready:
            return
        while self._pending_chats and not self._stop.is_set():
            item = self._pending_chats[0]
            if self.emit("chat", item) is False:
                raise RuntimeError(
                    "채팅 이벤트가 로컬 AI 큐에 수용되지 않아 보류 후 재연결합니다."
                )
            self._pending_chats.popleft()

    def stop(self):
        self._stop.set()
        sock = self._socket
        if sock:
            try:
                sock.close()
            except OSError:
                pass

    def _receive_socket(self, sock, parser, *, max_seconds=None, on_tick=None):
        import websocket
        deadline = time.monotonic() + max_seconds if max_seconds else None
        # 빈 채팅방과 통신 정지는 다르다. 채팅 본문이 아니라
        # 실제 서버 소켓 프레임의 도착 시간으로만 장기 반열림 감지.
        # 10분간 어떠한 프레임도 없다면 재접속을 요청한다.
        last_received_at = time.monotonic()
        while not self._stop.is_set():
            if deadline and time.monotonic() >= deadline:
                return
            if on_tick is not None:
                on_tick()
            # 새 연결이 JOIN 승인을 받은 뒤 과거 프레임의 미수용
            # 채팅부터 전달한다. 그 전에 새 소켓 데이터를 읽어
            # 채팅 순서를 뒤집지 않는다.
            self._flush_pending_chats()
            try:
                sock.settimeout(1)
                data = sock.recv()
            except websocket.WebSocketTimeoutException:
                if (max_seconds is None and not self._stop.is_set()
                        and time.monotonic() - last_received_at >= 600):
                    self.emit("transport_stalled", None)
                    raise ConnectionError("채팅 소켓 서버 응답이 10분간 없어서 재연결합니다.")
                continue
            except Exception:
                # The operator may close the socket while recv() is blocking.
                # An intentional stop is not a connection or chat failure.
                if self._stop.is_set():
                    return
                raise
            if self._stop.is_set():
                return
            if not data:
                raise RuntimeError("채팅 서버 연결이 종료됐습니다.")
            last_received_at = time.monotonic()
            # 내용 없는 채팅방에서도 실제 WebSocket 프레임 수신은
            # 연결 활동의 증거다. 메타데이터만 전달하고 본문 저장 없음.
            self.emit("transport_activity", None)
            # 전체 프레임을 먼저 보관한다. 콜백의 한 채팅이 실패해도
            # 동일 프레임 뒤쪽의 아직 미전달 채팅을 조용히 잃지 않는다.
            # 명시적 Stop에서는 후속 전달을 중지한다.
            self._queue_received_chats(parser(data, self.channel))
            self._flush_pending_chats()


class ChzzkReadOnlySession(ReadOnlySession):
    def __init__(self, channel: str, emit):
        super().__init__(channel, emit)
        self._prejoin_resume = PreJoinChatResumeState()
        if not re.fullmatch("[a-fA-F0-9]{32}", self.channel):
            raise ValueError("치지직 채널 ID는 32자리 16진수입니다.")

    def run(self, *, max_seconds=None):
        if self._stop.is_set():
            return
        import websocket
        live = _json_get("https://api.chzzk.naver.com/polling/v2/channels/"
                         + self.channel + "/live-status")
        live_id = (live.get("content") or {}).get("chatChannelId")
        if not isinstance(live_id, str) or not live_id:
            raise RuntimeError("치지직 방송이 진행 중이 아니거나 채팅방이 없습니다.")
        self._prejoin_resume.bind_room(
            live_id, accepted_pending=bool(self._pending_chats))
        token = _json_get("https://comm-api.game.naver.com/nng_main/v1/chats/"
                          "access-token?" + urlencode(
                            {"channelId": live_id, "chatType": "STREAMING"}))
        access = (token.get("content") or {}).get("accessToken")
        if not isinstance(access, str) or not access:
            raise RuntimeError("치지직 읽기 전용 접속 토큰을 받지 못했습니다.")
        index = sum(map(ord, live_id)) % 9 + 1
        sock = websocket.create_connection(
            "wss://kr-ss%d.chat.naver.com/chat" % index, timeout=10)
        self._socket = sock
        try:
            if self._stop.is_set():
                return
            sock.send(json.dumps({"ver":"2","cmd":100,"tid":1,"cid":live_id,
                                  "svcid":"game","bdy":{"uid":None,
                                    "devType":2001,"accTkn":access,"auth":"READ"}}))
            accepted = False
            # Chat may arrive during the server authentication handshake.
            # Preserve every original frame in order, then release it only
            # after a valid room-entry acknowledgement has been received.
            deadline = time.monotonic() + 15
            while not self._stop.is_set() and time.monotonic() < deadline:
                try:
                    sock.settimeout(2)
                    raw = sock.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception:
                    if self._stop.is_set():
                        return
                    raise
                if self._stop.is_set():
                    return
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError("치지직 접속 응답 형식 오류")
                self.emit("transport_activity", None)
                handshake_chats = parse_chzzk_frame(raw, self.channel)
                # JOIN 이전 연결에서 이미 수신한 사건도 동일 방송 ID인
                # 경우에만 유지한다. 프레임 재전송의 서버 ID 중복만 차단.
                self._prejoin_resume.stage(handshake_chats)
                if data.get("cmd") == 10100 and isinstance(data.get("bdy"), dict) and data["bdy"].get("sid"):
                    accepted = True
                    break
                if data.get("cmd") == 0:
                    sock.send('{"ver":"2","cmd":10000}')
            if self._stop.is_set():
                return
            if not accepted:
                raise RuntimeError("치지직 실제 채팅 연결 승인 응답이 없습니다.")
            self._chat_room_ready = True
            self.emit("ready", self.channel)
            # JOIN 전 받은 프레임도 현재 접속이 승인된 후에만
            # 이전 미수용 프레임 뒤에 넣고, 실패 시 함께 보존한다.
            self._prejoin_resume.release_to(self._pending_chats)
            self._flush_pending_chats()
            def parser(data, channel):
                frame = json.loads(data)
                if frame.get("cmd") == 0:
                    sock.send('{"ver":"2","cmd":10000}')
                    return []
                return parse_chzzk_frame(data, channel)
            self._receive_socket(sock, parser, max_seconds=max_seconds)
        finally:
            self._socket = None
            sock.close()
            self.emit("stopped", self.channel)


class SoopReadOnlySession(ReadOnlySession):
    def __init__(self, channel: str, emit):
        super().__init__(channel, emit)
        self._prejoin_resume = PreJoinChatResumeState()
        if not re.fullmatch("[A-Za-z0-9_]{2,30}/[0-9]{1,18}", self.channel):
            raise ValueError("SOOP은 방송자ID/방송번호 형태로 입력하세요.")

    def run(self, *, max_seconds=None):
        if self._stop.is_set():
            return
        import websocket
        from urllib.request import Request, urlopen
        bjid, bno = self.channel.split("/")
        data = urlencode({"bid":bjid,"bno":bno,"type":"live",
                          "confirm_adult":"false","player_type":"html5",
                          "mode":"landing","from_api":"0","pwd":"",
                          "stream_type":"common","quality":"HD"}).encode()
        request = Request("https://live.sooplive.com/afreeca/player_live_api.php?"
                          + urlencode({"bjid":bjid}), data=data,
                          headers={"Content-Type":"application/x-www-form-urlencoded"})
        with urlopen(request, timeout=10) as response:
            channel = json.loads(response.read(1_000_000)).get("CHANNEL") or {}
        domain, chatno, port = (channel.get("CHDOMAIN"),
                                channel.get("CHATNO"), channel.get("CHPT"))
        if not isinstance(domain, str) or not re.fullmatch(r"[a-zA-Z0-9.-]+", domain):
            raise RuntimeError("SOOP 실제 채팅 서버 정보가 올바르지 않습니다.")
        if not str(chatno).isdigit() or not str(port).isdigit():
            raise RuntimeError("SOOP 실제 채팅방 또는 포트 정보가 없습니다.")
        self._prejoin_resume.bind_room(
            str(chatno), accepted_pending=bool(self._pending_chats))
        sock = websocket.create_connection(
            f"wss://{domain}:{int(port)+1}/Websocket/{bjid}",
            timeout=10, subprotocols=["chat"],
            sslopt={"cert_reqs": ssl.CERT_REQUIRED, "check_hostname":True})
        self._socket = sock
        try:
            if self._stop.is_set():
                return
            sock.send("\x1b\t000100000600\x0c\x0c\x0c16\x0c")
            no = str(chatno)
            join_packet = ("\x1b\t0002%06d00\x0c%s\x0c\x0c\x0c\x0c\x0c" %
                           (len(no.encode("utf-8"))+6, no))
            # The server must acknowledge CONNECT (0001) before JOIN (0002).
            # A WebSocket connection alone does not mean the chat room was entered.
            self.emit("connected", self.channel)
            frames_seen = 0
            command_counts: dict[str, int] = {}
            join_sent = False
            entered = False
            next_ping = None
            # 실제 서버 JOIN 승인 전에 받은 0005 채팅은 임의 폐기하거나
            # 승인되지 않은 AI 호출로 전달하지 않고 동일 수신기 메모리에 보류.
            def parse_observed(raw, channel):
                nonlocal frames_seen, join_sent, entered, next_ping
                frames_seen += 1
                decoded = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
                if isinstance(decoded, str) and decoded.startswith("\x1b\t"):
                    for frame in decoded.split("\x1b\t")[1:]:
                        code = frame[:4]
                        if len(code) == 4 and code.isascii() and code.isdigit():
                            command_counts[code] = command_counts.get(code, 0) + 1
                        if code == "0001" and not join_sent:
                            sock.send(join_packet)
                            join_sent = True
                        elif code == "0002" and join_sent and not entered:
                            entered = True
                            self._chat_room_ready = True
                            next_ping = time.monotonic() + 60
                            self.emit("ready", self.channel)
                        elif code == "0007":
                            raise RuntimeError("SOOP 채팅 서버에서 연결 종료 응답을 받았습니다.")
                messages = parse_soop_frame(raw, channel)
                if not entered:
                    # JOIN 승인 전에 연결이 끊겨도 다음 수신기가 같은
                    # 채팅방 ID로 재접속하면 앞서 받은 사건을 먼저 전달.
                    self._prejoin_resume.stage(messages)
                    return []
                if self._prejoin_resume.pending:
                    # 기존 프레임 보류 큐를 먼저 연결해 재연결 전후 순서 보존.
                    # 서버 ID가 없는 SOOP의 동일 본문은 임의 중복 제거 금지.
                    self._prejoin_resume.release_to(self._pending_chats)
                return messages
            def keepalive():
                nonlocal next_ping
                if entered and next_ping is not None and time.monotonic() >= next_ping:
                    # SOOP 0000 keepalive is local protocol traffic, not a chat post.
                    sock.send("\x1b\t000000000100\x0c")
                    next_ping = time.monotonic() + 60
            try:
                self._receive_socket(sock, parse_observed, max_seconds=max_seconds,
                                     on_tick=keepalive)
            finally:
                # Counts only: never publish chat text or viewer identity.
                self.emit("packet_count", frames_seen)
                self.emit("packet_commands", dict(sorted(command_counts.items())))
        finally:
            self._socket = None
            sock.close()
            self.emit("stopped", self.channel)



_YOUTUBE_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")


def _youtube_video_id_or_none(value: str) -> str | None:
    """Resolve only well-formed public video references; raw liveChatIds still work.

    Never fetch arbitrary URLs. Actual ID-to-chat resolution uses Google's
    read-only videos.list with the operator-entered API key, not scraping.
    """
    if _YOUTUBE_VIDEO_ID.fullmatch(value):
        return value
    if "://" not in value:
        if any(ch in value for ch in ("/", "?", "#", "&", " ")):
            raise ValueError("유튜브 영상 ID 또는 주소 형식이 올바르지 않습니다.")
        return None  # Existing direct liveChatId; retain compatibility.
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.username is not None
            or parsed.password is not None or parsed.port is not None
            or parsed.fragment):
        raise ValueError("유튜브 주소는 HTTPS 공식 영상 주소여야 합니다.")
    host = (parsed.hostname or "").lower()
    if host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            ids = parse_qs(parsed.query).get("v", [])
            if len(ids) != 1 or not _YOUTUBE_VIDEO_ID.fullmatch(ids[0]):
                raise ValueError("유튜브 영상 주소에 올바른 v 값이 없습니다.")
            return ids[0]
        if parsed.path.startswith("/live/") and not parsed.query:
            video_id = parsed.path[len("/live/"):]
            if _YOUTUBE_VIDEO_ID.fullmatch(video_id):
                return video_id
    if host == "youtu.be" and not parsed.query:
        video_id = parsed.path.lstrip("/")
        if _YOUTUBE_VIDEO_ID.fullmatch(video_id):
            return video_id
    raise ValueError("유튜브 영상 주소 형식이 올바르지 않습니다.")


class YouTubeChatResumeState:
    """동일 공개 채팅방에 대한 네트워크 재연결 위치를 메모리에만 유지한다.

    저장 파일·계정 정보·메시지 본문은 보관하지 않는다. 실제로 전달한
    이벤트 ID만 기억하고 페이지는 마지막 항목을 전달한 뒤 확정한다.
    네트워크 공백 중 도착한 모든 채팅을 복구했다고 주장하지 않는다.
    """

    def __init__(self) -> None:
        self.live_chat_id: str | None = None
        self.next_page_token = ""
        self.recent_message_ids: deque[str] = deque()
        self.seen_message_ids: set[str] = set()
        self.delivered = 0
        self.completed_pages = 0
        # 현재 API 페이지의 파싱 완료 채팅을 콜백 수용 전 메모리에 보관한다.
        # 페이지 중간 실패 뒤 새 수신기가 다시 API를 호출하기 전에
        # 남은 사건을 이어서 전달한다. 본문/토큰은 파일에 저장하지 않는다.
        self.pending_page_chats: deque[PlatformChat] = deque()
        self.pending_page_active = False
        self.pending_page_next_token: str | None = None
        self.pending_page_poll_millis = 0
        self.pending_page_ended = False

    def stage_page(self, chats: list[PlatformChat], next_token: str | None,
                   poll_millis: int, ended: bool) -> None:
        """검증된 한 페이지를 먼저 보존하고 수용 완료 후에만 커서를 확정한다."""
        if self.pending_page_active:
            raise RuntimeError("이전 유튜브 채팅 페이지 전달이 완료되지 않았습니다.")
        if not isinstance(chats, list) or any(
                not isinstance(chat, PlatformChat) for chat in chats):
            raise ValueError("유튜브 채팅 페이지 항목 형식 오류")
        if next_token is not None and (
                not isinstance(next_token, str) or len(next_token) > 2048):
            raise ValueError("유튜브 채팅 페이지 토큰 오류")
        if type(poll_millis) is not int or not 0 < poll_millis <= 120000:
            raise ValueError("유튜브 채팅 폴링 간격 형식 오류")
        if type(ended) is not bool:
            raise ValueError("유튜브 방송 종료 상태 형식 오류")
        self.pending_page_chats.extend(chats)
        self.pending_page_next_token = next_token
        self.pending_page_poll_millis = poll_millis
        self.pending_page_ended = ended
        self.pending_page_active = True

    def clear_completed_page(self) -> None:
        """완전히 수용·커서 확정한 페이지의 메모리만 해제한다."""
        if not self.pending_page_active or self.pending_page_chats:
            raise RuntimeError("유튜브 미수용 채팅이 남아 페이지를 해제할 수 없습니다.")
        self.pending_page_next_token = None
        self.pending_page_poll_millis = 0
        self.pending_page_ended = False
        self.pending_page_active = False

    def bind_chat(self, live_chat_id: str) -> str:
        if not isinstance(live_chat_id, str) or not live_chat_id.strip():
            raise ValueError("유튜브 실제 채팅방 ID가 올바르지 않습니다.")
        if self.live_chat_id is not None and self.live_chat_id != live_chat_id:
            raise RuntimeError(
                "재연결된 YouTube 채팅방이 바뀌었습니다. "
                "이전 메시지 위치를 다른 방송에 적용하지 않습니다."
            )
        self.live_chat_id = live_chat_id
        return self.next_page_token

    def delivered_event(self, message_id: str | None) -> None:
        # 두 사용자가 같은 본문을 입력해도 개별 이벤트는 각각 전달된다.
        self.delivered += 1
        if message_id is None or message_id in self.seen_message_ids:
            return
        self.seen_message_ids.add(message_id)
        self.recent_message_ids.append(message_id)
        if len(self.recent_message_ids) > 50_000:
            self.seen_message_ids.discard(self.recent_message_ids.popleft())

    def completed_page(self, next_page_token: str | None) -> None:
        # 네트워크 단절 또는 UI 백프레셔 중 종료된 미완성 페이지의
        # 위치를 앞당기지 않는다. 같은 페이지 재조회 후 이벤트 ID로 재전송 방지.
        if next_page_token is not None and (
                not isinstance(next_page_token, str) or len(next_page_token) > 2048):
            raise ValueError("유튜브 채팅 페이지 토큰 오류")
        self.next_page_token = next_page_token or ""
        self.completed_pages += 1


class YouTubeReadOnlySession(ReadOnlySession):
    def __init__(self, channel: str, emit, api_key: str = "",
                 *, oauth_access_token: str = "",
                 resume_state: YouTubeChatResumeState | None = None):
        super().__init__(channel, emit)
        if type(oauth_access_token) is not str:
            raise ValueError("유튜브 OAuth 읽기 인증 형식이 잘못되었습니다.")
        if oauth_access_token:
            if (not 30 <= len(oauth_access_token) <= 4096
                    or oauth_access_token != oauth_access_token.strip()
                    or any(ord(ch) <= 32 or ord(ch) >= 127
                           for ch in oauth_access_token)):
                raise ValueError("유튜브 OAuth 읽기 인증 형식이 잘못되었습니다.")
        elif not isinstance(api_key, str) or not 20 <= len(api_key) <= 240:
            raise ValueError("유튜브 API 키 또는 승인받은 OAuth 읽기 인증이 필요합니다.")
        self._owner_active = self.channel == "내 활성 방송"
        if self._owner_active and not oauth_access_token:
            raise ValueError("내 활성 방송 조회에는 승인받은 OAuth 읽기 인증이 필요합니다.")
        self._video_id = (None if self._owner_active
                          else _youtube_video_id_or_none(self.channel))
        self._key = "" if oauth_access_token else api_key
        # No refresh token, OAuth login, token save, automatic consent or write access.
        self._oauth_access_token = oauth_access_token
        if resume_state is not None and not isinstance(
                resume_state, YouTubeChatResumeState):
            raise TypeError("유튜브 이어받기 상태 형식 오류")
        self._resume_state = (resume_state if resume_state is not None
                              else YouTubeChatResumeState())
        self._terminal_chat_end = False

    def run(self, *, max_seconds=None):
        if self._stop.is_set():
            return
        # Validate a bounded read before any YouTube API request or quota use.
        if max_seconds is not None:
            if (type(max_seconds) not in (int, float) or max_seconds < 0
                    or (type(max_seconds) is float and not math.isfinite(max_seconds))):
                raise ValueError("유튜브 검사 제한 시간이 올바르지 않습니다.")
            if max_seconds == 0:
                self.emit("stopped", self.channel)
                return
        start = time.monotonic()

        def remaining_timeout() -> float:
            # The user-supplied short probe must not unexpectedly spend the
            # full 10-second default HTTP timeout for each API page.
            if max_seconds is None:
                return 10.0
            return max(0.1, min(10.0, max_seconds - (time.monotonic() - start)))

        def guarded_get(url: str):
            # Keep the SAME URL/cursor on a transient connection failure.
            # A successful page is delivered only once; no API key is logged.
            # HTTP status errors (including quota, access and authentication)
            # must NEVER trigger automatic quota-consuming retries.
            for attempt in range(3):
                if self._stop.is_set():
                    return None
                try:
                    if self._oauth_access_token:
                        return _json_get(
                            url, timeout=remaining_timeout(),
                            headers={"Authorization": "Bearer " + self._oauth_access_token})
                    return _json_get(url, timeout=remaining_timeout())
                except HTTPError:
                    raise
                except OSError:
                    if (attempt >= 2 or (max_seconds is not None
                            and time.monotonic() - start >= max_seconds)):
                        raise
                    backoff = min(0.5 * (2 ** attempt),
                                  remaining_timeout() if max_seconds is not None else 2)
                    if self._stop.wait(backoff):
                        return None
            raise RuntimeError("유튜브 연결 복구 시도 제한 초과")

        live_chat_id = self.channel
        if self._owner_active:
            # Official read-only owner scope. List ONLY the authenticated
            # owner's broadcasts. Avoid ambiguous first-result selection.
            params = {"part": "snippet,status", "mine": "true",
                      "broadcastType": "all", "maxResults": "50"}
            try:
                result = guarded_get(
                    "https://www.googleapis.com/youtube/v3/liveBroadcasts?"
                    + urlencode(params))
            except Exception:
                raise RuntimeError("유튜브 소유 방송 조회 또는 OAuth 권한 오류") from None
            if self._stop.is_set():
                return
            rows = result.get("items") if isinstance(result, dict) else None
            if not isinstance(rows, list):
                raise RuntimeError("유튜브 소유 방송 목록 응답 형식 오류")
            if result.get("nextPageToken"):
                raise RuntimeError("활성 방송 목록이 여러 페이지입니다. 채팅 ID를 직접 입력하세요.")
            active = [item.get("snippet", {}).get("liveChatId")
                      for item in rows if isinstance(item, dict)
                      and isinstance(item.get("snippet"), dict)
                      and isinstance(item.get("status"), dict)
                      and item["status"].get("lifeCycleStatus") == "live"
                      and isinstance(item["snippet"].get("liveChatId"), str)
                      and item["snippet"]["liveChatId"].strip()]
            if len(active) != 1:
                raise RuntimeError("소유한 활성 방송 채팅이 없거나 여러 개입니다. 정확한 채팅 ID를 입력하세요.")
            live_chat_id = active[0]
        if self._video_id is not None:
            # Public videos.list only. Do not access an account, perform OAuth,
            # or attempt to infer a chat ID from a video ID string.
            lookup = {"part":"liveStreamingDetails",
                      "id":self._video_id}
            if not self._oauth_access_token:
                lookup["key"] = self._key
            try:
                details = guarded_get("https://www.googleapis.com/youtube/v3/"
                                      "videos?" + urlencode(lookup))
            except Exception:
                # An HTTP exception may contain the API key-bearing URL.
                raise RuntimeError("유튜브 영상의 실시간 채팅 조회 또는 권한 오류") from None
            if self._stop.is_set():
                return
            items = details.get("items")
            if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
                raise RuntimeError("유튜브 생방송 영상 정보를 확인하지 못했습니다.")
            live = items[0].get("liveStreamingDetails") or {}
            live_chat_id = live.get("activeLiveChatId") if isinstance(live, dict) else None
            if not isinstance(live_chat_id, str) or not live_chat_id.strip():
                raise RuntimeError("현재 생방송 중이거나 활성화된 유튜브 채팅방이 없습니다.")
        # 이전 연결에서 완전히 전달한 페이지 다음 위치부터 수신한다.
        # 페이지 중간 연결 실패는 같은 페이지를 다시 읽으며, 이미 UI에
        # 넘긴 이벤트 ID만 재전송하지 않는다. 본문 중복은 보존한다.
        resume = self._resume_state
        cursor = resume.bind_chat(live_chat_id)
        first = True
        seen_message_ids = resume.seen_message_ids
        # Some broken API/proxy responses can alternate A->B->A forever.
        # Track a bounded set of page tokens; fail before dispatching a
        # replayed page's events or consuming quota in an infinite cycle.
        recent_page_tokens = deque()
        seen_page_tokens = set()
        max_seen_pages = 10_000
        while not self._stop.is_set():
            if max_seconds is not None and time.monotonic() - start >= max_seconds:
                break
            if resume.pending_page_active:
                # 이전 API 응답을 이미 수신했다면 재연결 직후 불필요한
                # 동일 페이지 HTTP 요청 없이 미수용 채팅부터 FIFO 전달.
                # 서버 ID가 없는 서로 다른 채팅도 재요청 중복 없이 유지.
                while resume.pending_page_chats and not self._stop.is_set():
                    item = resume.pending_page_chats[0]
                    if item.event_id is not None and item.event_id in seen_message_ids:
                        self.emit("server_replay", None)
                        resume.pending_page_chats.popleft()
                        continue
                    if self.emit("chat", item) is False:
                        # 미수용 선두와 같은 페이지의 뒤쪽을 남긴다.
                        # 수용 성공한 앞쪽은 이미 pop했으므로 ID가 없어도
                        # 재연결 때 다시 AI 큐로 중복 제출하지 않는다.
                        raise RuntimeError(
                            "유튜브 채팅 수신 큐 전달이 완료되지 않아 페이지를 보존합니다."
                        )
                    resume.delivered_event(item.event_id)
                    resume.pending_page_chats.popleft()
                if self._stop.is_set():
                    break
                if first:
                    self.emit("ready", self.channel)
                first = False
                resume.completed_page(resume.pending_page_next_token)
                cursor = resume.next_page_token
                ended = resume.pending_page_ended
                millis = resume.pending_page_poll_millis
                resume.clear_completed_page()
                if ended:
                    self._terminal_chat_end = True
                    break
                self._stop.wait(millis / 1000)
                continue
            params = {"part":"id,snippet,authorDetails",
                      "liveChatId":live_chat_id}
            if not self._oauth_access_token:
                params["key"] = self._key
            if cursor:
                params["pageToken"] = cursor
            try:
                payload = guarded_get("https://www.googleapis.com/youtube/v3/"
                                      "liveChat/messages?" + urlencode(params))
            except Exception:
                # Never leak operator-entered API credentials into GUI or logs.
                raise RuntimeError("유튜브 채팅 API 연결 또는 권한 오류") from None
            if self._stop.is_set():
                break
            # Do not expose late responses after a bounded operator probe.
            if (max_seconds is not None
                    and time.monotonic() - start >= max_seconds):
                break
            if not isinstance(payload, dict):
                raise ValueError("유튜브 채팅 API 응답 형식 오류")
            # Parse and validate the entire envelope before sending any event.
            # In particular, a no-message response can keep the same cursor
            # while the broadcaster is idle; honor pollingIntervalMillis.
            raw_items = payload.get("items", [])
            if not isinstance(raw_items, list):
                raise ValueError("유튜브 채팅 페이지 메시지 목록 형식 오류")
            # YouTube는 WebSocket이 아닌 폴링 응답을 계측한다.
            # 채팅 없음 != 통신 없음. 응답 본문/키/토큰은 저장 금지.
            self.emit("transport_activity", None)
            next_cursor = payload.get("nextPageToken")
            ended = isinstance(payload.get("offlineAt"), str) and bool(payload["offlineAt"])
            if isinstance(next_cursor, str) and len(next_cursor) > 2048:
                raise ValueError("유튜브 채팅 페이지 토큰 길이가 올바르지 않습니다.")
            if (not isinstance(next_cursor, str) or not next_cursor) and not ended:
                # An empty cursor would silently restart at page one and
                # repeatedly respond to the same historical chat messages.
                raise RuntimeError("유튜브 채팅 페이지 응답 토큰이 없습니다.")
            idle_same_cursor = bool(not ended and cursor
                                    and next_cursor == cursor and not raw_items)
            if not ended and next_cursor in seen_page_tokens and not idle_same_cursor:
                # A nonempty replay or multi-page cycle is not an idle poll:
                # fail *before* forwarding any duplicate AI work.
                raise RuntimeError("유튜브 채팅 페이지 토큰이 반복되어 수신을 중단했습니다.")
            if not ended and next_cursor not in seen_page_tokens:
                seen_page_tokens.add(next_cursor)
                recent_page_tokens.append(next_cursor)
                if len(recent_page_tokens) > max_seen_pages:
                    seen_page_tokens.discard(recent_page_tokens.popleft())
            # Reject a bad polling interval before forwarding chat. If it is
            # rejected after delivery, reconnecting could replay that page.
            millis = payload.get("pollingIntervalMillis", 1000)
            if type(millis) is not int or not 0 < millis <= 120000:
                raise ValueError("유튜브 채팅 폴링 간격 형식 오류")
            # 페이지 전체를 파싱해 먼저 보관한다. 한 페이지 중간에서
            # AI FIFO가 거절하거나 예외가 나더라도 뒤쪽 채팅이 사라지지
            # 않고, 재연결된 새 리더가 동일 메모리 보류 큐를 이어받는다.
            parsed_chats = parse_youtube_page(payload, self.channel)
            resume.stage_page(parsed_chats, next_cursor, millis, ended)
            # 다음 루프가 보류 사건부터 처리하며 모든 채팅 수용 이후
            # 커서를 확정한다. 추가 HTTP 요청은 하지 않는다.
        self.emit("stopped", self.channel)
