@echo off
title AI-BS Matrix Launcher
color 0A

echo ===================================================
echo             AI-BS MATRIX BOOT SEQUENCE
echo ===================================================
echo.

set "BASE_DIR=%~dp0"

echo [Pre-Boot] Running Complete Save ^& Shutdown Sequence for a clean slate...
call "%BASE_DIR%Shutdown_AI_BS.bat"
echo.

echo [0/9] Rotating Headless Daemon Logs (Max 50MB ceiling)...
"%BASE_DIR%pyppeteer_env\Scripts\python.exe" "%BASE_DIR%scripts\log_rotator.py"
echo.

echo [1/9] Executing Smart Zombie Node Sweep to reclaim RAM...
"%BASE_DIR%pyppeteer_env\Scripts\python.exe" "%BASE_DIR%backend\zombie_node_cleaner.py"
echo.

echo [1.5/9] Verifying Windows Defender Firewall Streaming ^& Network Access Ports...
powershell -ExecutionPolicy Bypass -File "%BASE_DIR%scripts\open_streaming_firewall_ports.ps1"
echo.

echo [1.8/9] Verifying High-Speed ComfyUI Model Links (D:\AI-BS-ComfyUI-Models)...
if not exist "%BASE_DIR%ComfyUI\ComfyUI\models" (
    if exist "D:\AI-BS-ComfyUI-Models" (
        powershell -ExecutionPolicy Bypass -Command "New-Item -ItemType Junction -Path '%BASE_DIR%ComfyUI\ComfyUI\models' -Target 'D:\AI-BS-ComfyUI-Models' -Force" > nul 2>&1
    )
)
echo.

echo [2/9] Starting All Core Engines Silently in Background...
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
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList '%BASE_DIR%scripts\start_ollama_sovereign.py' -RedirectStandardOutput '%BASE_DIR%logs\start_ollama_sovereign.log' -RedirectStandardError '%BASE_DIR%logs\start_ollama_sovereign.err' -WindowStyle Hidden"

:: Web & Core Server Infrastructure (Bare Minimum Startup)
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'node.exe' -ArgumentList 'server.js' -WorkingDirectory '%BASE_DIR%backend' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'AI_BS_Backend.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\AI_BS_Backend.log' -RedirectStandardError '%BASE_DIR%logs\AI_BS_Backend.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'shm_websocket_gateway.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\shm_websocket_gateway.log' -RedirectStandardError '%BASE_DIR%logs\shm_websocket_gateway.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%go-core\aibs_engine.exe' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'C:\Users\footb\AppData\Local\Microsoft\WinGet\Packages\nginxinc.nginx_Microsoft.Winget.Source_8wekyb3d8bbwe\nginx-1.31.3\nginx.exe' -ArgumentList '-p C:\StehouwerPublishing.com -c C:\StehouwerPublishing.com\nginx.conf' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%vnc_bridge.exe' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'wsl.exe' -ArgumentList '-d Ubuntu -u root -- systemctl start clore-hosting.service' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'wsl.exe' -ArgumentList '-d Ubuntu -u root -- systemctl start ubuntu-bio-bridge.service' -WindowStyle Hidden"
:: NOTE: Host Nginx on Port 80 is handled above on Windows. Redundant WSL Nginx commented out to eliminate Port 80 contention.
:: powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'wsl.exe' -ArgumentList '-d Ubuntu -u root -- bash -c \"systemctl start nginx; sleep infinity\"' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%cloudflared.exe' -ArgumentList 'tunnel run ai-bs' -WindowStyle Hidden"

:: Launch ChromaDB Vector Database on E-Drive (Port 8002)
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\chroma.exe' -ArgumentList 'run --path E:\AI_BS_Resources\ChromaDB --port 8002 --host 127.0.0.1' -WindowStyle Hidden"

:: Launch Vite Web Frontend (Port 5173)
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d %BASE_DIR%frontend && npm run dev' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'gemini_mcp_server.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\gemini_mcp_server.log' -RedirectStandardError '%BASE_DIR%logs\gemini_mcp_server.err' -WindowStyle Hidden"

:: Note: Heavy creative and background engines are now ON-DEMAND to preserve memory:
:: - ComfyUI: Launch_ComfyUI_OnDemand.bat
:: - Unreal Engine: Launch_Unreal_OnDemand.bat
:: - Studio & Broadcast Suite: Launch_Studio_Suite_OnDemand.bat

echo.
echo [3/9] Instant UI Launch...
call :WaitForPort 5173 "Vite Frontend" 10

:: Immediately open native desktop application and browser tabs (Prioritize local C:\AI-BS Executive Studio)
if exist "%BASE_DIR%Launch_Desktop_Studio.vbs" (
    start "" "%BASE_DIR%Launch_Desktop_Studio.vbs"
) else if exist "C:\Program Files\AI-BS Sovereign Studio\Launch_Desktop_Studio.vbs" (
    start "" "C:\Program Files\AI-BS Sovereign Studio\Launch_Desktop_Studio.vbs"
) else if exist "C:\Program Files\AI-BS Sovereign Studio\Launch_Desktop_Studio.bat" (
    start "" "C:\Program Files\AI-BS Sovereign Studio\Launch_Desktop_Studio.bat"
) else if exist "%BASE_DIR%installer\Launch_Desktop_Studio.bat" (
    start "" "%BASE_DIR%installer\Launch_Desktop_Studio.bat"
)

echo.
echo ===================================================
echo   BACKGROUND ENGINE MONITOR (PARALLEL LOADING)
echo ===================================================
call :WaitForPort 8080 "FastAPI Engine" 15
call :WaitForPort 8000 "Go Gateway" 15
call :WaitForPort 8010 "SHM Telemetry Gateway" 15
call :WaitForPort 3001 "Node Backend" 15
call :WaitForPort 11434 "Ollama AI" 15
call :WaitForPort 8002 "ChromaDB E-Drive" 15
call :WaitForPort 8085 "Ubuntu-Bio Bridge" 5
call :WaitForPort 80 "StehouwerPublishing Nginx" 15
call :WaitForPort 8099 "Gemini MCP Server" 15
echo.

echo ===================================================
echo  Bare Minimum Servers Online! Systems On-Demand.
echo ===================================================
ping 127.0.0.1 -n 2 > nul
exit

:: ---------------------------------------------------
:: Subroutine: WaitForPort
:: Polls a specific local TCP port until it becomes active or times out.
:: Usage: call :WaitForPort <Port> <ServiceName> <TimeoutSeconds>
:: ---------------------------------------------------
:WaitForPort
set "PORT=%~1"
set "NAME=%~2"
set "MAXWAIT=%~3"
set "WAIT=0"

:loop
netstat -an | find ":%PORT% " | find "LISTENING" >nul
if %ERRORLEVEL% equ 0 (
    powershell -Command "Write-Host '[OK] %NAME% (%PORT%) is online!' -ForegroundColor Green"
    exit /b
)
powershell -Command "$c = New-Object System.Net.Sockets.TcpClient; try { if ($c.ConnectAsync('127.0.0.1', %PORT%).Wait(300)) { exit 0 } else { exit 1 } } catch { exit 1 } finally { $c.Dispose() }" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    powershell -Command "Write-Host '[OK] %NAME% (%PORT%) is online!' -ForegroundColor Green"
    exit /b
)
ping 127.0.0.1 -n 2 > nul
set /a WAIT+=1
if %WAIT% geq %MAXWAIT% (
    powershell -Command "Write-Host '[WARNING] %NAME% (%PORT%) failed to bind within %MAXWAIT%s. Continuing...' -ForegroundColor Yellow"
    exit /b
)
goto loop
