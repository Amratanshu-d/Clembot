@echo off
setlocal enabledelayedexpansion

REM ── Always run from the folder this .bat lives in ──────────────────────────
cd /d "%~dp0"

title Clembot - Windows Voice Assistant
echo ============================================================
echo   Starting Clembot - Powerful Windows Voice Assistant
echo ============================================================
echo Working directory: %CD%

REM ── Activate virtual environment if present ────────────────────────────────
if exist "%~dp0.venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment .venv...
    call "%~dp0.venv\Scripts\activate.bat"
) else if exist "%~dp0venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment venv...
    call "%~dp0venv\Scripts\activate.bat"
) else (
    echo [INFO] No virtual environment found, using system Python.
)

REM ── Confirm Python is available ────────────────────────────────────────────
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Python is not installed or not in PATH.
    echo         Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM ── Install / sync dependencies on first run ──────────────────────────────
if exist "%~dp0requirements.txt" (
    if not exist "%~dp0.deps_installed" (
        echo [INFO] Installing dependencies on first run...
        python -m pip install -r "%~dp0requirements.txt" --quiet
        if !ERRORLEVEL! EQU 0 (
            echo installed > "%~dp0.deps_installed"
            echo [INFO] Dependencies installed successfully.
        ) else (
            echo [WARN] Some dependencies may have failed to install.
        )
    )
)

REM ── Doctor / diagnostic mode ───────────────────────────────────────────────
if /i "%1"=="--doctor" goto :doctor
if /i "%1"=="doctor"   goto :doctor
goto :run

:doctor
python -m app.doctor
pause
exit /b 0

:run
REM ── Launch Clembot ─────────────────────────────────────────────────────────
echo Launching Clembot GUI and IPC Bridge...
python -m app.main %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NOTICE] Clembot exited with code %ERRORLEVEL%.
    echo          Run run_clembot.bat --doctor to diagnose issues.
    pause
)
endlocal
