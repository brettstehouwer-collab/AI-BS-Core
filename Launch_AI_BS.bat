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
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d %BASE_DIR%ComfyUI && run_nvidia_gpu.bat' -WindowStyle Hidden"
:: Minor staggering delay before launching the main backend to let PyTorch allocate VRAM
ping 127.0.0.1 -n 1 > nul
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'node.exe' -ArgumentList 'server.js' -WorkingDirectory '%BASE_DIR%backend' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'AI_BS_Backend.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\AI_BS_Backend.log' -RedirectStandardError '%BASE_DIR%logs\AI_BS_Backend.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'shm_websocket_gateway.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\shm_websocket_gateway.log' -RedirectStandardError '%BASE_DIR%logs\shm_websocket_gateway.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%go-core\aibs_engine.exe' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'C:\Users\footb\AppData\Local\Microsoft\WinGet\Packages\nginxinc.nginx_Microsoft.Winget.Source_8wekyb3d8bbwe\nginx-1.31.3\nginx.exe' -ArgumentList '-p C:\StehouwerPublishing.com -c C:\StehouwerPublishing.com\nginx.conf' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%vnc_bridge.exe' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'wsl.exe' -ArgumentList '-d Ubuntu -u root -- systemctl start clore-hosting.service' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'wsl.exe' -ArgumentList '-d Ubuntu -u root -- systemctl start ubuntu-bio-bridge.service' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'wsl.exe' -ArgumentList '-d Ubuntu -u root -- bash -c \"systemctl start nginx; sleep infinity\"' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%cloudflared.exe' -ArgumentList 'tunnel run ai-bs' -WindowStyle Hidden"

:: Launch ChromaDB Vector Database on E-Drive (Port 8002)
:: Minor staggering delay for ChromaDB initialization
ping 127.0.0.1 -n 1 > nul
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\chroma.exe' -ArgumentList 'run --path E:\AI_BS_Resources\ChromaDB --port 8002 --host 127.0.0.1' -WindowStyle Hidden"

powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d %BASE_DIR%frontend && npm run dev' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d %BASE_DIR%BroadcastStudioApp && npm run dev' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'AI_BS_Unreal_Signaling_Server.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\AI_BS_Unreal_Signaling_Server.log' -RedirectStandardError '%BASE_DIR%logs\AI_BS_Unreal_Signaling_Server.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'gemini_mcp_server.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\gemini_mcp_server.log' -RedirectStandardError '%BASE_DIR%logs\gemini_mcp_server.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'AI_BS_Master_Worker.py' -WorkingDirectory '%BASE_DIR%' -RedirectStandardOutput '%BASE_DIR%logs\AI_BS_Master_Worker.log' -RedirectStandardError '%BASE_DIR%logs\AI_BS_Master_Worker.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'AI_BS_Universal_Data_Ingestor.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\AI_BS_Universal_Data_Ingestor.log' -RedirectStandardError '%BASE_DIR%logs\AI_BS_Universal_Data_Ingestor.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'aibs_broadcast_kernel.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\aibs_broadcast_kernel.log' -RedirectStandardError '%BASE_DIR%logs\aibs_broadcast_kernel.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'aibs_broadcast_daemon.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\aibs_broadcast_daemon.log' -RedirectStandardError '%BASE_DIR%logs\aibs_broadcast_daemon.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'aibs_social_daemon.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\aibs_social_daemon.log' -RedirectStandardError '%BASE_DIR%logs\aibs_social_daemon.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'aibs_overlay_daemon.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\aibs_overlay_daemon.log' -RedirectStandardError '%BASE_DIR%logs\aibs_overlay_daemon.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'aibs_vst_daemon.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\aibs_vst_daemon.log' -RedirectStandardError '%BASE_DIR%logs\aibs_vst_daemon.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'aibs_security_watchdog.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\aibs_security_watchdog.log' -RedirectStandardError '%BASE_DIR%logs\aibs_security_watchdog.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'theatrical_gateway.py' -WorkingDirectory '%BASE_DIR%NoCo Vision' -RedirectStandardOutput '%BASE_DIR%logs\theatrical_gateway.log' -RedirectStandardError '%BASE_DIR%logs\theatrical_gateway.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'crypto_trader_bot.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\crypto_trader_bot.log' -RedirectStandardError '%BASE_DIR%logs\crypto_trader_bot.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'pearl_payout_watcher.py' -WorkingDirectory '%BASE_DIR%miners' -RedirectStandardOutput '%BASE_DIR%logs\pearl_payout_watcher.log' -RedirectStandardError '%BASE_DIR%logs\pearl_payout_watcher.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'vast_clore_pearl_watchdog.py' -WorkingDirectory '%BASE_DIR%miners' -RedirectStandardOutput '%BASE_DIR%logs\vast_clore_pearl_watchdog.log' -RedirectStandardError '%BASE_DIR%logs\vast_clore_pearl_watchdog.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'core\unified_crypto_pearl_watchdog.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\unified_crypto_pearl_watchdog.log' -RedirectStandardError '%BASE_DIR%logs\unified_crypto_pearl_watchdog.err' -WindowStyle Hidden"
:: Unreal Engine is now launched ON-DEMAND via Launch_Unreal_OnDemand.bat to save GPU resources.
:: Run C:\AI-BS\Launch_Unreal_OnDemand.bat when using 3D/Video Studio tools.

echo.
echo [3/9] Instant UI Launch...
call :WaitForPort 5173 "Vite Frontend" 10
call :WaitForPort 5174 "BroadcastStudioApp Vite" 10

:: Immediately open native desktop application and browser tabs
if exist "C:\Program Files\AI-BS Sovereign Studio\Launch_Desktop_Studio.vbs" (
    start "" "C:\Program Files\AI-BS Sovereign Studio\Launch_Desktop_Studio.vbs"
) else if exist "C:\Program Files\AI-BS Sovereign Studio\Launch_Desktop_Studio.bat" (
    start "" "C:\Program Files\AI-BS Sovereign Studio\Launch_Desktop_Studio.bat"
) else if exist "%BASE_DIR%installer\Launch_Desktop_Studio.bat" (
    start "" "%BASE_DIR%installer\Launch_Desktop_Studio.bat"
)
start "" "http://localhost"
start "" "C:\Users\footb\AppData\Local\Programs\Pearl Wallet\Pearl Wallet.exe"
start "" "https://clore.ai/my-servers/detail?name=LINUX_d5d4b81e2bc648be85e47ee0a745969c"

echo.
echo ===================================================
echo   BACKGROUND ENGINE MONITOR (PARALLEL LOADING)
echo ===================================================
call :WaitForPort 8080 "FastAPI Engine" 15
call :WaitForPort 8000 "Go Gateway" 15
call :WaitForPort 8010 "SHM Telemetry Gateway" 15
call :WaitForPort 3001 "Node Backend" 15
call :WaitForPort 11434 "Ollama AI" 15
call :WaitForPort 11435 "Ollama AI E-Drive" 15
call :WaitForPort 8002 "ChromaDB E-Drive" 15
call :WaitForPort 8189 "ComfyUI Renderer" 25
  call :WaitForPort 8888 "Unreal Python Signaling Server" 15
  call :WaitForPort 8085 "Ubuntu-Bio Bridge" 5
  call :WaitForPort 8006 "AI-BS Social Daemon" 5
  call :WaitForPort 8007 "AI-BS Crypto Trader Bot" 10
  call :WaitForPort 80 "StehouwerPublishing Nginx" 15
call :WaitForPort 8099 "Gemini MCP Server" 15
call :WaitForPort 8005 "AI-BS Broadcast Engine" 15
call :WaitForPort 8088 "AI-BS Broadcast Kernel" 15
call :WaitForPort 8013 "AI-BS VST Bridge" 15
call :WaitForPort 8001 "Theatrical Gateway" 15
call :WaitForPort 1935 "WSL RTMP Ingest Server" 10
call :WaitForPort 8089 "WSL HLS Streaming Server" 10
echo.

echo [Final] Pre-warming Stehouwer LLM in RTX 4090 VRAM...
start /b "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" run stehouwer_llm "ping" >nul 2>&1

echo.
echo ===================================================
echo  All systems go! Stehouwer LLM ^& AI-BS Online.
echo ===================================================
ping 127.0.0.1 -n 3 > nul
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
