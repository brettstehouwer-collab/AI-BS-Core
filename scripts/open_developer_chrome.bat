@echo off
title AI-BS Developer Chrome (Interactive Authentication Mode)
echo =========================================================================
echo   Launching Developer Chrome in Native Interactive Authentication Mode
echo   Profile Directory: C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile
echo =========================================================================
echo.
echo Launching Chrome without automation flags so Google Sign-In and 2FA succeed...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile" --profile-directory="Default" --no-first-run --no-default-browser-check --disable-blink-features=AutomationControlled "https://accounts.google.com"
