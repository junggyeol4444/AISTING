"""Windows PC에 이미 설치된 한국어 SAPI 음성을 사용하는 무료 미리 듣기.

명시적 버튼 클릭 이외에는 음성 재생/외부 통신/설치를 실행하지 않는다.
고정된 PowerShell 스크립트를 UTF-16LE로 인코딩하고, 사용자 텍스트는
UTF-8 JSON 표준 입력으로만 전달하여 명령어 삽입을 방지한다.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import threading
from dataclasses import dataclass
from typing import Callable


class SpeechError(RuntimeError):
    """Windows TTS 음성 장치·음성 목록·재생 오류."""


@dataclass(frozen=True)
class Voice:
    name: str
    culture: str

    def __post_init__(self) -> None:
        if (not isinstance(self.name, str) or not 1 <= len(self.name) <= 150
                or "\x00" in self.name):
            raise ValueError("음성 이름이 유효하지 않습니다.")
        if self.culture != "ko-KR":
            raise ValueError("한국어(ko-KR) 음성만 선택할 수 있습니다.")


# Windows PowerShell (.NET Framework System.Speech). 다운로드/유료 API 없음.
_LIST_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
$speech = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voices = @($speech.GetInstalledVoices() | Where-Object {
        $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'ko-KR'
    } | ForEach-Object {
        [pscustomobject]@{name=$_.VoiceInfo.Name; culture=$_.VoiceInfo.Culture.Name}
    })
    ConvertTo-Json -InputObject $voices -Depth 3 -Compress
} finally {
    $speech.Dispose()
}
"""

_SPEAK_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$reader = [System.IO.StreamReader]::new(
    [Console]::OpenStandardInput(), [System.Text.Encoding]::UTF8
)
try {
    $data = ConvertFrom-Json -InputObject ($reader.ReadToEnd())
} finally {
    $reader.Dispose()
}
Add-Type -AssemblyName System.Speech
$speech = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $wanted = [string]$data.voice
    $voices = @($speech.GetInstalledVoices() | Where-Object {
        $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'ko-KR' -and
        $_.VoiceInfo.Name -ceq $wanted
    })
    if ($voices.Count -ne 1) {
        throw 'The selected Korean TTS voice is not installed'
    }
    $speech.SelectVoice($wanted)
    $speech.Volume = [int]$data.volume
    $speech.Rate = [int]$data.rate
    $speech.SetOutputToDefaultAudioDevice()
    $speech.Speak([string]$data.text)
} finally {
    $speech.Dispose()
}
"""


def _command(script: str) -> list[str]:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return [
        "powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
        "-EncodedCommand", encoded,
    ]


def _windows_flags(platform: str) -> int:
    return 0x08000000 if platform == "win32" else 0


class WindowsSpeechPreview:
    """시스템 한국어 음성 탐색 및 1회 재생. GUI 별도 스레드에서 호출."""

    def __init__(
        self, *,
        platform: str | None = None,
        runner: Callable[..., object] = subprocess.run,
        process_factory: Callable[..., object] = subprocess.Popen,
    ) -> None:
        self.platform = sys.platform if platform is None else platform
        self._run = runner
        self._popen = process_factory
        self._lock = threading.Lock()
        self._active: object | None = None
        # A user-requested stop is not a broken speaker or missing voice.
        self._cancel = threading.Event()

    def _check_platform(self) -> None:
        if self.platform != "win32":
            raise SpeechError("Windows에서만 사용할 수 있는 음성 미리 듣기입니다.")

    def list_korean_voices(self) -> list[Voice]:
        """음성 목록만 조회하며 실제 소리/다운로드/외부 요청은 없음."""
        self._check_platform()
        try:
            result = self._run(
                _command(_LIST_SCRIPT),
                capture_output=True, timeout=15,
                creationflags=_windows_flags(self.platform),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SpeechError("Windows 음성 목록을 읽을 수 없습니다.") from exc
        if result.returncode != 0:
            raise SpeechError("Windows 한국어 음성 목록 조회에 실패했습니다.")
        try:
            raw = json.loads(result.stdout.decode("utf-8-sig").strip())
            if not isinstance(raw, list):
                raise ValueError("음성 목록 형식 오류")
            choices: list[Voice] = []
            for item in raw:
                if not isinstance(item, dict):
                    raise ValueError("음성 항목 형식 오류")
                choices.append(Voice(name=item["name"], culture=item["culture"]))
            return choices
        except (UnicodeError, ValueError, TypeError, KeyError) as exc:
            raise SpeechError("Windows 음성 목록을 해석하지 못했습니다.") from exc

    def speak(self, text: str, voice: Voice, *, volume: int = 85, rate: int = 0) -> None:
        """실제로 음성을 재생함. 반드시 사용자 명시적 버튼 클릭에서만 호출."""
        self._check_platform()
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 600:
            raise ValueError("미리 듣기 문장은 1~600자여야 합니다.")
        if not isinstance(voice, Voice):
            raise TypeError("설치된 한국어 음성 선택이 필요합니다.")
        if type(volume) is not int or not 0 <= volume <= 100:
            raise ValueError("볼륨은 0~100 범위의 정수입니다.")
        if type(rate) is not int or not -4 <= rate <= 4:
            raise ValueError("속도는 -4~4 범위의 정수입니다.")
        with self._lock:
            if self._active is not None:
                raise SpeechError("이미 음성을 재생 중입니다.")
            try:
                process = self._popen(
                    _command(_SPEAK_SCRIPT),
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=_windows_flags(self.platform),
                )
            except OSError as exc:
                raise SpeechError("Windows 음성 재생 도구를 실행하지 못했습니다.") from exc
            self._cancel.clear()
            self._active = process
        payload = json.dumps(
            {"text": text.strip(), "voice": voice.name, "volume": volume, "rate": rate},
            ensure_ascii=False,
        ).encode("utf-8")
        try:
            try:
                stdout, stderr = process.communicate(input=payload, timeout=95)
            except subprocess.TimeoutExpired as exc:
                process.kill()
                process.communicate()
                raise SpeechError("음성 재생 제한 시간이 초과됐습니다.") from exc
            if self._cancel.is_set():
                # Stop button intentionally terminated this process: no error.
                return
            if process.returncode != 0:
                raise SpeechError("Windows 음성 재생에 실패했습니다. 한국어 음성 설치 여부를 확인해 주세요.")
        finally:
            with self._lock:
                if self._active is process:
                    self._active = None
                    self._cancel.clear()

    def stop(self) -> bool:
        """현재 미리 듣기만 종료. 외부 방송·다른 프로세스에는 영향 없음."""
        with self._lock:
            current = self._active
            if current is None:
                return False
            if current.poll() is None:
                self._cancel.set()
                current.terminate()
                return True
            return False
