"""Windows 음성 테스트: 실제 스피커나 PowerShell 실행 없이 동작 및 보안 검증."""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ai_broadcaster.windows_tts import (
    SpeechError, Voice, WindowsSpeechPreview, _command, _LIST_SCRIPT, _SPEAK_SCRIPT,
)


def voices_result(rows):
    return subprocess.CompletedProcess(
        args=[], returncode=0,
        stdout=json.dumps(rows, ensure_ascii=False).encode("utf-8"), stderr=b"",
    )


class FakePlayer:
    def __init__(self, *, returncode=0, blocked=False):
        self.returncode = None
        self.target_code = returncode
        self.blocked = blocked
        self.payload = None
        self.ended = threading.Event()
        self.started = threading.Event()

    def communicate(self, input=None, timeout=None):
        self.payload = json.loads(input.decode("utf-8"))
        self.started.set()
        if self.blocked:
            self.ended.wait(timeout=3)
        self.returncode = self.target_code
        return b"", b""

    def poll(self):
        return self.returncode

    def terminate(self):
        self.target_code = -15
        self.ended.set()

    def kill(self):
        self.target_code = -9
        self.ended.set()


class TestWindowsTTS(unittest.TestCase):
    def setUp(self):
        self.voice=Voice("Microsoft Heami Desktop", "ko-KR")
        self.issued=[]
        self.process=FakePlayer()

        def fake_run(cmd, **kwargs):
            self.issued.append(("list", cmd, kwargs))
            return voices_result([{"name":self.voice.name,"culture":"ko-KR"}])

        def fake_popen(cmd, **kwargs):
            self.issued.append(("play", cmd, kwargs))
            return self.process

        self.service = WindowsSpeechPreview(
            platform="win32", runner=fake_run, process_factory=fake_popen,
        )

    def test_no_access_without_button(self):
        self.assertEqual(self.issued, [])

    def test_non_windows_rejected(self):
        svc=WindowsSpeechPreview(platform="linux",runner=lambda *x, **k: None)
        with self.assertRaises(SpeechError): svc.list_korean_voices()
        with self.assertRaises(SpeechError): svc.speak("안녕",self.voice)

    def test_list_only_installed_korean(self):
        voices=self.service.list_korean_voices()
        self.assertEqual(voices,[self.voice])
        self.assertEqual(self.issued[0][0],"list")
        self.assertEqual(self.issued[0][2]["creationflags"],0x08000000)

    def test_empty_voice_list(self):
        svc=WindowsSpeechPreview(platform="win32",runner=lambda *_a, **_k: voices_result([]))
        self.assertEqual(svc.list_korean_voices(),[])

    def test_invalid_voice_data_rejected(self):
        svc=WindowsSpeechPreview(platform="win32",runner=lambda *_a, **_k:
                                 voices_result([{"name":"English","culture":"en-US"}]))
        with self.assertRaises(SpeechError): svc.list_korean_voices()

    def test_voice_listing_failure(self):
        svc=WindowsSpeechPreview(platform="win32",runner=lambda *_a,**_k:
                                  subprocess.CompletedProcess([],1,b"",b"bad"))
        with self.assertRaises(SpeechError): svc.list_korean_voices()

    def test_voice_bad_json(self):
        svc=WindowsSpeechPreview(platform="win32",runner=lambda *_a, **_k:
                                  subprocess.CompletedProcess([],0,b"broken",b""))
        with self.assertRaises(SpeechError): svc.list_korean_voices()

    def test_powershell_script_encoded(self):
        command=_command(_SPEAK_SCRIPT)
        self.assertEqual(command[0],"powershell.exe")
        self.assertIn("-NoProfile",command)
        self.assertIn("-NonInteractive",command)
        decoded=base64.b64decode(command[-1]).decode("utf-16le")
        self.assertIn("System.Speech",decoded)
        self.assertIn("[Console]::OpenStandardInput()",decoded)

    def test_speak_passes_korean_as_json_not_script(self):
        content="안녕! $env:USERPROFILE; Remove-Item *"
        self.service.speak(content,self.voice,volume=40,rate=-2)
        self.assertEqual(self.process.payload["text"],content)
        self.assertEqual(self.process.payload["voice"],self.voice.name)
        self.assertEqual(self.process.payload["volume"],40)
        self.assertEqual(self.process.payload["rate"],-2)
        cmd=self.issued[0][1]
        script=base64.b64decode(cmd[-1]).decode("utf-16le")
        self.assertNotIn("Remove-Item",script)
        self.assertIsNone(self.service._active)

    def test_disallow_empty_or_oversized_text(self):
        for text in ("", " "*4, "가"*601):
            with self.subTest(value=text[:10]),self.assertRaises(ValueError):
                self.service.speak(text,self.voice)
        self.assertEqual(self.issued,[])

    def test_disallow_invalid_rate_volume(self):
        for props in ({"volume":101},{"volume":-1},{"rate":8},{"rate":-5},
                      {"rate":True}):
            with self.subTest(props=props),self.assertRaises(ValueError):
                self.service.speak("안녕",self.voice,**props)

    def test_voice_selection_rejects_non_korean(self):
        with self.assertRaises(ValueError):
            Voice("English", "en-US")

    def test_no_sound_without_ko_voice(self):
        with self.assertRaises(TypeError):
            self.service.speak("안녕하세요","없는 음성")

    def test_stop_is_limited_to_preview_process(self):
        self.process = FakePlayer(blocked=True)
        result=[]
        worker=threading.Thread(target=lambda: self._call_and_collect(result))
        worker.start()
        self.assertTrue(self.process.started.wait(2))
        self.assertTrue(self.service.stop())
        worker.join(timeout=4)
        self.assertFalse(worker.is_alive())
        self.assertEqual(result, [], "User-requested stop must not raise on the worker")
        self.assertIsNone(self.service._active)
        self.assertFalse(self.service.stop())

    def _call_and_collect(self,result):
        try:
            self.service.speak("안녕하세요",self.voice)
        except Exception as e:
            result.append(e)

    def test_no_second_play_while_running(self):
        self.process=FakePlayer(blocked=True)
        errors = []
        thread=threading.Thread(
            target=lambda: self._call_and_collect(errors), name="windows-tts-cancellation-test"
        )
        thread.start()
        self.assertTrue(self.process.started.wait(2))
        with self.assertRaises(SpeechError):
            self.service.speak("두 번째 문장",self.voice)
        self.assertTrue(self.service.stop())
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [], "Cancelling preview must not leave an uncaught thread error")

    def test_real_playback_failure_still_reports_error(self):
        self.process = FakePlayer(returncode=3)
        with self.assertRaises(SpeechError):
            self.service.speak("실제 음성 장치 실패", self.voice)
        self.assertIsNone(self.service._active)

    def test_missing_powershell_reported(self):
        def fail(cmd, **kwargs):
            raise FileNotFoundError("powershell.exe")
        svc=WindowsSpeechPreview(platform="win32",process_factory=fail)
        with self.assertRaises(SpeechError): svc.speak("안녕",self.voice)
