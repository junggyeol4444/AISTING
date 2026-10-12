"""무료 로컬 운영 및 선택 가능 설정 테스트."""
import copy
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))

from ai_broadcaster.operator_settings import (
    DEFAULT_SETTINGS, SettingsError, default_settings,
    load_settings, save_settings, validate_settings,
)
from settings_server import SettingsHandler


class TestOperatorSettings(unittest.TestCase):
    def test_defaults_are_local_and_free(self):
        s=default_settings()
        self.assertEqual(s["operation"]["host"],"local_pc")
        self.assertEqual(s["operation"]["budget_mode"],"free_only")
        self.assertFalse(any(v for k,v in s["operation"].items() if k.startswith("allow_")))
        self.assertEqual(s["platforms"],[])
        self.assertEqual(s["content"],"undecided")

    def test_multiple_platforms(self):
        s=default_settings();s["platforms"]=["chzzk","youtube"]
        self.assertEqual(validate_settings(s)["platforms"],["chzzk","youtube"])

    def test_content_choice(self):
        for content in ("chat","game","both","undecided"):
            s=default_settings();s["content"]=content
            self.assertEqual(validate_settings(s)["content"],content)

    def test_optional_persona_customization(self):
        s=default_settings()
        s["persona"]["mode"]="custom"
        s["persona"]["name"]="새 캐릭터"
        self.assertEqual(validate_settings(s)["persona"]["name"],"새 캐릭터")

    def test_voice_avatar_choice(self):
        for voice in ("undecided","local_basic","own_recording","licensed_recording"):
            for avatar in ("undecided","2d","3d"):
                s=default_settings();s["voice"]=voice;s["avatar"]=avatar
                self.assertEqual(validate_settings(s)["avatar"],avatar)

    def test_paid_api_rejected(self):
        s=default_settings();s["operation"]["allow_paid_api"]=True
        with self.assertRaises(SettingsError):validate_settings(s)

    def test_non_local_host_rejected(self):
        s=default_settings();s["operation"]["host"]="cloud"
        with self.assertRaises(SettingsError):validate_settings(s)

    def test_external_broadcast_rejected(self):
        s=default_settings();s["operation"]["allow_external_broadcast"]=True
        with self.assertRaises(SettingsError):validate_settings(s)

    def test_unknown_fields_rejected(self):
        s=default_settings();s["api_key"]="SECRET"
        with self.assertRaises(SettingsError):validate_settings(s)

    def test_persistence_and_default_immutable(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"data"/"settings.json"
            self.assertEqual(load_settings(p),DEFAULT_SETTINGS)
            s=default_settings();s["voice"]="local_basic"
            save_settings(s,p)
            self.assertEqual(load_settings(p)["voice"],"local_basic")
            self.assertEqual(default_settings()["voice"],"undecided")

    def test_invalid_does_not_overwrite_previous(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"settings.json";save_settings(default_settings(),p)
            bad=default_settings();bad["operation"]["allow_paid_assets"]=True
            with self.assertRaises(SettingsError):save_settings(bad,p)
            self.assertEqual(load_settings(p),default_settings())

    def test_duplicate_platforms_rejected(self):
        s=default_settings();s["platforms"]=["chzzk","chzzk"]
        with self.assertRaises(SettingsError):validate_settings(s)


class TestHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.path=Path(cls.temp.name)/"operator_settings.json"
        handler=type("TemporaryHandler",(SettingsHandler,),{"store_path":cls.path})
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.url="http://127.0.0.1:"+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5)
        cls.temp.cleanup()

    def test_page_loaded(self):
        with urlopen(self.url+"/",timeout=5) as r:
            self.assertIn("AI 방송인 설정",r.read().decode("utf-8"))

    def test_api_roundtrip(self):
        s=default_settings();s["content"]="both";s["platforms"]=["youtube"]
        payload=json.dumps(s,ensure_ascii=False).encode()
        req=Request(self.url+"/api/settings",data=payload,method="POST",
                    headers={"Content-Type":"application/json"})
        with urlopen(req,timeout=5) as r:
            self.assertEqual(r.status,200)
        with urlopen(self.url+"/api/settings",timeout=5) as r:
            self.assertEqual(json.load(r)["content"],"both")

    def test_origin_restriction(self):
        payload=json.dumps(default_settings()).encode()
        req=Request(self.url+"/api/settings",data=payload,method="POST",
                    headers={"Content-Type":"application/json","Origin":"https://attacker.example"})
        with self.assertRaises(HTTPError) as ctx:urlopen(req,timeout=5)
        self.assertEqual(ctx.exception.code,403)

    def test_http_paid_api_rejected(self):
        s=default_settings();s["operation"]["allow_paid_api"]=True
        req=Request(self.url+"/api/settings",data=json.dumps(s).encode(),method="POST",
                    headers={"Content-Type":"application/json"})
        with self.assertRaises(HTTPError) as ctx:urlopen(req,timeout=5)
        self.assertEqual(ctx.exception.code,400)
