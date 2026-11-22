@echo off
setlocal
set "AI_BS_NATIVE_MANAGE_DAEMONS=false"
set "AI_BS_NATIVE_BACKGROUND_UPDATES=false"
set "AI_BS_NATIVE_EXIT_PROCESS_CLEANUP=false"
set "AIBS_CANDIDATE=%~dp0native_studio\releases\v5.329.148\AI_BS_Studio\AI_BS_Studio.exe"
if not exist "%AIBS_CANDIDATE%" (
  echo AI-BS 5.329.148 candidate is missing from:
  echo %AIBS_CANDIDATE%
  exit /b 1
)
start "AI-BS 148 Candidate - Game Development" /D "%~dp0" "%AIBS_CANDIDATE%" --game-development
exit /b %errorlevel%
