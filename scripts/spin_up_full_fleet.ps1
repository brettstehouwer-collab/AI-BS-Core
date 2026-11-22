$BASE_DIR = "C:\AI-BS\"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  AI-BS SOVEREIGN MATRIX - FLEET SPIN-UP  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Node Backend (Port 3001)
if (-not (Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue)) {
    Write-Host "[+] Starting Node Backend (3001)..." -ForegroundColor Yellow
    Start-Process -FilePath "node.exe" -ArgumentList "server.js" -WorkingDirectory "$BASE_DIR\backend" -WindowStyle Hidden
}

# 2. ChromaDB (Port 8002)
if (-not (Get-NetTCPConnection -LocalPort 8002 -State Listen -ErrorAction SilentlyContinue)) {
    Write-Host "[+] Starting ChromaDB (8002)..." -ForegroundColor Yellow
    Start-Process -FilePath "$BASE_DIR\pyppeteer_env\Scripts\chroma.exe" -ArgumentList "run --path E:\AI_BS_Resources\ChromaDB --port 8002 --host 127.0.0.1" -WindowStyle Hidden
}

# 3. SHM Telemetry WebSocket Gateway (Port 8010)
if (-not (Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue)) {
    Write-Host "[+] Starting SHM Telemetry Gateway (8010)..." -ForegroundColor Yellow
    Start-Process -FilePath "$BASE_DIR\pyppeteer_env\Scripts\pythonw.exe" -ArgumentList "shm_websocket_gateway.py" -WorkingDirectory "$BASE_DIR\backend" -WindowStyle Hidden
}

# 4. Gemini MCP Server (Port 8099)
if (-not (Get-NetTCPConnection -LocalPort 8099 -State Listen -ErrorAction SilentlyContinue)) {
    Write-Host "[+] Starting Gemini MCP Server (8099)..." -ForegroundColor Yellow
    Start-Process -FilePath "$BASE_DIR\pyppeteer_env\Scripts\pythonw.exe" -ArgumentList "gemini_mcp_server.py" -WorkingDirectory "$BASE_DIR\backend" -WindowStyle Hidden
}

# 5. Crypto Swarm & Scalp Bot (Port 8007)
if (-not (Get-NetTCPConnection -LocalPort 8007 -State Listen -ErrorAction SilentlyContinue)) {
    Write-Host "[+] Starting Crypto Swarm Bot (8007)..." -ForegroundColor Yellow
    Start-Process -FilePath "$BASE_DIR\pyppeteer_env\Scripts\pythonw.exe" -ArgumentList "crypto_trader_bot.py" -WorkingDirectory "$BASE_DIR\backend" -WindowStyle Hidden
}

# 6. Vite Dev Web Frontend (Port 5173)
if (-not (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue)) {
    Write-Host "[+] Starting Vite Frontend (5173)..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d $BASE_DIR\frontend && npm run dev" -WindowStyle Hidden
}

# 7. Studio Broadcast Daemons (Ports 5174, 8005, 8006, 8013, 8088)
Write-Host "[+] Engaging Studio & Broadcast Daemons..." -ForegroundColor Yellow
Start-Process -FilePath "$BASE_DIR\pyppeteer_env\Scripts\pythonw.exe" -ArgumentList "aibs_broadcast_kernel.py" -WorkingDirectory "$BASE_DIR\backend" -WindowStyle Hidden
Start-Process -FilePath "$BASE_DIR\pyppeteer_env\Scripts\pythonw.exe" -ArgumentList "aibs_broadcast_daemon.py" -WorkingDirectory "$BASE_DIR\backend" -WindowStyle Hidden
Start-Process -FilePath "$BASE_DIR\pyppeteer_env\Scripts\pythonw.exe" -ArgumentList "aibs_social_daemon.py" -WorkingDirectory "$BASE_DIR\backend" -WindowStyle Hidden
Start-Process -FilePath "$BASE_DIR\pyppeteer_env\Scripts\pythonw.exe" -ArgumentList "aibs_vst_daemon.py" -WorkingDirectory "$BASE_DIR\backend" -WindowStyle Hidden
if (Test-Path "$BASE_DIR\BroadcastStudioApp") {
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d $BASE_DIR\BroadcastStudioApp && npm run dev" -WindowStyle Hidden
}

# 8. Recreational Debut (Ports 8095 & 5180)
if (Test-Path "C:\Recreational-Debut\backend\main.py") {
    Write-Host "[+] Starting Recreational Debut Backend (8095)..." -ForegroundColor Yellow
    Start-Process -FilePath "$BASE_DIR\pyppeteer_env\Scripts\pythonw.exe" -ArgumentList "main.py" -WorkingDirectory "C:\Recreational-Debut\backend" -WindowStyle Hidden
}
if (Test-Path "C:\Recreational-Debut\frontend\package.json") {
    Write-Host "[+] Starting Recreational Debut Frontend (5180)..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d C:\Recreational-Debut\frontend && npm run dev" -WindowStyle Hidden
}

Start-Sleep -Seconds 5
Write-Host "[OK] Spin-up signals dispatched." -ForegroundColor Green

