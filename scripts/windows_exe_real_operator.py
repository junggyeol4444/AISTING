"""Windows EXE black-box operator probe using mouse, keyboard and real screenshots.

No imported AISTING modules and no calls to app callbacks. This is deliberately
an EXTERNAL process interacting with an EXE as a human would.
Only synthetic local user preferences and scripted chat are used.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pyautogui

OUTPUT = Path("operator_e2e_evidence")
OUTPUT.mkdir(exist_ok=True)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.25

u32 = ctypes.windll.user32
WM_CLOSE = 0x0010


def windows():
    results = []
    fn_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def each(hwnd, unused):
        if not u32.IsWindowVisible(hwnd):
            return True
        length = u32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        u32.GetWindowTextW(hwnd, buf, length + 1)
        if "AISTING" in buf.value.upper():
            rect = ctypes.wintypes.RECT()
            u32.GetWindowRect(hwnd, ctypes.byref(rect))
            results.append({"hwnd": int(hwnd), "title": buf.value,
                            "rect": (rect.left, rect.top, rect.right, rect.bottom)})
        return True

    cb = fn_type(each)
    u32.EnumWindows(cb, 0)
    return results


def await_window(timeout=60):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        ws = windows()
        for w in ws:
            if "오프라인 AI 방송인" in w["title"]:
                return w
        time.sleep(0.5)
    raise AssertionError("EXE main GUI not found after launch; windows=" + repr(windows()))


def client_area(hwnd):
    rect = ctypes.wintypes.RECT()
    u32.GetClientRect(hwnd, ctypes.byref(rect))
    p = ctypes.wintypes.POINT(0, 0)
    u32.ClientToScreen(hwnd, ctypes.byref(p))
    return (p.x, p.y, rect.right, rect.bottom)


def snap(label, hwnd):
    bounds = client_area(hwnd)
    pyautogui.screenshot(region=bounds).save(OUTPUT / (label + ".png"))
    print("SCREENSHOT", label, bounds, flush=True)
    return bounds


def click_relative(hwnd, x, y):
    left, top, w, h = client_area(hwnd)
    assert 0 < x < w and 0 < y < h, (x, y, w, h)
    pyautogui.click(left + x, top + y)


def main():
    import pyperclip
    exe = Path("dist/AISTING.exe").resolve()
    assert exe.exists(), str(exe)
    isolation = Path(os.environ.get("RUNNER_TEMP", ".")) / "aisting_window_operator_e2e"
    isolation.mkdir(parents=True, exist_ok=True)
    os.environ["LOCALAPPDATA"] = str(isolation)
    print("EXE", exe, "isolated_data", isolation, flush=True)
    process = subprocess.Popen([str(exe)], env=os.environ.copy())
    hwnd = None
    try:
        w = await_window()
        hwnd = w["hwnd"]
        time.sleep(2.5)  # Wait until the EXE has populated the Tk notebook and settings.
        print("WINDOW", json.dumps(w, ensure_ascii=False), flush=True)
        x, y, width, height = snap("01_first_open_ready", hwnd)
        assert width >= 760 and height >= 625
        # Actual mouse clicks, keyboard selection and Ctrl+V; no app-internal method calls.
        click_relative(hwnd, 50, 210)  # Chzzk
        click_relative(hwnd, 50, 231)  # YouTube
        click_relative(hwnd, 150, 363) # Content combo: navigate to "수다 + 게임"
        pyautogui.press("home")
        pyautogui.press("down", presses=3, interval=0.15)
        pyautogui.press("enter")
        click_relative(hwnd, 150, 496) # Persona combo: navigate to "직접 만들기"
        pyautogui.press("home")
        pyautogui.press("down")
        pyautogui.press("enter")
        for y_pos, txt in ((524, "WINDOWS-OPERATOR"), (550, "E2E-SPEAKING"), (580, "E2E-CHARACTER")):
            click_relative(hwnd, 350, y_pos)
            pyautogui.hotkey("ctrl", "a")
            pyperclip.copy(txt)
            pyautogui.hotkey("ctrl", "v")
        time.sleep(0.7)
        snap("02_settings_interacted", hwnd)
        left, top, _, _ = client_area(hwnd)
        pyautogui.moveTo(left + 650, top + 430)
        pyautogui.scroll(-10)
        time.sleep(0.7)
        snap("03_after_user_mousewheel", hwnd)
        from PIL import Image, ImageChops
        earlier = Image.open(OUTPUT / "02_settings_interacted.png").convert("RGB")
        later = Image.open(OUTPUT / "03_after_user_mousewheel.png").convert("RGB")
        diff = ImageChops.difference(earlier, later).convert("L")
        pixels_changed = sum(1 for val in diff.getdata() if val > 15)
        print("MOUSEWHEEL_CHANGED_PIXELS", pixels_changed, flush=True)
        if pixels_changed < 6000:
            print("MOUSEWHEEL INPUT NOT OBSERVED; probing native WM_MOUSEWHEEL separately", flush=True)
            delta_hi = ((-120) & 0xFFFF) << 16
            pointer = (((top + 430) & 0xFFFF) << 16) | ((left + 650) & 0xFFFF)
            u32.SendMessageW(hwnd, 0x020A, delta_hi, pointer)
            time.sleep(0.5)
            snap("03b_after_native_windows_wheel_message", hwnd)
            latest = Image.open(OUTPUT / "03b_after_native_windows_wheel_message.png").convert("RGB")
            pixels_changed = sum(1 for val in ImageChops.difference(later, latest).convert("L").getdata() if val > 15)
            print("NATIVE_WM_MOUSEWHEEL_CHANGED_PIXELS", pixels_changed, flush=True)
        print("MOUSEWHEEL_INTERACTIVE_VERIFIED", pixels_changed > 6000, flush=True)
        pyautogui.moveTo(left + 835, top + 350)
        pyautogui.dragTo(left + 835, top + 610, duration=1.2)
        time.sleep(0.6)
        snap("04_settings_scrolled_by_scrollbar", hwnd)
        click_relative(hwnd, 200, 103)
        pyautogui.press("home")
        pyautogui.press("down")
        pyautogui.press("enter")
        time.sleep(1)
        snap("05_rehearsal_tab_via_real_navigation", hwnd)
        print("OPERATOR PROBE 2: mouse checks, keyboard selects, typed inputs, wheel/scrollbar, navigation. Inspect screenshots for real outcomes.", flush=True)
    finally:
        if hwnd:
            u32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        try:
            process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        print("SHUTDOWN PROBE", process.poll(), flush=True)


if __name__ == "__main__":
    main()
