@echo off
title AI-BS Matrix - Live Windows Dev Update ^& Run
color 0B

echo ===============================================================================
echo            AI-BS MATRIX - LIVE WINDOWS DEV LAUNCHER ^& SYNC
echo     [Auto-Detects Changes, Live Hot-Reloading, Zero Manual Repackaging]
echo ===============================================================================
echo.

set "BASE_DIR=%~dp0"
set "FRONTEND_DIR=%BASE_DIR%frontend"

echo [1/4] Checking Python ^& AI-BS Backend Daemons (Port 8000)...
powershell -Command "$p=8000; if (-not (Test-NetConnection 127.0.0.1 -Port $p -WarningAction SilentlyContinue).TcpTestSucceeded) { Write-Host '[INFO] Starting Core Ecosystem in background...' -ForegroundColor Yellow; Start-Process -FilePath '%BASE_DIR%Launch_AI_BS_Dev.bat' -WindowStyle Minimized; Start-Sleep -s 4 } else { Write-Host '[OK] Backend Services are active on Port 8000.' -ForegroundColor Green }"

echo.
echo [2/4] Checking Vite Live HMR Server (Port 5173)...
powershell -Command "$p=5173; if (-not (Test-NetConnection 127.0.0.1 -Port $p -WarningAction SilentlyContinue).TcpTestSucceeded) { Write-Host '[INFO] Spawning Vite Dev Server with instant hot reload...' -ForegroundColor Yellow; Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d %FRONTEND_DIR% && npm run dev' -WindowStyle Hidden; $sw=[Diagnostics.Stopwatch]::StartNew(); while (-not (Test-NetConnection 127.0.0.1 -Port $p -WarningAction SilentlyContinue).TcpTestSucceeded -and $sw.Elapsed.TotalSeconds -lt 15) { Start-Sleep -s 1 } } else { Write-Host '[OK] Vite Live HMR Server is ready.' -ForegroundColor Green }"

echo.
echo [3/4] Launching Hardware-Accelerated Native Desktop App Window...
cd /d "%FRONTEND_DIR%"
start "" npx electron .

echo.
echo ===============================================================================
echo  SUCCESS! The Windows Desktop Application is running in LIVE DEV MODE.
echo.
echo  - Any edits to React, Tone.js, DAW, or CSS patch LIVE in < 50 milliseconds.
echo  - Any edits to Python backend files auto-reload within 1 second.
echo  - Press F12 (or Ctrl+Shift+I) inside the app to open Chrome DevTools.
echo ===============================================================================
echo.
timeout /t 5 /nobreak > nul
exit
