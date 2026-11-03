@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0release\OliveTable\OliveTable.exe" (
    start "" "%~dp0release\OliveTable\OliveTable.exe"
    exit /b
)
if exist "%~dp0.venv-gestures\Scripts\pythonw.exe" (
    start "" "%~dp0.venv-gestures\Scripts\pythonw.exe" "%~dp0run_menu.py"
    exit /b
)
echo Open BLUETOOTH_SETUP.md for the Python setup instructions.
echo The portable Windows application is in release\OliveTable when built.
pause
