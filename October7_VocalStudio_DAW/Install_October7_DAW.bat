@echo off
setlocal DisableDelayedExpansion
title October 7 Vocal Studio - Installer
if not exist "%~dp0Install_Wizard.ps1" (
    echo [ERROR] The supported installer wizard is missing. No fallback install was attempted.
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install_Wizard.ps1"
set "OCTOBER7_INSTALL_RESULT=%ERRORLEVEL%"
if not "%OCTOBER7_INSTALL_RESULT%"=="0" echo [ERROR] Setup did not complete. Review the wizard error.
exit /b %OCTOBER7_INSTALL_RESULT%
