"""Check a REAL frozen Windows GUI window and capture an unaltered screenshot.

No mock API, model, voice, OBS, keyboard injection or broadcast. This checks
ONLY whether the native app starts and visibly renders its stage-one preview.
"""
from __future__ import annotations

import ctypes
import time
from pathlib import Path

import pyautogui


def find_window():
    user32 = ctypes.windll.user32
    found = []
    winfunctype = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    @winfunctype
    def visit(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if not n:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        if buf.value.startswith("AISTING · 1단계 실제 AI 연결"):
            found.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    return found[0] if found else None


def main():
    hwnd = None
    for _ in range(45):
        hwnd = find_window()
        if hwnd is not None:
            break
        time.sleep(1)
    assert hwnd, "Frozen stage-one EXE did not expose a real Windows HWND"
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 9)
    try:
        user32.SetForegroundWindow(hwnd)
    except OSError:
        pass
    time.sleep(2)
    evidence = Path("stage1_windows_evidence")
    evidence.mkdir(exist_ok=True)
    shot = pyautogui.screenshot()
    shot.save(evidence / "actual_stage1_window.png")
    pixels = list(shot.convert("RGB").getdata())
    face = pixels.count((246, 211, 197))
    hair = pixels.count((52, 79, 135))
    assert face > 300 and hair > 300, (
        "Actual Windows screenshot does not show even the labeled placeholder "
        "avatar. face=%d hair=%d" % (face, hair)
    )
    print(
        "PASS: native stage-one EXE HWND + real pixels + PNG. "
        "NOT VALIDATED: Ollama service, actual Live2D, TTS or real broadcast.",
        face, hair, flush=True,
    )


if __name__ == "__main__":
    main()
