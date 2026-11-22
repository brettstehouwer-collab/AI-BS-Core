@echo off
title AI-BS - Engage Game Mode
color 0E
echo ===================================================
echo             AI-BS: ENGAGING GAME MODE
echo ===================================================
echo [1/3] Pausing all active Clore rental containers in WSL2...
wsl.exe -d Ubuntu -u root -- bash -c "docker pause $(docker ps -q --filter name=clore) 2>/dev/null"

echo [2/3] Resetting locked clocks to unlock maximum gaming graphics boost...
nvidia-smi -rmc
nvidia-smi -rgc
nvidia-smi -pl 450

echo [3/3] Trimming Linux cache to maximize available host RAM...
wsl.exe -d Ubuntu -u root -- bash -c "sync; echo 3 > /proc/sys/vm/drop_caches"
wsl.exe -d Ubuntu-24.04 -u root -- bash -c "sync; echo 3 > /proc/sys/vm/drop_caches"

echo.
echo ===================================================
echo  Game Mode Active: RTX 4090 liberated at full 450W.
echo  Run Resume_Clore_After_Gaming.bat when finished!
echo ===================================================
pause
