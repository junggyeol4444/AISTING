"""Black-box frozen-Windows-EXE test of corrupted settings recovery.

Only synthetic data in RUNNER_TEMP. Interacts with real GUI controls and
a real native Windows messagebox, never with AISTING internal Python APIs.
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


def wait_window_title(title: str, *, timeout: float = 18.0) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        hwnd = int(op.u32.FindWindowW(None, title))
        if hwnd and op.u32.IsWindowVisible(hwnd):
            return hwnd
        time.sleep(0.15)
    raise AssertionError("Real Windows warning dialog not displayed: " + title)


def close_app(process: subprocess.Popen, hwnd: int) -> None:
    if hwnd and op.u32.IsWindow(hwnd):
        op.u32.PostMessageW(hwnd, op.WM_CLOSE, 0, 0)
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired as e:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        raise AssertionError("Frozen EXE failed to close after Windows window-close request") from e
    assert process.returncode == 0, ("Unexpected EXE exit code", process.returncode)


def main() -> None:
    exe = Path("dist/AISTING.exe").resolve()
    assert exe.is_file()
    temp = Path(os.environ.get("RUNNER_TEMP", ".")) / "aisting_corrupt_settings_user"
    settings = temp / "AISTING" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    original = b'{"platforms":["youtube"], "avatar": BAD_JSON'
    settings.write_bytes(original)

    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(temp)
    process = subprocess.Popen([str(exe)], env=env)
    hwnd = None
    try:
        hwnd = op.await_window(timeout=60)["hwnd"]
        message_window = wait_window_title("설정 복구")
        pyautogui.screenshot().save(op.OUTPUT / "30_invalid_settings_real_windows_warning.png")
        assert settings.read_bytes() == original, \
            "Opening GUI after corrupt settings must not silently overwrite original data"
        print("RECOVERY PASS: native Windows warning shown and original corrupt JSON preserved", flush=True)

        # Dismiss the warning as an ordinary Windows user.
        pyautogui.press("enter")
        time.sleep(0.7)
        assert not op.u32.IsWindow(message_window), "Warning dialog cannot be dismissed"
        op.snap("31_default_settings_after_warning", hwnd)

        # Explicitly let the user choose to replace the invalid file through Save.
        left, top, _, _ = op.client_area(hwnd)
        pyautogui.moveTo(left + 650, top + 430)
        high = ((-120 * 40) & 0xFFFF) << 16
        point = (((top + 430) & 0xFFFF) << 16) | ((left + 650) & 0xFFFF)
        op.u32.SendMessageW(hwnd, 0x020A, high, point)
        time.sleep(0.5)
        op.snap("32_after_user_scroll_to_save", hwnd)
        op.click_relative(hwnd, 765, 590)
        time.sleep(0.8)

        repaired_bytes = settings.read_bytes()
        assert repaired_bytes != original, "Clicking Save did not replace corrupt JSON"
        repaired = json.loads(repaired_bytes.decode("utf-8"))
        assert isinstance(repaired, dict)
        assert repaired["platforms"] == [], \
            "After invalid saved settings, safe defaults were not used"
        assert repaired["streaming_enabled"] is False
        assert repaired["external_publish_enabled"] is False
        print("RECOVERY PASS: user clicked real GUI Save; valid JSON and safe offline defaults persisted", flush=True)
        close_app(process, hwnd)
        hwnd = None
        process = None

        # Second fresh Windows EXE process should not show the old error again.
        process = subprocess.Popen([str(exe)], env=env)
        hwnd = op.await_window(timeout=60)["hwnd"]
        time.sleep(2)
        assert not op.u32.FindWindowW(None, "설정 복구"), \
            "App still reports corrupt settings after user saved repaired preferences"
        assert settings.read_bytes() == repaired_bytes, \
            "Reopening app modified saved user settings unexpectedly"
        op.snap("33_restarted_after_repair_no_warning", hwnd)
        print("RECOVERY PASS: full EXE restart has no warning and repaired settings remain byte-identical", flush=True)
    except BaseException:
        try:
            pyautogui.screenshot().save(op.OUTPUT / "FAILED_corrupt_settings_full_desktop.png")
        except Exception:
            pass
        raise
    finally:
        if process is not None:
            # Close possible startup modal before asking main window to exit.
            warning = op.u32.FindWindowW(None, "설정 복구")
            if warning:
                op.u32.PostMessageW(warning, op.WM_CLOSE, 0, 0)
            close_app(process, hwnd or 0)
    print("WINDOWS CORRUPT SETTINGS REAL-USER RECOVERY PASS", flush=True)


if __name__ == "__main__":
    main()
