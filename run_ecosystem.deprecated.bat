@echo off
echo ===================================================
echo           AI-BS MATRIX LIVE BOOTLOADER
echo ===================================================
echo.
echo Starting FastAPI Backend Server...
start "FastAPI Backend" cmd /k "start.bat"

echo Starting Daemon Manager...
start "Daemon Manager" cmd /k "pyppeteer_env\Scripts\python.exe daemon_manager.py C:\AI-BS"

echo Starting Clore.ai Hosting Agent Server...
start "Clore Hosting Server" cmd /k "Start_Clore_Server.bat"

echo Starting Vite Frontend...
start "Vite Frontend" cmd /k "cd /d C:\AI-BS\frontend && npm run dev"

echo.
echo All systems launched! You can monitor them in their respective windows.
exit
