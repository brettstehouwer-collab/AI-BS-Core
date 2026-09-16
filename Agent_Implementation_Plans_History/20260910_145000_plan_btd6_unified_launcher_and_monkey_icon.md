# Implementation Plan: Unified BTD6 + Trainer 1-Click Launcher & Desktop Monkey Shortcut

## 1. Executive Summary & Value Assessment

> [!NOTE]
> **User Question:** *"would it help to create a BAT file that launches the game with the trainer at the same time to autodetect setting create monkey shoirtcut on desktop?"*

**Yes, creating a unified batch launcher and dedicated desktop shortcut is highly advantageous for three specific reasons:**

1. **Zero-Friction 1-Click Game Launch:** Instead of manually launching Bloons TD 6 on Steam and then finding/running the trainer in a separate window, a single click starts both the game and the trainer together.
2. **Perfect Auto-Detection Synchronization:** Because `launch_btd6_trainer.py` runs a non-blocking continuous polling loop (`psutil` + Win32 snapshot), launching the trainer alongside the game allows it to hook into `BloonsTD6.exe` and `GameAssembly.dll` the millisecond the Unity engine initializes, pre-verifying memory addresses (`0x18de8408443`, `0x18de65357e3`) and projecting the transparent on-screen HUD overlay directly over the game window without user interaction.
3. **Authentic Monkey Desktop Shortcut:** We can extract the official Bloons monkey icon directly from `E:\SteamLibrary\steamapps\common\BloonsTD6\BloonsTD6.exe,0` and deploy a clean shortcut (`Play BTD6 (Monkey Trainer)`) to the Windows Desktop, matching standard native game shortcuts.

---

## 2. Technical Architecture & Proposed Implementation

### 2.1 Unified Launcher Batch Script (`Play_BTD6_With_Trainer.bat`)
Location: [Play_BTD6_With_Trainer.bat](file:///C:/AI-BS/Play_BTD6_With_Trainer.bat)

```cmd
@echo off
title AI-BS Bloons TD 6 + Sovereign Memory Trainer
color 0B

echo ===================================================
echo     LAUNCHING BLOONS TD 6 + AI-BS TRAINER
echo ===================================================
echo.

set "BASE_DIR=%~dp0"
set "BTD6_EXE=E:\SteamLibrary\steamapps\common\BloonsTD6\BloonsTD6.exe"

:: 1. Launch AI-BS Trainer in background/console with Transparent HUD
echo [1/2] Initializing AI-BS BTD6 Memory Trainer (Auto-Detecting)...
start "" "%BASE_DIR%Launch_BTD6_Trainer.bat"

:: 2. Launch Bloons TD 6 via Steam protocol (preferred for Steam Cloud/achievements)
echo [2/2] Launching Bloons TD 6 on Steam...
start steam://rungameid/960090

:: Fallback if Steam URI protocol is unhandled:
timeout /t 2 /nobreak > nul
tasklist /fi "imagename eq BloonsTD6.exe" 2>nul | find /i "BloonsTD6.exe" > nul
if errorlevel 1 (
    if exist "%BTD6_EXE%" (
        echo [Fallback] Direct binary execution...
        start "" "%BTD6_EXE%"
    )
)

echo.
echo ===================================================
echo   GAME AND TRAINER RUNNING IN SYNC.
echo   Press F1 for Cash, F2 for Lives, F6 for HUD.
echo ===================================================
timeout /t 3 > nul
exit
```

### 2.2 Desktop Monkey Shortcut Deployment
We deploy a VBScript/PowerShell helper to generate the `.lnk` file:
- **Shortcut Name:** `Play BTD6 (Monkey Trainer).lnk`
- **Target File:** `C:\AI-BS\Play_BTD6_With_Trainer.bat`
- **Icon Source:** `E:\SteamLibrary\steamapps\common\BloonsTD6\BloonsTD6.exe,0` (extracts the genuine Bloons monkey face icon)
- **Locations:**
  - `C:\Users\footb\Desktop\Play BTD6 (Monkey Trainer).lnk`
  - `C:\Users\footb\OneDrive\Desktop\Play BTD6 (Monkey Trainer).lnk`

---

## 3. Verification Plan

### Manual Verification
1. Run the new batch script: `C:\AI-BS\Play_BTD6_With_Trainer.bat`.
2. Observe Steam launching `BloonsTD6.exe` while `Launch_BTD6_Trainer.bat` simultaneously activates.
3. Confirm that the trainer's continuous auto-detect loop detects the game's PID, locks onto `GameAssembly.dll`, loads presets, and displays the transparent HUD overlay.
4. Verify the monkey icon renders sharply on the Windows Desktop shortcut.

---

## 4. User Confirmation Required

> [!IMPORTANT]
> Under the AI-BS strict manual consent policy, code generation and shortcut creation will pause until you review this plan and provide explicit typed confirmation (e.g. "proceed" or "yes, create it").
