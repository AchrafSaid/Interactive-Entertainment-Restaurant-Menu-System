@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv-gestures\Scripts\python.exe" (
    py -3.10 -m venv "%~dp0.venv-gestures"
    if errorlevel 1 (
        echo Install Python 3.10 with the Python launcher, then try again.
        pause
        exit /b 1
    )
)
"%~dp0.venv-gestures\Scripts\python.exe" -m pip install -r "%~dp0requirements-gestures.txt"
if errorlevel 1 (
    pause
    exit /b 1
)
echo Setup is complete. Open "Start Menu.cmd", or use "Start Gestures.cmd" for hand control.
pause
