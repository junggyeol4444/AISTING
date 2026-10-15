"""창이 열리는 환경에서 실행하는 빠른 오프라인 GUI/음성 FIFO 테스트.

실제 PowerShell, 스피커, GitHub, OBS, 방송 플랫폼에 접속하지 않는다.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_tts import KoreanVoice
from ai_broadcaster.offline_chat import ChatMessage, Answer


def main() -> None:
    window = AistingApp()
    try:
        window.update_idletasks()
        assert window._auto_read.get() is False, "자동 음성 읽기가 기본적으로 꺼져 있지 않음"
        assert not window._speaker.speaking
        window._events.put(("voices",[KoreanVoice("모의 한국어 음성")]))
        window._poll()
        assert window._selected_voice() is not None

        spoken: list[str] = []
        lock = threading.Lock()

        def fake_speak(text: str, voice: KoreanVoice) -> bool:
            with lock:
                spoken.append(text)
            time.sleep(.06)
            return True

        window._speaker.speak = fake_speak
        window._voice.set("Windows 무료 음성")
        window._auto_read.set(True)
        for i in range(4):
            window._events.put(("answer",Answer(ChatMessage(f"시청자{i}",f"질문{i}"),f"답변{i}")))
        window._events.put(("done",None))
        deadline = time.monotonic() + 5
        while (len(spoken) < 4 or window._speech_busy or window._speech_pending) and time.monotonic() < deadline:
            window.update()
            window._poll()
            time.sleep(.02)
        expected=[f"답변{i}" for i in range(4)]
        assert spoken == expected, f"음성 순서 오류: {spoken!r} != {expected!r}"
        print("GUI 초기화, 자동 음성 꺼짐, 모의 음성 FIFO 4개: 통과")
    finally:
        window.destroy()


if __name__ == "__main__":
    main()
