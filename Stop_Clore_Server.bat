@echo off
title AI-BS Clore.ai Hosting Agent - Stop ^& Release GPU
color 0C

echo ===================================================
echo       AI-BS CLORE.AI HOSTING SERVER SHUTDOWN
echo ===================================================
echo.

echo [1/3] Stopping clore-hosting.service in WSL2...
wsl.exe -d Ubuntu -u root systemctl stop clore-hosting.service >nul 2>&1

echo [2/3] Terminating any active rental order containers...
wsl.exe -d Ubuntu -u root bash -c "docker stop $(docker ps -q --filter name=clore-) 2>/dev/null || true"

echo [3/3] Verifying GPU Release Status...
echo.
nvidia-smi --query-gpu=name,utilization.gpu,power.draw,memory.used,memory.total,temperature.gpu --format=csv,noheader

echo.
echo ===================================================
echo  [SUCCESS] Clore.ai Hosting Stopped ^& GPU Released!
echo ===================================================
echo.
echo Your RTX 4090 is now completely free for gaming or local compute.
echo To resume hosting later, run: Start_Clore_Server.bat
echo.
pause
