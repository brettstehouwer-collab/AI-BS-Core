# Forensic Audit: 12 Desktop Shortcuts & Multi-Version Architecture Analysis

This audit examines the 12 shortcuts requested by the operator on `C:\Users\footb\OneDrive\Desktop`, analyzing the exact execution flow when opened, target binaries, version status, and whether underlying installations should be uninstalled to maintain only the latest version of AI-BS, the DAW, and Broadcast Studio.

---

## 1. Granular Breakdown of the 12 Desktop Shortcuts

### #1: `Stehouwer Publishing AI-BS Matrix.lnk`
- **Target Path:** `C:\Program Files\Google\Chrome\Application\chrome_proxy.exe`
- **Arguments:** `--user-data-dir="C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile" --profile-directory=Default --app-id=idemibpphagihbobmgmaojhjfidlfpdl --enable-automation`
- **Working Directory:** `C:\Program Files\Google\Chrome\Application`
- **What It Does When Opened:** 
  Launches Chrome in Progressive Web App (PWA) window mode targeting an older cached app ID (`idemibpphagihbobmgmaojhjfidlfpdl`). Critically, it passes the `--enable-automation` flag.
- **Why It Is Problematic:**
  The `--enable-automation` flag sets `navigator.webdriver = true` and disables Windows DPAPI credential decryption. When the user attempts to log into Google accounts or services, Google's identity servers detect the automated browser and block authentication with *"This browser or app may not be secure"*.
- **Recommendation:** 🗑️ **UNINSTALL / REMOVE FROM DESKTOP**
  - Superseded by `AI-BS Developer Chrome.lnk` on Port 9222 (which suppresses automation flags) and `AI-BS Sovereign Studio.lnk` (the true desktop app). Safely preserved in the backup archive.

---

### #2: `BS-Studio.lnk`
- **Target Path:** `C:\Program Files\BS-Studio\BS-Studio.exe`
- **Arguments:** *(None)*
- **Working Directory:** `C:\Program Files\BS-Studio`
- **What It Does When Opened:** 
  Launches the standalone Electron desktop wrapper for **BS-Studio** (v5.148.0 / v5.151.0, built August 30, 2026). It initializes an isolated audio workstation container containing Tone.js synthesizer engines, sample banks, and dedicated VST3 plugin hooks.
- **Directory Footprint:** `C:\Program Files\BS-Studio` consumes **3.10 GB** of disk space on Drive C:.
- **Recommendation:** 🎛️ **KEEP (IF STANDALONE DAW DESIRED)**
  - This is the dedicated standalone desktop application for music production and audio engineering. 
  - *Alternative Option:* If the operator prefers running the Neural DAW / Wave Studio integrated inside the primary Sovereign Studio (`Launch_Broadcast_Studio.bat` or Port 5173), `C:\Program Files\BS-Studio\Uninstall BS-Studio.exe` can be executed to reclaim **3.10 GB** of storage.

---

### #3: `AI-BS Matrix Boot.lnk`
- **Target Path:** `C:\AI-BS\Launch_AI_BS.bat`
- **Arguments:** *(None)*
- **Working Directory:** `C:\AI-BS`
- **Icon:** `C:\AI-BS\installer\app_icon.ico`
- **What It Does When Opened:** 
  Executes the master cold-boot sequence for the entire sovereign infrastructure:
  1. Executes `Shutdown_AI_BS.bat` to clear port locks and memory.
  2. Runs `zombie_node_cleaner.py` to reclaim RAM.
  3. Verifies Windows Defender firewall streaming ports (1935, 8000, 8080, etc.).
  4. Silently launches all 12 core background engines:
     - Primary Ollama (Port 11434, RTX 4090 high-performance profile).
     - Secondary Ollama (Port 11435).
     - ComfyUI GPU Image Generation (Port 8189).
     - Node.js WebSocket Gateway (Port 8080).
     - Python FastAPI Core Backend (Port 8000).
     - Shared Memory WebSocket Gateway.
     - Go Core Binary (`aibs_engine.exe`).
     - Local Nginx Web Server.
     - VNC Streaming Bridge.
     - WSL2 Ubuntu daemons (`clore-hosting`, `ubuntu-bio-bridge`, `nginx`).
     - Cloudflare Tunnel (`tunnel run ai-bs`).
- **Recommendation:** 🟢 **KEEP (MANDATORY MASTER LAUNCHER)**
  - Essential launcher for development, AI reasoning, and multi-daemon orchestration.

---

### #4: `Launch_Unreal_OnDemand.lnk`
- **Target Path:** `C:\AI-BS\Launch_Unreal_OnDemand.bat`
- **Arguments:** *(None)*
- **Working Directory:** `C:\AI-BS`
- **What It Does When Opened:** 
  Launches Unreal Engine 5 on demand with headless WebRTC Pixel Streaming enabled (`-PixelStreamingIP=127.0.0.1 -PixelStreamingPort=8888 -RenderOffScreen`). Prevents idle VRAM consumption on the RTX 4090 by only spinning up the 3D theatrical staging engine when actively requested.
- **Recommendation:** 🟢 **KEEP**
  - Dedicated utility launcher for virtual production and 3D rendering.

---

### #5: `Launch_AI_BS - Shortcut.lnk`
- **Target Path:** `C:\AI-BS\Launch_AI_BS.bat`
- **Arguments:** *(None)*
- **Working Directory:** `C:\AI-BS`
- **What It Does When Opened:** 
  Executes `Launch_AI_BS.bat` identically to `#3` above.
- **Issue:** 
  Redundant duplicate of `#3` created with Windows' default "- Shortcut" naming convention.
- **Recommendation:** 🗑️ **UNINSTALL / REMOVE FROM DESKTOP**
  - Completely replaced by the cleanly named `#3: AI-BS Matrix Boot.lnk`.

---

### #6: `Start Crypto Swarm.lnk`
- **Target Path:** `C:\AI-BS\Start_Crypto_Swarm.bat`
- **Arguments:** *(None)*
- **Working Directory:** `C:\AI-BS`
- **What It Does When Opened:** 
  Spawns the sovereign crypto mining and automated trading suite:
  1. Clamps RTX 4090 to optimal mining parameters (450W factory TDP / 5001 MHz locked GDDR6X VRAM).
  2. Launches WSL2 PeakMiner hashing to HeroMiners Pearl pool (`us2.pearl.herominers.com:1200`).
  3. Launches the headless payout watcher daemon (`pearl_payout_watcher.py`) logging directly to `aibs_master.db`.
  4. Launches the crypto trade bot on Port 8007.
- **Recommendation:** 🟢 **KEEP**
  - Dedicated launcher for autonomous compute monetization and zero-marginal-cost Pearl generation.

---

### #7: `AI-BS Matrix.lnk`
- **Target Path:** `C:\Program Files\AI-BS Matrix\AI-BS Matrix.exe`
- **Arguments:** *(None)*
- **Working Directory:** `C:\Program Files\AI-BS Matrix`
- **What It Does When Opened:** 
  Targeted an obsolete build of the application dated August 29, 2026 (v5.133.0). It attempted to launch a legacy standalone Electron client with unpatched port mappings and stale dependencies.
- **Status:** 
  The underlying directory `C:\Program Files\AI-BS Matrix` consumed 3.03 GB and was completely superseded by `C:\Program Files\AI-BS Sovereign Studio`. The directory has been removed, freeing 3.03 GB. The target binary no longer exists (`TargetExists: False`).
- **Recommendation:** 🗑️ **UNINSTALL / PURGE SHORTCUT**
  - Broken shortcut pointing to an obsolete, deleted version.

---

### #8: `AI-BS Broadcast Studio.lnk`
- **Target Path:** `C:\Program Files\AI-BS Sovereign Studio\Launch_Broadcast_Studio.bat`
- **Arguments:** *(None)*
- **Working Directory:** `C:\Program Files\AI-BS Sovereign Studio`
- **What It Does When Opened:** 
  Initializes the dedicated **Live Broadcast & Neural DAW Workstation**:
  1. Starts the Broadcast Kernel on Port 8088 (`backend\aibs_broadcast_kernel.py`).
  2. Starts the dedicated Broadcast UI server on Port 5174 (`serve_desktop.py 5174` serving `broadcast_dist\index.html`).
  3. Launches an isolated Edge App mode window at `1600x1000` resolution with independent user profile data (`%LOCALAPPDATA%\AI_BS_Studio\BroadcastProfile`).
- **Recommendation:** 🟢 **KEEP (ACTIVE BROADCAST & DAW LAUNCHER)**
  - This is the official, current launcher for live multi-platform broadcasting and stream control in the Sovereign Studio suite.

---

### #9: `AI-BS Sovereign Studio.lnk`
- **Target Path:** `C:\Program Files\AI-BS Sovereign Studio\AI-BS Sovereign Studio.exe` (or `Launch_Desktop_Studio.bat`)
- **Arguments:** *(None)*
- **Working Directory:** `C:\Program Files\AI-BS Sovereign Studio`
- **What It Does When Opened:** 
  Launches the flagship **AI-BS Sovereign Studio Desktop Suite** (v5.230.1):
  1. Runs `serve_desktop.py 5173` pointing to `frontend_dist` (synchronized today with 100% byte-for-byte parity to `v5.230.0`).
  2. Opens the dedicated standalone studio window.
  3. Provides full operational access to BS-Chat, Stehouwer LLM, ComfyUI Studio, Live Broadcast controls, Wave Studio, Crypto Accounting, and Matrix Health telemetry.
- **Recommendation:** 🟢 **KEEP (PRIMARY DESKTOP SUITE)**
  - This is the most up-to-date, comprehensive desktop installation.

---

### #10: `AI-BS Shutdown.lnk`
- **Target Path:** `C:\AI-BS\Shutdown_AI_BS.bat`
- **Arguments:** *(None)*
- **Working Directory:** `C:\AI-BS`
- **What It Does When Opened:** 
  Performs an immediate, graceful teardown of all background daemons, servers, and bridges:
  - Terminates Python backends (8000, 8006, 8007, 8013, 8088).
  - Terminates Node server (8080).
  - Stops Ollama (11434, 11435) and ComfyUI (8189).
  - Stops Cloudflare Tunnel, Nginx, and VNC bridge.
  - Cleans port locks and releases GPU VRAM cleanly back to the operating system.
- **Recommendation:** 🟢 **KEEP (CLEAN SLATE SHUTDOWN)**
  - Essential operational safety utility.

---

### #11: `Launch_Unreal_OnDemand (2).lnk`
- **Target Path:** `C:\AI-BS\Launch_Unreal_OnDemand.bat`
- **Arguments:** *(None)*
- **What It Does When Opened:** 
  Identical to `#4` (`Launch_Unreal_OnDemand.bat`).
- **Issue:** 
  OneDrive numbered sync collision duplicate created when OneDrive synced file metadata across devices.
- **Recommendation:** 🗑️ **UNINSTALL / REMOVE FROM DESKTOP**
  - Redundant duplicate.

---

### #12: `Launch_AI_BS - Shortcut (2).lnk`
- **Target Path:** `C:\AI-BS\Launch_AI_BS.bat`
- **Arguments:** *(None)*
- **What It Does When Opened:** 
  Identical to `#3` (`Launch_AI_BS.bat`).
- **Issue:** 
  OneDrive numbered sync collision duplicate.
- **Recommendation:** 🗑️ **UNINSTALL / REMOVE FROM DESKTOP**
  - Redundant duplicate.

---

## 2. Directory & Multi-Version Architecture Comparison

### The Three Installation Directories in `C:\Program Files`

| Directory Path | Installed Version | Disk Size | Target Workload | Current Status & Action |
| :--- | :--- | :--- | :--- | :--- |
| **`C:\Program Files\AI-BS Sovereign Studio`** | **`v5.230.1`** (Current) | **4.43 GB** | Full Sovereign Suite + Port 5174 Broadcast & Neural DAW Workstation | 🟢 **ACTIVE & PRIMARY**: Keep intact. Houses both `Launch_Desktop_Studio.bat` (Port 5173) and `Launch_Broadcast_Studio.bat` (Port 5174). |
| **`C:\Program Files\BS-Studio`** | **`v5.148.0`** (Aug 30, 2026) | **3.10 GB** | Standalone Electron Audio DAW & Synthesizer Suite | 🟡 **STANDALONE DAW**: If you want a separate dedicated window just for music/DAW, keep it. If you prefer running audio inside Sovereign Studio, this can be uninstalled to reclaim **3.10 GB**. |
| **`C:\Program Files\AI-BS Matrix`** | **`v5.133.0`** (Aug 29, 2026) | **3.03 GB** | Legacy predecessor app | 🔴 **OBSOLETE**: Completely superseded by Sovereign Studio. Already safely removed, freeing **3.03 GB** on Drive C:. |

### Core Git Repository: `C:\AI-BS`
- Houses the live development codebase (`v5.230.2`), Python virtual environments, miners, and orchestration scripts (`Launch_AI_BS.bat`, `Shutdown_AI_BS.bat`, `Launch_Unreal_OnDemand.bat`, `Start_Crypto_Swarm.bat`).
- This directory is never uninstalled; it is the master source of truth.

---

## 3. Summary: Retained vs Pruned Matrix

| # | Shortcut Name | Proposed Action | Final Target |
| :--- | :--- | :--- | :--- |
| 1 | `Stehouwer Publishing AI-BS Matrix.lnk` | 🗑️ **PRUNE** | Stale PWA with anti-bot `--enable-automation` flag |
| 2 | `BS-Studio.lnk` | 🎛️ **KEEP (or UNINSTALL APP)** | `C:\Program Files\BS-Studio\BS-Studio.exe` (Standalone DAW) |
| 3 | `AI-BS Matrix Boot.lnk` | 🟢 **KEEP** | `C:\AI-BS\Launch_AI_BS.bat` (Master Daemon Boot) |
| 4 | `Launch_Unreal_OnDemand.lnk` | 🟢 **KEEP** | `C:\AI-BS\Launch_Unreal_OnDemand.bat` (Unreal 5 Engine) |
| 5 | `Launch_AI_BS - Shortcut.lnk` | 🗑️ **PRUNE** | Duplicate of #3 |
| 6 | `Start Crypto Swarm.lnk` | 🟢 **KEEP** | `C:\AI-BS\Start_Crypto_Swarm.bat` (Crypto & Mining) |
| 7 | `AI-BS Matrix.lnk` | 🗑️ **PRUNE** | Points to obsolete deleted build (freed 3.03 GB) |
| 8 | `AI-BS Broadcast Studio.lnk` | 🟢 **KEEP** | `C:\Program Files\AI-BS Sovereign Studio\Launch_Broadcast_Studio.bat` (Port 5174) |
| 9 | `AI-BS Sovereign Studio.lnk` | 🟢 **KEEP** | `C:\Program Files\AI-BS Sovereign Studio\AI-BS Sovereign Studio.exe` (Port 5173 v5.230.1) |
| 10 | `AI-BS Shutdown.lnk` | 🟢 **KEEP** | `C:\AI-BS\Shutdown_AI_BS.bat` (Clean Process Shutdown) |
| 11 | `Launch_Unreal_OnDemand (2).lnk` | 🗑️ **PRUNE** | OneDrive collision copy |
| 12 | `Launch_AI_BS - Shortcut (2).lnk` | 🗑️ **PRUNE** | OneDrive collision copy |

---

## 4. Specific Decision on Standalone `BS-Studio` (DAW)

`C:\Program Files\AI-BS Sovereign Studio` already includes the **Broadcast Studio** (Port 5174 / Port 8088) and the full **Wave Studio / Linear Splicing / Neural Audio DAW** (Port 5173).

Do you wish to:
- **Option A (Retain Both):** Keep `BS-Studio.lnk` and `C:\Program Files\BS-Studio` (3.10 GB) as a standalone dedicated DAW workstation alongside Sovereign Studio.
- **Option B (Sovereign Studio Only):** Uninstall `C:\Program Files\BS-Studio` (running its official uninstaller) to reclaim an additional **3.10 GB** of Drive C: space, relying on `Launch_Broadcast_Studio.bat` and Sovereign Studio for all DAW and broadcasting needs.
