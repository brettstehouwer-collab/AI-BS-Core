# AI-BS Sovereign Fast Boot Script
$baseDir = "C:\AI-BS\"
$py = "C:\AI-BS\pyppeteer_env\Scripts\python.exe"
$chroma = "C:\AI-BS\pyppeteer_env\Scripts\chroma.exe"

Write-Host ">>> [1/7] Launching Sovereign Ollama Engine..." -ForegroundColor Cyan
Start-Process -FilePath $py -ArgumentList "scripts\start_ollama_sovereign.py" -WorkingDirectory $baseDir -WindowStyle Hidden

Write-Host ">>> [2/7] Launching ChromaDB Vector Store on Port 8002..." -ForegroundColor Cyan
Start-Process -FilePath $chroma -ArgumentList "run --path E:\AI_BS_Resources\ChromaDB --port 8002 --host 127.0.0.1" -WorkingDirectory $baseDir -WindowStyle Hidden

Write-Host ">>> [3/7] Launching Node Backend on Port 3001..." -ForegroundColor Cyan
Start-Process -FilePath "node.exe" -ArgumentList "server.js" -WorkingDirectory "$baseDir\backend" -WindowStyle Hidden

Write-Host ">>> [4/7] Launching FastAPI Core Backend on Port 8080..." -ForegroundColor Cyan
Start-Process -FilePath $py -ArgumentList "AI_BS_Backend.py" -WorkingDirectory "$baseDir\backend" -WindowStyle Hidden

Write-Host ">>> [5/7] Launching Go Matrix Gateway on Port 8000..." -ForegroundColor Cyan
if (Test-Path "$baseDir\go-core\aibs_engine.exe") {
    Start-Process -FilePath "$baseDir\go-core\aibs_engine.exe" -WorkingDirectory "$baseDir\go-core" -WindowStyle Hidden
}

Write-Host ">>> [6/7] Launching SHM WebSocket Gateway on Port 8010..." -ForegroundColor Cyan
Start-Process -FilePath $py -ArgumentList "shm_websocket_gateway.py" -WorkingDirectory "$baseDir\backend" -WindowStyle Hidden

Write-Host ">>> [7/7] Launching Daemons, Gemini MCP (Port 8099), Broadcast Kernel & Traders..." -ForegroundColor Cyan
Start-Process -FilePath $py -ArgumentList "gemini_mcp_server.py" -WorkingDirectory "$baseDir\backend" -WindowStyle Hidden
Start-Process -FilePath $py -ArgumentList "aibs_broadcast_kernel.py" -WorkingDirectory "$baseDir\backend" -WindowStyle Hidden
Start-Process -FilePath $py -ArgumentList "aibs_broadcast_daemon.py" -WorkingDirectory "$baseDir\backend" -WindowStyle Hidden
Start-Process -FilePath $py -ArgumentList "aibs_social_daemon.py" -WorkingDirectory "$baseDir\backend" -WindowStyle Hidden
Start-Process -FilePath $py -ArgumentList "aibs_vst_daemon.py" -WorkingDirectory "$baseDir\backend" -WindowStyle Hidden
Start-Process -FilePath $py -ArgumentList "crypto_trader_bot.py" -WorkingDirectory "$baseDir\backend" -WindowStyle Hidden

if (Test-Path "$baseDir\cloudflared.exe") {
    Start-Process -FilePath "$baseDir\cloudflared.exe" -ArgumentList "tunnel run ai-bs" -WorkingDirectory $baseDir -WindowStyle Hidden
}

# Launch frontend if not already running on Port 5173
$p5173 = Get-NetTCPConnection -State Listen -LocalPort 5173 -ErrorAction SilentlyContinue
if (-not $p5173) {
    Write-Host ">>> Launching Frontend Vite Dev Server (Port 5173)..." -ForegroundColor Cyan
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d $baseDir\frontend && npm run dev" -WindowStyle Hidden
}

Write-Host "All background engines dispatched successfully!" -ForegroundColor Green
