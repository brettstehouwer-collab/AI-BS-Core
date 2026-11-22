# Start Ollama Sovereign Daemon
Set-Item -Path "Env:CUDA_VISIBLE_DEVICES" -Value "0"
Set-Item -Path "Env:OLLAMA_IGPU_ENABLE" -Value "0"
Set-Item -Path "Env:OLLAMA_MODELS" -Value "E:\AI_BS_Resources\Ollama"
Set-Item -Path "Env:OLLAMA_HOST" -Value "127.0.0.1"
Set-Item -Path "Env:OLLAMA_KEEP_ALIVE" -Value "15m"
Set-Item -Path "Env:OLLAMA_NUM_PARALLEL" -Value "1"
Set-Item -Path "Env:OLLAMA_MAX_LOADED_MODELS" -Value "1"
Set-Item -Path "Env:OLLAMA_FLASH_ATTENTION" -Value "1"

Start-Process -FilePath "C:\AI-BS\pyppeteer_env\Scripts\pythonw.exe" -ArgumentList "C:\AI-BS\scripts\start_ollama_sovereign.py" -WindowStyle Hidden
Start-Sleep -Seconds 2

# Start Python FastAPI Backend Engine (Port 8080)
Start-Process -FilePath "C:\AI-BS\backend\.venv\Scripts\python.exe" -ArgumentList "AI_BS_Backend.py" -WorkingDirectory "C:\AI-BS\backend" -WindowStyle Hidden
Start-Sleep -Seconds 3

# Start Cloudflare Tunnel
$env:TUNNEL_ORIGIN_CERT = "C:\Users\footb\.cloudflared\cert.pem"
Start-Process -FilePath "C:\AI-BS\cloudflared.exe" -ArgumentList "--config C:\Users\footb\.cloudflared\config.yml tunnel run ai-bs" -WindowStyle Hidden
Start-Sleep -Seconds 3

