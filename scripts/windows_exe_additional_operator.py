"""Additional real Windows EXE operator scenario: 3D unavailable, restore 2D and voice tab.

Uses only Windows GUI mouse/keyboard input and synthetic isolated preferences.
Does not invoke internal AISTING callbacks, audio, OBS or external services.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import subprocess
import time

import pyautogui

import windows_exe_real_operator as op


def choose_page(hwnd, position: int) -> None:
    op.click_relative(hwnd, 200, 103)
    if position == 0:
        # Windows ttk Combobox ignores Home as a selection in some themes.
        # Repeated Up actively changes the selected item to the first page.
        pyautogui.press("up", presses=40, interval=0.015)
    else:
        pyautogui.press("home")
        pyautogui.press("down", presses=position, interval=0.14)
    pyautogui.press("enter")
    time.sleep(0.5)


def scroll_settings(hwnd) -> None:
    left, top, _, _ = op.client_area(hwnd)
    pyautogui.moveTo(left + 650, top + 430)
    delta = ((-120 * 30) & 0xFFFF) << 16
    loc = (((top + 430) & 0xFFFF) << 16) | ((left + 650) & 0xFFFF)
    op.u32.SendMessageW(hwnd, 0x020A, delta, loc)
    time.sleep(0.5)


def set_avatar_and_save(hwnd, kind: int) -> None:
    choose_page(hwnd, 0)
    scroll_settings(hwnd)
    op.click_relative(hwnd, 150, 464)
    if kind == 1:
        # Currently 3D: one actual Up key selects the preceding 2D option.
        pyautogui.press("up")
    else:
        # Clean profile: advance the choices from "미정" to 3D.
        pyautogui.press("home")
        pyautogui.press("down", presses=kind, interval=0.12)
    pyautogui.press("enter")
    time.sleep(0.2)
    op.snap(f"21_avatar_choice_{kind}", hwnd)
    op.click_relative(hwnd, 765, 590)
    time.sleep(0.65)


def main() -> None:
    exe = Path("dist/AISTING.exe").resolve()
    assert exe.is_file(), "Current Windows EXE missing"
    isolation = Path(os.environ.get("RUNNER_TEMP", ".")) / "aisting_extra_gui_operator"
    isolation.mkdir(parents=True, exist_ok=True)
    os.environ["LOCALAPPDATA"] = str(isolation)
    target = isolation / "AISTING" / "settings.json"
    assert not target.exists(), "Expected clean synthetic Windows profile"
    process = subprocess.Popen([str(exe)], env=os.environ.copy())
    hwnd = None
    try:
        hwnd = op.await_window()["hwnd"]
        time.sleep(2)
        set_avatar_and_save(hwnd, 2)  # 3D (VRM) in the readonly avatar choices
        assert target.is_file(), "Clicking save on 3D settings did not create settings"
        settings3d = json.loads(target.read_text(encoding="utf-8"))
        assert settings3d["avatar"] == "3d", settings3d["avatar"]
        choose_page(hwnd, 3)
        op.snap("22_real_3d_avatar_placeholder", hwnd)
        scroll_settings(hwnd)
        op.snap("23_real_3d_avatar_capture_disabled_visible", hwnd)
        op.click_relative(hwnd, 120, 523)
        time.sleep(0.65)
        assert not [w for w in op.windows() if "아바타 · 로컬 창 캡처용" in w["title"]], \
            "3D option must not launch a disguised 2D preview capture window"
        print("OPERATOR EXTRA PASS 3D selected/saved; unsupported 3D does not open a 2D popout", flush=True)

        set_avatar_and_save(hwnd, 1)  # restore intended 2D
        settings2d = json.loads(target.read_text(encoding="utf-8"))
        assert settings2d["avatar"] == "2d", settings2d["avatar"]
        assert settings2d["platforms"] == settings3d["platforms"]
        assert settings2d["persona"] == settings3d["persona"]
        print("OPERATOR EXTRA PASS changed and resaved avatar, preserved unrelated preferences", flush=True)

        choose_page(hwnd, 2)  # Windows voice preview tab
        op.snap("24_real_windows_voice_tab", hwnd)
        print("OPERATOR EXTRA Windows voice tab visible; no sound played", flush=True)
    except BaseException:
        if hwnd is not None and op.u32.IsWindow(hwnd):
            try:
                op.snap("FAILED_extra_windows_operator", hwnd)
                pyautogui.screenshot().save(op.OUTPUT / "FAILED_extra_desktop.png")
            except Exception:
                pass
        raise
    finally:
        if hwnd is not None and op.u32.IsWindow(hwnd):
            op.u32.PostMessageW(hwnd, op.WM_CLOSE, 0, 0)
        try:
            process.wait(timeout=18)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
            raise AssertionError("Additional Windows operator run did not close")
        assert process.returncode == 0, f"Unexpected EXE close code: {process.returncode}"

    print("OPERATOR EXTRA PASS all actual Windows user actions, normal GUI exit", flush=True)


if __name__ == "__main__":
    main()
