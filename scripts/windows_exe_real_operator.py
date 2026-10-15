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
    """Perform a complete black-box user journey on the real frozen Windows EXE."""
    import pyperclip
    from PIL import Image, ImageChops

    exe = Path("dist/AISTING.exe").resolve()
    assert exe.exists(), str(exe)
    isolation = Path(os.environ.get("RUNNER_TEMP", ".")) / "aisting_window_operator_e2e"
    isolation.mkdir(parents=True, exist_ok=True)
    os.environ["LOCALAPPDATA"] = str(isolation)
    settings_file = isolation / "AISTING" / "settings.json"
    if settings_file.exists():
        raise AssertionError("Operator test requires a clean isolated local profile")
    print("EXE", exe, "isolated_data", isolation, flush=True)
    process = None
    hwnd = None

    def open_app(label):
        nonlocal process, hwnd
        process = subprocess.Popen([str(exe)], env=os.environ.copy())
        hwnd = await_window()["hwnd"]
        time.sleep(2.5)
        dims = snap(label, hwnd)
        assert dims[2] >= 760 and 625 <= dims[3] <= 720
        assert dims[1] + dims[3] <= pyautogui.size().height - 35, \
            "Bottom of GUI is obscured by Windows taskbar"
        print("OPERATOR PASS open real EXE", label, flush=True)

    def close_app():
        nonlocal process, hwnd
        if hwnd is not None and u32.IsWindow(hwnd):
            u32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        if process is not None:
            try:
                process.wait(timeout=18)
            except subprocess.TimeoutExpired:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
                raise AssertionError("AISTING did not exit after real Windows close request")
            assert process.returncode == 0, f"Unexpected EXE return code {process.returncode}"
        process, hwnd = None, None
        print("OPERATOR PASS Windows GUI close and EXE exit", flush=True)

    def select_combobox(x, y, down):
        click_relative(hwnd, x, y)
        pyautogui.press("home")
        pyautogui.press("down", presses=down, interval=0.13)
        pyautogui.press("enter")

    def paste_at(x, y, txt):
        click_relative(hwnd, x, y)
        pyautogui.hotkey("ctrl", "a")
        pyperclip.copy(txt)
        pyautogui.hotkey("ctrl", "v")

    def native_wheel(down_steps=10):
        left, top, _, _ = client_area(hwnd)
        pyautogui.moveTo(left + 650, top + 430)
        high_word = ((-120 * down_steps) & 0xFFFF) << 16
        pointer = (((top + 430) & 0xFFFF) << 16) | ((left + 650) & 0xFFFF)
        u32.SendMessageW(hwnd, 0x020A, high_word, pointer)
        time.sleep(0.6)

    def read_output_clipboard(x, y):
        pyperclip.copy("BEFORE-COPY-CHANGEME")
        click_relative(hwnd, x, y)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.6)
        return pyperclip.paste()

    try:
        open_app("01_first_launch_ready")
        # Click settings physically and select contents from readonly drop-downs.
        click_relative(hwnd, 50, 210)
        click_relative(hwnd, 50, 231)
        select_combobox(150, 363, 3)  # content: "수다 + 게임"
        select_combobox(150, 496, 1)  # "직접 만들기"
        for yy, txt in ((524, "WINDOWS-OPERATOR"), (550, "E2E-SPEAKING"), (580, "E2E-CHARACTER")):
            paste_at(350, yy, txt)
        snap("02_real_platform_content_persona_entry", hwnd)
        print("OPERATOR PASS clicked platform, content, character input", flush=True)

        before = Image.open(OUTPUT / "02_real_platform_content_persona_entry.png").convert("RGB")
        left, top, _, _ = client_area(hwnd)
        pyautogui.moveTo(left + 650, top + 430)
        pyautogui.scroll(-10)
        time.sleep(0.6)
        snap("03_mouse_wheel_library", hwnd)
        after = Image.open(OUTPUT / "03_mouse_wheel_library.png").convert("RGB")
        raw_change = sum(v > 15 for v in ImageChops.difference(before, after).convert("L").getdata())
        print("PYAUTOGUI_SCROLL_PIXEL_CHANGE", raw_change, flush=True)
        if raw_change < 5000:
            native_wheel(4)
            snap("03b_native_windows_wheel", hwnd)
            native_img = Image.open(OUTPUT / "03b_native_windows_wheel.png").convert("RGB")
            os_change = sum(v > 15 for v in ImageChops.difference(after, native_img).convert("L").getdata())
            assert os_change > 5000, "Windows WM_MOUSEWHEEL does not scroll real settings screen"
            print("OPERATOR PASS native Windows mouse-wheel event scrolls visible GUI", os_change, flush=True)
        else:
            print("OPERATOR PASS physical mouse-wheel injector scrolls visible GUI", raw_change, flush=True)

        # Scrollbar drag to bottom even on a small laptop screen.
        left, top, _, _ = client_area(hwnd)
        pyautogui.moveTo(left + 835, top + 350)
        pyautogui.dragTo(left + 835, top + 610, duration=0.8)
        snap("04_real_settings_bottom", hwnd)
        select_combobox(150, 464, 1)  # avatar 2D
        select_combobox(545, 473, 1)  # local Windows voice choice
        snap("05_real_avatar_and_voice_selection", hwnd)
        click_relative(hwnd, 766, 591) # actual bottom "설정 PC에 저장" button
        time.sleep(1)
        snap("06_clicked_save_button", hwnd)
        assert settings_file.is_file(), \
            "Clicked the visible save button but application did not create local settings"
        saved = json.loads(settings_file.read_text(encoding="utf-8"))
        expected = {"platforms": ["chzzk", "youtube"], "content": "both", "avatar": "2d",
                    "voice": "windows_system", "persona_mode": "custom"}
        for key, value in expected.items():
            assert saved[key] == value, f"Saved {key}: expected {value!r}, got {saved[key]!r}"
        assert saved["persona"] == {"name": "WINDOWS-OPERATOR", "style": "E2E-SPEAKING",
                                    "character": "E2E-CHARACTER"}, saved["persona"]
        for guard in ("streaming_enabled", "external_publish_enabled", "scheduled_execution"):
            assert saved[guard] is False, f"User selection unexpectedly enabled {guard}"
        print("OPERATOR PASS real Save button, original platform choices and character/voice/avatar stored", flush=True)
        close_app()

        # True app restart: spawn the same Windows EXE, with the same isolated profile.
        open_app("07_reopened_settings_after_real_exit")
        stored_name = read_output_clipboard(350, 524)
        assert stored_name == "WINDOWS-OPERATOR", \
            f"UI did not display the saved character name after restart: {stored_name!r}"
        snap("08_reopened_character_name_verified", hwnd)
        native_wheel(40)
        snap("09_reopened_avatar_and_voice", hwnd)
        print("OPERATOR PASS restore user-visible name and existing preferences after EXE restart", flush=True)

        # Navigate to chat by the operator's real drop-down, not app code APIs.
        select_combobox(200, 103, 1)
        time.sleep(0.5)
        snap("10_real_chat_tab_selected", hwnd)
        paste_at(300, 230, "ALICE: HELLO\nALICE: HELLO\nBOB: LAST")
        snap("11_user_entered_three_scripted_chats", hwnd)
        click_relative(hwnd, 79, 348)  # "대기열에 추가"
        time.sleep(0.5)
        snap("12_clicked_enqueue_three_chats", hwnd)
        click_relative(hwnd, 176, 348) # "모두 답변"
        # Wait for visible output; do not assume function success from timers.
        initial = Image.open(OUTPUT / "12_clicked_enqueue_three_chats.png").convert("RGB")
        changed = 0
        deadline = time.monotonic() + 18
        while time.monotonic() < deadline:
            time.sleep(0.6)
            current = pyautogui.screenshot(region=client_area(hwnd)).convert("RGB")
            area_before = initial.crop((30, 401, 829, 600))
            area_after = current.crop((30, 401, 829, 600))
            changed = sum(v > 18 for v in ImageChops.difference(area_before, area_after).convert("L").getdata())
            if changed > 2000:
                break
        snap("13_actual_chat_answer_visible", hwnd)
        assert changed > 2000, "After clicking Reply, real GUI output stayed blank"
        visible_text = read_output_clipboard(300, 455)
        print("OPERATOR GUI COPYING", repr(visible_text[:550]), flush=True)
        if "ALICE" not in visible_text or visible_text.count("HELLO") < 2 or "BOB" not in visible_text:
            raise AssertionError("Real GUI does not show distinct replies for duplicate chats")
        print("OPERATOR PASS three scripted chat replies including duplicate after real buttons", flush=True)

        click_relative(hwnd, 787, 350) # "새 연습"
        time.sleep(0.7)
        snap("14_click_new_rehearsal_reset", hwnd)
        cleared = read_output_clipboard(300, 455)
        assert "ALICE" not in cleared and "BOB" not in cleared, \
            "Real new rehearsal button did not clear completed chat history"
        print("OPERATOR PASS clickable reset cleared the real completed reply view", flush=True)

        # Malformed user script must show a modal warning, then recover.
        paste_at(300, 235, "INVALID CHAT WITHOUT COLON")
        click_relative(hwnd, 79, 348)
        time.sleep(0.7)
        pyautogui.screenshot().save(OUTPUT / "15_invalid_chat_warning_full_desktop.png")
        assert u32.FindWindowW(None, "대본 형식") != 0, \
            "Invalid operator input did not display an actual native warning dialog"
        pyautogui.press("enter")
        time.sleep(0.4)
        paste_at(300, 230, "BOB: RECOVERED")
        click_relative(hwnd, 79, 348)
        click_relative(hwnd, 176, 348)
        time.sleep(1.5)
        snap("16_after_invalid_chat_recovered", hwnd)
        recovered = read_output_clipboard(300, 455)
        assert "BOB: RECOVERED" in recovered and "ALICE: HELLO" not in recovered, \
            "Actual Windows GUI did not recover cleanly after invalid user text"
        print("OPERATOR PASS actual native invalid-input dialog and subsequent new reply", flush=True)
        # Check whether a normal user can even see the 2D avatar launch controls.
        # Rehearsal is notebook position 1; two Down keys select Avatar position 3.
        select_combobox(200, 103, 2)
        time.sleep(0.5)
        snap("17_actual_avatar_preview_screen", hwnd)
        native_wheel(28)
        snap("17b_avatar_scrolled_to_bottom_controls", hwnd)
        preview = Image.open(OUTPUT / "17_actual_avatar_preview_screen.png").convert("RGB")
        scrolled = Image.open(OUTPUT / "17b_avatar_scrolled_to_bottom_controls.png").convert("RGB")
        moved_pixels = sum(val > 15 for val in ImageChops.difference(preview, scrolled).convert("L").getdata())
        print("AVATAR_SCROLL_MOVED_PIXELS", moved_pixels, flush=True)
        assert moved_pixels > 6000, "Avatar tab has no usable scrolling to its hidden buttons"
        print("OPERATOR PASS Windows 768p avatar controls are reachable by scrolling", flush=True)

        # Open the actual pop-out via its on-screen mouse button, no app APIs.
        click_relative(hwnd, 120, 523)
        deadline = time.monotonic() + 9
        popout = None
        while time.monotonic() < deadline:
            child_windows = [w for w in windows() if "아바타 · 로컬 창 캡처용" in w["title"]]
            if child_windows:
                popout = child_windows[0]
                break
            time.sleep(0.25)
        assert popout is not None, "Clicking the real 2D avatar button did not open a Windows child window"
        pyautogui.screenshot().save(OUTPUT / "18_actual_avatar_popout_full_desktop.png")
        print("OPERATOR PASS user mouse click opened standalone native avatar window", popout, flush=True)

        # A second click must activate the existing window, not create duplicates.
        click_relative(hwnd, 120, 523)
        time.sleep(0.6)
        children = [w for w in windows() if "아바타 · 로컬 창 캡처용" in w["title"]]
        assert len(children) == 1, "Second click created duplicate avatar popout windows"
        print("OPERATOR PASS repeated avatar open click did not duplicate windows", flush=True)

        # Close only the avatar window through its OS window close command.
        assert u32.PostMessageW(popout["hwnd"], WM_CLOSE, 0, 0), "Avatar child WM_CLOSE could not be sent"
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            if not [w for w in windows() if "아바타 · 로컬 창 캡처용" in w["title"]]:
                break
            time.sleep(0.2)
        assert not [w for w in windows() if "아바타 · 로컬 창 캡처용" in w["title"]], \
            "Closing avatar window left a native Windows child process or window"
        assert u32.IsWindow(hwnd), "Closing only the avatar unexpectedly closed AISTING main window"
        snap("19_after_avatar_child_closed_main_window_preserved", hwnd)
        assert json.loads(settings_file.read_text(encoding="utf-8")) == saved, \
            "Opening/closing standalone avatar window changed saved user settings"
        print("OPERATOR PASS avatar-only close leaves main EXE and settings intact", flush=True)
        close_app()

        assert settings_file.is_file()
        assert json.loads(settings_file.read_text(encoding="utf-8")) == saved, \
            "Mock chatting unexpectedly corrupted user preferences"
        print("OPERATOR FULL REAL-WINDOWS-EXE JOURNEY PASS: launch, physical settings, save, restart, chat, duplicate, error recovery, close", flush=True)
    except Exception:
        if hwnd is not None and u32.IsWindow(hwnd):
            try:
                snap("FAILED_REAL_USER_STEP", hwnd)
                pyautogui.screenshot().save(OUTPUT / "FAILED_FULL_DESKTOP.png")
            except Exception:
                pass
        raise
    finally:
        if hwnd is not None or process is not None:
            try:
                close_app()
            except Exception as exc:
                print("CLEANUP WARNING", repr(exc), flush=True)


if __name__ == "__main__":
    main()
