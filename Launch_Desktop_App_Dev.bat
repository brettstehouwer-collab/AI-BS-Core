@echo off
title AI-BS Matrix - Live Desktop Dev Launcher
color 0A

echo ===================================================
echo   AI-BS MATRIX - LIVE DESKTOP DEV WORKSPACE
echo      [Instant Hot-Reload - Zero Repackaging]
echo ===================================================
echo.

set "BASE_DIR=%~dp0"

echo [1/3] Checking Core Ecosystem Services...
call "%BASE_DIR%Launch_AI_BS_Dev.bat"

echo.
echo [2/3] Waiting for Vite Dev Server (Port 5173)...
powershell -Command "$sw=[Diagnostics.Stopwatch]::StartNew(); while (-not (Test-NetConnection 127.0.0.1 -Port 5173 -WarningAction SilentlyContinue).TcpTestSucceeded -and $sw.Elapsed.TotalSeconds -lt 15) { Start-Sleep -s 1 }; if ((Test-NetConnection 127.0.0.1 -Port 5173 -WarningAction SilentlyContinue).TcpTestSucceeded) { Write-Host '[OK] Vite Live HMR Server is ready!' -ForegroundColor Green } else { Write-Host '[INFO] Starting Vite dev server in background...' -ForegroundColor Yellow; Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d %BASE_DIR%frontend && npm run dev' -WindowStyle Hidden; Start-Sleep -s 3 }"

echo.
echo [3/3] Launching Native Desktop App Window in Live Dev Mode...
cd /d "%BASE_DIR%frontend"
start "" npx electron .

echo.
echo ===================================================
echo  READY! Edit any file in VS Code and watch the
echo  Desktop App update in real-time instantly.
echo ===================================================
echo.
timeout /t 3 /nobreak > nul
exit
