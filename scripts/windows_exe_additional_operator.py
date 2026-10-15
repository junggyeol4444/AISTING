"""Additional black-box frozen Windows EXE: 3D fallback, 2D restore, voice lookup.

Real Windows keyboard, mouse and screenshots. Synthetic local profile only.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time

import pyautogui
import windows_exe_real_operator as op


def main():
    from PIL import Image, ImageChops

    exe = Path("dist/AISTING.exe").resolve()
    assert exe.is_file()
    profile = Path(os.environ.get("RUNNER_TEMP", ".")) / "aisting_extra_gui_operator"
    settings_path = profile / "AISTING" / "settings.json"
    assert not settings_path.exists()
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(profile)
    process = subprocess.Popen([str(exe)], env=env)
    hwnd = None
    try:
        hwnd = op.await_window()["hwnd"]
        time.sleep(1.8)

        # The actual Windows GUI avatar dropdown receives keyboard inputs.
        op.choose_avatar(hwnd, 2)  # "3D" after home/down/down
        op.snap("21_selected_3d_avatar_on_operator_home", hwnd)
        op.save_preferences(hwnd)
        three_d = json.loads(settings_path.read_text(encoding="utf-8"))
        assert three_d["avatar"] == "3d", three_d["avatar"]

        op.go(hwnd, 5)
        op.snap("22_unimplemented_3d_placeholder", hwnd)
        op.native_wheel(hwnd)
        op.snap("23_3d_cannot_open_fake_2d_sample", hwnd)
        pyautogui.press("space")  # disabled open button should do nothing
        time.sleep(0.5)
        assert not [w for w in op.windows() if "아바타 · 로컬 창 캡처용" in w["title"]], \
            "3D setting created a misleading 2D popout"
        print("OPERATOR EXTRA PASS 3D preview correctly disabled", flush=True)

        op.choose_avatar(hwnd, 1)  # restore 2D using native dropdown
        op.save_preferences(hwnd)
        two_d = json.loads(settings_path.read_text(encoding="utf-8"))
        assert two_d["avatar"] == "2d"
        assert two_d["persona"] == three_d["persona"]
        assert two_d["platforms"] == three_d["platforms"]
        print("OPERATOR EXTRA PASS 2D restores without touching character", flush=True)

        op.go(hwnd, 4)  # native Windows voice tab, combobox focused
        op.snap("24_windows_voice_page_no_audio_playback", hwnd)
        before = Image.open(op.OUTPUT / "24_windows_voice_page_no_audio_playback.png").convert("RGB")
        pyautogui.press("tab")  # visible "음성 목록 확인" button
        pyautogui.press("space")
        time.sleep(3)
        op.snap("25_voice_lookup_clicked_on_real_windows", hwnd)
        after = Image.open(op.OUTPUT / "25_voice_lookup_clicked_on_real_windows.png").convert("RGB")
        changed = sum(v > 12 for v in ImageChops.difference(before, after).convert("L").getdata())
        assert changed > 350, "Real Windows voice lookup did not update screen"
        print("OPERATOR EXTRA PASS voice list lookup updated native UI; did not play audio", flush=True)
    except Exception:
        try:
            if hwnd and op.u32.IsWindow(hwnd):
                op.snap("FAILED_extra_windows_operator", hwnd)
            pyautogui.screenshot().save(op.OUTPUT / "FAILED_extra_desktop.png")
        except Exception:
            pass
        raise
    finally:
        op.close_app(process, hwnd)
    print("OPERATOR EXTRA PASS frozen EXE, 3D/2D/voice, normal close", flush=True)


if __name__ == "__main__":
    main()
