@echo off
title AI-BS Sovereign Studio In-Place Updater
color 0B

echo =========================================================
echo    AI-BS SOVEREIGN STUDIO - IN-PLACE APP UPDATER
echo =========================================================
echo.

:: 1. Detect application installation directory
set "APP_DIR=%~dp0"
set "TARGET_DIR="

if exist "%APP_DIR%AI-BS Sovereign Studio.exe" (
    set "TARGET_DIR=%APP_DIR%"
) else if exist "C:\Program Files\AI-BS Sovereign Studio\AI-BS Sovereign Studio.exe" (
    set "TARGET_DIR=C:\Program Files\AI-BS Sovereign Studio\"
) else if exist "%LOCALAPPDATA%\Programs\AI-BS Sovereign Studio\AI-BS Sovereign Studio.exe" (
    set "TARGET_DIR=%LOCALAPPDATA%\Programs\AI-BS Sovereign Studio\"
) else if exist "C:\AI-BS\frontend\desktop-build\win-unpacked\AI-BS Sovereign Studio.exe" (
    set "TARGET_DIR=C:\AI-BS\frontend\desktop-build\win-unpacked\"
) else (
    set "TARGET_DIR=%APP_DIR%"
)

echo [AI-BS] Target Application Directory: %TARGET_DIR%
echo.

:: 2. Check for Administrator privileges if target is in Program Files
echo %TARGET_DIR% | find /i "Program Files" >nul
if %ERRORLEVEL% equ 0 (
    net session >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [AI-BS] Administrator permissions required to update files in Program Files.
        echo [AI-BS] Elevating updater via Windows UAC...
        powershell -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c `\"\"%~f0\"\"' -Verb RunAs"
        exit /b 0
    )
)

:: 3. Ensure aibs_updater.exe is present
if not exist "%APP_DIR%aibs_updater.exe" (
    if exist "C:\AI-BS\go-core\aibs_updater.exe" (
        copy /y "C:\AI-BS\go-core\aibs_updater.exe" "%APP_DIR%aibs_updater.exe" >nul
    ) else if exist "%TARGET_DIR%aibs_updater.exe" (
        copy /y "%TARGET_DIR%aibs_updater.exe" "%APP_DIR%aibs_updater.exe" >nul
    ) else (
        echo [ERROR] aibs_updater.exe not found.
        pause
        exit /b 1
    )
)

:: 4. Create staging directory in %TEMP%
set "TEMP_DIR=%TEMP%\aibs_update"
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
set "PAYLOAD_ZIP=%TEMP_DIR%\aibs_update_payload.zip"
set "VERSION_JSON=%TEMP_DIR%\version.json"

:: 5. Fetch manifest
echo [AI-BS] Checking for latest release manifest...
powershell -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $wc = New-Object Net.WebClient; $wc.Headers.Add('User-Agent', 'Mozilla/5.0'); try { $wc.DownloadFile('https://ai-bs-dashboard.web.app/updates/version.json', '%VERSION_JSON%') } catch { exit 1 }"

if not exist "%VERSION_JSON%" (
    echo [AI-BS] Cloud manifest fallback: checking local backend on port 8080...
    powershell -ExecutionPolicy Bypass -Command "$wc = New-Object Net.WebClient; $wc.Headers.Add('User-Agent', 'Mozilla/5.0'); try { $wc.DownloadFile('http://127.0.0.1:8080/api/v1/updater/check', '%VERSION_JSON%') } catch { exit 1 }"
)

:: 6. Locate or Download Update Delta Payload (Zip)
if exist "C:\AI-BS\frontend\public\updates\aibs_update_payload.zip" (
    echo [AI-BS] Found local update payload. Staging directly from disk...
    copy /y "C:\AI-BS\frontend\public\updates\aibs_update_payload.zip" "%PAYLOAD_ZIP%" >nul
) else (
    echo [AI-BS] Downloading latest delta payload from Cloudflare tunnel...
    powershell -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $wc = New-Object Net.WebClient; $wc.Headers.Add('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'); try { $wc.DownloadFile('https://api.brettstehouwer.live/api/v1/updater/payload', '%PAYLOAD_ZIP%') } catch { exit 1 }"
    
    if not exist "%PAYLOAD_ZIP%" (
        echo [AI-BS] Tunnel fallback: downloading from local backend (Port 8080)...
        powershell -ExecutionPolicy Bypass -Command "$wc = New-Object Net.WebClient; $wc.Headers.Add('User-Agent', 'Mozilla/5.0'); try { $wc.DownloadFile('http://127.0.0.1:8080/api/v1/updater/payload', '%PAYLOAD_ZIP%') } catch { exit 1 }"
    )
)

if not exist "%PAYLOAD_ZIP%" (
    echo [ERROR] Failed to obtain update payload zip. Please check network connectivity.
    pause
    exit /b 1
)

:: 7. Copy updater to temp so it does not self-lock during overwrites
copy /y "%APP_DIR%aibs_updater.exe" "%TEMP_DIR%\aibs_updater.exe" >nul

:: 8. Terminate running local services and desktop app before patching
echo [AI-BS] Stopping running desktop studio processes for patching...
taskkill /F /IM "AI-BS Sovereign Studio.exe" >nul 2>&1
taskkill /F /IM "serve_desktop.py" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *serve_desktop*" >nul 2>&1

:: 9. Determine relaunch executable
set "RELAUNCH_EXE=AI-BS Sovereign Studio.exe"
if not exist "%TARGET_DIR%AI-BS Sovereign Studio.exe" (
    if exist "%TARGET_DIR%Launch_Desktop_Studio.bat" (
        set "RELAUNCH_EXE=Launch_Desktop_Studio.bat"
    )
)

:: 10. Execute in-place updater
echo [AI-BS] Applying in-place update to %TARGET_DIR%...
echo [AI-BS] Extracting updated files and creating rollback backup...
"%TEMP_DIR%\aibs_updater.exe" -target-dir="%TARGET_DIR%" -payload-zip="%PAYLOAD_ZIP%" -executable="%RELAUNCH_EXE%" -relaunch=true -backup=true

echo.
echo [AI-BS] Update sequence finished successfully.
exit /b 0
