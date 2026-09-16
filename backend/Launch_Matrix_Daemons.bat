@echo off
title AI-BS Matrix Boot Sequence
color 0b

echo Booting the Matrix...

start "Ollama Service" cmd /T:0A /k "ollama serve"
powershell -Command "Start-Sleep -s 2"

start "AI-BS Backend API" cmd /T:0A /k "cd /d %~dp0 && start_server.bat"
powershell -Command "Start-Sleep -s 3"

start "AI-BS Remote Bridge" cmd /T:0A /k "cd /d %~dp0 && call .venv\Scripts\activate && python AI_BS_Remote_Backend.py"
start "AI-BS Bullshit Sponge" cmd /T:0A /k "cd /d %~dp0 && call .venv\Scripts\activate && python bullshit_sponge.py"
start "AI-BS Bullshit Builder" cmd /T:0A /k "cd /d %~dp0 && call .venv\Scripts\activate && python bullshit_builder.py"

exit

