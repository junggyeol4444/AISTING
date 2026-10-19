"""운영자 PC/Windows 음성 엔진 없이 테스트하는 로컬 TTS 검증."""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ai_broadcaster.offline_tts import (
    KoreanVoice, SpeechUnavailable, WindowsKoreanSpeech,
    _command, _LIST_VOICES, _SPEAK, speech_chunks,
)


class FakeProcess:
    def __init__(self, *, code=0, blocked=False):
        self.returncode = None
        self.final_code = code
        self.blocked = blocked
        self.payload = None
        self.started = threading.Event()
        self.release = threading.Event()
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.final_code = -15
        self.release.set()

    def kill(self):
        self.final_code = -9
        self.release.set()

    def communicate(self, input=None, timeout=None):
        if input is not None:
            self.payload = json.loads(input.decode("utf-8"))
        self.started.set()
        if self.blocked:
            self.release.wait(3)
        self.returncode = self.final_code
        return b"", b""


class TestOfflineWindowsSpeech(unittest.TestCase):
    def setUp(self):
        self.voice = KoreanVoice("Microsoft Heami Desktop", "ko-KR")
        self.actions = []
        self.player = FakeProcess()

        def voice_run(command, **kwargs):
            self.actions.append(("list", command, kwargs))
            return SimpleNamespace(returncode=0, stdout=json.dumps([
                {"name": self.voice.name, "culture": self.voice.culture}
            ], ensure_ascii=False).encode("utf-8"))

        def speak_popen(command, **kwargs):
            self.actions.append(("speak", command, kwargs))
            return self.player

        self.engine = WindowsKoreanSpeech(platform="win32", run=voice_run, popen=speak_popen)

    def test_initialization_does_not_run_process(self):
        self.assertEqual(self.actions, [])
        self.assertFalse(self.engine.speaking)

    def test_voices_only_after_explicit_call(self):
        self.assertEqual(self.engine.installed_voices(), [self.voice])
        self.assertEqual([a[0] for a in self.actions], ["list"])

    def test_command_is_fixed_encoded_powershell_without_download(self):
        for script in (_LIST_VOICES, _SPEAK):
            cmd = _command(script)
            self.assertEqual(cmd[0], "powershell.exe")
            self.assertIn("-NoProfile", cmd)
            self.assertIn("-NonInteractive", cmd)
            recovered = base64.b64decode(cmd[-1]).decode("utf-16le")
            self.assertIn("System.Speech", recovered)
            for prohibited in ("Invoke-WebRequest", "DownloadString", "StartStream", "github.com"):
                self.assertNotIn(prohibited, recovered)

    def test_powershell_injection_is_only_data(self):
        dangerous = '안녕; Start-Process calc; $env:PATH; "quotes"\n테스트'
        self.assertTrue(self.engine.speak(dangerous, self.voice))
        self.assertEqual(self.player.payload["text"], dangerous.strip())
        encoded_command = self.actions[0][1]
        recovered = base64.b64decode(encoded_command[-1]).decode("utf-16le")
        self.assertNotIn("Start-Process calc", recovered)

    def test_default_local_speaker_parameters(self):
        self.engine.speak("안녕하세요", self.voice)
        self.assertEqual(self.player.payload["voice"], self.voice.name)
        self.assertEqual(self.player.payload["rate"], 0)
        self.assertEqual(self.player.payload["volume"], 85)

    def test_korean_voice_only(self):
        with self.assertRaises(ValueError):
            KoreanVoice("English voice", "en-US")
        with self.assertRaises(ValueError):
            KoreanVoice("")
        with self.assertRaises(ValueError):
            KoreanVoice("x" * 161)

    def test_not_windows_never_launches_subprocess(self):
        eng = WindowsKoreanSpeech(platform="linux", run=lambda *_a, **_kw: self.fail("called"),
                                  popen=lambda *_a, **_kw: self.fail("called"))
        with self.assertRaises(SpeechUnavailable):
            eng.installed_voices()
        with self.assertRaises(SpeechUnavailable):
            eng.speak("안녕", self.voice)

    def test_empty_installed_voice_list(self):
        eng = WindowsKoreanSpeech(platform="win32", run=lambda *_a, **_kw:
                                  SimpleNamespace(returncode=0, stdout=b"[]"))
        self.assertEqual(eng.installed_voices(), [])

    def test_reject_bad_voice_response(self):
        for out in (b"not-json", b"{}", b'[{"name":"english","culture":"en-US"}]',
                    b'[{"name":"x"}]'):
            eng = WindowsKoreanSpeech(platform="win32", run=lambda *_a, **_kw:
                                      SimpleNamespace(returncode=0, stdout=out))
            with self.subTest(out=out), self.assertRaises(SpeechUnavailable):
                eng.installed_voices()

    def test_list_failure(self):
        eng = WindowsKoreanSpeech(platform="win32", run=lambda *_a, **_kw:
                                  SimpleNamespace(returncode=1, stdout=b""))
        with self.assertRaises(SpeechUnavailable):
            eng.installed_voices()

    def test_list_missing_powershell(self):
        eng = WindowsKoreanSpeech(platform="win32", run=lambda *_a, **_kw:
                                  (_ for _ in ()).throw(FileNotFoundError()))
        with self.assertRaises(SpeechUnavailable):
            eng.installed_voices()

    def test_invalid_input_never_starts_player(self):
        for value in ("", "   ", "가" * 601, None):
            with self.subTest(value=repr(value)[:30]), self.assertRaises(ValueError):
                self.engine.speak(value, self.voice)
        self.assertEqual(self.actions, [])

    def test_rate_and_volume_validation(self):
        for kwargs in ({"rate": 5}, {"rate": -5}, {"volume": -1},
                       {"volume": 101}, {"rate": True}, {"volume": False}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.engine.speak("안녕", self.voice, **kwargs)
        self.assertEqual(self.actions, [])

    def test_non_voice_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.speak("안녕", "한국어")
        self.assertEqual(self.actions, [])

    def test_active_speech_blocks_second_voice(self):
        self.player = FakeProcess(blocked=True)
        errors = []
        t = threading.Thread(target=lambda: self._speak_catch(errors))
        t.start()
        self.assertTrue(self.player.started.wait(2))
        self.assertTrue(self.engine.speaking)
        with self.assertRaises(SpeechUnavailable):
            self.engine.speak("다른 채팅", self.voice)
        self.engine.stop()
        t.join(3)
        self.assertFalse(t.is_alive())
        self.assertFalse(self.engine.speaking)
        self.assertEqual(errors, [])

    def _speak_catch(self, errors):
        try:
            self.engine.speak("첫 번째", self.voice)
        except Exception as exc:
            errors.append(exc)

    def test_stop_only_started_process(self):
        self.player = FakeProcess(blocked=True)
        t = threading.Thread(target=lambda: self.engine.speak("안녕", self.voice))
        t.start()
        self.assertTrue(self.player.started.wait(2))
        self.assertTrue(self.engine.stop())
        t.join(3)
        self.assertTrue(self.player.terminated)
        self.assertFalse(self.engine.stop())

    def test_failed_speech_releases_busy(self):
        self.player = FakeProcess(code=3)
        with self.assertRaises(SpeechUnavailable):
            self.engine.speak("안녕", self.voice)
        self.assertFalse(self.engine.speaking)

    def test_missing_player_releases_busy(self):
        eng = WindowsKoreanSpeech(platform="win32", popen=lambda *_a, **_kw:
                                  (_ for _ in ()).throw(FileNotFoundError()))
        with self.assertRaises(SpeechUnavailable):
            eng.speak("안녕", self.voice)
        self.assertFalse(eng.speaking)


class TestSpeechText(unittest.TestCase):
    def test_short_reply(self):
        self.assertEqual(speech_chunks("안녕"), ["안녕"])

    def test_long_reply_is_lossless(self):
        source = "가" * 1280
        result = speech_chunks(source)
        self.assertEqual("".join(result), source)
        self.assertTrue(all(len(x) <= 600 for x in result))

    def test_split_respects_blank_between_words(self):
        source = "가" * 450 + " " + "나" * 450
        result = speech_chunks(source)
        self.assertEqual("".join(result), source)
        self.assertEqual(len(result), 2)

    def test_chunk_invalid_bounds(self):
        for value in (0, 601, -1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                speech_chunks("안녕", value)
        for source in ("", " ", "가" * 6001, None):
            with self.subTest(source=str(source)[:15]), self.assertRaises(ValueError):
                speech_chunks(source)

    def test_gui_auto_read_opt_in(self):
        gui = (ROOT / "src/ai_broadcaster/desktop.py").read_text(encoding="utf-8")
        self.assertIn("self._auto_read = tk.BooleanVar(value=False)", gui)
        self.assertIn("_speaker.speaking", gui)
        self.assertIn('"무료 한국어 음성"', gui)
        self.assertNotIn("git push", gui)

    def test_window_close_stops_local_audio(self):
        gui = (ROOT / "src/ai_broadcaster/desktop.py").read_text(encoding="utf-8")
        self.assertIn('self.protocol("WM_DELETE_WINDOW", self._shutdown)', gui)
        self.assertIn('self._speaker.stop()', gui)
        self.assertIn('self._speech_pending.clear()', gui)

    def test_no_remote_ci_build_or_automation(self):
        # Build workflows may live in GitHub while the shipped Windows app stays offline.
        script = (ROOT / "build_exe_windows.bat").read_text(encoding="utf-8")
        for snippet in ("curl", "pip install", "schtasks", "git push"):
            self.assertNotIn(snippet, script)


if __name__ == "__main__":
    unittest.main()
