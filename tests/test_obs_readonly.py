"""OBS v5 read-only WebSocket client tests. No real OBS or internet required."""
import base64
import hashlib
import json
import re
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from ai_broadcaster.obs_readonly import (
    ObsError, ObsSnapshot, SceneItem, _authentication, _request,
    get_obs_snapshot, avatar_capture_diagnostic,
)


def server_frame(obj):
    payload=json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode()
    head=b"\x81"
    if len(payload)<126:
        head+=bytes([len(payload)])
    elif len(payload)<65536:
        head+=b"\x7e"+struct.pack("!H",len(payload))
    else:
        head+=b"\x7f"+struct.pack("!Q",len(payload))
    return head+payload


class FakeObsSocket:
    def __init__(self, *, password=None, scenes=None, live=False,
                 malformed_status=False, invalid_upgrade=False,
                 wrong_auth=False, items_by_scene=None):
        self.required_password=password
        self.scenes=scenes if scenes is not None else ["대기 화면","게임 화면"]
        self.live=live
        self.items_by_scene=items_by_scene or {}
        self.malformed_status=malformed_status
        self.invalid_upgrade=invalid_upgrade
        self.wrong_auth=wrong_auth
        self.pending=bytearray()
        self.calls=[]
        self.timeout=None
        self.connected=True

    def settimeout(self,value):
        self.timeout=value

    def __enter__(self): return self
    def __exit__(self,*args):
        self.connected=False

    def sendall(self,data):
        if data.startswith(b"GET / HTTP/1.1\r\n"):
            request=data.decode("ascii")
            key=re.search(r"Sec-WebSocket-Key: (.+?)\r\n",request).group(1)
            accept=base64.b64encode(hashlib.sha1(
                (key+"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()
            ).digest()).decode()
            if self.invalid_upgrade:
                accept="wrong"
            response=("HTTP/1.1 101 Switching Protocols\r\n"
                      "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                      f"Sec-WebSocket-Accept: {accept}\r\n\r\n")
            self.pending+=response.encode()
            hello={"op":0,"d":{"rpcVersion":1,"obsWebSocketVersion":"5.4.0"}}
            if self.required_password is not None:
                hello["d"]["authentication"]={"challenge":"challenge","salt":"salt"}
            self.pending+=server_frame(hello)
            return
        # Decode the mandatory masked client -> server frame.
        self._consume_masked(data)

    def _consume_masked(self,data):
        self.calls.append(("raw",data))
        if len(data)<6 or (data[1]&0x80)==0:
            raise AssertionError("Unmasked client WebSocket frame")
        length=data[1]&0x7f
        offset=2
        if length==126:
            length=struct.unpack("!H",data[offset:offset+2])[0]
            offset+=2
        if length==127:
            length=struct.unpack("!Q",data[offset:offset+8])[0]
            offset+=8
        mask=data[offset:offset+4]
        body=bytes(b ^ mask[i%4] for i,b in enumerate(data[offset+4:offset+4+length]))
        msg=json.loads(body)
        self.calls.append(("message",msg))
        if msg["op"]==1:
            proof=msg["d"].get("authentication")
            expected=_authentication(self.required_password or "","challenge","salt")
            success=self.required_password is None or (proof==expected and not self.wrong_auth)
            self.pending+=server_frame({"op":2 if success else 5,"d":{}})
            return
        if msg["op"]!=6:
            raise AssertionError("Only Identify and read requests allowed")
        d=msg["d"]
        request=d["requestType"]
        self.calls.append(("request",request))
        if request=="GetVersion":
            payload={"obsVersion":"31.0.0","obsWebSocketVersion":"5.4.0"}
        elif request=="GetSceneList":
            payload={"scenes":[{"sceneName":s} for s in self.scenes]}
        elif request=="GetStreamStatus":
            payload={"outputActive": "yes" if self.malformed_status else self.live}
        elif request=="GetSceneItemList":
            selected=d.get("requestData",{}).get("sceneName")
            if selected not in self.scenes:
                raise AssertionError("Non-existent OBS scene requested")
            payload={"sceneItems":self.items_by_scene.get(selected,[])}
        else:
            raise AssertionError("Non read-only OBS request received")
        self.pending+=server_frame({
            "op":7,"d":{"requestType":request,"requestId":d["requestId"],
                        "requestStatus":{"result":True,"code":100},
                        "responseData":payload}
        })

    def recv(self,length):
        if not self.pending:
            raise AssertionError("Unexpected OBS recv without pending data")
        take=min(length,len(self.pending))
        buf=bytes(self.pending[:take])
        del self.pending[:take]
        return buf


class TestObsClient(unittest.TestCase):
    def connect(self, server, **kwargs):
        with patch("ai_broadcaster.obs_readonly.socket.create_connection",return_value=server) as mocked:
            result=get_obs_snapshot(**kwargs)
            self.assertEqual(mocked.call_args.args[0][0],"127.0.0.1")
            return result

    def test_scene_list_and_status(self):
        fake=FakeObsSocket()
        info=self.connect(fake)
        self.assertEqual(info,ObsSnapshot("31.0.0","5.4.0",("대기 화면","게임 화면"),False))
        self.assertEqual([p for k,p in fake.calls if k=="request"],
                         ["GetVersion","GetSceneList","GetStreamStatus"])
        self.assertFalse(fake.connected)

    def test_stream_already_live_is_read_only(self):
        fake=FakeObsSocket(live=True)
        info=self.connect(fake)
        self.assertTrue(info.streaming)
        self.assertNotIn("StartStream",str(fake.calls))
        self.assertNotIn("StopStream",str(fake.calls))
        self.assertNotIn("SetCurrentProgramScene",str(fake.calls))

    def test_authenticated_obs(self):
        fake=FakeObsSocket(password="비밀암호")
        info=self.connect(fake,password="비밀암호")
        self.assertEqual(info.obs_version,"31.0.0")

    def test_missing_password_rejected(self):
        with patch("ai_broadcaster.obs_readonly.socket.create_connection",
                   return_value=FakeObsSocket(password="secret")):
            with self.assertRaisesRegex(ObsError,"비밀번호"):
                get_obs_snapshot()

    def test_wrong_password_rejected(self):
        with patch("ai_broadcaster.obs_readonly.socket.create_connection",
                   return_value=FakeObsSocket(password="secret")):
            with self.assertRaises(ObsError):
                get_obs_snapshot(password="wrong")

    def test_handshake_accept_must_match(self):
        with patch("ai_broadcaster.obs_readonly.socket.create_connection",
                   return_value=FakeObsSocket(invalid_upgrade=True)):
            with self.assertRaises(ObsError):
                get_obs_snapshot()

    def test_malformed_stream_status_rejected(self):
        with patch("ai_broadcaster.obs_readonly.socket.create_connection",
                   return_value=FakeObsSocket(malformed_status=True)):
            with self.assertRaises(ObsError):
                get_obs_snapshot()

    def test_invalid_port_rejected_before_connect(self):
        with patch("ai_broadcaster.obs_readonly.socket.create_connection") as mocked:
            for port in (-1,0,65536,True,1.3):
                with self.subTest(port=port),self.assertRaises(ValueError):
                    get_obs_snapshot(port=port)
            mocked.assert_not_called()

    def test_timeout_bounds(self):
        with patch("ai_broadcaster.obs_readonly.socket.create_connection") as mocked:
            for timeout in (0,22,True):
                with self.subTest(timeout=timeout),self.assertRaises(ValueError):
                    get_obs_snapshot(timeout=timeout)
            mocked.assert_not_called()

    def test_long_password_rejected(self):
        with patch("ai_broadcaster.obs_readonly.socket.create_connection") as mocked:
            with self.assertRaises(ValueError):
                get_obs_snapshot(password="a"*513)
            mocked.assert_not_called()

    def test_request_allowlist_prevents_broadcast(self):
        fake=FakeObsSocket()
        for method in ("StartStream","StopStream","SetCurrentProgramScene","CreateScene","SetStreamServiceSettings"):
            with self.subTest(method=method),self.assertRaises(ObsError):
                _request(fake,method,1)
        self.assertEqual(fake.calls,[])

    def test_http_password_not_embedded(self):
        fake=FakeObsSocket(password="super secret")
        with patch("ai_broadcaster.obs_readonly.socket.create_connection",return_value=fake):
            get_obs_snapshot(password="super secret")
        sent=b"".join(data for k,data in fake.calls if k=="raw")
        self.assertNotIn(b"super secret",sent)

    def test_one_character_recv_fragmentation(self):
        fake=FakeObsSocket(scenes=["나의 장면","제2 화면","OBS 장면3"])
        with patch("ai_broadcaster.obs_readonly.socket.create_connection",return_value=fake):
            result=get_obs_snapshot()
        self.assertEqual(result.scenes,("나의 장면","제2 화면","OBS 장면3"))

    def test_empty_scene_list(self):
        self.assertEqual(self.connect(FakeObsSocket(scenes=[])).scenes,())

    def test_connection_failure(self):
        with patch("ai_broadcaster.obs_readonly.socket.create_connection",
                   side_effect=ConnectionRefusedError("offline")):
            with self.assertRaisesRegex(ObsError,"연결할 수 없습니다"):
                get_obs_snapshot()

    def test_obs_window_capture_button_exists(self):
        app=(ROOT/"src/ai_broadcaster/desktop.py").read_text(encoding="utf-8")
        self.assertIn("tk.Toplevel(self)",app)
        self.assertIn("아바타 별도 창 열기",app)
        self.assertIn("self._speech_activity",app)
        self.assertIn("ObsStatusTab(obs)",app)

    def test_never_store_obs_password_in_settings(self):
        app=(ROOT/"src/ai_broadcaster/desktop_obs_tab.py").read_text(encoding="utf-8")
        self.assertIn("show=\"*\"",app)
        self.assertNotIn("save_settings(",app)
        self.assertNotIn("StartStream",app)


class TestObsSceneInspection(unittest.TestCase):
    def connect(self, server, **kwargs):
        with patch("ai_broadcaster.obs_readonly.socket.create_connection",return_value=server) as mocked:
            value=get_obs_snapshot(**kwargs)
            self.assertEqual(mocked.call_args.args[0],("127.0.0.1",kwargs.get("port",4455)))
            return value

    @staticmethod
    def sample(enabled=True, name="AISTING 창", kind="window_capture", item_id=3):
        return {"sourceName":name,"inputKind":kind,
                "sceneItemEnabled":enabled,"sceneItemId":item_id}

    def test_scene_items_requested_only_on_explicit_inspection(self):
        fake=FakeObsSocket(items_by_scene={"게임 화면":[self.sample()]})
        self.connect(fake)
        self.assertEqual([x for k,x in fake.calls if k=="request"],
                         ["GetVersion","GetSceneList","GetStreamStatus"])

    def test_selected_scene_lists_sources(self):
        fake=FakeObsSocket(items_by_scene={"게임 화면":[
            self.sample(),self.sample(False,"카메라","dshow_input",4)
        ]})
        result=self.connect(fake,scene_name="게임 화면")
        self.assertEqual(result.inspected_scene,"게임 화면")
        self.assertEqual(result.scene_items,(
            SceneItem("AISTING 창","window_capture",True,3),
            SceneItem("카메라","dshow_input",False,4),
        ))
        self.assertEqual([x for k,x in fake.calls if k=="request"],
            ["GetVersion","GetSceneList","GetStreamStatus","GetSceneItemList"])
        frame=next(x for k,x in fake.calls
                   if k=="message" and x.get("d",{}).get("requestType")=="GetSceneItemList")
        self.assertEqual(frame["d"]["requestData"],{"sceneName":"게임 화면"})

    def test_missing_scene_rejected_without_source_request(self):
        fake=FakeObsSocket()
        with patch("ai_broadcaster.obs_readonly.socket.create_connection",return_value=fake):
            with self.assertRaisesRegex(ObsError,"장면 목록"):
                get_obs_snapshot(scene_name="없는 장면")
        self.assertNotIn("GetSceneItemList",[v for k,v in fake.calls if k=="request"])

    def test_bad_scene_name_fails_before_connect(self):
        with patch("ai_broadcaster.obs_readonly.socket.create_connection") as mocked:
            for value in ("","  ", "x"*257,True,8):
                with self.subTest(value=str(value)[:20]),self.assertRaises(ValueError):
                    get_obs_snapshot(scene_name=value)
            mocked.assert_not_called()

    def test_malformed_source_list_rejected(self):
        malformed=[
            {"sourceName":"A","sceneItemEnabled":True,"sceneItemId":"1","inputKind":"window_capture"},
            {"sourceName":"A","sceneItemEnabled":"yes","sceneItemId":1,"inputKind":"window_capture"},
            {"sourceName":"A","sceneItemEnabled":True,"sceneItemId":1,"inputKind":{}},
            {"sourceName":"","sceneItemEnabled":True,"sceneItemId":1,"inputKind":"window_capture"},
            "not a mapping",
        ]
        for item in malformed:
            with self.subTest(item=item):
                fake=FakeObsSocket(items_by_scene={"게임 화면":[item]})
                with patch("ai_broadcaster.obs_readonly.socket.create_connection",return_value=fake):
                    with self.assertRaises(ObsError):get_obs_snapshot(scene_name="게임 화면")

    def test_source_count_bounded(self):
        fake=FakeObsSocket(items_by_scene={"게임 화면":[self.sample(item_id=i) for i in range(501)]})
        with patch("ai_broadcaster.obs_readonly.socket.create_connection",return_value=fake):
            with self.assertRaises(ObsError):get_obs_snapshot(scene_name="게임 화면")

    def test_inspected_empty_scene_returns_no_candidate(self):
        snap=self.connect(FakeObsSocket(),scene_name="게임 화면")
        self.assertIn("찾지 못했습니다",avatar_capture_diagnostic(snap))

    def test_uninspected_scene_never_claims_capture_ready(self):
        snap=self.connect(FakeObsSocket())
        self.assertIn("선택",avatar_capture_diagnostic(snap))

    def test_aisting_named_capture_is_only_candidate(self):
        fake=FakeObsSocket(items_by_scene={"게임 화면":[self.sample(name="AISTING window")]})
        diag=avatar_capture_diagnostic(self.connect(fake,scene_name="게임 화면"))
        self.assertIn("후보",diag)
        self.assertIn("직접 확인",diag)
        self.assertNotIn("캡처 성공",diag)

    def test_non_aisting_capture_is_unverified(self):
        fake=FakeObsSocket(items_by_scene={"게임 화면":[self.sample(name="Browser")]})
        diag=avatar_capture_diagnostic(self.connect(fake,scene_name="게임 화면"))
        self.assertIn("미확인",diag)

    def test_disabled_aisting_window_not_a_candidate(self):
        fake=FakeObsSocket(items_by_scene={"게임 화면":[self.sample(enabled=False)]})
        diag=avatar_capture_diagnostic(self.connect(fake,scene_name="게임 화면"))
        self.assertIn("찾지 못했습니다",diag)

    def test_scene_capture_read_only_allowlist(self):
        fake=FakeObsSocket()
        for name in ("CreateInput","SetSceneItemEnabled","StartStream","StopStream",
                     "SetCurrentProgramScene","CreateSceneItem"):
            with self.subTest(name=name),self.assertRaises(ObsError):
                _request(fake,name,4,scene_name="게임 화면")
        self.assertEqual(fake.calls,[])
        for name in ("GetVersion","GetStreamStatus"):
            with self.assertRaises(ObsError):
                _request(fake,name,2,scene_name="게임 화면")
        self.assertEqual(fake.calls,[])

    def test_gui_selection_and_check_explicit(self):
        ui=(ROOT/"src/ai_broadcaster/desktop_obs_tab.py").read_text(encoding="utf-8")
        self.assertIn("command=self._inspect_scene",ui)
        self.assertIn('scene_name=scene_name',ui)
        self.assertIn("avatar_capture_diagnostic(item)",ui)
        self.assertNotIn('command=self._set_scene',ui)
