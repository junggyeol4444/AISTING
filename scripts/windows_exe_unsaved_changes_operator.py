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


def read_field(hwnd, y):
    pyperclip.copy("UNCHANGED-CLIPBOARD")
    op.click_relative(hwnd, 350, y)
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
        paste(hwnd, 350, 550, "SAVED-STYLE-TEST")
        paste(hwnd, 350, 580, "SAVED-CHARACTER-TEST")
        scroll_to_save(hwnd)
        op.snap("41_setting_saved_by_user", hwnd)
        op.click_relative(hwnd, 200, 379)  # Commit character once.
        time.sleep(0.65)
        op.click_relative(hwnd, 765, 590)
        time.sleep(0.85)
        assert config.is_file(), "User explicitly clicked Save but no file exists"
        original_bytes = config.read_bytes()
        saved = json.loads(original_bytes.decode("utf-8"))
        assert saved["persona"] == {
            "name": "SAVED-PERSONA-TEST",
            "style": "SAVED-STYLE-TEST",
            "character": "SAVED-CHARACTER-TEST",
        }, saved["persona"]
        assert saved["persona_mode"] == "custom"
        print("UNSAVED PASS 1: actual Save button stored original persona", flush=True)
        close(process, hwnd)
        process = hwnd = None

        process, hwnd = start(exe, env, "42_reopened_existing_saved_user")
        for y, expected in ((524, "SAVED-PERSONA-TEST"), (550, "SAVED-STYLE-TEST"),
                            (580, "SAVED-CHARACTER-TEST")):
            assert read_field(hwnd, y) == expected, f"Initial EXE relaunch lost character at y={y}"
        paste(hwnd, 350, 524, "MUST-NOT-BE-SAVED")
        paste(hwnd, 350, 550, "UNSAVED-STYLE")
        paste(hwnd, 350, 580, "UNSAVED-CHARACTER")
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
        op.snap("45_previous_saved_persona_restored", hwnd)
        for y, expected in ((524, "SAVED-PERSONA-TEST"), (550, "SAVED-STYLE-TEST"),
                            (580, "SAVED-CHARACTER-TEST")):
            actual = read_field(hwnd, y)
            assert actual == expected, f"Unsaved character edit leaked on restart: {actual!r}"
        assert config.read_bytes() == original_bytes
        print("UNSAVED PASS 4: second restart restored all three saved character fields", flush=True)

        # The operator may save broadcast settings WITHOUT accepting a character draft.
        paste(hwnd, 350, 524, "DRAFT-NAME-NOT-COMMITTED")
        paste(hwnd, 350, 550, "DRAFT-STYLE-NOT-COMMITTED")
        paste(hwnd, 350, 580, "DRAFT-PERSONALITY-NOT-COMMITTED")
        op.click_relative(hwnd, 52, 210)  # Chzzk preference is the only requested change
        scroll_to_save(hwnd)
        op.snap("46_general_save_while_character_draft_is_uncommitted", hwnd)
        op.click_relative(hwnd, 765, 590)  # ordinary Save, NOT character confirmation
        time.sleep(0.85)
        after_general = json.loads(config.read_text(encoding="utf-8"))
        assert after_general["persona"] == saved["persona"], \
            "General Save silently committed unconfirmed character name/style/personality"
        assert after_general["persona_mode"] == "custom"
        assert after_general["platforms"] == ["chzzk"], after_general["platforms"]
        print("UNSAVED PASS 5: ordinary Windows Save preserves committed identity", flush=True)
        close(process, hwnd)
        process = hwnd = None

        process, hwnd = start(exe, env, "47_restart_after_broadcast_settings_save")
        for y, expected in ((524, "SAVED-PERSONA-TEST"), (550, "SAVED-STYLE-TEST"),
                            (580, "SAVED-CHARACTER-TEST")):
            assert read_field(hwnd, y) == expected, \
                f"Broadcast Save changed character shown by EXE after restart y={y}"

        # The explicit character button is the ONLY operation that changes identity.
        paste(hwnd, 350, 524, "CONFIRMED-SECOND-NAME")
        paste(hwnd, 350, 550, "CONFIRMED-SECOND-STYLE")
        paste(hwnd, 350, 580, "CONFIRMED-SECOND-PERSONALITY")
        scroll_to_save(hwnd)
        op.snap("48_explicit_character_change_before_confirmation", hwnd)
        op.click_relative(hwnd, 200, 379)  # explicit character Save
        time.sleep(0.85)
        confirmed = json.loads(config.read_text(encoding="utf-8"))
        assert confirmed["persona"] == {
            "name": "CONFIRMED-SECOND-NAME",
            "style": "CONFIRMED-SECOND-STYLE",
            "character": "CONFIRMED-SECOND-PERSONALITY",
        }, confirmed["persona"]
        assert confirmed["platforms"] == ["chzzk"]
        print("UNSAVED PASS 6: explicit character confirmation changes all three fields", flush=True)
        close(process, hwnd)
        process = hwnd = None

        process, hwnd = start(exe, env, "49_reopened_confirmed_character")
        for y, expected in ((524, "CONFIRMED-SECOND-NAME"), (550, "CONFIRMED-SECOND-STYLE"),
                            (580, "CONFIRMED-SECOND-PERSONALITY")):
            assert read_field(hwnd, y) == expected, \
                f"Confirmed character was lost on another Windows EXE restart y={y}"
        assert json.loads(config.read_text(encoding="utf-8")) == confirmed
        op.snap("50_explicit_identity_edit_persists_after_restart", hwnd)
        print("UNSAVED PASS 7: edited character survives Windows EXE quit/restart", flush=True)
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
