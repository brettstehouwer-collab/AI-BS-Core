# AI-BS Detached Ecosystem Launcher
# Launches all core engines and daemons detached from the calling terminal Job Object

function Start-DetachedProcess {
    param(
        [string]$CommandLine,
        [string]$CurrentDirectory = "C:\AI-BS"
    )
    $res = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $CommandLine
        CurrentDirectory = $CurrentDirectory
    }
    return $res.ProcessId
}

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "       AI-BS DETACHED ECOSYSTEM BOOT SEQUENCE       " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Ollama Instances
Write-Host "[1/6] Launching Ollama Local LLM Engines (Ports 11434 & 11435)..." -ForegroundColor Yellow
$localAppData = $env:LOCALAPPDATA
Start-DetachedProcess -CommandLine "cmd.exe /c set OLLAMA_HOST=127.0.0.1:11434&& set OLLAMA_MODELS=C:\AI-BS\models\ollama&& `"$localAppData\Programs\Ollama\ollama.exe`" serve" -CurrentDirectory "C:\AI-BS"
Start-Sleep -Seconds 1
Start-DetachedProcess -CommandLine "cmd.exe /c set OLLAMA_HOST=127.0.0.1:11435&& set OLLAMA_MODELS=C:\AI-BS\models\ollama&& `"$localAppData\Programs\Ollama\ollama.exe`" serve" -CurrentDirectory "C:\AI-BS"

# 2. ComfyUI
Write-Host "[2/6] Launching ComfyUI Neural Studio (Port 8189)..." -ForegroundColor Yellow
Start-DetachedProcess -CommandLine "C:\AI-BS\ComfyUI\python_embeded\python.exe -s C:\AI-BS\ComfyUI\ComfyUI\main.py --windows-standalone-build --port 8189" -CurrentDirectory "C:\AI-BS\ComfyUI"

# 3. Core Gateways & Backend
Write-Host "[3/6] Launching Core Gateways & Node Backend..." -ForegroundColor Yellow
# Node backend (Port 3001)
Start-DetachedProcess -CommandLine "node.exe server.js" -CurrentDirectory "C:\AI-BS\backend"
# Go Gateway (Port 8000)
Start-DetachedProcess -CommandLine "C:\AI-BS\go-core\aibs_engine.exe" -CurrentDirectory "C:\AI-BS\go-core"
# SHM Telemetry Gateway (Port 8010)
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe shm_websocket_gateway.py" -CurrentDirectory "C:\AI-BS\backend"
# ChromaDB Vector Store (Port 8002)
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\chroma.exe run --path E:\AI_BS_Resources\ChromaDB --port 8002 --host 127.0.0.1" -CurrentDirectory "C:\AI-BS"

# 4. Frontend Web Workstations
Write-Host "[4/6] Launching Frontend Web Workstations (Ports 5173 & 5174)..." -ForegroundColor Yellow
Start-DetachedProcess -CommandLine "cmd.exe /c npm run dev" -CurrentDirectory "C:\AI-BS\frontend"
Start-DetachedProcess -CommandLine "cmd.exe /c npm run dev" -CurrentDirectory "C:\AI-BS\BroadcastStudioApp"

# 5. Core Daemons & Hardware Bridges
Write-Host "[5/6] Launching Core Daemons & Hardware Bridges..." -ForegroundColor Yellow
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe aibs_broadcast_kernel.py" -CurrentDirectory "C:\AI-BS\backend"
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe aibs_broadcast_daemon.py" -CurrentDirectory "C:\AI-BS\backend"
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe aibs_social_daemon.py" -CurrentDirectory "C:\AI-BS\backend"
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe aibs_vst_daemon.py" -CurrentDirectory "C:\AI-BS\backend"
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe aibs_security_watchdog.py" -CurrentDirectory "C:\AI-BS\backend"
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe crypto_trader_bot.py" -CurrentDirectory "C:\AI-BS\backend"
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe theatrical_gateway.py" -CurrentDirectory "C:\AI-BS\NoCo Vision"
Write-Host 'Unreal Pixel Streaming signaling is on demand; use Launch_Unreal_OnDemand.bat for a streaming session.'

Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe gemini_mcp_server.py" -CurrentDirectory "C:\AI-BS\backend"
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe AI_BS_Master_Worker.py" -CurrentDirectory "C:\AI-BS"
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe AI_BS_Universal_Data_Ingestor.py" -CurrentDirectory "C:\AI-BS\backend"
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe aibs_overlay_daemon.py" -CurrentDirectory "C:\AI-BS\backend"
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe pearl_payout_watcher.py" -CurrentDirectory "C:\AI-BS\miners"
Start-DetachedProcess -CommandLine "C:\AI-BS\pyppeteer_env\Scripts\python.exe vast_clore_pearl_watchdog.py" -CurrentDirectory "C:\AI-BS\miners"

# 6. Reverse Proxies & Tunnels
Write-Host "[6/6] Launching Nginx, Cloudflare Tunnel & WSL Services..." -ForegroundColor Yellow
$nginxPath = "C:\Users\footb\AppData\Local\Microsoft\WinGet\Packages\nginxinc.nginx_Microsoft.Winget.Source_8wekyb3d8bbwe\nginx-1.31.3\nginx.exe"
if (Test-Path $nginxPath) {
    Start-DetachedProcess -CommandLine "`"$nginxPath`" -p C:\StehouwerPublishing.com -c nginx.conf" -CurrentDirectory "C:\StehouwerPublishing.com"
}
Start-DetachedProcess -CommandLine "C:\AI-BS\cloudflared.exe tunnel run ai-bs" -CurrentDirectory "C:\AI-BS"

# WSL Services
wsl.exe -d Ubuntu -u root -- systemctl start clore-hosting.service 2>$null
wsl.exe -d Ubuntu -u root -- systemctl start ubuntu-bio-bridge.service 2>$null
wsl.exe -d Ubuntu -u root -- bash -c "systemctl start nginx" 2>$null

Write-Host "All services dispatched." -ForegroundColor Green
