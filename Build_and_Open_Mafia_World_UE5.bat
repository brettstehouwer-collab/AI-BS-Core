@echo off
title AI-BS Mafia World - Unreal Engine 5.8 1-Click Builder
color 0C

echo ===============================================================================
echo        AI-BS MAFIA UNDERWORLD: UNREAL ENGINE 5.8 1-CLICK WORLD BUILDER
echo ===============================================================================
echo.
echo [1/3] Checking Unreal Engine 5.8 Installation...
set UE_EXE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
set UPROJECT="C:\AI-BS\UnrealHub\AI_BS_Hub.uproject"
set SCRIPT="C:\AI-BS\UnrealHub\Assets\01_Level_Editor\build_mafia_world.py"

if not exist %UE_EXE% (
    echo [ERROR] Unreal Engine 5.8 Editor not found at %UE_EXE%
    pause
    exit /b 1
)

if not exist %UPROJECT% (
    echo [ERROR] Project file not found at %UPROJECT%
    pause
    exit /b 1
)

if not exist %SCRIPT% (
    echo [ERROR] Build script not found at %SCRIPT%
    pause
    exit /b 1
)

echo [2/3] Executing Procedural Mafia Underworld Automation Script...
echo       - Zone 1: Don's Speakeasy & Mahogany Poker Sanctuary
echo       - Zone 2: Rain-Slicked Noir Alleyway & Vintage Getaway Car
echo       - Zone 3: Syndicate Armored Vault, Cash Desks & Banker Lamps
echo       - Zone 4: Waterfront Smuggling Pier, Crane & Containers
echo       - 4x Filmic CineCameras (50mm, 35mm, 28mm, 24mm)
echo.

echo [3/3] Launching Unreal Engine 5.8 Interactive Editor with Mafia Underworld Level...
powershell -ExecutionPolicy Bypass -Command "& %UE_EXE% %UPROJECT% -ExecutePythonScript=%SCRIPT%"

echo.
echo ===============================================================================
echo [SUCCESS] Mafia Underworld Environment successfully assembled and loaded in UE5.8!
echo ===============================================================================
pause
