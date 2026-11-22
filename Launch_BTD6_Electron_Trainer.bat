@echo off
title AI-BS Bloons TD 6 Memory Trainer (Electron + Go + React)
cd /d "C:\AI-BS"

echo =================================================================
echo   AI-BS BLOONS TD 6 MEMORY TRAINER (ELECTRON + GO + REACT)
echo =================================================================
echo  Architecture:
echo    - UI: React 19 / TypeScript / Vite (Plitch-Style Cyberpunk Desktop)
echo    - Shell: Electron Frameless Container
echo    - Engine: Native 64-bit Go Daemon (btd6_trainer_daemon.exe)
echo    - Memory: Strict 8-byte/4-byte Alignment, 2MB Chunk Overlap
echo    - IPC: Stdio Line-Delimited JSON Pipeline
echo =================================================================

if exist "C:\AI-BS\trainer_frontend\dist\win-unpacked\trainer_frontend.exe" (
    start "" "C:\AI-BS\trainer_frontend\dist\win-unpacked\trainer_frontend.exe"
) else (
    echo [ERROR] Unpacked Electron binary not found. Running development runner...
    cd /d "C:\AI-BS\trainer_frontend"
    npm run dev
)
