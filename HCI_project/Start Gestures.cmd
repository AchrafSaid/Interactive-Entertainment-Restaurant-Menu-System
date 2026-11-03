@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv-gestures\Scripts\python.exe" (
    echo The gesture environment has not been set up.
    echo Run "Setup Gestures.cmd" first.
    pause
    exit /b 1
)
"%~dp0.venv-gestures\Scripts\python.exe" "%~dp0integrated_menu.py"
if errorlevel 1 pause
