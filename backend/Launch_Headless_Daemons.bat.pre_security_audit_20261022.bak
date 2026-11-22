@echo off
if not exist "%~dp0logs" mkdir "%~dp0logs"

echo Clearing old logs...
type nul > "%~dp0logs\ollama.log"
type nul > "%~dp0logs\backend.log"
type nul > "%~dp0logs\remote_bridge.log"
type nul > "%~dp0logs\hunter.log"
type nul > "%~dp0logs\refactoring.log"

set OLLAMA_IGPU_ENABLE=1
netstat -ano | findstr :11434 >nul
if %errorlevel% neq 0 (
    start "" /b cmd /c "set OLLAMA_HOST=0.0.0.0:11434&& set OLLAMA_MODELS=E:\AI_BS_Resources\Ollama&& ollama serve > "%~dp0logs\ollama.log" 2>&1"
) else (
    echo [Ollama] Engine is already running natively on port 11434. > "%~dp0logs\ollama.log"
)
start "" /b cmd /c "cd /d %~dp0 && call .venv\Scripts\activate && python -u AI_BS_Backend.py > logs\backend.log 2>&1"
start "" /b cmd /c "cd /d %~dp0 && call .venv\Scripts\activate && python -u AI_BS_Remote_Backend.py > logs\remote_bridge.log 2>&1"
start "" /b cmd /c "cd /d %~dp0 && call .venv\Scripts\activate && python -u bullshit_sponge.py > logs\hunter.log 2>&1"
start "" /b cmd /c "cd /d %~dp0 && call .venv\Scripts\activate && python -u bullshit_builder.py > logs\refactoring.log 2>&1"
exit

