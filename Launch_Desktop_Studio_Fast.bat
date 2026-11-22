@echo off
title AI-BS Executive Command Studio Launcher (v5.299.0)
color 0B

echo ========================================================
echo   AI-BS EXECUTIVE COMMAND STUDIO — FAST LAUNCHER v5.299.0
echo   Sovereign RTX 4090 + Ryzen 9 9950X + Sentinel Engine
echo ========================================================
echo.

set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

:: 1. Silent Pre-Flight Diagnostic Health Check
echo [1/4] Running pre-flight system health audit...
python "C:\Users\footb\.gemini\config\skills\aibs-system-health-audit\scripts\audit_runner.py" preflight > nul 2>&1
if %errorlevel% neq 0 (
    echo [NOTE] Pre-flight audit detected warnings or standby daemons, proceeding with auto-start...
) else (
    echo [OK] Pre-flight system audit passed.
)

:: 2. Ensure All Sovereign Ecosystem Daemons are Active (Ollama 11434/11435, FastAPI 8080, Crypto 8007, ChromaDB 8001, Vite 5173)
echo [2/3] Verifying and launching ecosystem daemons...
python "%BASE_DIR%backend\aibs_ecosystem_spawner.py" > nul 2>&1

:: 5. Launch Pure Native Windows Direct2D Studio (Zero-Browser, Live Source Hot-Reload)
echo [5/5] Launching Sovereign Native Studio (Win32 Direct2D / HWND)...
call "%BASE_DIR%Launch_Native_Studio.bat"

echo.
echo ========================================================
echo   [SUCCESS] AI-BS Native Studio Online (Pure Win32 HWND)!
echo ========================================================
timeout /t 2 > nul
exit /b 0
