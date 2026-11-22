@echo off
setlocal
set "AIBS_CHAT=%~dp0native_studio\releases\v5.329.145\AI_BS_Studio\AI_BS_Studio.exe"
if not exist "%AIBS_CHAT%" (
  echo AI-BS chat tools 5.329.145 are missing from:
  echo %AIBS_CHAT%
  pause
  exit /b 1
)
start "AI-BS BS-Chat" /D "%~dp0" "%AIBS_CHAT%" --bs-chat
exit /b %errorlevel%
