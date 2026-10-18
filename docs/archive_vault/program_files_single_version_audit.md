# Program Files & Unified Single-Version Architecture Audit

This audit evaluates the 40 directory paths in `C:\Program Files` provided by the operator, confirming that all duplicate and predecessor installations of AI-BS and Broadcast/DAW suites have been eliminated in favor of a **single, unified, up-to-date version**.

---

## 1. The Single Unified Sovereign Suite: `C:\Program Files\AI-BS Sovereign Studio`

| Property | Value / Specification |
| :--- | :--- |
| **Directory Path** | `C:\Program Files\AI-BS Sovereign Studio` |
| **Installed Version** | **`v5.230.1`** (September 9, 2026) |
| **Disk Footprint** | **4.33 GB** |
| **Frontend Distribution** | `frontend_dist` (100% byte-for-byte parity with `C:\AI-BS\frontend\dist` at `v5.230.0`) |
| **Broadcast Distribution** | `broadcast_dist` (Port 5174 dedicated UI) |
| **Broadcast Kernel** | `backend\aibs_broadcast_kernel.py` (Port 8088 DirectX 11 / NVENC engine) |
| **Integrated DAW** | **Wave Studio** (Multi-track linear splicing, 4-stem separation, Tone.js PolySynth, DSP spectral analysis) |
| **Launchers** | `Launch_Desktop_Studio.bat` (Port 5173 Full Suite) & `Launch_Broadcast_Studio.bat` (Port 5174 Broadcast & DAW) |

> [!IMPORTANT]
> **Single Unified Installation Guaranteed:**
> There are no longer multiple competing instances of AI-BS or Broadcast/DAW workstations. All studio, broadcast, and music DAW features are consolidated under this single 4.33 GB directory.

---

## 2. Decommissioned & Excised Duplicate Versions (6.13 GB Total Freed)

1. **`C:\Program Files\AI-BS Matrix` (Legacy Predecessor, v5.133.0):**
   - **Status:** **Completely Removed.**
   - **Reclaimed Storage:** **3.03 GB** restored to Drive C:.
   - **Shortcuts:** `AI-BS Matrix.lnk` pruned from Public and User desktops.
2. **`C:\Program Files\BS-Studio` (Standalone DAW Build, v5.151.0):**
   - **Status:** **Uninstalled.** All Electron binaries, node packages, Python runtime, and app archives removed (freed **3.10 GB**). Directory reduced from 3.10 GB to 0.00 GB (residual 50KB virtualcam DLL flagged for automatic removal on next system restart).
   - **Shortcuts:** `BS-Studio.lnk` pruned from both Public and User desktops.

---

## 3. Categorization of All 40 `C:\Program Files` Directories

### A. AI-BS Sovereign Suite (Active Primary)
- **`AI-BS Sovereign Studio`** (4.33 GB): The sole active primary production installation.

### B. Audio, Music & DAW Production Assets (Used by Sovereign Studio)
- **`Cymatics`** (0.20 GB): Sound banks, acoustic presets, and sample packs referenced by Wave Studio.
- **`Vstplugins`** (0.03 GB): 64-bit VST audio plugin instruments and effects.
- **`MuseScore 4`** (0.40 GB) & **`MuseHub`** (0.14 GB): Notation engine and orchestral sound library.
- **`Audacity`** (0.09 GB) & **`Audacity 4`** (0.24 GB): Standalone waveform editors (v3 stable and v4 beta).

### C. Live Video Ingestion & Streaming Infrastructure
- **`obs-studio`** (0.46 GB): Core OBS Studio installation hooked into AI-BS for virtual camera, game window capture, and RTMP ingestion.
- **`Streamlabs OBS`** (0.97 GB): Third-party Streamlabs desktop software.
- **`TikTok LIVE Studio`** (2.22 GB): Third-party TikTok broadcasting client.

### D. System Runtimes, Compilers & Dev Infrastructure (Mandatory)
- **`Git`**: Version control CLI and Git Bash.
- **`Go`**: Go compiler for `aibs_engine.exe` high-concurrency binary.
- **`nodejs`**: Node.js runtime for `backend/server.js` (Port 8080).
- **`Google`**: Google Chrome browser (linked to Port 9222 developer debugging).
- **`WSL`**: Windows Subsystem for Linux (Ubuntu runtime for Clore, Bio Bridge, and PeakMiner).
- **`Epic Games`**: Unreal Engine 5 installation (Pixel Streaming staging engine).
- **`Tailscale`**: Encrypted peer-to-peer mesh networking.
- **`Certbot`**: Let's Encrypt automated SSL/TLS certificate renewal.
- **`NVIDIA Corporation`**: GPU drivers, NVENC encoders, and CUDA 12.x computing tools.
- **`ASUS`**: ASUS Motherboard utilities & DriverHub.
- **`CPUID`**: Hardware telemetry monitoring (HWMonitor).
- **`Softdeluxe`**: Free Download Manager utility.
- **`Salad`** (0.17 GB): Dormant compute client (service permanently disabled).

### E. Hardware Drivers & Peripherals
- **`Logi`**, **`LogiOptionsPlus`**, **`LogiDownloadAssistant`**: Logitech mouse, keyboard, and peripheral drivers.

### F. Windows 11 Operating System Core Components (Do Not Modify)
- `WindowsApps`, `Common Files`, `Internet Explorer`, `Microsoft GameInput`, `Microsoft`, `Windows Defender`, `Windows Media Player`, `Windows Photo Viewer`, `Windows Mail`, `Windows NT`, `WindowsPowerShell`, `ModifiableWindowsApps`, `Uninstall Information`.

---

## 4. Current Desktop Launcher Inventory (Final Consolidated Topology)

Only the following **6 primary AI-BS icons** reside on the user's desktop:

1. **`AI-BS Sovereign Studio.lnk`** -> `C:\Program Files\AI-BS Sovereign Studio\AI-BS Sovereign Studio.exe` (or `Launch_Desktop_Studio.bat`)
   - *Target:* Full Desktop Suite on Port 5173 (includes full Wave Studio DAW).
2. **`AI-BS Broadcast Studio.lnk`** -> `C:\Program Files\AI-BS Sovereign Studio\Launch_Broadcast_Studio.bat`
   - *Target:* Dedicated Broadcast & Neural DAW Workstation on Port 5174 (Broadcast Kernel on Port 8088).
3. **`AI-BS Matrix Boot.lnk`** -> `C:\AI-BS\Launch_AI_BS.bat`
   - *Target:* Master boot for all 12 core background engines and ports.
4. **`AI-BS Shutdown.lnk`** -> `C:\AI-BS\Shutdown_AI_BS.bat`
   - *Target:* Clean process shutdown releasing all VRAM and port bindings.
5. **`Launch_Unreal_OnDemand.lnk`** -> `C:\AI-BS\Launch_Unreal_OnDemand.bat`
   - *Target:* Headless Unreal Engine 5 Pixel Streaming launcher.
6. **`Start Crypto Swarm.lnk`** -> `C:\AI-BS\Start_Crypto_Swarm.bat`
   - *Target:* Autonomous crypto trading and sovereign Pearl mining launcher.
*(Plus `AI-BS Developer Chrome.lnk` on Port 9222).*
