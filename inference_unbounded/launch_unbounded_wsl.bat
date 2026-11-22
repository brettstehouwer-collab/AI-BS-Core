@echo off
title AI-BS Unbounded Engine (WSL2 + vLLM + LMCache)
echo =====================================================================
echo  AI-BS Unbounded Engine Launcher (vLLM + LMCache + FastAPI SSE)
echo  NVMe Tier-3 Virtual Memory Offloading | Port 8009 vLLM | Port 8089 API
echo =====================================================================

wsl.exe -d Ubuntu -u root -- bash -c "chmod +x /mnt/c/AI-BS/inference_unbounded/*.sh /mnt/c/AI-BS/inference_unbounded/systemd/*.sh && /mnt/c/AI-BS/inference_unbounded/launch_stack.sh"

pause
