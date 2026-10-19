"""Operator-selected, read-only CHZZK / SOOP / YouTube live chat transports.

No platform chat posting, OAuth login, account scraping, credential persistence,
startup connections or stream start. Each adapter is an explicit, stoppable reader.
Unofficial CHZZK/SOOP protocols may change; connection errors are surfaced.
"""
from __future__ import annotations

import json
import math
import re
import ssl
import threading
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class PlatformChat:
    channel: str
    sender: str
    text: str
    platform: str


def _json_get(url: str, *, timeout: float = 10) -> dict:
    request = Request(url, headers={"User-Agent": "AISTING/1.0 (read-only chat)",
                                    "Accept": "application/json"})
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
        if not isinstance(item, dict) or not isinstance(item.get("msg"), str):
            continue
        profile = item.get("profile") or {}
        if isinstance(profile, str):
            try:
                profile = json.loads(profile)
            except ValueError:
                profile = {}
        nick = profile.get("nickname") if isinstance(profile, dict) else None
        nick = nick or item.get("uid") or "anonymous"
        if item["msg"]:
            # Preserve nonempty whitespace-only chat exactly.
            out.append(PlatformChat(channel, str(nick), item["msg"], "chzzk"))
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
        if len(frame) < 12 or frame[:4] != "0005":
            continue
        fields = frame[12:].split("\x0c")
        if len(fields) < 3:
            continue
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
        if not isinstance(item, dict):
            continue
        snippet = item.get("snippet") or {}
        author = item.get("authorDetails") or {}
        if not isinstance(snippet, dict) or not isinstance(author, dict):
            continue
        # Ignore non-chat control events, do not invent a message body.
        if snippet.get("type") not in ("textMessageEvent", "superChatEvent",
                                       "superStickerEvent", "memberMilestoneChatEvent"):
            continue
        text = snippet.get("displayMessage")
        if not isinstance(text, str) or not text:
            continue
        result.append(PlatformChat(channel,
                    str(author.get("displayName") or "YouTube 시청자"), text, "youtube"))
    return result


class ReadOnlySession:
    def __init__(self, channel: str, emit):
        if not isinstance(channel, str) or not channel.strip() or len(channel) > 130:
            raise ValueError("채널 식별자가 올바르지 않습니다.")
        self.channel, self.emit = channel.strip(), emit
        self._stop = threading.Event()
        self._socket = None

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
        while not self._stop.is_set():
            if deadline and time.monotonic() >= deadline:
                return
            if on_tick is not None:
                on_tick()
            try:
                sock.settimeout(1)
                data = sock.recv()
            except websocket.WebSocketTimeoutException:
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
            for item in parser(data, self.channel):
                if self._stop.is_set():
                    return
                self.emit("chat", item)


class ChzzkReadOnlySession(ReadOnlySession):
    def __init__(self, channel: str, emit):
        super().__init__(channel, emit)
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
            startup_chats = []
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
                startup_chats.extend(parse_chzzk_frame(raw, self.channel))
                if data.get("cmd") == 10100 and isinstance(data.get("bdy"), dict) and data["bdy"].get("sid"):
                    accepted = True
                    break
                if data.get("cmd") == 0:
                    sock.send('{"ver":"2","cmd":10000}')
            if self._stop.is_set():
                return
            if not accepted:
                raise RuntimeError("치지직 실제 채팅 연결 승인 응답이 없습니다.")
            self.emit("ready", self.channel)
            for item in startup_chats:
                if self._stop.is_set():
                    return
                self.emit("chat", item)
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
                            next_ping = time.monotonic() + 60
                            self.emit("ready", self.channel)
                        elif code == "0007":
                            raise RuntimeError("SOOP 채팅 서버에서 연결 종료 응답을 받았습니다.")
                return parse_soop_frame(raw, channel)
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


class YouTubeReadOnlySession(ReadOnlySession):
    def __init__(self, channel: str, emit, api_key: str):
        super().__init__(channel, emit)
        if not isinstance(api_key, str) or not 20 <= len(api_key) <= 240:
            raise ValueError("유튜브 Data API 키를 프로그램에서 입력하세요.")
        self._video_id = _youtube_video_id_or_none(self.channel)
        self._key = api_key

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
        live_chat_id = self.channel
        if self._video_id is not None:
            # Public videos.list only. Do not access an account, perform OAuth,
            # or attempt to infer a chat ID from a video ID string.
            lookup = {"part":"liveStreamingDetails",
                      "id":self._video_id, "key":self._key}
            try:
                details = _json_get("https://www.googleapis.com/youtube/v3/"
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
        cursor = ""
        first = True
        while not self._stop.is_set():
            if max_seconds is not None and time.monotonic() - start >= max_seconds:
                break
            params = {"part":"id,snippet,authorDetails",
                      "liveChatId":live_chat_id, "key":self._key}
            if cursor:
                params["pageToken"] = cursor
            try:
                payload = _json_get("https://www.googleapis.com/youtube/v3/"
                                    "liveChat/messages?" + urlencode(params))
            except Exception:
                # Never leak operator-entered API credentials into GUI or logs.
                raise RuntimeError("유튜브 채팅 API 연결 또는 권한 오류") from None
            if self._stop.is_set():
                break
            next_cursor = payload.get("nextPageToken")
            ended = isinstance(payload.get("offlineAt"), str) and bool(payload["offlineAt"])
            if (not isinstance(next_cursor, str) or not next_cursor) and not ended:
                # An empty cursor would silently restart at page one and
                # repeatedly respond to the same historical chat messages.
                raise RuntimeError("유튜브 채팅 페이지 응답 토큰이 없습니다.")
            # Reject a bad polling interval before forwarding chat. If it is
            # rejected after delivery, reconnecting could replay that page.
            millis = payload.get("pollingIntervalMillis", 1000)
            if type(millis) is not int or not 0 < millis <= 120000:
                raise ValueError("유튜브 채팅 폴링 간격 형식 오류")
            for item in parse_youtube_page(payload, self.channel):
                # An initial page can contain real history; do not filter by
                # content or sender, and preserve repeated text.
                if self._stop.is_set():
                    break
                self.emit("chat", item)
            if self._stop.is_set():
                break
            if first:
                self.emit("ready", self.channel)
            first = False
            cursor = next_cursor
            if ended:
                # YouTube has explicitly ended this live chat. A final page
                # may omit nextPageToken; still deliver its actual messages.
                break
            # Respect Google's server-designated strictly positive interval.
            self._stop.wait(millis / 1000)
        self.emit("stopped", self.channel)
