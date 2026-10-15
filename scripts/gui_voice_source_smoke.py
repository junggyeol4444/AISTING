"""목소리 확보 방식/PC 저장/재실행/한국어 음성 재생 파라미터 GUI 연동 검사.

Linux/Xvfb 또는 Windows 화면에서 실행. 실제 스피커/외부 서버/음성 학습은 사용하지 않음.
"""
from __future__ import annotations

import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_tts import KoreanVoice
from ai_broadcaster.offline_settings import load_settings, save_settings


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        file = Path(folder) / "settings.json"
        opts = [KoreanVoice("무료 음성 A"), KoreanVoice("무료 음성 B")]
        with (patch("ai_broadcaster.desktop.load_settings", side_effect=lambda: load_settings(file)),
              patch("ai_broadcaster.desktop.save_settings", side_effect=lambda v: save_settings(v, file)),
              patch("socket.create_connection") as network):
            app = AistingApp()
            try:
                app.update()
                assert app._voice.get() == "미정"
                assert app._auto_read.get() is False
                for source in ("내 목소리 (추후 직접 녹음)", "동의받은 목소리 (추후 확보)",
                               "라이선스 확보 목소리 (추후 확보)", "미정"):
                    app._voice.set(source)
                    app._save()
                    assert load_settings(file)["voice"] in (
                        "own_recording", "consented_recording", "licensed_recording", "undecided"
                    )
                    assert not load_settings(file)["streaming_enabled"]
                app._voice_lookup_done("voices", opts)
                assert app._voice_preferred_name == "", "목록 조회만으로 임의의 목소리를 저장해선 안 됨"
                app._voice_name.set("무료 음성 B (ko-KR)")
                app._on_installed_voice_selected()
                assert app._voice.get() == "Windows 무료 음성"
                assert app._voice_preferred_name == "무료 음성 B"
                app._voice_rate.set("-2")
                app._voice_volume.set("67")
                app._save()
                stored = load_settings(file)
                assert stored["voice"] == "windows_system", stored
                assert stored["voice_profile"] == {
                    "installed_voice_name":"무료 음성 B", "rate":-2, "volume":67
                },stored
                network.assert_not_called()
            finally:
                app._shutdown()

            app = AistingApp()
            try:
                app.update()
                assert app._voice_preferred_name == "무료 음성 B"
                assert app._voice_rate.get() == "-2"
                assert app._voice_volume.get() == "67"
                app._voice_lookup_done("voices", list(reversed(opts)))
                assert app._selected_voice().name == "무료 음성 B"
                spoken = []
                started = threading.Event()
                def fake_speak(text, voice, *, rate=0, volume=85):
                    spoken.append((text, voice.name, rate, volume))
                    started.set()
                    return True
                app._speaker.speak = fake_speak
                app._start_speech("안녕하세요 테스트")
                deadline = time.monotonic() + 3
                while (not started.is_set() or app._speech_busy) and time.monotonic() < deadline:
                    app.update()
                    app._poll()
                    time.sleep(.01)
                assert spoken == [("안녕하세요 테스트", "무료 음성 B", -2, 67)],spoken
                app._voice_lookup_done("voices", [opts[0]])
                assert app._selected_voice() is None
                assert "없어" in app._speech_status.get()
                # 미설치 음성이 있다고 거짓으로 표시하거나 임의의 대체값을 저장하지 않음.
                app._save()
                assert load_settings(file)["voice_profile"]["installed_voice_name"] == "무료 음성 B"
                network.assert_not_called()
                print("GUI 목소리 확보 방식 선택·저장·복원·속도/음량 전달·미설치 음성 대체 방지: 통과")
            finally:
                app._shutdown()


if __name__ == "__main__":
    main()
