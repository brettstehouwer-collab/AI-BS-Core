@echo off
echo [Bootloader] Initializing AI-BS Master Ecosystem...

cd /d "%~dp0"

IF EXIST "..\pyppeteer_env" (
    echo [Bootloader] Activating primary virtual environment (pyppeteer_env)...
    call "..\pyppeteer_env\Scripts\activate.bat"
) ELSE (
    IF NOT EXIST ".venv" (
        echo [Bootloader] Creating virtual environment...
        python -m venv .venv
    )
    echo [Bootloader] Activating local virtual environment...
    call ".venv\Scripts\activate.bat"
)

echo [Bootloader] Installing dependencies...
pip install fastapi uvicorn > nul 2>&1

echo [Bootloader] Launching AI-BS Backend Server Architecture...
echo [Bootloader] Launching Real FastAPI Backend Router on Port 8000...
python "..\AI_BS_Backend.py"

