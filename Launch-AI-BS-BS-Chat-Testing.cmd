@echo off
setlocal
set "AI_BS_NATIVE_MANAGE_DAEMONS=false"
set "AI_BS_NATIVE_BACKGROUND_UPDATES=false"
set "AI_BS_NATIVE_EXIT_PROCESS_CLEANUP=false"
set "AIBS_CHAT=%~dp0native_studio\releases\v5.329.173-workshop.7.1-chat-access.1\AI_BS_Studio\AI_BS_Studio.exe"
if not exist "%AIBS_CHAT%" (
  echo BS-Chat testing package is missing at "%AIBS_CHAT%".
  exit /b 1
)
start "AI-BS BS-Chat Testing" /D "%~dp0" "%AIBS_CHAT%" --bs-chat
exit /b %errorlevel%
