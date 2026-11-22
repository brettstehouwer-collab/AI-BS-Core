@echo off
ECHO =================================================
ECHO  INITIALIZING AI-BS BACKEND SERVER
ECHO =================================================

REM Get the directory of this script to run from anywhere
set "SCRIPT_DIR=%~dp0"

REM Activate the virtual environment
ECHO [1/2] Activating Python virtual environment...
call "%SCRIPT_DIR%pyppeteer_env\Scripts\activate.bat"

IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Failed to activate virtual environment. Make sure it exists at '%SCRIPT_DIR%pyppeteer_env'.
    pause
    exit /b
)

ECHO [SUCCESS] Virtual environment activated.

REM Start the Clore.ai Hosting Agent Server (WSL2)
ECHO [2/3] Starting Clore.ai Hosting Agent Server in WSL2...
wsl.exe -d Ubuntu -u root systemctl start clore-hosting.service >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    ECHO [SUCCESS] Clore.ai hosting agent server is running.
) ELSE (
    ECHO [WARNING] Could not start clore-hosting.service in WSL2. Continuing...
)

REM Start the FastAPI server using uvicorn
ECHO [3/3] Starting FastAPI server on localhost:8000...
ECHO Launching AI_BS_Backend:app from backend directory...
cd /d "%SCRIPT_DIR%backend"
"%SCRIPT_DIR%pyppeteer_env\Scripts\python.exe" -m uvicorn AI_BS_Backend:app --host 0.0.0.0 --port 8000

echo.
ECHO Server stopped.
pause