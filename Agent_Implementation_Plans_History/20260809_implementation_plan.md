# AI-BS Ecosystem Packaging Plan

Currently, the AI-BS Matrix ecosystem requires running `Launch_AI_BS.bat` from the source directory, which launches dozens of daemons (Python, Go, Node, Ollama, Nginx, Unreal, etc.) manually. The goal is to package the entire ecosystem into a single installable software program (`.exe`) that installs with **Administrator credentials** (as requested), allowing you to specify the installation path (e.g., your `E:\` drive). 

## User Review Required

> [!CAUTION]
> **Massive File Sizes Discovered:**
> I checked the total size of the `C:\AI-BS` folder and it is **788.94 GB**.
> The `E:\` drive currently has **803.31 GB** of free space.
> 
> The top folders consuming space are:
> - `ComfyUI`: 221.40 GB
> - `.ollama`: 189.41 GB
> - `backend` (databases/envs): 119.79 GB
> - `blobs`: 110.59 GB
> - `.git`: 55.16 GB
> - `AI-BS-Models`: 36.35 GB
>
> **Installer Limitation:** It is physically impossible to package 789 GB into a single `.exe` setup file due to Windows executable size limits (usually 4GB limit for standard installers like NSIS). 
> 
> **The Solution (Decoupled Installation):**
> 1. The installer we build will ONLY contain the **Core Application Code** (the compiled React Frontend, the Go Engine, the compiled Python backend, Node services, etc.). This will be around 1-2 GB in size.
> 2. For **Unreal Engine 5.8, ComfyUI, and Ollama**, the installer will NOT bundle them. Instead, after installation, the software will link directly to where they already exist on your system (e.g. hooking into Epic Launcher's Unreal path, and your existing `ComfyUI` / `.ollama` folders). 

## Open Questions

> [!IMPORTANT]
> 1. Does the "Decoupled Installation" approach above work for you? (You install a lightweight AI-BS Software package on your `E:\` drive, and it automatically connects to your existing 221GB ComfyUI and 189GB Ollama models).
> 2. WSL2 Services (`clore-hosting.service`): Since WSL2 is tied to your Windows user account, the installer won't touch it. It will just execute the WSL commands exactly as `Launch_AI_BS.bat` does today. Does this sound correct?

## Proposed Changes

### 1. PyInstaller Backend Compilation
Compile the core Python backend and its dependencies into a standalone executable.
#### [MODIFY] [brain_backend.spec](file:///C:/AI-BS/brain_backend.spec)
- Compile `AI_BS_Backend.py`, `shm_websocket_gateway.py`, etc., without bundling massive databases or vector stores.

### 2. Electron Builder Configuration (Admin Installer)
Configure `electron-builder` in the frontend to bundle the lightweight backend binaries and create an NSIS installer.
#### [MODIFY] [package.json](file:///C:/AI-BS/frontend/package.json)
- Set `nsis.perMachine = true` to install via Administrator privileges.
- Set `nsis.allowToChangeInstallationDirectory = true` so you can select the `E:\` drive during install.
- Bundle the compiled `brain_backend.exe`, `aibs_engine.exe`, and Nginx as `extraResources`.

### 3. Desktop Lifecycle & External Hooks
Update the Electron main process to act as the master supervisor, replacing `Launch_AI_BS.bat`.
#### [MODIFY] [main.js](file:///C:/AI-BS/frontend/electron/main.js)
- Modify `spawnBackend()` to orchestrate the launch of `aibs_engine.exe`, Nginx, and the compiled Python backend.
- Read an `.env` or registry key to locate external dependencies like `C:\Program Files\Epic Games\UE_5.8\Engine\...`, your existing `ComfyUI` path, and `Ollama`.

### 4. Build Pipeline Automation
Create a unified build script to sequence the packaging.
#### [NEW] [build_installer.ps1](file:///C:/AI-BS/build_installer.ps1)
- A master script that:
  1. Compiles the Python backend via PyInstaller.
  2. Compiles the React frontend via Vite.
  3. Packages everything into an `AI-BS-Setup.exe` file via `electron-builder`.

## Verification Plan

### Manual Verification
- Run `build_installer.ps1` to generate `AI-BS-Setup.exe`.
- Ensure the setup file size is manageable (under 2GB).
- Execute the setup file, ensure it asks for Admin credentials and lets you pick the `E:\` drive.
- Launch the installed app and verify that all core services spin up, and it correctly hooks into your existing ComfyUI and Unreal Engine installations.
