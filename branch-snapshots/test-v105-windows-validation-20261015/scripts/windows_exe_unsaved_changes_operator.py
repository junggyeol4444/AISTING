"""Black-box real Windows EXE: one-time character, unsaved drafts, explicit edits.

Real desktop keyboard only, native widgets and screenshots. Isolated dummy data.
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
    exe = Path("dist/AISTING.exe").resolve()
    assert exe.is_file()
    profile = Path(os.environ.get("RUNNER_TEMP", ".")) / "aisting_unsaved_changes_user"
    config = profile / "AISTING" / "settings.json"
    assert not config.exists(), "Need a clean synthetic Windows profile"
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(profile)
    process = hwnd = None

    def start(label):
        nonlocal process, hwnd
        process = subprocess.Popen([str(exe)], env=env)
        hwnd = op.await_window(timeout=65)["hwnd"]
        time.sleep(1.8)
        op.snap(label, hwnd)

    def close():
        nonlocal process, hwnd
        op.close_app(process, hwnd)
        process = hwnd = None

    original = {"name": "SAVED-PERSONA-TEST", "style": "SAVED-STYLE-TEST",
                "character": "SAVED-CHARACTER-TEST"}
    draft = {"name": "UNSAVED-NAME", "style": "UNSAVED-STYLE",
             "character": "UNSAVED-CHARACTER"}
    confirmed = {"name": "CONFIRMED-SECOND-NAME", "style": "CONFIRMED-SECOND-STYLE",
                 "character": "CONFIRMED-SECOND-PERSONALITY"}
    try:
        start("40_operator_initial_character_setup")
        op.edit_character(hwnd, original, save=False)
        op.snap("41_real_unsaved_character_form", hwnd)
        assert not config.exists(), "Typing identity automatically saved settings"
        op.edit_character(hwnd, original, save=True)
        assert json.loads(config.read_text(encoding="utf-8"))["persona"] == original
        op.save_preferences(hwnd)
        saved_bytes = config.read_bytes()
        print("UNSAVED PASS 1 explicitly confirmed name/style/personality", flush=True)
        close()

        start("42_restarted_without_character_setup_prompts")
        assert op.read_character(hwnd) == original
        print("UNSAVED PASS 2 full EXE relaunch restored character fields", flush=True)
        op.edit_character(hwnd, draft, save=False)
        op.snap("43_unsaved_draft_isolated_on_character_page", hwnd)
        assert config.read_bytes() == saved_bytes
        op.go(hwnd, 1)
        pyautogui.press("space")  # modify platform checkbox, but do not Save
        close()
        assert config.read_bytes() == saved_bytes
        print("UNSAVED PASS 3 both draft and preferences discarded on exit", flush=True)

        start("44_restarted_after_unsaved_character_and_platform")
        assert op.read_character(hwnd) == original
        assert config.read_bytes() == saved_bytes
        op.snap("45_unchanged_character_restored", hwnd)
        op.edit_character(hwnd, draft, save=False)
        op.snap("46_character_draft_before_unrelated_settings_save", hwnd)
        op.go(hwnd, 1)
        pyautogui.press("space")  # change Chzzk selection
        op.save_preferences(hwnd)
        after_general = json.loads(config.read_text(encoding="utf-8"))
        assert after_general["persona"] == original, "General Save committed identity draft"
        assert after_general["persona_mode"] == "custom"
        assert after_general["platforms"] == ["chzzk"]
        print("UNSAVED PASS 4 settings Save did not change identity", flush=True)
        close()

        start("47_restarted_after_general_broadcast_save")
        assert op.read_character(hwnd) == original
        op.edit_character(hwnd, confirmed, save=False)
        op.snap("48_explicit_edit_before_character_confirmation", hwnd)
        assert json.loads(config.read_text(encoding="utf-8"))["persona"] == original
        op.edit_character(hwnd, confirmed, save=True)
        changed = json.loads(config.read_text(encoding="utf-8"))
        assert changed["persona"] == confirmed
        assert changed["platforms"] == ["chzzk"]
        print("UNSAVED PASS 5 explicit character Save changed only identity", flush=True)
        close()

        start("49_final_relaunch_confirmed_character")
        assert op.read_character(hwnd) == confirmed
        assert json.loads(config.read_text(encoding="utf-8")) == changed
        op.snap("50_final_saved_character_auto_restored", hwnd)
        print("UNSAVED PASS 6 confirmed name/style/personality survive EXE restart", flush=True)
        close()
    except Exception:
        try:
            if hwnd and op.u32.IsWindow(hwnd):
                op.snap("FAILED_unsaved_changes", hwnd)
            pyautogui.screenshot().save(op.OUTPUT / "FAILED_unsaved_changes_desktop.png")
        except Exception:
            pass
        raise
    finally:
        if process is not None:
            try:
                close()
            except Exception:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    print("REAL WINDOWS EXE PERSISTENT CHARACTER USER JOURNEY PASS", flush=True)


if __name__ == "__main__":
    main()
