@echo off
title AI-BS Sovereign Studio Launcher
color 0B

echo ===================================================
echo     AI-BS SOVEREIGN NATIVE STUDIO (WIN32 PURE)
echo     Windows 10/11 x64 Direct2D / DirectX GUI
echo ===================================================
echo.

set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

:: Set PYTHONPATH to include project root and native_studio
set "PYTHONPATH=%BASE_DIR%;%BASE_DIR%native_studio;%BASE_DIR%backend"

echo [1/2] Ensuring all sovereign ecosystem daemons are active (Ollama, FastAPI, Crypto, ChromaDB, Vite)...
start "" /B "%BASE_DIR%pyppeteer_env\Scripts\python.exe" -m backend.aibs_ecosystem_spawner

echo [2/2] Launching AI-BS Sovereign Studio (Pure Win32 HWND Engine)...
start "" "%BASE_DIR%pyppeteer_env\Scripts\python.exe" "%BASE_DIR%native_studio\app.py"

echo [SUCCESS] Studio running directly in native Windows RAM!
timeout /t 2 > nul
exit /b 0
