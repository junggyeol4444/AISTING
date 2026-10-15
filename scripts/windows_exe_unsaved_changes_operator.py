"""Real frozen Windows EXE user journey: unsaved GUI edits must not persist.

All actions are desktop mouse/keyboard events. No app callbacks or imported app
modules. Uses a disposable GitHub runner profile, no real accounts or streaming.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time

import pyautogui
import pyperclip
import windows_exe_real_operator as op


def start(exe: Path, env: dict[str, str], name: str):
    process = subprocess.Popen([str(exe)], env=env)
    hwnd = op.await_window(timeout=65)["hwnd"]
    time.sleep(1.8)
    op.snap(name, hwnd)
    return process, hwnd


def close(process, hwnd):
    if op.u32.IsWindow(hwnd):
        op.u32.PostMessageW(hwnd, op.WM_CLOSE, 0, 0)
    process.wait(timeout=18)
    assert process.returncode == 0, "Windows GUI unexpectedly crashed on close"


def paste(hwnd, x, y, value):
    op.click_relative(hwnd, x, y)
    pyautogui.hotkey("ctrl", "a")
    pyperclip.copy(value)
    pyautogui.hotkey("ctrl", "v")


def scroll_to_save(hwnd):
    x, y, _, _ = op.client_area(hwnd)
    pyautogui.moveTo(x + 650, y + 430)
    # Native WM_MOUSEWHEEL reaches Tk even on Windows runner lacking a
    # physical mouse-wheel device. This is an OS event, not an app method.
    delta = ((-120 * 40) & 0xFFFF) << 16
    pos = (((y + 430) & 0xFFFF) << 16) | ((x + 650) & 0xFFFF)
    op.u32.SendMessageW(hwnd, 0x020A, delta, pos)
    time.sleep(0.6)


def read_name(hwnd):
    pyperclip.copy("UNCHANGED-CLIPBOARD")
    op.click_relative(hwnd, 350, 524)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.4)
    return pyperclip.paste()


def main():
    exe = Path("dist/AISTING.exe").resolve()
    assert exe.is_file()
    root = Path(os.environ.get("RUNNER_TEMP", ".")) / "aisting_unsaved_changes_user"
    config = root / "AISTING" / "settings.json"
    assert not config.exists(), "Synthetic user profile is not clean"
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(root)

    process = hwnd = None
    try:
        process, hwnd = start(exe, env, "40_initial_fresh_user")
        # Select custom persona with actual combo and type unique synthetic name.
        op.click_relative(hwnd, 148, 496)
        pyautogui.press("home")
        pyautogui.press("down")
        pyautogui.press("enter")
        paste(hwnd, 350, 524, "SAVED-PERSONA-TEST")
        scroll_to_save(hwnd)
        op.snap("41_setting_saved_by_user", hwnd)
        op.click_relative(hwnd, 765, 590)
        time.sleep(0.85)
        assert config.is_file(), "User explicitly clicked Save but no file exists"
        original_bytes = config.read_bytes()
        saved = json.loads(original_bytes.decode("utf-8"))
        assert saved["persona"]["name"] == "SAVED-PERSONA-TEST", saved["persona"]
        assert saved["persona_mode"] == "custom"
        print("UNSAVED PASS 1: actual Save button stored original persona", flush=True)
        close(process, hwnd)
        process = hwnd = None

        process, hwnd = start(exe, env, "42_reopened_existing_saved_user")
        assert read_name(hwnd) == "SAVED-PERSONA-TEST", \
            "Fresh EXE did not display previous saved custom persona"
        paste(hwnd, 350, 524, "MUST-NOT-BE-SAVED")
        op.click_relative(hwnd, 52, 210)  # modify Chzzk check without saving
        scroll_to_save(hwnd)
        op.snap("43_unsaved_changes_visible_before_exit", hwnd)
        assert config.read_bytes() == original_bytes, \
            "App persisted changes before user clicked Save"
        print("UNSAVED PASS 2: GUI changed without writing saved preferences", flush=True)
        close(process, hwnd)
        process = hwnd = None
        assert config.read_bytes() == original_bytes, \
            "Closing GUI silently saved modified settings"
        print("UNSAVED PASS 3: exit without Save preserved previous file byte-for-byte", flush=True)

        process, hwnd = start(exe, env, "44_reopened_after_unsaved_changes")
        recovered = read_name(hwnd)
        op.snap("45_previous_saved_persona_restored", hwnd)
        assert recovered == "SAVED-PERSONA-TEST", \
            f"Unsaved edit carried over after application restart: {recovered!r}"
        assert config.read_bytes() == original_bytes
        print("UNSAVED PASS 4: 2nd restart restored saved GUI name, discarded unsaved edits", flush=True)
        close(process, hwnd)
        process = hwnd = None
    except Exception:
        try:
            pyautogui.screenshot().save(op.OUTPUT / "FAILED_unsaved_changes_desktop.png")
        except Exception:
            pass
        raise
    finally:
        if process is not None:
            try:
                close(process, hwnd or 0)
            except Exception:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True
                )
    print("REAL WINDOWS EXE UNSAVED USER CHANGES PASS", flush=True)


if __name__ == "__main__":
    main()
