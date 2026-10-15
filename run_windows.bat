@echo off
cd /d "%~dp0"
py -3 scripts\run_desktop.py
if errorlevel 1 (
  echo Python 3.11+ or tkinter is required to start the source GUI.
  pause
)
