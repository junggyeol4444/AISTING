"""v3 guard/regression checks, NOT evidence of real AI or actual OBS traffic."""
from __future__ import annotations

import os
from pathlib import Path
import stat
import sys
import tempfile
import types
import unittest
import wave
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'payload' / 'src'))
from ai_broadcaster.original_plan_studio import (
    official_frontend_http_status, StageOneUnavailable, save_official_persona,
)
from ai_broadcaster.original_plan_tts import apply_official_gpt_sovits
from ai_broadcaster.original_plan_obs import OfficialObsWebsocket, ObsConnectionError
from test_revision import IDENTITY, UPSTREAM_CONF
from test_real_tts_config import CONF


class ReadinessContracts(unittest.TestCase):
    def test_local_http_request_is_exactly_upstream_loopback_no_redirect(self):
        instances=[]
        class InspectionClient:
            def __init__(self, host, port, timeout):
                instances.append(self)
                self.host,self.port,self.timeout=host,port,timeout
            def request(self, verb, resource, headers):
                self.verb,self.resource,self.headers=verb,resource,headers
            def getresponse(self):
                return types.SimpleNamespace(status=200, read=lambda count:b'html')
            def close(self): pass
        with patch('ai_broadcaster.original_plan_studio.http.client.HTTPConnection', InspectionClient):
            status=official_frontend_http_status()
        self.assertEqual(status,200)
        self.assertEqual((instances[0].host,instances[0].port),('127.0.0.1',12393))
        self.assertEqual((instances[0].verb,instances[0].resource),('GET','/'))
        with patch('ai_broadcaster.original_plan_studio.http.client.HTTPConnection',side_effect=OSError('offline')):
            with self.assertRaises(StageOneUnavailable):official_frontend_http_status()

    def test_confidential_real_config_backups_are_private(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            (root/'run_server.py').write_text('pass\n',encoding='utf8')
            (root/'pyproject.toml').write_text('',encoding='utf8')
            conf=root/'conf.yaml'
            conf.write_text(UPSTREAM_CONF,encoding='utf8')
            conf_path,backup=save_official_persona(root,IDENTITY)
            self.assertEqual(conf_path,conf)
            self.assertEqual(backup.read_bytes(),UPSTREAM_CONF.encode('utf-8'))
            if os.name=='posix':
                self.assertEqual(stat.S_IMODE(backup.stat().st_mode),0o600)
                self.assertEqual(stat.S_IMODE(conf.stat().st_mode),0o644)
            conf.write_text(CONF,encoding='utf8')
            sound=root/'operator-consented.wav'
            with wave.open(str(sound), 'wb') as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(24000)
                audio.writeframes(b'\x00\x00' * 100)
            _,ttsbackup=apply_official_gpt_sovits(root,sound,'안녕하세요')
            self.assertIn(b'tts_model',ttsbackup.read_bytes())
            if os.name=='posix':
                self.assertEqual(stat.S_IMODE(ttsbackup.stat().st_mode),0o600)

    def test_obs_inventory_requires_connected_real_endpoint(self):
        self.assertRaises(ObsConnectionError, OfficialObsWebsocket('test-only').read_scene_inventory)


if __name__=='__main__':unittest.main()
