@echo off
setlocal
cd /d "%~dp0"
rem Build the EXISTING AISTING native Windows GUI, not a website.
rem Never install dependencies or overwrite the user's previous EXE.
rem CI may select its isolated Python; manual Windows builds keep py -3.
if not defined AISTING_PYTHON set "AISTING_PYTHON=py -3"
%AISTING_PYTHON% -c "import tkinter, PyInstaller, webview" >nul 2>&1
if errorlevel 1 (
  echo Windows native build requires already installed Python, PyInstaller and pywebview.
  echo Nothing has been installed or downloaded. Existing EXE is preserved.
  exit /b 1
)
if not exist "src\ai_broadcaster\desktop.py" (
  echo Existing AISTING desktop.py is missing. Build cancelled.
  exit /b 1
)
if not exist "src\ai_broadcaster\original_plan_frontend.py" (
  echo Integrated native Live2D module is missing. Build cancelled.
  exit /b 1
)
if not exist "scripts\run_desktop.py" (
  echo Existing Windows entrypoint is missing. Build cancelled.
  exit /b 1
)
set "BUILD_ID=%RANDOM%_%RANDOM%"
set "OUT=dist-native-%BUILD_ID%"
set "WORK=build-native-%BUILD_ID%"
if exist "%OUT%" (
  echo Output exists. No overwrite permitted.
  exit /b 1
)
if exist "%WORK%" (
  echo Working output exists. No overwrite permitted.
  exit /b 1
)
%AISTING_PYTHON% -m PyInstaller --onefile --windowed --name AISTING --paths src --collect-all webview --hidden-import clr --distpath "%OUT%" --workpath "%WORK%" --specpath "%WORK%" --add-data "%CD%\config;config" --add-data "%CD%\docs;docs" scripts\run_desktop.py
if errorlevel 1 (
  echo Build failed. Original program and previous EXEs were not overwritten.
  exit /b 1
)
if not exist "%OUT%\AISTING.exe" (
  echo PyInstaller reported success but AISTING.exe is missing.
  exit /b 1
)
rem Run the actual frozen Windows EXE without GUI, settings writes, network,
rem audio or broadcast. CMD needs START /WAIT for GUI-subsystem executables.
start "" /wait "%OUT%\AISTING.exe" --aisting-selftest
if errorlevel 1 (
  echo The built AISTING.exe failed its offline bundled-source and 100-step check.
  echo The file remains only in its new build folder. No prior EXE was overwritten.
  echo Do NOT treat this build as verified.
  exit /b 1
)
echo Native Windows EXE offline bundle check passed.
echo Built original AISTING Windows desktop program: %OUT%\AISTING.exe
echo The bundled WebView2 renderer still requires a compatible Windows Edge Runtime.
echo Real AI, TTS, Live2D and OBS operation must be verified separately.
exit /b 0
