@echo off
title AI-BS - Resume Clore Compute
color 0A
echo ===================================================
echo       AI-BS: RESUMING CLORE COMPUTE WORKLOADS
echo ===================================================
echo [1/2] Unpausing all Clore rental containers in WSL2...
wsl.exe -d Ubuntu -u root -- bash -c "docker unpause $(docker ps -q --filter name=clore) 2>/dev/null"

echo [2/2] Re-applying 450W TDP and mining memory profile...
call "%~dp0miners\apply_gpu_persistence.bat"

echo.
echo ===================================================
echo  Clore rental computation successfully resumed!
echo ===================================================
pause
