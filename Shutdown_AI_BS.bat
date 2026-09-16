@echo off
title AI-BS Save ^& Shutdown Sequence
color 0C

echo ===================================================
echo           AI-BS SAVE ^& SHUTDOWN SEQUENCE
echo ===================================================
echo.

:: Ensure script executes in the directory it resides in
if exist "%~dp0.git" (
    cd /d "%~dp0"
) else if exist "C:\AI-BS\.git" (
    cd /d "C:\AI-BS"
)

echo [1/3] Saving all workspace changes in Git...
git rev-parse --is-inside-work-tree >nul 2>&1
if %ERRORLEVEL% equ 0 (
    git add -u
    git add backend/ frontend/src/ go-core/ scripts/ docs/ *.md >nul 2>&1
    git diff --cached --quiet || git commit -m "Auto-saved workspace before shutdown"
) else (
    echo [Notice] Git repository not detected or already clean.
)
echo.

echo [2/3] Terminating background server processes...
taskkill /F /IM node.exe /T >nul 2>&1
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM brain_backend.exe /T >nul 2>&1
taskkill /F /IM ollama.exe /T >nul 2>&1
taskkill /F /IM chroma.exe /T >nul 2>&1
taskkill /F /IM daemon_manager.exe /T >nul 2>&1
taskkill /F /IM vnc_bridge.exe /T >nul 2>&1
:: --> New additions for updated Matrix architecture <--
taskkill /F /IM aibs_engine.exe /T >nul 2>&1
taskkill /F /IM cloudflared.exe /T >nul 2>&1
:: --> Addition based on Launch_AI_BS.bat <--
taskkill /F /IM nginx.exe /T >nul 2>&1
taskkill /F /IM "AI-BS Sovereign Studio.exe" /T >nul 2>&1
taskkill /F /IM AI_BS_Hub.exe /T >nul 2>&1
taskkill /F /IM UnrealEditor.exe /T >nul 2>&1
:: Clore.ai Hosting Agent is kept sovereign & running to prevent dropping active GPU rentals
:: To intentionally stop Clore, use Start_Clore_Server.bat or systemctl stop clore-hosting.service directly.
wsl.exe -d Ubuntu -u root -- pkill -f "uvicorn main:app" >nul 2>&1
echo.

echo [3/3] Clearing daemon logs and temporary media files...
:: --> Paths fixed to map to the correct C:\AI-BS\ directory <--
del /F /Q "C:\AI-BS\chroma_daemon.pid" >nul 2>&1
del /F /Q "C:\AI-BS\media_ingest_daemon.pid" >nul 2>&1
del /F /Q "C:\AI-BS\memory_daemon.pid" >nul 2>&1
del /F /Q "C:\AI-BS\trainer_daemon.pid" >nul 2>&1
echo.

echo ===================================================
echo  All systems shut down and saved successfully.
echo ===================================================
ping 127.0.0.1 -n 3 > nul
exit /b
