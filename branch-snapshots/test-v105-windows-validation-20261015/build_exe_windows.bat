@echo off
cd /d "%~dp0"
py -3 -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo PyInstaller is not available on this Windows PC.
  echo Nothing has been installed or downloaded.
  echo After reviewing and approving the free build tool, install it manually.
  echo Then run this file again.
  pause
  exit /b 1
)
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name AISTING --paths src --add-data "config;config" --add-data "docs;docs" --add-data "logs\STAGE100_FINAL_VALIDATION.txt;logs" --add-data "logs\STAGE100_UNITTEST.log;logs" scripts\run_desktop.py
if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)
echo Created dist\AISTING.exe
pause
