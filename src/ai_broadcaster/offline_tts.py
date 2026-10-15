"""Windows PC 내장 System.Speech 한국어 TTS. 외부 서버/다운로드/유료 API 없음.

버튼을 누른 경우에만 프로그램이 OS에 음성 목록 조회·재생을 요청한다.
명령어 문자열에 사용자가 작성한 텍스트를 결합하지 않는다: JSON stdin 사용.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from typing import Any, Callable


class SpeechUnavailable(RuntimeError):
    """PC에 음성 엔진이 없거나 재생할 수 없는 상태."""


@dataclass(frozen=True)
class KoreanVoice:
    name: str
    culture: str = "ko-KR"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not 1 <= len(self.name) <= 160 or "\x00" in self.name:
            raise ValueError("한국어 음성 이름이 유효하지 않습니다.")
        if self.culture != "ko-KR":
            raise ValueError("설치된 한국어(ko-KR) 음성만 선택할 수 있습니다.")


# 시스템 .NET Framework 음성 엔진만 사용. 네트워크 호출이 전혀 없음.
_LIST_VOICES = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
$tts = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voices = @($tts.GetInstalledVoices() | Where-Object {
        $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'ko-KR'
    } | ForEach-Object {
        [pscustomobject]@{name = $_.VoiceInfo.Name; culture = 'ko-KR'}
    })
    ConvertTo-Json -InputObject $voices -Depth 3 -Compress
} finally {
    $tts.Dispose()
}
'''

# 사용자 입력은 명령어 문자열에 포함되지 않고 표준 입력 JSON으로 전달한다.
_SPEAK = r'''
$ErrorActionPreference = 'Stop'
$reader = [System.IO.StreamReader]::new([Console]::OpenStandardInput(), [System.Text.Encoding]::UTF8)
try {
    $data = ConvertFrom-Json -InputObject ($reader.ReadToEnd())
} finally {
    $reader.Dispose()
}
Add-Type -AssemblyName System.Speech
$tts = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $match = @($tts.GetInstalledVoices() | Where-Object {
        $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'ko-KR' -and
        $_.VoiceInfo.Name -ceq [string]$data.voice
    })
    if ($match.Count -ne 1) { throw 'Korean voice missing' }
    $tts.SelectVoice([string]$data.voice)
    $tts.Volume = [int]$data.volume
    $tts.Rate = [int]$data.rate
    $tts.SetOutputToDefaultAudioDevice()
    $tts.Speak([string]$data.text)
} finally {
    $tts.Dispose()
}
'''


def _command(script: str) -> list[str]:
    return ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
            "-EncodedCommand", base64.b64encode(script.encode("utf-16le")).decode("ascii")]


def _flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


class WindowsKoreanSpeech:
    """순수 Windows 기본 TTS. 말하는 동안 다른 동시 재생은 막고 중지는 가능."""

    def __init__(self, *, platform: str | None = None,
                 run: Callable[..., Any] | None = None,
                 popen: Callable[..., Any] | None = None) -> None:
        self.platform = sys.platform if platform is None else platform
        self._run = subprocess.run if run is None else run
        self._popen = subprocess.Popen if popen is None else popen
        self._lock = threading.RLock()
        self._process: Any | None = None
        self._busy = False
        self._cancel = threading.Event()

    def _ensure_windows(self) -> None:
        if self.platform != "win32":
            raise SpeechUnavailable("한국어 음성은 Windows PC에서만 재생할 수 있어요.")

    @property
    def speaking(self) -> bool:
        with self._lock:
            return self._busy

    def installed_voices(self) -> list[KoreanVoice]:
        """설치된 한국어 시스템 음성만 조회. 조회 시 소리는 나지 않음."""
        self._ensure_windows()
        try:
            proc = self._run(_command(_LIST_VOICES), capture_output=True,
                             timeout=20, creationflags=_flags())
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SpeechUnavailable("PC의 Windows 음성 목록을 읽을 수 없습니다.") from exc
        if proc.returncode != 0:
            raise SpeechUnavailable("한국어 시스템 음성 조회에 실패했습니다.")
        try:
            payload = json.loads(proc.stdout.decode("utf-8-sig"))
            if not isinstance(payload, list) or len(payload) > 100:
                raise ValueError("목록 형식 오류")
            voices = [KoreanVoice(item["name"], item["culture"]) for item in payload]
            if len({v.name for v in voices}) != len(voices):
                raise ValueError("음성 이름 중복")
            return voices
        except (ValueError, KeyError, UnicodeError, TypeError) as exc:
            raise SpeechUnavailable("한국어 시스템 음성 목록 형식이 올바르지 않습니다.") from exc

    def speak(self, text: str, voice: KoreanVoice, *, rate: int = 0,
              volume: int = 85) -> bool:
        """선택한 문장 1회 재생. 성공 True, 중지되면 False.

        GUI 이벤트 스레드가 아닌 백그라운드 스레드에서 호출해야 한다.
        """
        self._ensure_windows()
        if not isinstance(voice, KoreanVoice):
            raise ValueError("설치된 한국어 목소리를 선택해 주세요.")
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 600:
            raise ValueError("미리 듣기 문장은 1~600글자여야 합니다.")
        if type(rate) is not int or not -4 <= rate <= 4:
            raise ValueError("음성 속도는 -4~4 사이의 정수여야 합니다.")
        if type(volume) is not int or not 0 <= volume <= 100:
            raise ValueError("음량은 0~100이어야 합니다.")
        with self._lock:
            if self._busy:
                raise SpeechUnavailable("이미 음성 재생 중입니다.")
            self._busy = True
            self._cancel.clear()
        process = None
        try:
            try:
                process = self._popen(_command(_SPEAK), stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      creationflags=_flags())
            except OSError as exc:
                raise SpeechUnavailable("Windows 기본 음성 도구를 실행할 수 없습니다.") from exc
            with self._lock:
                self._process = process
                if self._cancel.is_set() and process.poll() is None:
                    process.terminate()
            data = json.dumps({"text": text.strip(), "voice": voice.name,
                               "rate": rate, "volume": volume}, ensure_ascii=False).encode("utf-8")
            try:
                process.communicate(input=data, timeout=95)
            except subprocess.TimeoutExpired as exc:
                process.kill()
                process.communicate()
                raise SpeechUnavailable("음성 재생 제한 시간을 초과했습니다.") from exc
            if self._cancel.is_set():
                return False
            if process.returncode != 0:
                raise SpeechUnavailable("음성을 재생할 수 없습니다. 한국어 음성/스피커를 확인해 주세요.")
            return True
        finally:
            with self._lock:
                self._process = None
                self._busy = False

    def stop(self) -> bool:
        """AISTING이 시작한 TTS 프로세스만 중단. 시스템의 다른 소리에는 영향 없음."""
        with self._lock:
            if not self._busy:
                return False
            self._cancel.set()
            if self._process is not None and self._process.poll() is None:
                self._process.terminate()
            return True


def speech_chunks(answer: str, maximum: int = 600) -> list[str]:
    """긴 답변을 전부 유지하면서 한 번에 재생 가능한 길이로 분할."""
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 6000:
        raise ValueError("읽을 답변은 1~6000자여야 합니다.")
    if type(maximum) is not int or not 1 <= maximum <= 600:
        raise ValueError("음성 구간 크기가 올바르지 않습니다.")
    source = answer.strip()
    result = []
    while source:
        cut = min(len(source), maximum)
        # 공백/문장 경계를 사용하되 손실 없이 원문을 보존한다.
        if cut < len(source):
            split_at = max(source.rfind(" ", cut//2, cut), source.rfind("\n", cut//2, cut))
            if split_at > 0:
                cut = split_at + 1
        result.append(source[:cut])
        source = source[cut:]
    return result
