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
            if w["title"].startswith("AISTING |"):
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



def go(hwnd, number):
    assert 1 <= number <= 5
    u32.SetForegroundWindow(hwnd)
    pyautogui.hotkey("ctrl", str(number))
    time.sleep(0.45)


def type_focused(value):
    import pyperclip
    pyperclip.copy(value)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "v")


def copy_focused():
    import pyperclip
    pyperclip.copy("BEFORE-READ")
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.2)
    return pyperclip.paste()


def read_character(hwnd):
    go(hwnd, 2)
    pyautogui.press("tab")
    data = {}
    for key in ("name", "style", "character"):
        data[key] = copy_focused()
        if key != "character":
            pyautogui.press("tab")
    return data


def edit_character(hwnd, identity, save=True):
    go(hwnd, 2)
    pyautogui.press("home")
    pyautogui.press("down")  # choose custom persona on the visible readonly combobox
    pyautogui.press("enter")
    pyautogui.press("tab")
    for index, key in enumerate(("name", "style", "character")):
        type_focused(identity[key])
        if index < 2:
            pyautogui.press("tab")
    if save:
        pyautogui.hotkey("ctrl", "enter")  # dedicated character Save, not settings Save
        time.sleep(0.65)


def save_preferences(hwnd):
    go(hwnd, 1)
    pyautogui.hotkey("ctrl", "s")
    time.sleep(0.65)


def choose_avatar(hwnd, down):
    go(hwnd, 1)  # focus first native platform checkbox
    pyautogui.press("tab", presses=4)  # next 2 platforms, content, avatar
    pyautogui.press("home")
    if down:
        pyautogui.press("down", presses=down, interval=0.12)
    pyautogui.press("enter")


def close_app(process, hwnd):
    if hwnd is not None and u32.IsWindow(hwnd):
        u32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    try:
        process.wait(timeout=18)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        raise AssertionError("Windows EXE did not close")
    assert process.returncode == 0, process.returncode


def native_wheel(hwnd, steps=30):
    left, top, _, _ = client_area(hwnd)
    pyautogui.moveTo(left + 650, top + 350)
    data = ((-120 * steps) & 0xFFFF) << 16
    location = (((top + 350) & 0xFFFF) << 16) | ((left + 650) & 0xFFFF)
    u32.SendMessageW(hwnd, 0x020A, data, location)
    time.sleep(0.55)


def main():
    """Black-box Windows EXE, native keyboard and mouse, disposable local profile."""
    from PIL import Image, ImageChops

    exe = Path("dist/AISTING.exe").resolve()
    assert exe.is_file()
    root = Path(os.environ.get("RUNNER_TEMP", ".")) / "aisting_window_operator_e2e"
    settings_path = root / "AISTING" / "settings.json"
    assert not settings_path.exists(), "Synthetic user profile must be clean"
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(root)
    identity = {"name": "WINDOWS-OPERATOR", "style": "E2E-SPEAKING",
                "character": "E2E-CHARACTER"}
    process = hwnd = None

    def start(label):
        nonlocal process, hwnd
        process = subprocess.Popen([str(exe)], env=env)
        hwnd = await_window(timeout=65)["hwnd"]
        time.sleep(2)
        w = snap(label, hwnd)[2]
        assert w >= 820, "Windows GUI is too narrow for navigation"
        print("OPERATOR PASS new Windows EXE process", flush=True)

    def stop():
        nonlocal process, hwnd
        close_app(process, hwnd)
        process = hwnd = None

    try:
        start("01_operator_home_not_developer_tab_strip")
        edit_character(hwnd, identity, save=False)
        snap("02_character_unsaved_draft_on_dedicated_page", hwnd)
        assert not settings_path.exists(), "Typing unsaved persona wrote settings"
        edit_character(hwnd, identity)
        assert settings_path.exists()
        assert json.loads(settings_path.read_text(encoding="utf-8"))["persona"] == identity
        print("OPERATOR PASS explicit character identity creation", flush=True)

        go(hwnd, 1)
        pyautogui.press("space")  # Chzzk checkbox
        pyautogui.press("tab")
        pyautogui.press("space")  # YouTube checkbox
        pyautogui.press("tab", presses=2)  # Twitch -> content combo
        pyautogui.press("home")
        pyautogui.press("down", presses=3, interval=0.12)  # content both
        pyautogui.press("enter")
        pyautogui.press("tab")  # avatar combo
        pyautogui.press("home")
        pyautogui.press("down")  # 2D
        pyautogui.press("enter")
        pyautogui.press("tab")  # voice combo
        pyautogui.press("home")
        pyautogui.press("down")  # Windows voice
        pyautogui.press("enter")
        save_preferences(hwnd)
        saved = json.loads(settings_path.read_text(encoding="utf-8"))
        assert saved["persona"] == identity, saved
        assert saved["platforms"] == ["chzzk", "youtube"], saved
        assert saved["content"] == "both" and saved["avatar"] == "2d"
        assert saved["voice"] == "windows_system"
        for flag in ("streaming_enabled", "external_publish_enabled", "scheduled_execution"):
            assert saved[flag] is False
        snap("03_settings_saved_without_reentering_character", hwnd)
        stop()

        start("04_relaunched_same_windows_exe")
        assert read_character(hwnd) == identity, "Windows restart failed to restore name/style/character"
        snap("05_restored_character_without_retyping", hwnd)
        print("OPERATOR PASS persisted character after full EXE restart", flush=True)

        go(hwnd, 3)  # visible keyboard navigation to chat, script focused
        type_focused("ALICE: HELLO\nALICE: HELLO\nBOB: LAST")
        snap("06_chat_user_typed_three_messages", hwnd)
        pyautogui.press("tab", presses=3)  # mode -> model -> queue
        pyautogui.press("space")
        pyautogui.press("tab")  # Run all
        snap("07_chat_enqueued_before_clicking_run", hwnd)
        before = Image.open(OUTPUT / "07_chat_enqueued_before_clicking_run.png").convert("RGB")
        pyautogui.press("space")
        time.sleep(1.8)
        snap("08_chat_replied_after_real_keyboard_button", hwnd)
        after = Image.open(OUTPUT / "08_chat_replied_after_real_keyboard_button.png").convert("RGB")
        changed = sum(v > 12 for v in ImageChops.difference(before, after).convert("L").getdata())
        assert changed > 350, "No visible Windows reply after real Run button"
        print("OPERATOR PASS three-scripted-message GUI response", changed, flush=True)

        go(hwnd, 3)
        pyautogui.press("tab", presses=5)  # new rehearsal button
        pyautogui.press("space")
        go(hwnd, 3)
        type_focused("INVALID CHAT WITHOUT COLON")
        pyautogui.press("tab", presses=3)
        pyautogui.press("space")
        time.sleep(0.6)
        pyautogui.screenshot().save(OUTPUT / "09_native_invalid_script_warning.png")
        assert u32.FindWindowW(None, "대본 형식"), "Malformed chat did not show a native warning"
        pyautogui.press("enter")
        go(hwnd, 3)
        type_focused("BOB: RECOVERED")
        pyautogui.press("tab", presses=3)
        pyautogui.press("space")
        pyautogui.press("tab")
        pyautogui.press("space")
        time.sleep(1)
        snap("10_chat_recovered_after_invalid_user_script", hwnd)
        print("OPERATOR PASS native invalid-chat warning and recovery", flush=True)

        go(hwnd, 5)  # avatar page, opening button focused
        native_wheel(hwnd)
        snap("11_avatar_window_control_visible", hwnd)
        pyautogui.press("space")
        time.sleep(0.8)
        popups = [w for w in windows() if "아바타 · 로컬 창 캡처용" in w["title"]]
        assert len(popups) == 1, "User keyboard did not open exactly one 2D avatar window"
        pyautogui.screenshot().save(OUTPUT / "12_native_2d_avatar_popout.png")
        u32.PostMessageW(popups[0]["hwnd"], WM_CLOSE, 0, 0)
        time.sleep(0.5)
        assert u32.IsWindow(hwnd), "Avatar-only close terminated main EXE"
        go(hwnd, 5)
        pyautogui.hotkey("shift", "tab")  # mouth demo checkbox
        pyautogui.press("space")
        frames = []
        for _ in range(8):
            frames.append(pyautogui.screenshot(region=client_area(hwnd)).convert("RGB"))
            time.sleep(0.16)
        delta = max((sum(v > 20 for v in ImageChops.difference(frames[0], other).convert("L").getdata())
                     for other in frames[1:]), default=0)
        snap("13_avatar_mouth_demo_enabled", hwnd)
        assert delta > 45, "Visible avatar demo mouth did not animate"
        print("OPERATOR PASS 2D avatar popout/close + animation", delta, flush=True)
        stop()
        assert json.loads(settings_path.read_text(encoding="utf-8")) == saved
        print("OPERATOR FULL REAL-WINDOWS-EXE JOURNEY PASS", flush=True)
    except Exception:
        try:
            if hwnd and u32.IsWindow(hwnd):
                snap("FAILED_REAL_USER_STEP", hwnd)
            pyautogui.screenshot().save(OUTPUT / "FAILED_FULL_DESKTOP.png")
        except Exception:
            pass
        raise
    finally:
        if process is not None:
            try:
                stop()
            except Exception:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)


if __name__ == "__main__":
    main()
