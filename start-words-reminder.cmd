@echo off
REM Launcher for simple-word-memory (see README.md).
REM Prefers the local .venv if it exists, otherwise falls back to the system Python.
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" main.py
    endlocal
    exit /b 0
)

where python >nul 2>&1
if errorlevel 1 (
    echo Python was not found on PATH. Install Python 3.11 or later and try again.
    pause
    exit /b 1
)

echo No .venv found. Creating one and installing dependencies...
python -m venv .venv
if errorlevel 1 (
    echo Failed to create the virtual environment.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" main.py
endlocal
