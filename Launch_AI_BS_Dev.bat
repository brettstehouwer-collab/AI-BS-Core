@echo off
title AI-BS Matrix DEV Launcher (Auto-Reload Enabled)
color 0B

echo ===================================================
echo     AI-BS MATRIX FAST DEVELOPMENT BOOT SEQUENCE
echo        [Live Auto-Reload & Watcher Active]
echo ===================================================
echo.

set "BASE_DIR=%~dp0"
set "AIBS_DEV_RELOAD=1"

echo [Pre-Boot] Running Complete Save ^& Shutdown Sequence for a clean slate...
call "%BASE_DIR%Shutdown_AI_BS.bat"
echo.

echo [1/9] Executing Smart Zombie Node Sweep to reclaim RAM...
"%BASE_DIR%pyppeteer_env\Scripts\python.exe" "%BASE_DIR%backend\zombie_node_cleaner.py"
echo.

echo [2/9] Starting All Core Engines in Background...
set CUDA_VISIBLE_DEVICES=0
set OLLAMA_IGPU_ENABLE=0
set OLLAMA_MODELS=E:\AI_BS_Resources\Ollama
set OLLAMA_HOST=0.0.0.0

:: RTX 4090 (24GB VRAM) & Ryzen 9 9950X (32 Threads) High-Performance Sovereign Profile
set OLLAMA_KEEP_ALIVE=15m
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_MAX_LOADED_MODELS=1
set OLLAMA_FLASH_ATTENTION=1

:: Launch background Ollama daemon with verified model directory
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\python.exe' -ArgumentList '%BASE_DIR%scripts\start_ollama_sovereign.py' -WindowStyle Hidden"

powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d %BASE_DIR%ComfyUI && run_nvidia_gpu.bat' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'node.exe' -ArgumentList 'server.js' -WorkingDirectory '%BASE_DIR%backend' -WindowStyle Hidden"

:: Launch FastAPI Backend with UVICORN AUTO-RELOAD (Dedicated Watcher Window)
echo [DEV ENGINE] Spawning FastAPI Live Watcher (auto-reloads on python edits)...
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\python.exe' -ArgumentList 'AI_BS_Backend.py --reload' -WorkingDirectory '%BASE_DIR%backend' -WindowStyle Normal"

powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\python.exe' -ArgumentList 'shm_websocket_gateway.py' -WorkingDirectory '%BASE_DIR%backend' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%go-core\aibs_engine.exe' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'C:\Users\footb\AppData\Local\Microsoft\WinGet\Packages\nginxinc.nginx_Microsoft.Winget.Source_8wekyb3d8bbwe\nginx-1.31.3\nginx.exe' -ArgumentList '-p C:\StehouwerPublishing.com -c C:\StehouwerPublishing.com\nginx.conf' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%vnc_bridge.exe' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'wsl.exe' -ArgumentList '-d Ubuntu -u root -- systemctl start clore-hosting.service' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'wsl.exe' -ArgumentList '-d Ubuntu -u root -- bash /mnt/c/AI-BS/backend/ubuntu_bio_bridge/start_fastapi.sh' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%cloudflared.exe' -ArgumentList 'tunnel run ai-bs' -WindowStyle Hidden"

:: Launch ChromaDB Vector Database on E-Drive (Port 8002)
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\chroma.exe' -ArgumentList 'run --path E:\AI_BS_Resources\ChromaDB --port 8002 --host 127.0.0.1' -WindowStyle Hidden"

:: Launch Vite Frontend Dev Server (HMR enabled)
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d %BASE_DIR%frontend && npm run dev' -WindowStyle Hidden"

powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\python.exe' -ArgumentList 'AI_BS_Unreal_Signaling_Server.py' -WorkingDirectory '%BASE_DIR%backend' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\python.exe' -ArgumentList 'gemini_mcp_server.py' -WorkingDirectory '%BASE_DIR%backend' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\python.exe' -ArgumentList 'aibs_broadcast_daemon.py' -WorkingDirectory '%BASE_DIR%backend' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\python.exe' -ArgumentList 'AI_BS_Master_Worker.py' -WorkingDirectory '%BASE_DIR%' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\python.exe' -ArgumentList 'AI_BS_Universal_Data_Ingestor.py' -WorkingDirectory '%BASE_DIR%backend' -WindowStyle Hidden"

echo.
echo [3/9] Instant UI Launch...
call :WaitForPort 5173 "Vite Frontend" 10

:: Open browser tabs
start "" "http://localhost:5173"
start "" "http://localhost"

echo.
echo ===================================================
echo   BACKGROUND ENGINE MONITOR (DEV AUTO-RELOAD)
echo ===================================================
call :WaitForPort 8080 "FastAPI Engine (Dev Reload)" 15
call :WaitForPort 8000 "Go Gateway" 15
call :WaitForPort 8010 "SHM Telemetry Gateway" 15
call :WaitForPort 3001 "Node Backend" 15
call :WaitForPort 11434 "Ollama AI" 15
call :WaitForPort 11435 "Ollama AI E-Drive" 15
call :WaitForPort 8002 "ChromaDB E-Drive" 15
echo.

echo ===================================================
echo  DEV ENVIRONMENT ONLINE: Code changes auto-reload!
echo ===================================================
timeout /t 3 /nobreak > nul
exit

:: ---------------------------------------------------
:: Subroutine: WaitForPort
:: ---------------------------------------------------
:WaitForPort
set "PORT=%~1"
set "NAME=%~2"
set "MAXWAIT=%~3"
powershell -Command "$p=%PORT%; $t=%MAXWAIT%; $sw=[Diagnostics.Stopwatch]::StartNew(); while (-not (Test-NetConnection 127.0.0.1 -Port $p -WarningAction SilentlyContinue).TcpTestSucceeded -and $sw.Elapsed.TotalSeconds -lt $t) { Start-Sleep -s 1 }; if ($sw.Elapsed.TotalSeconds -ge $t) { Write-Host '[WARNING] %NAME% (%PORT%) failed to bind within %MAXWAIT%s. Continuing...' -ForegroundColor Yellow } else { Write-Host '[OK] %NAME% (%PORT%) is online!' -ForegroundColor Green }"
exit /b
