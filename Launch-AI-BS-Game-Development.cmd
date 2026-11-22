@echo off
setlocal
set "AIBS_GAME_TOOLS=%~dp0native_studio\releases\v5.329.144\AI_BS_Studio\AI_BS_Studio.exe"
if not exist "%AIBS_GAME_TOOLS%" (
  echo AI-BS game tools 5.329.144 are missing from:
  echo %AIBS_GAME_TOOLS%
  echo See docs\game_engine\UPDATED_GAME_TOOLS_2026-11-11.md
  pause
  exit /b 1
)
start "AI-BS Game Development" /D "%~dp0" "%AIBS_GAME_TOOLS%" --game-development
exit /b %errorlevel%
