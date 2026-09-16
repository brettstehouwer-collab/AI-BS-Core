# Implementation Plan: BTD6 In-Process Modding Architecture (MelonLoader + BTD Mod Helper)

Deploy the standard community in-process modding architecture for Bloons TD 6 to completely bypass Ninja Kiwi's KonFuze memory encryption, providing 100% reliable in-game cash, monkey money, lives, and tower cost control.

## Background Context
External memory scanners (Cheat Engine, native Win32 ReadProcessMemory/WriteProcessMemory) fail on modern BTD6 because the authoritative simulation cash is managed by the obfuscated `KonFuze` class with dynamic seed arrays. The floating-point addresses detected in user memory are temporary GUI rendering projections that get overwritten every frame. In-process modding via **MelonLoader** hooks directly into `GameAssembly.dll` and IL2CPP, calling `Simulation.AddCash()` natively.

---

## Proposed Changes

### System Runtimes
#### [NEW] .NET Desktop Runtime 6.0 (x64)
- Install `Microsoft.DotNet.DesktopRuntime.6` via `winget` to provide the required IL2CPP runtime for MelonLoader.

### Game Directory Deployment (`E:\SteamLibrary\steamapps\common\BloonsTD6`)
#### [NEW] MelonLoader Core
- Download and unpack `MelonLoader.x64.zip` (v0.7.3) directly into the game root.
- Deploys `version.dll` (proxy DLL) and `MelonLoader/` engine directory.

#### [NEW] BTD Mod Helper (`Mods/Btd6ModHelper.dll`)
- Download and deploy official `Btd6ModHelper.dll` v3.6.8 into `Mods/`.
- Provides the in-game Mod Management UI and native IL2CPP API bindings.

#### [NEW] In-Game Currency & Sandbox Mod (`Mods/Multitool.dll`)
- Download or deploy verified single-player currency and sandbox extension mod.
- Binds direct hotkeys (e.g. `F6` to inject match cash, `F7` for Monkey Money).

---

## Verification Plan

### Automated Verification
- Verify .NET 6.0 Desktop Runtime presence in `C:\Program Files\dotnet`.
- Verify `version.dll` and `MelonLoader` folder exist in `E:\SteamLibrary\steamapps\common\BloonsTD6`.
- Verify `Btd6ModHelper.dll` exists in `E:\SteamLibrary\steamapps\common\BloonsTD6\Mods`.

### In-Game Verification
- Launch Bloons TD 6.
- Confirm MelonLoader console initializes and hooks into `GameAssembly.dll`.
- Verify in-game Mod Helper icon appears on the title screen.
- Enter a match and press the currency hotkey (`F6`) to confirm cash updates instantly without memory scan calibration.
